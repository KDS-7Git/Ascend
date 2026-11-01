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
    parser.add_argument(
        "--motion-demo",
        action="store_true",
        help="Also record a short motion and hover preview",
    )
    args = parser.parse_args()
    records = []
    captures = 0

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
        for pack in (ROOT / "packs/community").rglob("*.toml"):
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
        next_node = tracker.overview()["next"]
        challenge_ref = f"{next_node['pack_id']}:{next_node['id']}"
        labs.start(tracker, challenge_ref)
        feedback_level, feedback_node = next(
            (level, node)
            for level in tracker.levels()
            for node in level["nodes"]
            if node.get("verify", {}).get("type") == "file"
            and f"{node['pack_id']}:{node['id']}" != challenge_ref
        )
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
                    ("wide", 1920, 1080, "light"),
                    ("laptop", 1024, 900, "light"),
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
                    for route in [
                        "today",
                        "path",
                        "stats",
                        "more",
                        "profile",
                        "docs/timers",
                        "challenge/" + challenge_ref,
                    ]:
                        page.goto(base + "/#" + route)
                        if route.startswith("challenge"):
                            page.locator(".lab-data").wait_for()
                        elif route.startswith("docs"):
                            expect(page.locator("#guide-title")).to_have_text(
                                "Timers & XP"
                            )
                        elif route == "more":
                            page.locator(".pack-item").first.wait_for()
                        elif route == "profile":
                            page.locator(".profile-metric").first.wait_for()
                        elif route == "stats":
                            page.locator(".metric-strip").wait_for()
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
                        layout = page.evaluate("""() => {
                            const screen = document.querySelector('.screen:not([hidden])').getBoundingClientRect();
                            const header = document.querySelector('.topbar-inner').getBoundingClientRect();
                            const sections = [...document.querySelectorAll('.screen:not([hidden]) .card, .screen:not([hidden]) .page-section, .screen:not([hidden]) .level-section, .screen:not([hidden]) .docs-article')].filter(e => e.getClientRects().length);
                            return {
                                aligned: Math.abs(screen.left - header.left) < 1 && Math.abs(screen.right - header.right) < 1,
                                contained: sections.every(e => { const r = e.getBoundingClientRect(); return r.left >= screen.left - 1 && r.right <= screen.right + 1; })
                            };
                        }""")
                        assert layout["aligned"] and layout["contained"], (
                            label,
                            route,
                            layout,
                        )
                        if route == "today":
                            primary = page.locator(".next-card").bounding_box()
                            supporting = page.locator(".today-aside").bounding_box()
                            assert (
                                supporting["y"] >= primary["y"] + primary["height"]
                            ), label
                        audit(page, label, route)
                        page.screenshot(
                            path=TARGET / f"{route.split('/')[0]}-{label}.png",
                            full_page=False,
                        )
                        captures += 1
                        if route.startswith("docs"):
                            article = page.locator("#docs-article")
                            before = article.bounding_box()
                            if width <= 1100:
                                page.get_by_role(
                                    "button", name="Guide menu", exact=True
                                ).click()
                                expect(page.locator("#docs-menu")).to_be_visible()
                            else:
                                page.get_by_label("Search documentation").fill(
                                    "runs continuously"
                                )
                                expect(page.locator("#docs-topics a")).to_have_count(1)
                            after = article.bounding_box()
                            for key in ["x", "y", "width"]:
                                assert abs(before[key] - after[key]) < 1, (
                                    label,
                                    key,
                                    before,
                                    after,
                                )
                            audit(
                                page,
                                label,
                                "docs-menu" if width <= 1100 else "docs-search",
                            )
                            page.screenshot(
                                path=TARGET / f"docs-navigation-{label}.png"
                            )
                            captures += 1
                            if width <= 1100:
                                page.keyboard.press("Escape")
                            else:
                                page.get_by_label("Search documentation").fill("")
                        if route == "more":
                            page.locator(".library").screenshot(
                                path=TARGET / f"library-{label}.png"
                            )
                            captures += 1
                    page.goto(base + "/#path")
                    level = page.locator("#level-" + feedback_level["id"])
                    level.evaluate("e => e.open = true")
                    level.locator(".path-node").filter(
                        has_text=feedback_node["title"]
                    ).first.click()
                    page.locator(".manage-challenge > summary").click()
                    page.get_by_role(
                        "button", name="Check evidence", exact=True
                    ).click()
                    expect(page.locator("#sheet .notice")).to_be_visible()
                    audit(page, label, "lesson-feedback")
                    page.screenshot(path=TARGET / f"lesson-feedback-{label}.png")
                    captures += 1
                    assert not errors, errors
                    page.close()
                if args.motion_demo:
                    context = browser.new_context(
                        viewport={"width": 1440, "height": 1000},
                        reduced_motion="no-preference",
                        record_video_dir=str(Path(folder) / "video"),
                        record_video_size={"width": 1008, "height": 700},
                    )
                    page = context.new_page()
                    page.goto(base + "/#today")
                    page.locator(".next-card").wait_for()
                    expect(page.locator(".next-card.challenge-intro")).to_be_visible()
                    page.wait_for_timeout(850)
                    page.screenshot(path=TARGET / "challenge-glow-desktop.png")
                    captures += 1
                    expect(page.locator(".next-card.challenge-intro")).to_have_count(0)
                    page.locator(".next-card").hover(position={"x": 260, "y": 120})
                    page.wait_for_timeout(250)
                    page.screenshot(path=TARGET / "motion-hover-desktop.png")
                    audit(page, "desktop-light", "today-hover")
                    captures += 1
                    page.evaluate("localStorage.setItem('ascend-theme', 'dark')")
                    page.reload()
                    page.locator(".next-card").wait_for()
                    expect(page.locator(".next-card.challenge-intro")).to_be_visible()
                    page.wait_for_timeout(850)
                    page.screenshot(path=TARGET / "motion-dark-desktop.png")
                    audit(page, "desktop-dark", "today-motion")
                    captures += 1
                    expect(page.locator(".next-card.challenge-intro")).to_have_count(0)
                    page.locator(".next-card").hover(position={"x": 260, "y": 120})
                    page.wait_for_timeout(250)
                    page.screenshot(path=TARGET / "motion-hover-desktop-dark.png")
                    audit(page, "desktop-dark", "today-hover")
                    captures += 1
                    page.get_by_role("button", name="Stats", exact=True).click()
                    page.wait_for_timeout(900)
                    page.get_by_role("button", name="Docs", exact=True).click()
                    page.wait_for_timeout(900)
                    page.get_by_role(
                        "button", name="Pause motion effects", exact=True
                    ).click()
                    video = page.video
                    video_path = TARGET / "motion-preview.webm"
                    context.close()
                    video.save_as(video_path)
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
        f"RESULT: {captures} workspace screenshots captured at 320, 390, 768, 1024, 1440 and 1920 px, including dark mode; shared page alignment, contained sections, no horizontal overflow or JavaScript errors. Temporary learner account only."
    )


if __name__ == "__main__":
    main()
