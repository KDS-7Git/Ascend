"""Practice clock, teaching-only walkthroughs and saved-session continuity."""

from datetime import timedelta
import json

import pytest
from fastapi.testclient import TestClient

from ascend.application import Tracker
from ascend.cli import execute, parser
from ascend.playground.catalog import CATALOG
from ascend.server.app import create_app
from ascend.storage import Database


def test_clock_pauses_resumes_and_finishes_without_awarding_speed_xp(tracker, now):
    p = tracker.playground
    run = p.start("example-integrity")
    tracker.clock = lambda: now + timedelta(seconds=75)
    assert p.view(run["id"])["timer"]["elapsed_seconds"] == 75
    p.save(run["id"], {"notes": "unfinished"})
    tracker.clock = lambda: now + timedelta(hours=2)
    assert p.view(run["id"])["timer"] == {
        "elapsed_seconds": 75,
        "target_seconds": 300,
        "running": False,
        "server_time": tracker.now().isoformat(),
    }
    p.resume(run["id"])
    tracker.clock = lambda: now + timedelta(hours=2, seconds=15)
    p.resume(run["id"])  # Repeated resume must not reset the active interval.
    completed = p.submit(
        run["id"], {}, "A newline changes the bytes but renaming does not."
    )
    assert completed["timer"]["elapsed_seconds"] == 90
    assert not completed["timer"]["running"]
    assert completed["result"]["xp"] == 0
    tracker.clock = lambda: now + timedelta(days=2)
    assert p.view(run["id"])["timer"]["elapsed_seconds"] == 90
    assert (
        tracker.entries()[0]["next_step"]
        == "Choose another activity or return to your track"
    )


def test_switching_foreground_pauses_previous_activity(tracker, now):
    first = tracker.playground.start("example-access")
    tracker.clock = lambda: now + timedelta(seconds=30)
    second = tracker.playground.start("example-python")
    tracker.clock = lambda: now + timedelta(seconds=60)
    assert tracker.playground.view(first["id"])["elapsed_seconds"] == 30
    assert tracker.playground.view(second["id"])["elapsed_seconds"] == 30
    tracker.playground.end(second["id"])
    assert not tracker.playground.view(second["id"])["timer"]["running"]


@pytest.mark.parametrize("status", ["finished", "skipped"])
def test_guidance_remembers_skill_without_claiming_learning(tracker, status):
    p = tracker.playground
    run = p.start("example-integrity")
    assert run["tour"]["status"] == "pending"
    p.tour(run["id"], 1)
    # An old autosave cannot reset the walkthrough step.
    p.save(run["id"], {"tour": {"step": 0}, "notes": "draft"}, pause=False)
    assert p.view(run["id"])["tour"] == {"status": "active", "step": 1}
    p.tour(run["id"], 2, status)
    assert p.view(run["id"])["status"] == "active"
    assert not p.evidence()
    assert not tracker.entries()
    assert not tracker.db.rows("activity_rewards")
    assert p.start("example-integrity")["tour"]["status"] == "available"
    assert p.start("example-python")["tour"]["status"] == "pending"
    challenge = p.start("copy-check", deliberate=True)
    assert "teaching_steps" not in challenge
    with pytest.raises(ValueError, match="only for separate worked examples"):
        p.tour(challenge["id"])


def test_every_example_has_actionable_teaching_and_choices(tracker):
    for item in CATALOG:
        if item["role"] != "example":
            continue
        run = tracker.playground.start(item["id"])
        assert len(run["teaching_steps"]) >= 3
        assert run["reflection_prompt"]
        assert any(s["question"] for s in run["teaching_steps"])
        for step in run["teaching_steps"]:
            if step["question"]:
                assert step["choices"][step["answer"]]
                assert step["explanation"]


def test_tour_cli_api_and_user_isolation(tmp_path):
    with TestClient(create_app(tmp_path, scheduler=False)) as client:
        run = client.post(
            "/api/playground/activities/example-integrity/start", json={}
        ).json()
        route = f"/api/playground/runs/{run['id']}/tour"
        assert client.post(route, json={"step": 1}).json()["tour"]["step"] == 1
        assert client.post(route, json={"step": 50}).status_code == 400
        assert client.post(route, json={"step": True}).status_code == 422
        db = Database(tmp_path)
        tracker = Tracker(db)
        result = execute(
            tracker,
            parser().parse_args(
                ["playground", "tour", run["id"], "--status", "skipped"]
            ),
        )
        assert result["tour"]["status"] == "skipped"
        db.connection.execute(
            "INSERT INTO users(id,username,password_hash,created_at) VALUES (2,'other','unused','2026-11-02')"
        )
        other = Tracker(Database(tmp_path, user_id=2))
        with pytest.raises(ValueError, match="not found"):
            other.playground.tour(run["id"])
        assert not other.db.rows("activity_tour_history")
        assert (
            json.loads(tracker.playground.owned(run["id"])["work"])["tour"]["status"]
            == "skipped"
        )
        other.db.close()
        db.close()
