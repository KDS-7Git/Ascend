"""Real landing, discovery, login, signup, and recovery journeys in Chromium."""

import os
import json
import re
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

PASSWORD = "a synthetic public browser password"
NEW_PASSWORD = "a new synthetic browser password"


@pytest.fixture
def public_server(tmp_path, pack_data, request):
    mode = getattr(request, "param", "multi")
    db = Database(tmp_path)
    if mode != "single":
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
        "single" if mode == "single" else "multi",
    ]
    if mode != "single":
        args.append("--account-management")
    if mode == "multi":
        args.append("--registration")
    process = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env={
            **os.environ,
            "ASCEND_ACCOUNT_MANAGEMENT": "0",
            "ASCEND_REGISTRATION": "0",
        },
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
            pytest.fail("Isolated website server did not start")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stderr.close()


def login(page, username="alice", password=PASSWORD):
    expect(page.locator("#auth-form")).to_be_visible()
    page.get_by_label("Username", exact=True).fill(username)
    page.get_by_label("Password", exact=True).fill(password)
    page.locator("#auth-form").get_by_role("button", name="Sign in", exact=True).click()
    expect(page.locator("#profile-link")).to_have_attribute(
        "title", f"{username} · Profile"
    )


def assert_fits(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), page.url


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width", [320, 390, 1440])
def test_product_preview_uses_real_curriculum_and_keyboard_controls(
    public_server, width, theme
):
    catalog = httpx.get(public_server + "/api/catalog").json()["tracks"]
    track = httpx.get(public_server + "/api/catalog/devops-service-foundations").json()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": width, "height": 1000},
            color_scheme=theme,
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(public_server)
        expect(page.locator("#product-track-count")).to_have_text(f"{len(catalog):,}")
        expect(page.locator("#product-task-count")).to_have_text(
            f"{sum(item['nodes'] for item in catalog):,}"
        )
        main = [level for level in track["levels"] if level["lane"] == "main"]
        expect(page.locator("#preview-task")).to_have_text(
            main[0]["challenges"][0]["title"]
        )
        palette = page.locator("#preview-description").evaluate("""element => ({
            text:getComputedStyle(element).color,
            background:getComputedStyle(element.closest('.product-task')).backgroundColor
        })""")
        assert contrast_ratio(palette["text"], palette["background"]) >= 4.5
        learn = page.get_by_role("tab", name="Learn", exact=True)
        learn.focus()
        page.keyboard.press("ArrowRight")
        expect(page.get_by_role("tab", name="Practice", exact=True)).to_be_focused()
        expect(page.locator("#preview-practice")).to_be_visible()
        expect(page.locator("#preview-learn")).to_be_hidden()
        page.get_by_role("button", name="Copy example command", exact=True).click()
        expect(page.locator("#preview-copy-status")).to_have_text(
            "Example command copied."
        )
        assert (
            page.evaluate("navigator.clipboard.readText()")
            == "curl -I http://localhost:8080"
        )
        assert_fits(page)
        page.get_by_role("tab", name="Practice", exact=True).focus()
        page.keyboard.press("End")
        expect(page.get_by_role("tab", name="Progress", exact=True)).to_be_focused()
        expect(page.locator("#preview-progress")).to_be_visible()
        expect(page.locator("#preview-level-count")).to_have_text(f"{len(main)} levels")
        expect(page.locator("#preview-path li")).to_have_count(3)
        for index, level in enumerate(main[:3]):
            expect(page.locator("#preview-path li").nth(index)).to_contain_text(
                level["title"]
            )
        assert_fits(page)
        page.keyboard.press("Home")
        expect(learn).to_be_focused()
        expect(page.locator("#preview-learn")).to_be_visible()
        assert not errors, errors
        browser.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width", [390, 1440])
def test_direct_profile_opens_before_deferred_rewards(public_server, width, theme):
    token = httpx.post(
        public_server + "/api/login",
        json={"username": "alice", "password": PASSWORD},
    ).json()["token"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": 1000}, color_scheme=theme
        )
        page.add_init_script(
            "sessionStorage.setItem('ascend-token', " + json.dumps(token) + ")"
        )
        waiting = []
        page.route("**/api/rewards", lambda route: waiting.append(route))
        page.goto(public_server + "/app#profile", wait_until="domcontentloaded")
        expect(page.locator("#profile-preferences")).to_be_visible(timeout=2500)
        expect(page.locator("#app-loader")).to_be_hidden(timeout=2500)
        expect(page.locator("#profile-summary")).to_contain_text("alice")
        expect(page.get_by_label("Timezone", exact=True)).to_have_value("UTC")
        expect(page.locator("#logout")).to_be_visible()
        assert waiting
        waiting.pop().continue_()
        expect(page.locator("#account-security .account-password")).to_be_visible()
        expect(page.locator("#profile")).not_to_have_attribute("aria-busy", "true")
        assert_fits(page)
        browser.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width", [390, 1440])
def test_profile_keeps_controls_and_edits_during_slow_refresh(
    public_server, width, theme
):
    token = httpx.post(
        public_server + "/api/login",
        json={"username": "alice", "password": PASSWORD},
    ).json()["token"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": 1000}, color_scheme=theme
        )
        page.add_init_script(
            "if (location.pathname === '/app') sessionStorage.setItem('ascend-token', "
            + json.dumps(token)
            + ")"
        )
        page.goto(public_server + "/app#today")
        expect(page.locator(".next-card")).to_be_visible()
        expect(page.locator("#app-loader")).to_be_hidden()
        waiting = []
        page.route("**/api/account", lambda route: waiting.append(route))
        page.get_by_role("button", name="Open profile", exact=True).click()
        expect(page.locator("#profile-preferences")).to_be_visible(timeout=1000)
        expect(page.locator("#profile-summary")).to_contain_text("alice")
        expect(page.locator("#logout")).to_be_visible()
        page.get_by_label("Timezone", exact=True).fill("Europe/London")
        page.get_by_label("Private ntfy topic", exact=True).fill(
            "an unsaved reminder preference"
        )
        # Stay beyond the previous skeleton timeout with the request held open.
        page.wait_for_timeout(250)
        expect(page.locator("#profile-preferences")).to_be_visible()
        expect(page.locator("#profile-reminders")).to_be_visible()
        expect(page.locator("#profile")).to_have_attribute("aria-busy", "true")
        assert waiting
        waiting.pop().continue_()
        page.unroute("**/api/account")
        expect(page.locator("#account-security .account-password")).to_be_visible()
        expect(page.locator("#profile")).not_to_have_attribute("aria-busy", "true")
        expect(page.get_by_label("Timezone", exact=True)).to_have_value("Europe/London")
        expect(page.get_by_label("Private ntfy topic", exact=True)).to_have_value(
            "an unsaved reminder preference"
        )
        page.get_by_label("Current password", exact=True).fill(PASSWORD)
        page.get_by_role("button", name="Today", exact=True).click()
        expect(page.locator("#today")).to_be_visible()
        page.get_by_role("button", name="Open profile", exact=True).click()
        expect(page.locator("#profile")).to_be_visible()
        expect(page.locator("#profile")).not_to_have_attribute("aria-busy", "true")
        expect(page.get_by_label("Current password", exact=True)).to_have_value(
            PASSWORD
        )
        page.get_by_role("button", name="Privacy", exact=True).click()
        expect(page.locator("#profile-privacy")).to_be_focused()
        expect(page).to_have_url(public_server + "/app#profile")
        assert_fits(page)

        # Session rotation during refresh must keep controls usable and finish its status.
        page.get_by_role("button", name="Today", exact=True).click()
        expect(page.locator("#today")).to_be_visible()
        page.route("**/api/account", lambda route: waiting.append(route))
        page.get_by_role("button", name="Open profile", exact=True).click()
        expect(page.locator("#profile-status")).to_contain_text("Updating")
        replacement = httpx.post(
            public_server + "/api/login",
            json={"username": "alice", "password": PASSWORD},
        ).json()["token"]
        assert httpx.post(
            public_server + "/api/logout",
            headers={"Authorization": "Bearer " + token},
        ).is_success
        page.evaluate(
            "token => { window.AscendSession.set(token,false); state.token = token; }",
            replacement,
        )
        waiting.pop().continue_()
        page.unroute("**/api/account")
        expect(page.locator("#profile-status")).not_to_contain_text("Updating")
        expect(page.locator("#profile-preferences")).to_be_visible()
        expect(page).to_have_url(public_server + "/app#profile")
        token = replacement

        # A late profile response must not pull a newer navigation back to Profile.
        page.get_by_role("button", name="Today", exact=True).click()
        expect(page.locator("#today")).to_be_visible()
        page.route("**/api/account", lambda route: waiting.append(route))
        page.get_by_role("button", name="Open profile", exact=True).click()
        expect(page.locator("#profile")).to_be_visible()
        expect(page.locator("#profile-status")).to_contain_text("Updating")
        page.get_by_role("button", name="Today", exact=True).click()
        expect(page.locator("#today")).to_be_visible()
        assert waiting
        waiting.pop().continue_()
        page.unroute("**/api/account")
        expect(page.locator("#today")).to_be_visible()
        expect(page.locator("#profile")).to_be_hidden()
        page.locator("#header-logout").click()
        expect(page.locator("#auth-form")).to_be_visible()
        assert page.evaluate("sessionStorage.getItem('ascend-token')") is None
        assert (
            httpx.get(
                public_server + "/api/account",
                headers={"Authorization": "Bearer " + token},
            ).status_code
            == 401
        )
        browser.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width", [320, 390, 1440])
def test_public_header_logout_revokes_remembered_session(public_server, width, theme):
    token = httpx.post(
        public_server + "/api/login",
        json={"username": "alice", "password": PASSWORD},
    ).json()["token"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": 900}, color_scheme=theme
        )
        page.add_init_script(
            "if (location.pathname === '/welcome') localStorage.setItem('ascend-token', "
            + json.dumps(token)
            + ")"
        )
        page.goto(public_server + "/welcome")
        logout = page.get_by_role("button", name="Log out", exact=True)
        expect(logout).to_be_visible()
        assert_fits(page)
        logout.click()
        expect(page.locator("#auth-form")).to_be_visible()
        expect(page.locator("#auth-feedback")).to_contain_text("signed out")
        assert page.evaluate("localStorage.getItem('ascend-token')") is None
        assert (
            httpx.get(
                public_server + "/api/account",
                headers={"Authorization": "Bearer " + token},
            ).status_code
            == 401
        )
        assert_fits(page)
        browser.close()


def contrast_ratio(first, second):
    def luminance(color):
        channels = [int(channel) / 255 for channel in re.findall(r"\d+", color)[:3]]
        linear = [
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return sum(
            value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722))
        )

    dark, light = sorted((luminance(first), luminance(second)))
    return (light + 0.05) / (dark + 0.05)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_auth_hides_logout_after_switching_accounts(public_server, theme):
    token = httpx.post(
        public_server + "/api/login",
        json={"username": "alice", "password": PASSWORD},
    ).json()["token"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 390, "height": 1000}, color_scheme=theme
        )
        page.add_init_script(
            "sessionStorage.setItem('ascend-token', " + json.dumps(token) + ")"
        )
        page.goto(public_server + "/auth")
        expect(page.locator("#auth-session")).to_be_visible()
        expect(page.get_by_role("button", name="Log out", exact=True)).to_be_visible()
        page.get_by_role("button", name="Use another account", exact=True).click()
        expect(page.locator("#auth-form")).to_be_visible()
        expect(page.locator("[data-sign-out]")).to_be_hidden()
        assert page.evaluate("sessionStorage.getItem('ascend-token')") is None
        assert (
            httpx.get(
                public_server + "/api/account",
                headers={"Authorization": "Bearer " + token},
            ).status_code
            == 401
        )
        assert_fits(page)
        browser.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_theme_changes_in_another_tab_update_profile_preferences(public_server, theme):
    token = httpx.post(
        public_server + "/api/login",
        json={"username": "alice", "password": PASSWORD},
    ).json()["token"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 390, "height": 1000}, color_scheme=theme
        )
        page = context.new_page()
        page.add_init_script(
            "sessionStorage.setItem('ascend-token', " + json.dumps(token) + ")"
        )
        page.goto(public_server + "/app#profile")
        expect(page.locator("#profile-preferences")).to_be_visible()
        expect(page.get_by_label("Color theme", exact=True)).to_have_value("system")
        other = context.new_page()
        other.goto(public_server + "/welcome")
        opposite = "light" if theme == "dark" else "dark"
        other.get_by_role(
            "button", name=f"Switch to {opposite} theme", exact=True
        ).click()
        expect(page.locator("html")).to_have_attribute("data-workspace-theme", opposite)
        expect(page.get_by_label("Color theme", exact=True)).to_have_value(opposite)
        page.get_by_label("Color theme", exact=True).select_option(theme)
        expect(other.locator("html")).to_have_attribute("data-workspace-theme", theme)
        expect(page.get_by_label("Color theme", exact=True)).to_have_value(theme)
        assert_fits(page)
        assert_fits(other)
        browser.close()


@pytest.mark.parametrize("width", [320, 390, 820, 1440])
def test_public_discovery_navigation_and_shared_theme(public_server, width, tmp_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(public_server)
        expect(page.locator("#home-heading")).to_be_visible()
        expect(page.locator("#featured-tracks .site-track-card")).to_have_count(3)
        assert_fits(page)
        page.screenshot(
            path=str(tmp_path / f"landing-home-{width}.png"),
            full_page=True,
            animations="disabled",
        )
        if width <= 650:
            page.get_by_role("button", name="Open navigation", exact=True).click()
            expect(
                page.get_by_role("navigation", name="Main navigation")
            ).to_be_visible()
            page.keyboard.press("Escape")
            expect(
                page.get_by_role("button", name="Open navigation", exact=True)
            ).to_be_focused()
        page.get_by_role("button", name="Switch to dark theme", exact=True).click()
        expected = page.evaluate(
            "getComputedStyle(document.documentElement).getPropertyValue('--accent')"
        )
        page.locator(".site-domain-purple").click()
        expect(page.locator("#track-results .site-track-card")).to_have_count(3)
        expect(page.get_by_label("Subject", exact=True)).to_have_value("DevOps")
        assert_fits(page)
        assert (
            page.evaluate(
                "getComputedStyle(document.documentElement).getPropertyValue('--accent')"
            )
            == expected
        )
        page.get_by_label("What would you like to learn?").fill(
            "no-such-learning-track"
        )
        expect(page.locator("#track-results")).to_contain_text("No tracks found.")
        page.get_by_role("button", name="Show all tracks", exact=True).click()
        expect(page.locator("#track-results .site-track-card").first).to_be_visible()
        page.goto(public_server + "/how-it-works")
        expect(page.locator("#how-heading")).to_be_visible()
        page.get_by_text("Is my learning progress private?", exact=True).click()
        expect(page.locator("#questions details[open]")).to_contain_text(
            "Learning histories are scoped to each account"
        )
        assert_fits(page)
        page.goto(public_server + "/privacy")
        expect(page.locator("#privacy-heading")).to_be_visible()
        assert_fits(page)
        page.goto(public_server + "/auth?next=%2Fapp%23profile")
        expect(page.locator("#auth-form")).to_be_visible()
        assert (
            page.evaluate(
                "getComputedStyle(document.documentElement).getPropertyValue('--accent')"
            )
            == expected
        )
        assert_fits(page)
        page.screenshot(
            path=str(tmp_path / f"landing-auth-dark-{width}.png"),
            full_page=True,
            animations="disabled",
        )
        login(page)
        expect(page).to_have_url(public_server + "/app#profile")
        assert (
            page.evaluate(
                "getComputedStyle(document.documentElement).getPropertyValue('--accent')"
            )
            == expected
        )
        assert not errors, errors
        browser.close()


def test_signup_validates_then_returns_to_track_setup_and_remembers_session(
    public_server,
):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 390, "height": 844}, timezone_id="Asia/Kolkata"
        )
        page = context.new_page()
        page.goto(public_server + "/tracks/devops-service-foundations")
        expect(page.locator(".site-detail-levels>li")).to_have_count(8)
        assert_fits(page)
        page.get_by_role("link", name="Add to my tracks", exact=True).click()
        expect(page).to_have_url(re.compile(r"/auth\?next="))
        page.get_by_role("button", name="Create account", exact=True).click()
        page.get_by_label("Username", exact=True).fill("new-learner")
        page.get_by_label("Password", exact=True).fill(PASSWORD)
        page.get_by_label("Confirm password", exact=True).fill("different password")
        page.locator("#auth-form").get_by_role(
            "button", name="Create account", exact=True
        ).click()
        expect(page.get_by_role("alert")).to_contain_text("passwords do not match")
        page.get_by_label("Confirm password", exact=True).fill(PASSWORD)
        page.get_by_label("Remember me on this device").check()
        expect(page.get_by_label("Your timezone", exact=True)).to_have_value(
            "Asia/Kolkata"
        )
        with page.expect_response("**/api/register") as registered:
            page.locator("#auth-form").get_by_role(
                "button", name="Create account", exact=True
            ).click()
        assert registered.value.status == 201, registered.value.text()
        expect(page.locator("#auth-code-result")).to_be_visible()
        assert (
            page.get_by_label("Your recovery code", exact=True)
            .input_value()
            .startswith("ASCEND-")
        )
        with page.expect_download() as downloaded:
            page.get_by_role("button", name="Download code", exact=True).click()
        assert downloaded.value.suggested_filename == "ascend-recovery-new-learner.txt"
        page.get_by_label("I’ve saved my recovery code somewhere safe.").check()
        page.get_by_role("button", name="Continue to workspace", exact=True).click()
        expect(page.locator("#sheet")).to_be_visible()
        expect(page.locator("#catalog-search")).to_have_value(
            "devops-service-foundations"
        )
        page.get_by_role(
            "button",
            name="Install DevOps 1: Service & Deployment Foundations",
            exact=True,
        ).click()
        expect(page.locator("#pack-list")).to_contain_text(
            "DevOps 1: Service & Deployment Foundations"
        )
        token = page.evaluate("localStorage.getItem('ascend-token')")
        assert token and token == page.evaluate(
            "sessionStorage.getItem('ascend-token')"
        )
        page.close()
        page = context.new_page()
        page.goto(public_server + "/app#profile")
        expect(page.locator("#account-security")).to_be_visible()
        page.get_by_label("Current password", exact=True).fill(PASSWORD)
        page.get_by_label("New password", exact=True).fill(NEW_PASSWORD)
        page.get_by_label("Confirm new password", exact=True).fill(NEW_PASSWORD)
        page.get_by_role("button", name="Change password", exact=True).click()
        expect(page.locator(".account-security-status")).to_contain_text(
            "Password changed"
        )
        assert page.evaluate("localStorage.getItem('ascend-token')") != token
        assert (
            httpx.get(
                public_server + "/api/account",
                headers={"Authorization": "Bearer " + token},
            ).status_code
            == 401
        )
        page.locator("#logout").click()
        expect(page.locator("#auth-form")).to_be_visible()
        assert page.evaluate("localStorage.getItem('ascend-token')") is None
        assert page.evaluate("sessionStorage.getItem('ascend-token')") is None
        browser.close()


def test_recovery_replaces_code_and_ends_prior_browser_session(public_server):
    token = httpx.post(
        public_server + "/api/login", json={"username": "alice", "password": PASSWORD}
    ).json()["token"]
    code = httpx.post(
        public_server + "/api/account/recovery-code",
        json={"current_password": PASSWORD},
        headers={"Authorization": "Bearer " + token},
    ).json()["recovery_code"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(public_server + "/auth?mode=recover&next=%2Fapp%23profile")
        expect(page.locator("#auth-form")).to_be_visible()
        page.get_by_label("Username", exact=True).fill("alice")
        page.get_by_label("Recovery code", exact=True).fill("wrong-code")
        page.get_by_label("New password", exact=True).fill(NEW_PASSWORD)
        page.get_by_label("Confirm password", exact=True).fill(NEW_PASSWORD)
        page.get_by_role("button", name="Reset password", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text(
            "Recovery details are incorrect"
        )
        page.get_by_label("Recovery code", exact=True).fill(code)
        page.get_by_role("button", name="Reset password", exact=True).click()
        expect(page.locator("#auth-code-result")).to_be_visible()
        assert page.get_by_label("Your recovery code", exact=True).input_value() != code
        assert_fits(page)
        page.get_by_label("I’ve saved my recovery code somewhere safe.").check()
        page.get_by_role("button", name="Back to sign in", exact=True).click()
        expect(page.get_by_label("Username", exact=True)).to_have_value("alice")
        login(page, password=NEW_PASSWORD)
        expect(page).to_have_url(public_server + "/app#profile")
        assert (
            httpx.get(
                public_server + "/api/account",
                headers={"Authorization": "Bearer " + token},
            ).status_code
            == 401
        )
        assert (
            httpx.post(
                public_server + "/api/recover",
                json={
                    "username": "alice",
                    "recovery_code": code,
                    "new_password": PASSWORD,
                },
            ).status_code
            == 400
        )
        browser.close()


@pytest.mark.parametrize("public_server", ["single", "operator"], indirect=True)
def test_auth_adapts_to_local_or_operator_accounts(public_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(public_server + "/auth")
        if httpx.get(public_server + "/api/site").json()["auth_mode"] == "single":
            expect(page.locator("#auth-local")).to_be_visible()
            expect(page.locator("#auth-forms")).to_be_hidden()
            page.get_by_role("link", name="Open my workspace", exact=True).click()
            expect(page.locator("#today-heading")).to_be_visible()
        else:
            expect(page.locator("#auth-sign-up-tab")).to_be_hidden()
            login(page)
        assert_fits(page)
        browser.close()


def test_bad_login_and_safe_redirect_keep_form_usable(public_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(public_server + "/auth?next=https%3A%2F%2Fexternal.example%2F")
        expect(page.locator("#auth-form")).to_be_visible()
        page.get_by_label("Username", exact=True).fill("alice")
        page.get_by_label("Password", exact=True).fill("incorrect")
        page.locator("#auth-form").get_by_role(
            "button", name="Sign in", exact=True
        ).click()
        expect(page.get_by_role("alert")).to_contain_text(
            "Invalid username or password"
        )
        expect(page.locator("#auth-submit")).to_be_enabled()
        login(page)
        expect(page).to_have_url(public_server + "/app#today")
        browser.close()


def test_missing_recovery_code_has_real_administrator_help(public_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(public_server + "/auth")
        expect(page.locator("#auth-form")).to_be_visible()
        page.get_by_role("link", name="Forgot password?", exact=True).click()
        page.get_by_role(
            "button", name="I don’t have a recovery code", exact=True
        ).click()
        expect(page.locator("#auth-operator-help")).to_be_visible()
        expect(page.locator("#auth-operator-help")).to_contain_text(
            "Your saved learning stays with your account"
        )
        expect(page.locator("#auth-form")).to_be_hidden()
        page.get_by_role("button", name="Back to sign in", exact=True).click()
        login(page)
        assert_fits(page)
        browser.close()


def test_catalog_network_failure_can_be_retried(public_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route("**/api/catalog", lambda route: route.abort())
        page.goto(public_server + "/tracks")
        expect(page.locator("#track-results")).to_contain_text(
            "The server is not responding"
        )
        page.unroute("**/api/catalog")
        page.get_by_role("button", name="Try again", exact=True).click()
        expect(page.locator("#track-results .site-track-card").first).to_be_visible()
        browser.close()


def test_legacy_workspace_bookmark_survives_landing_route(public_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(public_server + "/#profile")
        login(page)
        expect(page).to_have_url(public_server + "/app#profile")
        browser.close()
