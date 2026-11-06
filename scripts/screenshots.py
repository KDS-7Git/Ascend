"""Capture illustrative browser screenshots using a disposable local server."""

from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import sync_playwright
from ascend.application import Tracker
from ascend.storage import Database

root = Path(__file__).resolve().parents[1]
target = root / "docs/screenshots"
target.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="ascend-screenshot-") as directory:
    db = Database(directory)
    tracker = Tracker(db)
    tracker.install_pack(
        (root / "packs/community/foundations/networking-for-security.toml").read_text()
    )
    tracker.start_mission("networking-for-security")
    # Illustrative progress belongs only to this disposable screenshot database.
    tracker.backfill(["osi-vs-tcpip", "mac-and-arp"])
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
            directory,
            "--port",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                with urlopen(url + "/api/health", timeout=1):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            raise RuntimeError("Screenshot server did not start")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for width, height, label in [(1440, 1000, "desktop"), (390, 844, "mobile")]:
                page = browser.new_page(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                    reduced_motion="reduce",
                )
                page.goto(url + "/app")
                page.locator(".next-card h2").wait_for()
                page.screenshot(path=target / f"today-{label}.png", full_page=True)
                page.get_by_role("button", name="Path", exact=True).click()
                page.locator(".path-node").first.wait_for()
                page.screenshot(path=target / f"path-{label}.png", full_page=True)
                page.locator(".path-node.open").first.click()
                page.screenshot(path=target / f"challenge-{label}.png", full_page=True)
                page.close()
            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
print("Wrote illustrative screenshots to docs/screenshots/")
