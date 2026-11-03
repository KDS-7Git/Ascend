import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from test_integration import live_server as live_server  # noqa: PLC0414

from ascend.server.app import create_app


@pytest.mark.parametrize("activity", ["copy-check", "desk-17"])
def test_challenge_timer_survives_save_leave_and_repeat_resume(tracker, now, activity):
    p = tracker.playground
    run = p.start(activity, deliberate=True)
    original = p.owned(run["id"])["running_since"]
    tracker.clock = lambda: now + timedelta(seconds=75)
    saved = p.save(run["id"], {"notes": "My unfinished observation"}, pause=True)
    assert (
        saved["status"] == "active"
        and saved["timer"]["running"]
        and saved["timer"]["strict"]
    )
    tracker.clock = lambda: now + timedelta(hours=2)
    assert p.view(run["id"])["timer"]["elapsed_seconds"] == 7200
    assert p.resume(run["id"])["timer"]["elapsed_seconds"] == 7200
    assert p.owned(run["id"])["running_since"] == original
    with pytest.raises(ValueError, match="timed Playground challenge"):
        p.start("example-access")
    example = p.start("example-access", end_scored=True)
    old = p.view(run["id"])
    assert (
        old["status"] == "ended" and old["work"]["notes"] == "My unfinished observation"
    )
    assert not old["timer"]["running"] and not p.db.rows("activity_rewards")
    p.save(example["id"], {"notes": "Paused worked example"})
    tracker.clock = lambda: now + timedelta(days=1)
    assert p.view(run["id"])["timer"]["elapsed_seconds"] == 7200
    assert p.view(example["id"])["elapsed_seconds"] == 0


def test_legacy_saved_challenge_keeps_original_start_after_return(tracker, now):
    p = tracker.playground
    run = p.start("copy-check", deliberate=True)
    tracker.db.update(
        "activity_runs",
        "id=?",
        (run["id"],),
        status="saved",
        elapsed_seconds=12,
        running_since=None,
    )
    tracker.clock = lambda: now + timedelta(minutes=8)
    assert p.resume(run["id"])["timer"]["elapsed_seconds"] == 480
    tracker.clock = lambda: now + timedelta(minutes=9)
    answers = json.loads(p.owned(run["id"])["fixture"])["expected"]
    complete = p.submit(run["id"], answers)
    assert complete["result"]["passed"] and complete["timer"]["elapsed_seconds"] == 540
    tracker.clock = lambda: now + timedelta(days=1)
    assert p.view(run["id"])["timer"]["elapsed_seconds"] == 540


def test_http_pause_request_keeps_challenge_running(tmp_path):
    c = TestClient(create_app(tmp_path, scheduler=False))
    run = c.post(
        "/api/playground/activities/copy-check/start", json={"deliberate": True}
    ).json()
    saved = c.post(
        "/api/playground/runs/" + run["id"] + "/save",
        json={"data": {"notes": "Kept on server"}, "pause": True},
    ).json()
    assert (
        saved["status"] == "active"
        and saved["timer"]["running"]
        and saved["timer"]["strict"]
    )
    assert (
        c.post("/api/playground/activities/example-access/start", json={}).status_code
        == 400
    )
    assert (
        c.post(
            "/api/playground/activities/example-access/start", json={"end_scored": True}
        ).status_code
        == 200
    )
    old = c.get("/api/playground/runs/" + run["id"]).json()
    assert old["status"] == "ended" and old["work"]["notes"] == "Kept on server"


def test_legacy_saved_challenge_blocks_switching_and_can_end(tracker):
    from ascend import timing

    p = tracker.playground
    run = p.start("copy-check", deliberate=True)
    tracker.db.update(
        "activity_runs", "id=?", (run["id"],), status="saved", running_since=None
    )
    assert timing.summary(tracker)["playground_active"]["id"] == run["id"]
    with pytest.raises(ValueError, match="timed Playground challenge"):
        p.start("example-access")
    p.start("example-access", end_scored=True)
    assert p.view(run["id"])["status"] == "ended"


def test_worked_example_pause_excludes_time_away(tracker, now):
    p = tracker.playground
    run = p.start("example-access")
    tracker.clock = lambda: now + timedelta(seconds=80)
    saved = p.save(run["id"], {"notes": "Return to step two"}, pause=True)
    assert saved["status"] == "saved" and not saved["timer"]["running"]
    tracker.clock = lambda: now + timedelta(days=1)
    assert p.resume(run["id"])["timer"]["elapsed_seconds"] == 80
    tracker.clock = lambda: now + timedelta(days=1, seconds=20)
    assert p.view(run["id"])["timer"]["elapsed_seconds"] == 100


@pytest.mark.parametrize("width", [390, 1440])
def test_browser_challenge_has_no_pause_and_example_switch_ends_it(live_server, width):
    import httpx
    from playwright.sync_api import expect, sync_playwright
    from test_ui_feedback import accessibility, capture

    run = httpx.post(
        live_server + "/api/playground/activities/copy-check/start",
        json={"deliberate": True},
    ).json()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(live_server + "/#activity/" + run["id"])
        expect(
            page.get_by_text(
                "This timer keeps running when you leave. Complete or end the attempt to stop it.",
                exact=True,
            )
        ).to_be_visible()
        expect(
            page.get_by_role("button", name="Pause & save", exact=True)
        ).to_have_count(0)
        capture(page, f"strict-challenge-{width}")
        accessibility(page)
        page.get_by_role("button", name="Save & leave", exact=True).click()
        expect(page.locator(".work-group-row")).to_have_count(1)
        active = httpx.get(live_server + "/api/playground/runs/" + run["id"]).json()
        assert active["status"] == "active" and active["timer"]["running"]
        page.locator(".work-group-row").get_by_role("button").click()
        page.locator("#attempts .work-row").get_by_role("button").click()
        page.get_by_text("Study a separate example", exact=True).click()
        page.get_by_role("button", name="Study integrity", exact=True).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.get_by_role(
            "button", name="End scored attempt and switch", exact=True
        ).click()
        expect(
            page.get_by_role("button", name="Pause & save", exact=True)
        ).to_be_visible()
        old = httpx.get(live_server + "/api/playground/runs/" + run["id"]).json()
        assert old["status"] == "ended" and not old["timer"]["running"]
        assert not errors
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        browser.close()
