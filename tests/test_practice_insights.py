from copy import deepcopy
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from ascend.engine.practice import recommend, review_due, selection_minutes
from ascend.playground import catalog
from ascend.server.app import create_app


FEEDBACK = {
    "working_minutes": 12,
    "setup_minutes": 1,
    "difficulty": "about-right",
    "clarity": "clear",
    "repetition": "fresh",
    "environment_issue": False,
}


def test_feedback_is_scoped_idempotent_and_never_awards_learning(tracker):
    p = tracker.playground
    run = p.start("example-integrity")
    before = deepcopy(tracker.stats())
    p.feedback(run["id"], FEEDBACK)
    p.feedback(run["id"], {**FEEDBACK, "clarity": "unclear"})
    assert len(p.db.rows("activity_feedback")) == 1
    assert tracker.stats() == before
    assert p.insights()["unclear_reports"] == 1
    assert not p.evidence()
    assert not tracker.entries()
    with pytest.raises(ValueError, match="not found"):
        p.feedback("other-run", FEEDBACK)
    for invalid in (
        {"working_minutes": True},
        {"clarity": "maybe"},
        {"environment_issue": 2},
        {"note": "x" * 2001},
    ):
        with pytest.raises(ValueError):
            p.feedback(run["id"], FEEDBACK | invalid)


def test_personal_estimates_require_three_clear_completed_sessions(tracker):
    p = tracker.playground
    for index in range(3):
        run = p.start("example-python")
        p.submit(
            run["id"],
            {},
            f"The loop preserves each matching value, observation {index}.",
        )
        p.feedback(run["id"], FEEDBACK)
        estimate = p.detail("example-python")
        assert estimate["selection_minutes"] == (13 if index == 2 else 5)
    assert not p.list(minutes=10, domain="python", search="Worked example")[
        "activities"
    ]
    assert p.list(minutes=15, domain="python", search="Worked example")["activities"]
    item = catalog.get("example-python")
    rows = [
        {
            **FEEDBACK,
            "activity_id": item["id"],
            "status": "passed",
            "run_id": str(i),
            "working_minutes": 1,
        }
        for i in range(3)
    ]
    assert selection_minutes(item, rows)[0] == 5
    assert selection_minutes(item, [r | {"clarity": "unclear"} for r in rows]) == (5, 0)
    assert selection_minutes(item, [r | {"environment_issue": True} for r in rows]) == (
        5,
        0,
    )


def test_selection_is_observed_explicitly_and_deduplicated(tracker, now):
    p = tracker.playground
    p.recommendations(5)
    assert p.insights()["selection_queries"] == 0
    p.observe_selection({"minutes": 5, "domain": "python"})
    p.observe_selection({"domain": "python", "minutes": 5})
    assert p.insights()["selection_queries"] == 1
    assert p.insights()["queries_with_ready_choices"] == 1
    tracker.clock = lambda: now + timedelta(days=15)
    assert p.insights()["selection_queries"] == 0


def test_examples_do_not_delay_review_and_assistance_resets_spacing(now):
    day = now.date()
    evidence = [
        {
            "skill": "python.trace",
            "day": (day - timedelta(days=7 - i)).isoformat(),
            "fixture_key": str(i),
            "outcome": "passed",
            "independent": True,
        }
        for i in range(3)
    ]
    assert not review_due(evidence, day)["python.trace"]["due"]
    evidence.append(
        evidence[-1]
        | {"day": (day - timedelta(days=2)).isoformat(), "independent": False}
    )
    evidence.append(evidence[-1] | {"day": day.isoformat(), "outcome": "example"})
    assert review_due(evidence, day)["python.trace"]["due"]


def test_unwanted_repeats_rank_below_other_ready_choices(now):
    activities = [catalog.get("example-python"), catalog.get("example-spatial")]
    picked = recommend(
        activities,
        [],
        [],
        now.date(),
        feedback=[{"activity_id": "example-python", "repetition": "unwanted-repeat"}],
    )
    assert picked[0]["id"] == "example-spatial"


def test_feedback_http_contract(tmp_path):
    with TestClient(create_app(tmp_path, scheduler=False)) as client:
        run = client.post(
            "/api/playground/activities/example-python/start", json={}
        ).json()
        route = f"/api/playground/runs/{run['id']}/feedback"
        assert client.post(route, json={"data": FEEDBACK}).json()["saved"]
        assert client.get("/api/playground/insights").json()["feedback_reports"] == 1
        assert client.post(
            "/api/playground/selection", json={"data": {"minutes": 5}}
        ).json()["recorded"]
        assert (
            client.post(
                "/api/playground/selection", json={"data": {"search": []}}
            ).status_code
            == 400
        )
