"""Capture the workspace UI against a disposable account with a real graded fixture."""

import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import sync_playwright, expect
from ascend import labs
from ascend.application import Tracker
from ascend.storage import Database

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs/screenshots/ui-workspace"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--axe",
        type=Path,
        help="Optional local axe-core JavaScript for the temporary-profile audit",
    )
    args = parser.parse_args()
    records = []

    def audit(page, label, route):
        if args.axe:
            page.evaluate(args.axe.read_text())
            result = page.evaluate(
                "async () => await axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})"
            )
            records.append(
                {
                    "viewport": label,
                    "screen": route,
                    "violations": [
                        {
                            "id": r["id"],
                            "impact": r["impact"],
                            "help": r["help"],
                            "nodes": [
                                {
                                    "target": n["target"],
                                    "summary": n.get("failureSummary", ""),
                                }
                                for n in r["nodes"]
                            ],
                        }
                        for r in result["violations"]
                    ],
                }
            )

    TARGET.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ascend-ui-review-") as folder:
        tracker = Tracker(Database(folder))
        for pack in (ROOT / "packs/community").glob("*.toml"):
            tracker.install_pack(pack.read_text())
        tracker.start_mission("verified-security-lab")
        run = labs.start(tracker, "verified-security-lab:lab-readiness")
        labs.emit(tracker, run["id"], "ok")
        run = labs.emit(tracker, run["id"], "error")
        event = next(
            e
            for e in run["data"]["events"]
            if e["marker"] == run["marker"] and e["status"] >= 400
        )
        assert labs.submit(
            tracker, run["id"], {"request_id": event["request_id"], "errors": 1}
        )["completed"]
        tracker.finish_mission("paused")
        tracker.start_mission("defensive-security-and-detection")
        tracker.db.close()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "ascend.server",
                "--home",
                folder,
                "--port",
                str(port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        base = f"http://127.0.0.1:{port}"
        try:
            for _ in range(100):
                try:
                    with urlopen(base + "/api/health", timeout=1):
                        break
                except OSError:
                    time.sleep(0.05)
            else:
                raise RuntimeError("Screenshot server did not start")
            with sync_playwright() as p:
                browser = p.chromium.launch()
                for label, width, height, theme in [
                    ("desktop", 1440, 1000, "light"),
                    ("mobile", 390, 844, "light"),
                    ("mobile-dark", 390, 844, "dark"),
                    ("tablet", 768, 1024, "light"),
                    ("narrow", 320, 740, "light"),
                ]:
                    page = browser.new_page(
                        viewport={"width": width, "height": height},
                        reduced_motion="reduce",
                    )
                    page.add_init_script(
                        f"localStorage.setItem('ascend-theme', '{theme}')"
                    )
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    for route in ["today", "path", "more", "profile", "docs/timers"]:
                        page.goto(base + "/#" + route)
                        if route.startswith("docs"):
                            expect(page.locator("#docs-article h2")).to_have_text(
                                "Timers & XP"
                            )
                        elif route == "more":
                            page.locator(".pack-item").first.wait_for()
                        elif route == "profile":
                            page.locator(".profile-metric").first.wait_for()
                        else:
                            page.locator(
                                ".mission-info h2"
                                if route == "today"
                                else ".path-node.open"
                            ).first.wait_for()
                        page.evaluate("document.fonts.ready")
                        assert page.evaluate(
                            "document.documentElement.scrollWidth <= innerWidth"
                        ), (label, route)
                        audit(page, label, route)
                        page.screenshot(
                            path=TARGET / f"{route.split('/')[0]}-{label}.png",
                            full_page=False,
                        )
                        if route == "more":
                            page.locator(".library").screenshot(
                                path=TARGET / f"library-{label}.png"
                            )
                    page.goto(base + "/#today")
                    page.locator(".next-card").get_by_role(
                        "button", name="Open challenge"
                    ).click()
                    page.locator(".manage-challenge > summary").click()
                    page.get_by_role(
                        "button", name="Check evidence", exact=True
                    ).click()
                    expect(page.locator("#sheet .notice")).to_be_visible()
                    audit(page, label, "lesson-feedback")
                    page.screenshot(path=TARGET / f"lesson-feedback-{label}.png")
                    assert not errors, errors
                    page.close()
                browser.close()
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stderr.close()
    if records:
        (ROOT / "docs/testing/ui-accessibility.json").write_text(
            json.dumps(
                {
                    "tool": "axe-core 4.10.3",
                    "scope": "WCAG 2 A/AA and 2.1 AA tagged rules; automated checks are not a complete accessibility assessment",
                    "checks": records,
                },
                indent=2,
            )
            + "\n"
        )
        failures = [
            (r["viewport"], r["screen"], [v["id"] for v in r["violations"]])
            for r in records
            if r["violations"]
        ]
        if failures:
            raise AssertionError(failures)
        print(
            f"Accessibility: {len(records)} screen/viewport checks have no detected violations in the selected rules."
        )
    print(
        "RESULT: 35 workspace screenshots captured at 320, 390, 768 and 1440 px, including dark mode; no horizontal overflow or JavaScript errors. Temporary learner account only."
    )


if __name__ == "__main__":
    main()
