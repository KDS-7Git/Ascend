"""Exercise hidden single-user mode and real multi-account security controls."""

import os
import socket
import subprocess
import sys
import time

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

from ascend.application import Tracker
from ascend.engine.packs import dump_toml
from ascend.server.auth import create_user
from ascend.storage import Database

PASSWORD = "a synthetic browser test password"
NEW_PASSWORD = "a different browser test password"


@pytest.fixture
def account_server(tmp_path, pack_data, request):
    mode = getattr(request, "param", "multi")
    db = Database(tmp_path)
    for name in ("alice", "bob"):
        db.user_id = create_user(db, name, PASSWORD, "UTC")
        tracker = Tracker(db)
        tracker.install_pack(dump_toml(pack_data))
        tracker.start_mission("test-pack")
    db.close()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    args = [
        sys.executable,
        "-m",
        "ascend.server",
        "--home",
        str(tmp_path),
        "--port",
        str(port),
        "--auth-mode",
        mode,
    ]
    if mode == "multi":
        args.append("--account-management")
    process = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env={**os.environ, "ASCEND_ACCOUNT_MANAGEMENT": "0"},
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                if httpx.get(url + "/api/health", timeout=1).is_success:
                    break
            except httpx.TransportError:
                if process.poll() is not None:
                    pytest.fail(process.stderr.read().decode())
            time.sleep(0.05)
        else:
            pytest.fail("Isolated account server did not start")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stderr.close()


def browser_login(page, username, password=PASSWORD):
    expect(page.locator("#auth-forms")).to_be_visible()
    page.get_by_label("Username", exact=True).fill(username)
    page.get_by_label("Password", exact=True).fill(password)
    page.locator("#auth-form").get_by_role("button", name="Sign in", exact=True).click()
    expect(page.locator("#auth-forms")).not_to_be_visible()
    expect(page.locator("#profile-link")).to_have_attribute(
        "title", f"{username} · Profile"
    )


@pytest.mark.parametrize("account_server", ["single"], indirect=True)
def test_default_dashboard_stays_logged_in_without_account_controls(account_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(account_server + "/app#profile")
        expect(page.locator("#profile-summary")).to_contain_text(
            "Local learning account"
        )
        expect(page.locator("#account-security")).to_be_hidden()
        expect(page.locator("#login-dialog")).to_be_hidden()
        expect(page.locator("#logout")).to_be_hidden()
        browser.close()


def test_password_controls_and_delayed_old_session_response(account_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(account_server + "/app#profile")
        browser_login(page, "alice")
        expect(page.locator("#account-security")).to_be_visible()
        old = page.evaluate("sessionStorage.getItem('ascend-token')")
        page.get_by_label("Current password", exact=True).fill(PASSWORD)
        page.get_by_label("New password", exact=True).fill(NEW_PASSWORD)
        page.get_by_label("Confirm new password", exact=True).fill(NEW_PASSWORD)
        page.get_by_role("button", name="Change password", exact=True).click()
        expect(page.locator(".account-security-status")).to_contain_text(
            "Password changed"
        )
        assert (
            httpx.get(
                account_server + "/api/account",
                headers={"Authorization": "Bearer " + old},
            ).status_code
            == 401
        )
        expect(page.locator(".account-session")).to_have_count(1)

        # The actual api() helper must ignore an old token's delayed auth failure.
        waiting = []
        page.route("**/api/account?stale-probe=1", lambda route: waiting.append(route))
        with page.expect_request("**/api/account?stale-probe=1"):
            page.evaluate(
                "() => { window.oldSessionRequest = api('account?stale-probe=1').catch(error => error.message); }"
            )
        replacement = httpx.post(
            account_server + "/api/login",
            json={"username": "alice", "password": NEW_PASSWORD},
        ).json()["token"]
        page.evaluate(
            "token => { state.token = token; sessionStorage.setItem('ascend-token', token); }",
            replacement,
        )
        waiting[0].fulfill(
            status=401,
            content_type="application/json",
            body='{"detail":"Login required"}',
        )
        assert "earlier session" in page.evaluate("window.oldSessionRequest")
        expect(page.locator("#login-dialog")).to_be_hidden()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors, errors
        browser.close()


def test_expired_login_cannot_submit_old_notebook_as_another_user(account_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(account_server + "/app#challenge/test-pack%3Aone")
        browser_login(page, "alice")
        page.get_by_role("button", name="Start timed task", exact=True).click()
        expect(page.get_by_label("Your notes", exact=True)).to_be_visible()
        token = page.evaluate("sessionStorage.getItem('ascend-token')")
        httpx.post(
            account_server + "/api/logout", headers={"Authorization": "Bearer " + token}
        ).raise_for_status()
        note = "Alice's private draft belongs only to the account that wrote it."
        page.get_by_label("Your notes", exact=True).fill(note)
        expect(page.locator("#auth-forms")).to_be_visible()
        browser_login(page, "bob")
        page.get_by_role("button", name="Start timed task", exact=True).click()
        expect(page.get_by_label("Your notes", exact=True)).to_have_value("")
        bob = page.evaluate("sessionStorage.getItem('ascend-token')")
        state = httpx.get(
            account_server + "/api/challenges/test-pack:one",
            headers={"Authorization": "Bearer " + bob},
        ).json()
        assert state["work"]["learned"] == ""
        assert note in page.evaluate(
            "localStorage.getItem('ascend-notes:alice:test-pack:one')"
        )
        browser.close()
