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
        expect(page.get_by_text("A smaller step, perhaps.")).to_be_visible()
        page.get_by_role("button", name="Any time", exact=True).click()
        page.locator(".next-card").get_by_role("button", name="Open challenge").click()
        expect(page.get_by_role("heading", name="Your finish line")).to_be_visible()
        expect(
            page.get_by_role("link", name="Open learning resource")
        ).to_have_attribute("href", "https://docs.python.org/3/")
        page.locator("#sheet").get_by_role(
            "button", name="Log progress", exact=True
        ).click()
        page.get_by_label("What I did", exact=True).fill(
            "I tested this example and explained why it worked"
        )
        page.get_by_label("What's next", exact=True).fill("Try the second exercise")
        page.get_by_text("Add details", exact=True).click()
        page.get_by_label("Minutes spent", exact=True).fill("15")
        page.get_by_label("Mark as done", exact=True).check()
        page.get_by_role("button", name="Complete challenge", exact=True).click()
        expect(page.locator("#sheet")).not_to_be_visible()
        expect(page.locator("#session-result")).to_contain_text("Challenge complete!")
        expect(page.locator("#session-result")).to_contain_text("Unlocked: Second")
        expect(page.locator("#streak")).to_have_text("1")
        page.get_by_role("button", name="Path", exact=True).click()
        expect(page.locator(".path-node.done")).to_have_count(1)
        page.get_by_role("button", name="Stats", exact=True).click()
        page.get_by_label("Search your notes", exact=True).fill("explained")
        page.get_by_role("button", name="Search", exact=True).click()
        expect(page.locator(".search-result")).to_have_count(1)
        page.get_by_role("button", name="More", exact=True).click()
        page.get_by_label("Color theme", exact=True).select_option("dark")
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
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
        expect(page.locator(".challenge-steps li")).to_have_count(2)
        expect(
            page.get_by_text("Change one input at a time.", exact=True)
        ).not_to_be_visible()
        page.get_by_text("Hint 1", exact=True).click()
        expect(
            page.get_by_text("Change one input at a time.", exact=True)
        ).to_be_visible()
        page.locator("#sheet").get_by_role(
            "button", name="Log progress", exact=True
        ).click()
        page.get_by_label("What I did", exact=True).fill(
            "I compared a prediction with the first observed result"
        )
        page.get_by_role("button", name="Save progress", exact=True).click()
        expect(page.locator("#session-result")).to_contain_text("Progress saved")
        expect(page.locator(".next-card h2")).to_have_text("First task")
        page.locator(".next-card").get_by_role(
            "button", name="Log progress", exact=True
        ).click()
        page.get_by_label("What I did", exact=True).fill(
            "I tried another input but have not saved the evidence file"
        )
        page.get_by_label("Mark as done", exact=True).check()
        page.get_by_role("button", name="Complete challenge", exact=True).click()
        expect(page.locator("#session-result")).to_contain_text(
            "Evidence file does not exist"
        )
        expect(page.locator("#session-result")).not_to_have_class(
            "session-result completed"
        )
        expect(page.locator(".next-card h2")).to_have_text("First task")
        assert len(httpx.get(live_server + "/api/entries").json()) == 2
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
