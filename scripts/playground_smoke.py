"""Exercise Playground in Chromium on desktop and phone using disposable profiles."""

import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

from ascend.application import Tracker
from ascend.storage import Database

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="ascend-playground-browser-") as folder:
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
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            for _ in range(100):
                try:
                    urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1).close()
                    break
                except OSError:
                    if process.poll() is not None:
                        raise RuntimeError(process.stderr.read().decode())
                    time.sleep(0.1)
            target = ROOT / "docs/screenshots/playground"
            target.mkdir(parents=True, exist_ok=True)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                for width in (1440, 390):
                    page = browser.new_page(
                        viewport={"width": width, "height": 1000},
                        reduced_motion="reduce",
                    )
                    errors = []
                    page.on(
                        "pageerror",
                        lambda error, errors=errors: errors.append(str(error)),
                    )
                    page.goto(f"http://127.0.0.1:{port}/#playground/quick")
                    expect(
                        page.get_by_role("heading", name="Playground", exact=True)
                    ).to_be_visible()
                    expect(page.locator(".pg-catalog-card").first).to_be_visible()
                    page.get_by_role("link", name="Quick practice", exact=True).focus()
                    page.keyboard.press("Tab")
                    expect(
                        page.get_by_role("link", name="Challenges", exact=True)
                    ).to_be_focused()
                    page.screenshot(
                        path=str(target / f"quick-{width}.png"), full_page=True
                    )
                    # Cold start: a separate teaching fixture, then an independent one.
                    card = page.locator(".pg-catalog-card").filter(
                        has=page.get_by_role(
                            "heading",
                            name="Worked example: request decisions",
                            exact=True,
                        )
                    )
                    if card.count() == 0:
                        page.get_by_label("Search", exact=True).fill(
                            "Worked example: request decisions"
                        )
                        page.get_by_role(
                            "button", name="Apply filters", exact=True
                        ).click()
                        expect(card).to_be_visible()
                    card.get_by_role("button", name="Study example", exact=True).click()
                    expect(page).to_have_url(
                        __import__("re").compile(r"/#activity/[a-f0-9]+$")
                    )
                    expect(page.locator(".playground-tabs")).not_to_be_visible()
                    expect(page.locator(".pg-clock-value")).to_be_visible()
                    if width == 390:
                        page.get_by_role(
                            "button", name="Open walkthrough", exact=True
                        ).click()
                    expect(
                        page.get_by_role(
                            "heading", name="Read the rule before the request"
                        )
                    ).to_be_visible()
                    page.get_by_role("button", name="Next step", exact=True).click()
                    page.get_by_role("button", name="No", exact=True).click()
                    expect(page.locator(".pg-prediction-feedback")).to_contain_text(
                        "That’s right"
                    )
                    page.reload()
                    expect(
                        page.get_by_role("heading", name="Follow one request")
                    ).to_be_visible()
                    page.get_by_role("button", name="Back", exact=True).click()
                    expect(
                        page.get_by_role(
                            "heading", name="Read the rule before the request"
                        )
                    ).to_be_visible()
                    page.screenshot(
                        path=str(target / f"walkthrough-{width}.png"), full_page=True
                    )
                    page.get_by_role("button", name="Next step", exact=True).click()
                    page.get_by_role("button", name="Next step", exact=True).click()
                    page.get_by_role(
                        "button", name="Finish walkthrough", exact=True
                    ).click()
                    page.get_by_label("In your own words: what did you learn?").fill(
                        f"I compared owner and administrator access using separate requests at width {width}."
                    )
                    page.get_by_role(
                        "button", name="Finish example", exact=True
                    ).focus()
                    page.keyboard.press("Enter")
                    expect(
                        page.get_by_role(
                            "heading",
                            name="Example complete. Put it into practice.",
                            exact=True,
                        )
                    ).to_be_visible()
                    example_id = page.url.split("/")[-1]
                    example_url = (
                        f"http://127.0.0.1:{port}/api/playground/runs/{example_id}"
                    )
                    completed_at = page.request.get(example_url).json()["updated_at"]
                    page.get_by_role("button", name="Try a separate challenge").click()
                    expect(
                        page.get_by_role(
                            "heading", name="Who can open this file?", exact=True
                        )
                    ).to_be_visible()
                    run_id = page.url.split("/")[-1]
                    assert (
                        page.request.get(example_url).json()["updated_at"]
                        == completed_at
                    )
                    expect(
                        page.get_by_role("button", name="Check evidence", exact=True)
                    ).to_be_visible()
                    db = Database(folder)
                    t = Tracker(db)
                    fixture = json.loads(t.playground.owned(run_id)["fixture"])
                    for key, value in fixture["expected"].items():
                        page.get_by_label(f"Allow {key}?", exact=True).select_option(
                            str(value).lower()
                        )
                    page.get_by_role(
                        "button", name="Check evidence", exact=True
                    ).click()
                    expect(
                        page.get_by_role(
                            "heading", name="Activity complete", exact=True
                        )
                    ).to_be_visible()
                    page.screenshot(
                        path=str(target / f"result-{width}.png"), full_page=True
                    )
                    # Dedicated work pages return to the catalog through an explicit link.
                    page.get_by_role(
                        "link", name="← Back to Playground", exact=True
                    ).click()
                    page.get_by_role("link", name="Free practice", exact=True).click()
                    expect(page.locator(".pg-catalog-card")).to_have_count(2)
                    for title in (
                        "Permission policy sandbox",
                        "Log and timeline sandbox",
                    ):
                        card = page.locator(".pg-catalog-card").filter(
                            has=page.get_by_role("heading", name=title, exact=True)
                        )
                        card.get_by_role(
                            "button", name="Open workspace", exact=True
                        ).click()
                        expect(
                            page.get_by_role(
                                "button", name="Run experiment", exact=True
                            )
                        ).to_be_visible()
                        if title.startswith("Permission"):
                            page.get_by_label(
                                "Allow admins to write", exact=True
                            ).check()
                        else:
                            page.get_by_label("Minimum status", exact=True).fill("500")
                        page.get_by_role(
                            "button", name="Run experiment", exact=True
                        ).click()
                        page.get_by_label("What did you learn?", exact=True).fill(
                            f"I changed the inputs and compared the result for {title} at {width}."
                        )
                        page.get_by_role(
                            "button", name="Save workspace", exact=True
                        ).click()
                        expect(
                            page.get_by_role(
                                "heading", name="Saved work & history", exact=True
                            )
                        ).to_be_visible()
                        page.reload()
                        page.get_by_label("Search saved work").fill(title)
                        card = (
                            page.locator(".work-row")
                            .filter(
                                has=page.get_by_role("heading", name=title, exact=True)
                            )
                            .first
                        )
                        card.get_by_role("button").click()
                        page.locator("#attempts .work-row").first.get_by_role(
                            "button"
                        ).click()
                        expect(
                            page.get_by_label("What did you learn?", exact=True)
                        ).to_have_value(
                            f"I changed the inputs and compared the result for {title} at {width}."
                        )
                        if title.startswith("Permission"):
                            expect(
                                page.get_by_label("Allow admins to write", exact=True)
                            ).to_be_checked()
                        else:
                            expect(
                                page.get_by_label("Minimum status", exact=True)
                            ).to_have_value("500")
                        page.screenshot(
                            path=str(
                                target
                                / f"{'policy' if title.startswith('Permission') else 'timeline'}-{width}.png"
                            ),
                            full_page=True,
                        )
                        original = page.url
                        page.get_by_role(
                            "button", name="Reset into a new copy", exact=True
                        ).click()
                        expect(page).not_to_have_url(original)
                        page.get_by_role(
                            "link", name="← Back to Playground", exact=True
                        ).click()
                        expect(page.locator(".pg-catalog-card")).to_have_count(2)
                    page.get_by_role("link", name="Challenges", exact=True).click()
                    expect(page.locator(".pg-catalog-card")).to_have_count(10)
                    card = page.locator(".pg-catalog-card").filter(
                        has=page.get_by_role(
                            "heading", name="The disputed incident", exact=True
                        )
                    )
                    card.get_by_role(
                        "button", name="Start challenge", exact=True
                    ).click()
                    expect(
                        page.get_by_role(
                            "button", name="Try this challenge", exact=True
                        )
                    ).to_be_visible()
                    page.get_by_role(
                        "button", name="Try this challenge", exact=True
                    ).click()
                    expect(
                        page.get_by_role(
                            "heading", name="The disputed incident", exact=True
                        )
                    ).to_be_visible()
                    page.get_by_label("Notes and hypotheses").fill(
                        "Compare the UTC offsets before ordering the records."
                    )
                    page.get_by_role("button", name="Save & leave", exact=True).click()
                    expect(
                        page.get_by_role(
                            "heading", name="Saved work & history", exact=True
                        )
                    ).to_be_visible()
                    page.get_by_role("button", name="Today", exact=True).click()
                    expect(
                        page.locator(".pg-recommendation").get_by_role("button").first
                    ).to_be_visible()
                    # Reproduce the owner's integrity example in dark mode.
                    page.emulate_media(color_scheme="dark")
                    created = page.request.post(
                        f"http://127.0.0.1:{port}/api/playground/activities/example-integrity/start",
                        data={"end_scored": True},
                    ).json()
                    page.goto(f"http://127.0.0.1:{port}/#activity/{created['id']}")
                    if width == 390:
                        page.get_by_role(
                            "button", name="Open walkthrough", exact=True
                        ).click()
                    expect(
                        page.get_by_role(
                            "heading", name="Compare content, not filenames", exact=True
                        )
                    ).to_be_visible()
                    expect(page.locator(".pg-tour")).to_contain_text('"note\\n"')
                    expect(page.locator(".pg-clock-value")).not_to_have_text("0:00")
                    page.screenshot(
                        path=str(target / f"integrity-tour-{width}.png"), full_page=True
                    )
                    page.get_by_role("button", name="Next step", exact=True).click()
                    page.get_by_role("button", name="Copy A", exact=True).click()
                    expect(page.locator(".pg-prediction-feedback")).to_contain_text(
                        "missing the final newline"
                    )
                    page.get_by_role("button", name="Pause & save", exact=True).click()
                    expect(page.locator(".pg-clock")).to_contain_text("Clock stopped")
                    page.get_by_role(
                        "button", name="Resume activity", exact=True
                    ).click()
                    expect(
                        page.get_by_role(
                            "heading", name="Spot the invisible difference", exact=True
                        )
                    ).to_be_visible()
                    page.get_by_role("button", name="Skip tour", exact=True).click()
                    expect(
                        page.get_by_role("button", name="Open walkthrough", exact=True)
                    ).to_be_visible()
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= innerWidth"
                    ), "Horizontal page overflow"
                    assert not errors, errors
                    db.close()
                    page.close()
                browser.close()
            print(
                "Playground browser checks passed at 1440px and 390px; screenshots in docs/screenshots/playground."
            )
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
