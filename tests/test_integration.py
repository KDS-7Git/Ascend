from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from ascend.application import Tracker
from ascend.engine.packs import dump_toml
from ascend.storage import Database


def test_browser_saves_authored_checkpoint_without_completing_task(
    live_server, tmp_path, pack_data
):
    from playwright.sync_api import expect, sync_playwright

    pack_data["node"][0]["checkpoints"] = [
        {
            "id": "compare",
            "title": "Compare one observation",
            "minutes": 10,
            "done_when": "Write down one expected result and compare it with your actual observation.",
            "next_step": "Finish the remaining observations in the parent task.",
        }
    ]
    db = Database(tmp_path / "server")
    t = Tracker(db)
    t.install_pack(dump_toml(pack_data))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(live_server)
        page.get_by_role("button", name="10 min", exact=True).click()
        page.get_by_role("button", name="Open checkpoint", exact=True).click()
        page.get_by_label("What did you observe or learn?", exact=True).fill(
            "The control and the changed input produced different responses."
        )
        page.get_by_label("Minutes spent (optional)", exact=True).fill("8")
        page.get_by_role("button", name="Save checkpoint note", exact=True).click()
        expect(
            page.get_by_text(
                "Partial learning saved. The parent task keeps its own finish line.",
                exact=True,
            )
        ).to_be_visible()
        assert not t.states("test-pack").get("one")
        assert not t.db.rows("task_sessions")
        assert t.entries()[0]["minutes"] == 8
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        browser.close()
    db.close()


@pytest.fixture
def live_server(tmp_path, pack_data):
    home = tmp_path / "server"
    db = Database(home)
    tracker = Tracker(db)
    tracker.install_pack(dump_toml(pack_data))
    tracker.start_mission("test-pack")
    db.close()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "ascend.server",
            "--home",
            str(home),
            "--port",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                with urlopen(url + "/api/health", timeout=1):
                    break
            except (URLError, OSError):
                if process.poll() is not None:
                    pytest.fail(process.stderr.read().decode())
                time.sleep(0.05)
        else:
            pytest.fail("Server did not become healthy")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stderr.close()


def test_remote_cli_uses_only_server_database(live_server, tmp_path):
    client_home = tmp_path / "client"
    env = {**os.environ, "ASCEND_HOME": str(client_home), "ASCEND_SERVER": live_server}
    for args in [
        [],
        ["levels"],
        [
            "done",
            "I proved the remote client shares the same log",
            "Try the browser",
            "--complete",
        ],
        ["stats"],
    ]:
        result = subprocess.run(
            [sys.executable, "-m", "ascend", *args],
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr
    assert not (client_home / "ascend.db").exists()


def test_concurrent_server_writes(live_server):
    import httpx

    def log(i):
        return httpx.post(
            live_server + "/api/entries",
            json={
                "learned": f"I explained independent example number {i}",
                "next_step": "Continue",
            },
        ).status_code

    with ThreadPoolExecutor(max_workers=6) as pool:
        assert list(pool.map(log, range(12))) == [200] * 12
    stats = httpx.get(live_server + "/api/stats").json()
    assert stats["current_streak"] == 1
    assert len(httpx.get(live_server + "/api/entries").json()) == 12


def test_phase_one_database_upgrades_without_losing_entries(tmp_path):
    connection = sqlite3.connect(tmp_path / "ascend.db")
    migrations = Path("ascend/storage/migrations")
    connection.executescript((migrations / "0001_init.sql").read_text())
    connection.executescript((migrations / "0002_packs.sql").read_text())
    connection.executescript(
        "CREATE TABLE schema_version(version INTEGER NOT NULL); INSERT INTO schema_version VALUES (2);"
    )
    connection.execute(
        "INSERT INTO entries(day,logged_at,learned,next_step) VALUES (?,?,?,?)",
        (
            "2026-11-04",
            "2026-11-04T12:00:00+00:00",
            "An original entry before the server upgrade",
            "Next",
        ),
    )
    connection.commit()
    connection.close()
    db = Database(tmp_path)
    assert (
        db.rows("entries")[0]["learned"]
        == "An original entry before the server upgrade"
    )
    assert (
        db.connection.execute("SELECT username FROM users WHERE id=1").fetchone()[0]
        == "local"
    )
    db.close()


@pytest.mark.parametrize("width,height", [(390, 844), (768, 1024), (1440, 1000)])
def test_browser_complete_flow(live_server, width, height, tmp_path):
    from playwright.sync_api import sync_playwright, expect

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(live_server)
        expect(page.locator(".next-card h2")).to_have_text("First task")
        expect(page.locator(".quick-card h2")).to_have_text("Small task")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.get_by_role("button", name="10 min", exact=True).click()
        expect(page.locator(".time-fit-card")).to_be_visible()
        assert int(page.locator(".time-fit-card").get_attribute("data-suggested-minutes")) <= 10
        expect(
            page.get_by_role("button", name="Start guided example", exact=True)
        ).to_be_visible()
        page.get_by_role("button", name="Any time", exact=True).click()
        page.locator(".next-card").get_by_role("button", name="Open challenge").click()
        expect(page.get_by_role("heading", name="Your finish line")).to_have_count(0)
        expect(page.get_by_role("link", name="Learning reference")).to_have_attribute(
            "href", "https://docs.python.org/3/"
        )
        page.get_by_role("button", name="Start timed task", exact=True).click()
        expect(page.get_by_role("heading", name="Your finish line")).to_be_visible()
        expect(page.get_by_role("link", name="Learning reference")).to_have_attribute(
            "href", "https://docs.python.org/3/"
        )
        page.locator(".lab-toolbar").get_by_role(
            "button", name="Notes & evidence", exact=True
        ).click()
        page.get_by_label("Your notes", exact=True).fill(
            "I tested this example and explained why it worked"
        )
        page.get_by_label("Next step", exact=True).fill("Try the second exercise")
        page.locator(".notebook-complete").click()
        expect(page.locator("#sheet")).not_to_be_visible()
        expect(page.locator(".lab-celebration")).to_contain_text("Lab complete!")
        page.get_by_role("button", name="Today", exact=True).click()
        expect(page.locator(".next-card h2")).to_have_text("Second task")
        expect(page.locator(".topbar #streak")).to_have_text("1")
        page.get_by_role("button", name="Path", exact=True).click()
        expect(page.locator(".path-node.done")).to_have_count(1)
        page.get_by_role("button", name="View streak stats: 1 day", exact=True).click()
        page.get_by_label("Search your notes", exact=True).fill("explained")
        page.get_by_role("button", name="Search", exact=True).click()
        expect(page.locator(".search-result")).to_have_count(1)
        page.get_by_role("button", name="Tracks", exact=True).click()
        page.get_by_role("button", name="Open profile", exact=True).click()
        page.get_by_label("Color theme", exact=True).select_option("dark")
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        page.get_by_role("button", name="Tracks", exact=True).click()
        page.get_by_text("Ideas for later", exact=True).click()
        page.get_by_label("An idea for later", exact=True).fill(
            "Try a different topic next month"
        )
        page.get_by_role("button", name="Park it", exact=True).click()
        expect(page.locator("#parked-list")).to_contain_text("different topic")
        page.reload()
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        assert not errors
        browser.close()


def test_browser_guidance_partial_work_and_failed_evidence(
    live_server, pack_data, tmp_path
):
    import httpx
    from playwright.sync_api import sync_playwright, expect

    pack_data["node"][0].update(
        brief="Find the clue hidden in your own tiny experiment.",
        steps=["Make a prediction.", "Compare it with the observed output."],
        hints=["Change one input at a time."],
        verify={"type": "file", "path": str(tmp_path / "missing-evidence.txt")},
    )
    response = httpx.post(
        live_server + "/api/packs",
        files={"file": ("test.toml", dump_toml(pack_data), "text/plain")},
    )
    assert response.status_code == 200
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": 390, "height": 844}, reduced_motion="reduce"
        )
        page.goto(live_server)
        page.get_by_role("button", name="Open challenge", exact=True).click()
        expect(page.locator(".challenge-steps li")).to_have_count(0)
        page.get_by_role("button", name="Start timed task", exact=True).click()
        expect(page.locator(".challenge-steps li")).to_have_count(2)
        expect(
            page.get_by_text("Change one input at a time.", exact=True)
        ).not_to_be_visible()
        page.get_by_text("Hint 1", exact=True).click()
        expect(
            page.get_by_text("Change one input at a time.", exact=True)
        ).to_be_visible()
        page.locator(".lab-toolbar").get_by_role(
            "button", name="Notes & evidence", exact=True
        ).click()
        page.get_by_label("Your notes", exact=True).fill(
            "I compared a prediction with the first observed result"
        )
        page.get_by_role("button", name="Save progress", exact=True).click()
        expect(page.locator(".notebook-status")).to_have_text("Progress saved")
        page.get_by_role("button", name="Today", exact=True).click()
        expect(page.locator(".next-card h2")).to_have_text("First task")
        page.locator(".next-card").get_by_role(
            "button", name="Log progress", exact=True
        ).click()
        expect(page.get_by_label("Your notes", exact=True)).to_have_value("I compared a prediction with the first observed result")
        page.get_by_label("Your notes", exact=True).fill(
            "I tried another input but have not saved the evidence file"
        )
        page.locator(".notebook-complete").click()
        expect(page.locator("#notice")).to_contain_text(
            "Evidence file does not exist"
        )
        expect(page.locator(".lab-celebration")).to_have_count(0)
        page.get_by_role("button", name="Today", exact=True).click()
        expect(page.locator(".next-card h2")).to_have_text("First task")
        assert len(httpx.get(live_server + "/api/entries").json()) == 1
        assert httpx.get(live_server + "/api/challenges/test-pack:one").json()["node"]["status"] == "todo"
        page.get_by_role("button", name="Path", exact=True).click()
        page.locator("#level-second > summary").click()
        page.locator(".path-node.locked").click()
        expect(
            page.locator("#sheet").get_by_role(
                "button", name="Log progress", exact=True
            )
        ).to_have_count(0)
        expect(page.locator(".lock-note")).to_contain_text("previous level")
        browser.close()


def test_browser_skips_do_not_earn_milestones(live_server, pack_data):
    import httpx
    from playwright.sync_api import sync_playwright, expect

    for node in pack_data["node"][:2]:
        node["milestone"] = True
    assert (
        httpx.post(
            live_server + "/api/packs",
            files={"file": ("test.toml", dump_toml(pack_data), "text/plain")},
        ).status_code
        == 200
    )
    for node, status in [("one", "skipped"), ("two", "done")]:
        assert (
            httpx.post(
                live_server + f"/api/nodes/test-pack:{node}/mark",
                json={"status": status},
            ).status_code
            == 200
        )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(live_server)
        expect(
            page.get_by_role("heading", name="Your main path is explored.")
        ).to_be_visible()
        expect(page.locator(".mission-meta")).to_contain_text("50%")
        expect(page.locator(".mission-meta")).to_contain_text(
            "1/2 complete · 1 skipped"
        )
        page.get_by_role("button", name="Stats", exact=True).click()
        expect(page.locator(".earned-badge")).to_have_count(1)
        expect(page.locator(".earned-badge")).to_contain_text("Second task")
        browser.close()


@pytest.mark.parametrize("width,height", [(390, 844), (1440, 1000)])
def test_browser_verified_logging_timer_and_catalog(
    live_server, width, height, tmp_path
):
    import httpx
    from playwright.sync_api import sync_playwright, expect

    def command(argv):
        response = httpx.post(live_server + "/api/command", json={"argv": argv})
        assert response.status_code == 200, response.text
        return response.json()

    command(["pack", "install", "verified-security-lab"])
    command(["mission", "pause"])
    command(["mission", "start", "verified-security-lab"])
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(live_server)
        page.locator(".next-card").get_by_role("button", name="Open challenge").click()
        expect(page.get_by_label("Session target (minutes)")).to_have_value("15")
        expect(
            page.get_by_label("Split into smaller steps (one per line)")
        ).to_have_count(0)
        page.get_by_role("button", name="Start verified exercise").click()
        challenge_url = (
            live_server + "/#challenge/verified-security-lab%3Alab-readiness"
        )
        expect(page).to_have_url(challenge_url)
        expect(page.locator("#sheet")).not_to_be_visible()
        expect(page.locator("#challenge-title")).to_be_visible()
        page.get_by_role("button", name="Send successful request").click()
        page.get_by_role("button", name="Send failed request").click()
        page.wait_for_function("""() => {
            const text = document.querySelector('.lab-data')?.textContent;
            if (!text) return false;
            const marker = [...document.querySelectorAll('#challenge p')].find(p => p.textContent.startsWith('Your exercise marker:'))?.textContent.split(': ')[1];
            return JSON.parse(text).events.some(e => e.marker === marker && e.status >= 400);
        }""")
        import json

        data = json.loads(page.locator(".lab-data").inner_text())
        marker = (
            page.get_by_text("Your exercise marker:").inner_text().split(": ", 1)[1]
        )
        event = next(
            e for e in data["events"] if e["marker"] == marker and e["status"] >= 400
        )
        page.get_by_label("request id", exact=True).fill(event["request_id"])
        endpoint = live_server + "/api/challenges/verified-security-lab:lab-readiness"
        before = httpx.get(endpoint).json()
        page.reload()
        expect(page.locator("#challenge-title")).to_be_visible()
        expect(page.get_by_label("request id", exact=True)).to_have_value(
            event["request_id"]
        )
        restored = httpx.get(endpoint).json()
        assert restored["exercise"]["id"] == before["exercise"]["id"]
        assert restored["exercise"]["data"] == before["exercise"]["data"]
        assert (
            restored["session"]["running_since"] == before["session"]["running_since"]
        )
        expect(
            page.get_by_role("button", name="Pause session", exact=True)
        ).to_have_count(0)
        page.get_by_role("button", name="Open profile", exact=True).click()
        page.get_by_role("button", name="Resume challenge", exact=True).click()
        expect(page).to_have_url(challenge_url)
        expect(page.get_by_label("request id", exact=True)).to_have_value(
            event["request_id"]
        )
        assert httpx.get(endpoint).json()["exercise"]["id"] == before["exercise"]["id"]
        page.get_by_label("errors", exact=True).fill("1")
        page.get_by_role("button", name="Verify my result").click()
        expect(page.get_by_text("✓ Verified. +100 XP.", exact=False)).to_be_visible()
        assert command(["session", "status"])["xp"] == 100
        expect(page.locator("#xp-balance")).to_have_text("100 XP")
        page.screenshot(path=str(tmp_path / f"verified-{width}.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.keyboard.press("Escape")
        page.get_by_role("button", name="Tracks", exact=True).click()
        page.get_by_role("button", name="Browse learning tracks").click()
        page.get_by_label("Search subjects and roles").fill("active directory")
        expect(page.locator(".catalog-card")).to_have_count(1)
        expect(page.locator(".catalog-card h3")).to_contain_text("Active Directory")
        assert not errors
        browser.close()


def test_browser_timed_task_can_only_end_without_awarding_completion(live_server):
    import httpx
    from playwright.sync_api import sync_playwright, expect

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(live_server)
        page.locator(".next-card").get_by_role("button", name="Open challenge").click()
        page.get_by_role("button", name="Start timed task", exact=True).click()
        expect(page).to_have_url(live_server + "/#challenge/test-pack%3Aone")
        expect(page.locator("#sheet")).not_to_be_visible()
        expect(page.get_by_role("heading", name="Your finish line")).to_be_visible()
        page.reload()
        page.get_by_role("button", name="Finish session", exact=True).click()
        page.get_by_role("button", name="End session without completing", exact=True).click()
        expect(page.locator("#task-session")).not_to_be_visible()
        expect(
            page.get_by_role("button", name="End session without completing", exact=True)
        ).not_to_be_visible()
        expect(page.locator("#challenge-content")).to_contain_text("Session ended")
        state = httpx.get(live_server + "/api/challenges/test-pack:one").json()
        assert state["session"]["status"] == "finished"
        assert state["node"]["status"] == "todo"
        session = httpx.post(
            live_server + "/api/command", json={"argv": ["session", "status"]}
        ).json()
        assert session["active"] is None and session["xp"] == 0
        page.reload()
        expect(page.locator("#task-session")).not_to_be_visible()
        expect(page.locator("#challenge-content")).to_contain_text("Session ended")
        browser.close()


@pytest.mark.parametrize("width,height", [(390, 844), (1440, 1000)])
def test_dialog_feedback_stays_visible_and_returns_keyboard_focus(
    live_server, pack_data, tmp_path, width, height
):
    import httpx
    from playwright.sync_api import sync_playwright, expect

    pack_data["node"][0]["verify"] = {
        "type": "file",
        "path": str(tmp_path / "missing-proof.txt"),
    }
    pack_data["node"][0]["requirements"] = (
        "Arrange the required local tools before starting the task. " * 30
    )
    assert (
        httpx.post(
            live_server + "/api/packs",
            files={"file": ("test.toml", dump_toml(pack_data), "text/plain")},
        ).status_code
        == 200
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height}, reduced_motion="reduce"
        )
        page.goto(live_server)
        opener = page.locator(".next-card").get_by_role("button", name="Open challenge")
        opener.click()
        page.locator(".manage-challenge > summary").click()
        # Exercise a preview action; evidence checks require a started workspace.
        page.route(
            "**/api/nodes/*/mark",
            lambda route: route.fulfill(
                status=400,
                content_type="application/json",
                body='{"detail":"Challenge could not be skipped"}',
            ),
        )
        page.get_by_role("button", name="Skip challenge", exact=True).click()
        feedback = page.locator("#sheet .dialog-feedback #notice")
        expect(feedback).to_be_visible()
        expect(feedback).to_have_attribute("role", "alert")
        expect(feedback).to_contain_text("Challenge could not be skipped")
        assert feedback.evaluate(
            "e => { const r=e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight && e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)); }"
        )
        page.clock.install()
        page.clock.fast_forward(9000)
        expect(feedback).to_be_visible()
        close = page.get_by_role("button", name="Close dialog")
        assert close.bounding_box()["y"] >= 0
        page.keyboard.press("Escape")
        expect(page.locator("#sheet")).not_to_be_visible()
        expect(opener).to_be_focused()
        expect(page.locator("#notice")).not_to_be_visible()
        browser.close()


@pytest.mark.parametrize("width,height", [(390, 844), (1440, 1000)])
def test_library_rows_profile_and_guide_navigation(live_server, width, height):
    import httpx
    from playwright.sync_api import sync_playwright, expect

    for pack in ["active-directory-security", "verified-security-lab"]:
        assert (
            httpx.post(
                live_server + "/api/command", json={"argv": ["pack", "install", pack]}
            ).status_code
            == 200
        )
    data = httpx.get(live_server + "/api/packs").json()
    assert next(p for p in data if p["id"] == "active-directory-security")[
        "title"
    ].startswith("Active Directory")
    assert all("path" not in p and "fingerprint" not in p for p in data)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height}, reduced_motion="reduce"
        )
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(live_server + "/#more")
        page.get_by_label("Search installed packs").fill("active directory")
        expect(page.locator(".pack-item")).to_have_count(1)
        row = page.locator(".pack-item")
        title = row.locator(".pack-name").bounding_box()
        read = row.get_by_role("button").bounding_box()
        assert title["y"] >= read["y"] - 8 and title["y"] < read["y"] + read["height"]
        assert title["x"] + title["width"] <= read["x"]
        row.get_by_role("button").click()
        expect(page.locator("#sheet-title")).to_contain_text("Active Directory")
        expect(page.locator(".pack-level")).to_have_count(10)
        page.keyboard.press("Escape")
        page.get_by_role("button", name="Open profile", exact=True).click()
        expect(page.locator("#profile-summary")).to_contain_text("local")
        expect(page.locator("#profile-summary")).to_contain_text("Verified XP")
        page.get_by_label("Color theme").select_option("dark")
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        expect(
            page.locator('#timezone-options option[value="Asia/Kolkata"]')
        ).to_have_count(1)
        page.get_by_label("Timezone", exact=True).fill("UTC+5:30")
        page.get_by_role("button", name="Save timezone").click()
        expect(page.locator("#notice")).to_contain_text("Asia/Kolkata")
        page.get_by_label("Timezone", exact=True).fill("Asia/Kolkata")
        page.get_by_role("button", name="Save timezone").click()
        expect(page.locator("#notice")).to_contain_text("Timezone saved")
        assert (
            httpx.get(live_server + "/api/account").json()["timezone"] == "Asia/Kolkata"
        )
        page.get_by_label("Timezone", exact=True).fill("Europe/London")
        page.get_by_role("button", name="Save timezone").click()
        expect(page.locator("#notice")).to_contain_text("Timezone saved")
        assert (
            httpx.get(live_server + "/api/account").json()["timezone"]
            == "Europe/London"
        )
        page.reload()
        expect(page.locator("#profile-heading")).to_be_visible()
        expect(page.get_by_label("Timezone", exact=True)).to_have_value("Europe/London")
        page.get_by_role("button", name="Docs", exact=True).click()
        expect(page.locator("#guide-title")).to_have_text("Getting started")
        page.evaluate("document.fonts.ready")
        article = page.locator("#docs-article")
        before = article.bounding_box()
        if width <= 1100:
            expect(page.locator("#docs-topics")).not_to_be_visible()
            page.get_by_role("button", name="Guide menu", exact=True).click()
            expect(page.get_by_label("Search documentation")).to_be_focused()
            page.keyboard.press("Shift+Tab")
            expect(page.get_by_role("button", name="Close guide menu")).to_be_focused()
            page.keyboard.press("Escape")
            expect(page.locator("#docs-menu")).not_to_be_visible()
            expect(page.locator("#docs-toggle")).to_be_focused()
            page.get_by_role("button", name="Guide menu", exact=True).click()
        expect(page.locator("#docs-topics")).to_be_visible()
        after = article.bounding_box()
        for key in ["x", "y", "width"]:
            assert abs(before[key] - after[key]) < 1, (key, before, after)
        page.locator("#docs-topics").get_by_role(
            "link", name="Getting started", exact=True
        ).click()
        expect(page.locator("#docs-menu")).not_to_be_visible()
        expect(page.locator("#guide-title")).to_be_focused()
        if width <= 1100:
            page.get_by_role("button", name="Guide menu", exact=True).click()
        before = article.bounding_box()
        page.get_by_label("Search documentation").fill("unmatched-example-123")
        expect(page.locator("#docs-topics")).to_contain_text("No guide matches")
        page.get_by_label("Search documentation").fill("reward declines gradually")
        expect(page.locator("#docs-topics a")).to_have_count(1)
        after = article.bounding_box()
        for key in ["x", "y", "width"]:
            assert abs(before[key] - after[key]) < 1, (key, before, after)
        if width <= 1100:
            page.keyboard.press("Escape")
            expect(page.locator("#docs-menu")).not_to_be_visible()
            expect(page.locator("#docs-toggle")).to_be_focused()
            page.get_by_role("button", name="Guide menu", exact=True).click()
        page.locator("#docs-topics").get_by_role(
            "link", name="Timers & XP", exact=True
        ).click()
        expect(page.locator("#docs-menu")).not_to_be_visible()
        expect(page.locator("#guide-title")).to_have_text("Timers & XP")
        expect(page).to_have_url(live_server + "/#docs/timers")
        expect(page.locator("#docs-article")).to_contain_text("100 XP")
        page.reload()
        expect(page.locator("#guide-title")).to_have_text("Timers & XP")
        expect(page.locator("#xp-balance")).to_have_text("0 XP")
        expect(page.locator(".topbar #streak")).to_have_text("0")
        if width <= 1100:
            page.evaluate("window.scrollTo(0, 160)")
            before = article.bounding_box()
            scroll_before = page.evaluate("scrollY")
            page.locator("#docs-toggle").evaluate("e => e.click()")
            expect(page.locator("#docs-menu")).to_be_visible()
            assert page.evaluate("scrollY") == scroll_before
            assert abs(article.bounding_box()["y"] - before["y"]) < 1
            page.set_viewport_size({"width": 1440, "height": 1000})
            expect(page.locator("#docs-menu")).not_to_be_visible()
            expect(page.locator("#docs-sidebar-slot #docs-topics")).to_be_visible()
            expect(page.locator("#guide-title")).to_be_focused()
            page.set_viewport_size({"width": width, "height": height})
            expect(page.locator("#docs-toggle")).to_be_visible()
            expect(page.locator("#docs-topics")).not_to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors
        browser.close()


@pytest.mark.parametrize("installed_category", [None, "Custom"])
def test_track_picker_groups_existing_packs_from_catalog(
    live_server, installed_category
):
    import httpx
    from playwright.sync_api import sync_playwright, expect

    from ascend.registry import registry_entries

    catalog = registry_entries()
    for pack in catalog:
        response = httpx.post(
            live_server + "/api/command",
            json={"argv": ["pack", "install", pack["id"]]},
        )
        assert response.status_code == 200, response.text

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def legacy_packs(route):
            response = route.fetch()
            packs = response.json()
            for pack in packs:
                pack.pop("category", None)
                if installed_category:
                    pack["category"] = installed_category
            route.fulfill(response=response, json=packs)

        page.route("**/api/packs", legacy_packs)
        page.goto(live_server + "/#more")
        domain = page.get_by_label("Choose a domain", exact=True)
        track = page.get_by_label("Choose a track", exact=True)
        start = page.get_by_role("button", name="Start mission", exact=True)
        expect(domain).to_be_enabled()
        expect(domain.locator("option")).to_have_count(9)

        # The custom fixture stays separate; the 28 known IDs use catalog domains.
        domain.select_option("Custom")
        expect(track.locator("option")).to_have_count(2)
        expect(track.locator('option[value="test-pack"]')).to_have_count(1)
        domain.select_option("Foundations")
        expect(
            track.locator('option[value="ethical-hacking-foundations"]')
        ).to_have_count(1)
        domain.select_option("Offensive")
        expect(
            track.locator('option[value="ethical-hacking-foundations"]')
        ).to_have_count(0)
        expect(track.locator('option[value="api-security"]')).to_have_count(1)
        expect(track.locator("option")).to_have_count(7)
        track.select_option("api-security")
        expect(start).to_be_disabled()

        # Pausing preserves the pending selection; starting uses that exact ID.
        page.get_by_role("button", name="Pause", exact=True).click()
        expect(start).to_be_enabled()
        expect(domain).to_have_value("Offensive")
        expect(track).to_have_value("api-security")
        domain.select_option("Defensive")
        expect(track).to_have_value("")
        expect(start).to_be_disabled()
        track.select_option("soc-analyst")
        start.click()
        expect(page.locator("#notice")).to_contain_text("Mission started.")
        assert (
            httpx.get(live_server + "/api/me").json()["mission"]["pack_id"]
            == "soc-analyst"
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors, errors
        browser.close()


def test_documentation_is_readable_offline_after_shell_install(live_server):
    from playwright.sync_api import sync_playwright, expect

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        page.goto(live_server + "/#docs/verification")
        expect(page.locator("#guide-title")).to_have_text("Evidence & verification")
        page.evaluate(
            'navigator.serviceWorker.ready.then(() => new Promise(resolve => navigator.serviceWorker.controller ? resolve() : navigator.serviceWorker.addEventListener("controllerchange", resolve, {once:true})))'
        )
        context.set_offline(True)
        page.reload()
        expect(page.locator("#guide-title")).to_have_text("Evidence & verification")
        expect(page.locator("#login-dialog")).not_to_be_visible()
        expect(page.locator("#xp-balance")).to_have_text("— XP")
        expect(page.locator(".topbar #streak")).to_have_text("—")
        assert page.evaluate("Boolean(window.AscendMotion)")
        browser.close()


def test_motion_controls_persist_and_honor_device_preferences(live_server):
    from playwright.sync_api import sync_playwright, expect

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000}, reduced_motion="no-preference"
        )
        page.goto(live_server)
        page.locator(".next-card").wait_for()
        page.wait_for_function(
            "document.querySelector('.ambient-scene').getAnimations({subtree:true}).some(a => a.playState === 'running')"
        )
        page.locator(".next-card").hover(position={"x": 180, "y": 80})
        expect(page.locator(".next-card .hover-light")).to_be_visible()
        page.locator(".page-header h1").first.hover()
        expect(page.locator(".workspace-hover")).to_have_class(
            "hover-light workspace-hover pointer-present"
        )
        assert (
            page.locator(".next-card").evaluate("e => getComputedStyle(e).cursor")
            != "none"
        )
        expect(page.locator("#motion-toggle")).to_have_count(0)
        page.get_by_role("button", name="Open profile", exact=True).click()
        page.get_by_label("Motion effects", exact=True).select_option("off")
        expect(page.locator("html")).to_have_attribute("data-motion", "off")
        assert not page.locator(".ambient-scene").evaluate(
            "e => e.getAnimations({subtree:true}).some(a => a.playState === 'running')"
        )
        page.reload()
        expect(page.get_by_label("Motion effects", exact=True)).to_have_value("off")
        page.get_by_label("Motion effects", exact=True).select_option("calm")
        expect(page.locator("html")).to_have_attribute("data-motion", "calm")
        page.emulate_media(reduced_motion="reduce")
        expect(page.locator("html")).to_have_attribute("data-motion", "off")
        expect(page.locator("#motion-toggle")).to_have_count(0)
        page.get_by_role("button", name="Docs", exact=True).click()
        expect(page.locator("#guide-title")).to_be_visible()
        assert not page.locator("#docs").evaluate(
            "e => e.getAnimations({subtree:true}).some(a => a.playState === 'running')"
        )
        page.emulate_media(reduced_motion="no-preference")
        expect(page.locator("html")).to_have_attribute("data-motion", "calm")
        browser.close()


@pytest.mark.parametrize("width,height", [(320, 480), (1440, 1000)])
def test_challenge_glow_plays_once_when_visible_per_load(live_server, width, height):
    from playwright.sync_api import sync_playwright, expect

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height}, reduced_motion="no-preference"
        )
        page.add_init_script("""
            window.challengeSweeps = 0;
            document.addEventListener('animationstart', event => {
                if (event.animationName === 'challenge-border-sweep') {
                    document.documentElement.dataset.testSweeps = String(++window.challengeSweeps);
                }
            });
        """)
        page.goto(live_server)
        card = page.locator(".next-card")
        card.wait_for()
        if width == 320:
            bounds = card.bounding_box()
            assert bounds["y"] + bounds["height"] > height
            assert page.evaluate("window.challengeSweeps") == 0
        card.scroll_into_view_if_needed()
        expect(page.locator("html")).to_have_attribute("data-test-sweeps", "1")
        expect(page.locator(".next-card.challenge-intro")).to_have_count(0)
        page.get_by_role("button", name="Path", exact=True).click()
        page.locator(".path-node").first.wait_for()
        page.get_by_role("button", name="Today", exact=True).click()
        card.scroll_into_view_if_needed()
        previous_card = card.element_handle()
        page.get_by_role("button", name="30 min", exact=True).click()
        expect(page.get_by_role("button", name="30 min", exact=True)).to_have_attribute(
            "aria-pressed", "true"
        )
        previous_card.wait_for_element_state("hidden")
        card.scroll_into_view_if_needed()
        # Flush rendering so a mistakenly replayed CSS animation can emit its event.
        page.evaluate(
            "new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
        )
        assert page.evaluate("window.challengeSweeps") == 1
        page.reload()
        card.wait_for()
        card.scroll_into_view_if_needed()
        expect(page.locator("html")).to_have_attribute("data-test-sweeps", "1")
        browser.close()


@pytest.mark.parametrize("width,height", [(390, 844), (1440, 1000)])
def test_mcq_has_one_submission_clear_result_and_persistent_timer(
    live_server, pack_data, width, height
):
    import httpx
    from playwright.sync_api import sync_playwright, expect

    pack_data["node"][0]["verify"] = {
        "type": "lab",
        "exercise": "case",
        "case_id": "ethical-hacking-foundations:foundations",
    }
    response = httpx.post(
        live_server + "/api/packs",
        files={"file": ("test.toml", dump_toml(pack_data), "text/plain")},
    )
    assert response.status_code == 200
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height}, reduced_motion="reduce"
        )
        page.goto(live_server)
        page.locator(".next-card").get_by_role(
            "button", name="Open challenge", exact=True
        ).click()
        page.get_by_label("Session target (minutes)").fill("5")
        page.get_by_role("button", name="Start verified exercise", exact=True).click()
        expect(page.locator("#challenge-title")).to_have_text(
            "Does setup prove completion?"
        )
        expect(page.locator(".session-clock")).to_contain_text("elapsed / target")
        expect(page.locator(".clock-value")).to_contain_text("/ 5:00")
        expect(
            page.get_by_text(
                "One submission. Review your choice before sending.", exact=True
            )
        ).to_be_visible()
        expect(page.locator(".exercise-evidence")).to_have_count(0)
        page.get_by_role("button", name="Docs", exact=True).click()
        expect(page.locator(".session-clock")).to_be_visible()
        page.get_by_role("button", name="Resume challenge", exact=True).click()
        wrong = page.get_by_role(
            "radio", name="Yes. The version command proves", exact=False
        )
        wrong.check()
        page.reload()
        expect(wrong).to_be_checked()
        page.get_by_role("button", name="Submit answer", exact=True).click()
        expect(page.locator(".case-feedback")).to_contain_text("No XP earned")
        expect(page.locator(".case-feedback")).to_contain_text(
            "A version command proves only"
        )
        expect(
            page.get_by_role("button", name="Submit answer", exact=True)
        ).to_have_count(0)
        expect(page.locator("#task-session")).to_be_hidden()
        page.reload()
        expect(wrong).to_be_checked()
        expect(wrong).to_be_disabled()
        expect(page.locator(".case-feedback")).to_contain_text("No XP earned")
        page.get_by_role("button", name="Stats", exact=True).click()
        page.get_by_role("button", name="Today", exact=True).click()
        page.locator(".next-card").get_by_role(
            "button", name="Open challenge", exact=True
        ).click()
        page.get_by_role("button", name="Review attempt", exact=True).click()
        expect(page.locator(".case-feedback")).to_be_visible()
        page.get_by_role("button", name="Continue without XP", exact=True).click()
        expect(page).to_have_url(live_server + "/#today")
        state = httpx.get(live_server + "/api/challenges/test-pack:one").json()
        assert state["node"]["status"] == "skipped"
        assert state["exercise"]["attempts"] == 1 and not state["exercise"]["passed"]
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        browser.close()


@pytest.mark.parametrize("width,height", [(320, 740), (390, 844), (1440, 1000)])
def test_permission_requests_have_explicit_choices_and_separate_submit(
    live_server, pack_data, width, height
):
    import httpx
    from playwright.sync_api import sync_playwright, expect

    pack_data["node"][0]["verify"] = {"type": "lab", "exercise": "access-policy"}
    response = httpx.post(
        live_server + "/api/packs",
        files={"file": ("test.toml", dump_toml(pack_data), "text/plain")},
    )
    assert response.status_code == 200
    challenge_url = live_server + "/api/challenges/test-pack:one"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height}, reduced_motion="reduce"
        )
        page.goto(live_server)
        page.locator(".next-card").get_by_role("button", name="Open challenge").click()
        page.get_by_role("button", name="Start verified exercise").click()
        expect(page.locator(".decision-field")).to_have_count(6)
        expect(page.locator(".decision-field :checked")).to_have_count(0)
        run = httpx.get(challenge_url).json()["exercise"]
        draft_key = f"ascend-answer-local-{run['id']}"
        # Old checkbox drafts stored booleans, including explicit false values.
        page.evaluate(
            "key => sessionStorage.setItem(key, JSON.stringify({r2: false}))", draft_key
        )
        page.reload()
        expect(
            page.get_by_role("group", name="Request r2", exact=True).get_by_role(
                "radio", name="Deny", exact=True
            )
        ).to_be_checked()
        submit = page.get_by_role("button", name="Submit decisions", exact=True)
        submit.click()
        assert httpx.get(challenge_url).json()["exercise"]["attempts"] == 0
        page.get_by_role("group", name="Request r1", exact=True).get_by_role(
            "radio", name="Allow", exact=True
        ).check()
        assert page.evaluate(
            "key => JSON.parse(sessionStorage.getItem(key))", draft_key
        ) == {"r1": True, "r2": False}
        page.reload()
        for request in run["data"]["requests"]:
            allowed = request["enabled"] and (
                request["caller"] == request["owner"]
                or (request["role"] == "admin" and request["action"] == "read")
            )
            if request["id"] in {"r1", "r2"}:
                allowed = not allowed
            group = page.get_by_role(
                "group", name=f"Request {request['id']}", exact=True
            )
            group.get_by_role(
                "radio", name="Allow" if allowed else "Deny", exact=True
            ).check()
            choices = group.locator(".decision-choice")
            left, right = choices.nth(0).bounding_box(), choices.nth(1).bounding_box()
            assert left["height"] >= 44 and right["height"] >= 44
            assert abs(left["y"] - right["y"]) < 1
        # Compare document coordinates, independently of the browser's focus scroll.
        assert page.evaluate("""() => {
            const action = document.querySelector('.exercise-actions').getBoundingClientRect();
            return [...document.querySelectorAll('.decision-field')].every(
                field => field.getBoundingClientRect().bottom + 16 <= action.top
            );
        }""")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        submit.click()
        expect(page.locator("#policy-result")).to_have_text("4 of 6 correct · +66 XP")
        expect(page.locator(".decision-explanation")).to_have_count(6)
        expect(submit).to_have_count(0)
        page.reload()
        expect(page.locator("#policy-result")).to_have_text("4 of 6 correct · +66 XP")
        expect(submit).to_have_count(0)
        result = httpx.get(challenge_url).json()["exercise"]
        assert not result["passed"] and result["attempts"] == 1
        page.get_by_role(
            "button", name="Continue with partial result", exact=True
        ).click()
        expect(page).to_have_url(live_server + "/#today")
        assert httpx.get(challenge_url).json()["node"]["status"] == "skipped"
        browser.close()


def test_loading_screen_recovers_from_slow_response_and_missing_script(live_server):
    from playwright.sync_api import sync_playwright, expect

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(service_workers="block")
        page.add_init_script("localStorage.setItem('ascend-theme', 'dark')")
        pending = []
        page.route("**/api/me", lambda route: pending.append(route))
        page.goto(live_server, wait_until="domcontentloaded")
        expect(page.locator("#app-loader")).to_be_visible()
        assert (
            page.locator("#app-loader").evaluate(
                "e => getComputedStyle(e).backgroundColor"
            )
            == "rgb(28, 29, 27)"
        )
        # The overlay has a bounded lifetime even while the request is still pending.
        expect(page.locator("#app-loader")).not_to_be_visible(timeout=6500)
        expect(page.get_by_role("link", name="Reload the workspace")).to_be_visible()
        pending[0].continue_()
        expect(page.locator(".next-card")).to_be_visible()
        expect(
            page.get_by_role("link", name="Reload the workspace")
        ).not_to_be_visible()
        page.unroute("**/api/me")
        page.reload()
        expect(page.locator(".next-card")).to_be_visible()
        expect(page.locator("#app-loader")).not_to_be_visible()
        page.route("**/app.js*", lambda route: route.abort())
        page.reload()
        expect(page.locator("#app-loader")).not_to_be_visible(timeout=6500)
        expect(page.get_by_role("link", name="Reload the workspace")).to_be_visible()
        browser.close()


@pytest.mark.parametrize("width,height", [(390, 844), (1440, 1000)])
def test_guided_challenge_has_copyable_commands_and_free_reference(
    live_server, pack_data, width, height
):
    import httpx
    from playwright.sync_api import sync_playwright, expect
    from ascend.engine.packs import parse_pack
    from ascend.registry import bundled_pack_path

    pack = parse_pack(bundled_pack_path("ethical-hacking-foundations").read_text())
    guide = next(n for n in pack.nodes if n.id == "foundations-experiment")
    for key in [
        "title",
        "brief",
        "done_when",
        "resource",
        "resource_label",
        "resource_note",
        "setup",
        "preview",
        "requirements",
        "minutes",
    ]:
        pack_data["node"][0][key] = getattr(guide, key)
    pack_data["node"][0]["steps"] = list(guide.steps)
    pack_data["node"][0]["materials"] = list(guide.materials)
    response = httpx.post(
        live_server + "/api/packs",
        files={"file": ("test.toml", dump_toml(pack_data), "text/plain")},
    )
    assert response.status_code == 200
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height}, reduced_motion="reduce"
        )
        page.context.grant_permissions(["clipboard-read", "clipboard-write"])
        page.goto(live_server)
        page.locator(".next-card").get_by_role("button", name="Open challenge").click()
        expect(page.locator("#sheet-title")).to_have_text(guide.title)
        expect(page.get_by_role("heading", name="Required setup")).to_be_visible()
        expect(page.get_by_text(guide.preview, exact=True)).to_be_visible()
        reference = page.get_by_role(
            "link", name="Free HTTP server reference (optional)"
        )
        expect(reference).to_be_visible()
        expect(reference).to_have_attribute("href", guide.resource)
        expect(reference).to_have_attribute("rel", "noopener noreferrer")
        expect(page.get_by_text(guide.resource_note, exact=True)).to_be_visible()
        # Opening a learning reference must not start the challenge timer.
        page.context.route(
            guide.resource.split("#")[0],
            lambda route: route.fulfill(
                body="Learning reference", content_type="text/plain"
            ),
        )
        with page.expect_popup() as popup:
            reference.click()
        expect(popup.value).to_have_url(guide.resource)
        popup.value.close()
        assert (
            httpx.get(live_server + "/api/challenges/test-pack:one").json()["session"]
            is None
        )
        expect(page.locator("#sheet .challenge-steps")).to_have_count(0)
        expect(page.get_by_role("button", name="Copy terminal block")).to_have_count(0)
        expect(
            page.get_by_role("link", name="Download this track’s lab files (ZIP)")
        ).to_have_count(0)
        expect(page.get_by_role("heading", name="Your finish line")).to_have_count(0)
        page.locator("#sheet").get_by_role("button", name="Close dialog").click()
        page.goto(live_server + "/#challenge/test-pack%3Aone")
        expect(page.locator("#challenge-content .challenge-steps")).to_have_count(0)
        expect(reference).to_be_visible()
        page.get_by_role("button", name="Start timed task", exact=True).click()
        expect(page.get_by_role("heading", name="Workspace setup")).to_be_visible()
        material = page.get_by_role(
            "link", name="Download this track’s lab files (ZIP)"
        )
        expect(material).to_have_attribute("href", guide.materials[0]["url"])
        with page.expect_download() as download:
            material.click()
        assert download.value.suggested_filename == "ethical-hacking-foundations.zip"
        assert download.value.failure() is None
        expect(
            page.locator("#challenge-content .challenge-steps .doc-code")
        ).to_have_count(5)
        expect(
            page.get_by_role("link", name="Free HTTP server reference (optional)")
        ).to_have_attribute("href", guide.resource)
        page.get_by_role("button", name="Copy terminal block").first.click()
        assert (
            page.evaluate("navigator.clipboard.readText()")
            == "python3 --version\ncurl --version"
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        expect(
            page.locator("#challenge-content .challenge-steps .doc-code")
        ).to_have_count(5)
        expect(page.locator(".session-clock")).to_be_visible()
        page.reload()
        expect(page.locator("#challenge-title")).to_have_text(guide.title)
        expect(page.locator(".session-clock")).to_be_visible()
        browser.close()


def test_browser_explains_stale_server_and_recovers_after_retry(live_server):
    from playwright.sync_api import expect, sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def missing_playground(route):
            route.fulfill(status=404, json={"detail": "Not Found"})

        old_stats_data = page.request.get(live_server + "/api/stats").json()
        old_stats_data.pop("xp")
        old_stats_data.pop("playground")

        def old_stats(route):
            route.fulfill(status=200, json=old_stats_data)

        page.route("**/api/playground**", missing_playground)
        page.route("**/api/stats", old_stats)
        page.goto(live_server + "/#playground/quick")
        message = "The running Ascend server has not loaded this update. Restart the server, then reload this page."
        for tab in (
            "Quick practice",
            "Challenges",
            "Free practice",
            "Saved work & history",
        ):
            page.get_by_role("link", name=tab, exact=True).click()
            expect(page.locator("#playground-content")).to_contain_text(message)
            expect(
                page.get_by_role("button", name="Try again", exact=True)
            ).to_be_visible()
            expect(page.locator("#playground-content")).not_to_contain_text("Not Found")
        page.get_by_role("button", name="Stats", exact=True).click()
        expect(page.locator("#stats-content")).to_contain_text(message)
        expect(page.locator("#stats-content")).not_to_contain_text("undefined")
        page.unroute("**/api/stats", old_stats)
        page.unroute("**/api/playground**", missing_playground)
        page.get_by_role("button", name="Try again", exact=True).click()
        expect(page.locator("#stats-content")).to_contain_text(
            "XP contributions: track 0"
        )
        page.get_by_role("button", name="Playground", exact=True).click()
        page.get_by_role("link", name="Quick practice", exact=True).click()
        expect(page.locator(".pg-catalog-card").first).to_be_visible()
        # Static assets can update before either Linux-lab API is loaded.
        for endpoint in ("lab-catalog", "lab-attempts"):
            page.get_by_role("link", name="Quick practice", exact=True).click()
            expect(page.locator(".pg-catalog-card").first).to_be_visible()
            pattern = f"**/api/{endpoint}"
            page.route(pattern, missing_playground)
            page.get_by_role("link", name="Linux labs", exact=True).click()
            expect(page.locator("#playground-content")).to_contain_text(message)
            expect(page.locator("#playground-content")).not_to_contain_text("Not Found")
            page.unroute(pattern, missing_playground)
            page.get_by_role("button", name="Try again", exact=True).click()
            expect(page.get_by_role("heading", name="Linux labs", exact=True)).to_be_visible()
            expect(page.locator(".pg-lab")).to_have_count(15)
        assert not errors
        browser.close()
