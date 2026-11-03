import json
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import httpx
import pytest

from ascend.application import Tracker
from ascend.engine.packs import dump_toml
from ascend.storage import Database


@pytest.fixture
def notebook_server(tmp_path, pack_data):
    pack_data["node"][0].update(
        preview="Compare two local HTTP responses.",
        requirements="Python 3 and curl.",
        steps=["Record your two observations."],
        verify={
            "type": "file",
            "path": "/unavailable/server/report.json",
            "min_bytes": 15,
        },
    )
    db = Database(tmp_path)
    t = Tracker(db)
    t.install_pack(dump_toml(pack_data))
    t.start_mission("test-pack")
    db.close()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "ascend.server",
            "--home",
            str(tmp_path),
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
                urlopen(url + "/api/health", timeout=1)
                break
            except OSError:
                if process.poll() is not None:
                    pytest.fail(process.stderr.read().decode())
                time.sleep(0.05)
        else:
            pytest.fail("Temporary server did not become ready")
        yield url
    finally:
        process.terminate()
        process.wait(timeout=8)
        process.stderr.close()


@pytest.mark.parametrize("width,height", [(390, 844), (1440, 1000), (1920, 1080)])
def test_notebook_upload_completion_and_recovery(
    notebook_server, width, height, tmp_path
):
    from playwright.sync_api import sync_playwright, expect

    url = notebook_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height}, reduced_motion="reduce"
        )
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.locator(".next-card").get_by_role("button", name="Open challenge").click()
        page.get_by_role("button", name="Start timed task", exact=True).click()
        expect(page.locator(".lab-toolbar")).to_be_visible()
        expect(page.locator("#sheet")).not_to_be_visible()
        page.locator(".lab-toolbar").get_by_role(
            "button", name="Notes & evidence", exact=True
        ).click()
        note = "I observed two different HTTP responses and explained why the missing page returned an error."
        page.get_by_label("Your notes", exact=True).fill(note)
        expect(page.locator(".notebook-status")).to_have_text("All changes saved")
        assert not httpx.get(url + "/api/entries").json()
        page.get_by_role("button", name="Save progress", exact=True).click()
        expect(page.locator(".notebook-status")).to_have_text("Progress saved")
        page.reload()
        expect(page.locator(".lab-toolbar")).to_be_visible()
        page.locator(".lab-toolbar").get_by_role(
            "button", name="Notes & evidence", exact=True
        ).click()
        expect(page.get_by_label("Your notes", exact=True)).to_have_value(note)
        page.get_by_label("Your notes", exact=True).fill(
            note + " I repeated the comparison."
        )
        page.get_by_role("button", name="Save progress", exact=True).click()
        expect(page.locator(".notebook-status")).to_have_text("Progress saved")
        assert len(httpx.get(url + "/api/entries").json()) == 1
        page.get_by_label("Upload evidence", exact=True).set_input_files(
            {
                "name": "report.json",
                "mimeType": "application/json",
                "buffer": json.dumps({"observations": note}).encode(),
            }
        )
        expect(page.locator(".notebook-evidence")).to_contain_text("evidence accepted")
        page.get_by_role("button", name="Check evidence", exact=True).click()
        expect(page.locator(".notebook-body")).to_contain_text("Complete the lab below")
        page.get_by_role("button", name="Finish session", exact=True).click()
        page.get_by_role(
            "button", name="End session without completing", exact=True
        ).click()
        expect(page.locator(".lab-state")).to_contain_text("Session ended")
        expect(page.locator("#task-session")).not_to_be_visible()
        page.locator(".lab-toolbar").get_by_role(
            "button", name="Notes & evidence", exact=True
        ).click()
        expect(page.get_by_label("Your notes", exact=True)).to_have_value(
            note + " I repeated the comparison."
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        if width >= 1100:
            a = page.locator(".lab-instructions").bounding_box()
            b = page.locator(".lab-notebook").bounding_box()
            assert a["x"] + a["width"] < b["x"]
        page.locator(".lab-toolbar").get_by_role(
            "button", name="Complete lab", exact=True
        ).click()
        expect(page.locator(".lab-celebration")).to_contain_text("Lab complete!")
        assert (
            httpx.get(url + "/api/challenges/test-pack:one").json()["node"]["status"]
            == "done"
        )
        page.locator(".lab-celebration").get_by_role(
            "button", name="Continue learning"
        ).click()
        expect(page.locator(".next-card h2")).to_have_text("Second task")
        expect(page.locator("#task-session")).not_to_be_visible()
        page.goto(url + "/#challenge/test-pack%3Aone")
        expect(page.locator(".lab-toolbar")).to_be_visible()
        page.locator(".lab-toolbar").get_by_role(
            "button", name="Notes & evidence", exact=True
        ).click()
        page.get_by_role("button", name="Practice again", exact=True).click()
        expect(page.locator("#task-session")).to_contain_text("Practice")
        assert (
            httpx.get(url + "/api/challenges/test-pack:one").json()["session"][
                "potential_xp"
            ]
            == 0
        )
        assert not errors, errors
        browser.close()
