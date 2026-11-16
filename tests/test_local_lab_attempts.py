import json
from copy import deepcopy
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from ascend import timing
from ascend.application import Tracker
from ascend.local_labs import catalog
from ascend.local_labs.attempts import Attempts
from ascend.server.app import create_app
from ascend.storage import Database

ANSWERS = {
    "discovery_event_id": "92733",
    "executable": "/usr/sbin/arp",
    "arguments": ["arp", "-a"],
    "companion_event_id": "92734",
    "uid": 1000,
    "benign_event_ids": ["control-1"],
    "intent": "insufficient-evidence",
    "explanation": "This is neighbor discovery; the audit record cannot establish the user's intent.",
}


@pytest.fixture
def reviewed_pilot(monkeypatch):
    # Unit tests exercise a candidate before publishing the real review results.
    recipe = deepcopy(
        next(r for r in catalog.recipes() if r["id"] == "linux-audit-discovery")
    )
    recipe.update(
        status="reviewed",
        tested_platforms=["linux-x86_64"],
        lifecycle_verified=True,
        measurements={
            k: 1
            for k in (
                "download_bytes",
                "expanded_bytes",
                "peak_disk_bytes",
                "startup_cold_seconds",
                "startup_warm_seconds",
                "peak_memory_bytes",
            )
        },
    )
    monkeypatch.setattr(catalog, "recipes", lambda: [recipe])
    return recipe


def payload(attempt, answers=None):
    return {
        k: attempt[k]
        for k in ("nonce", "recipe_version", "checker_version", "fixture_id")
    } | {"answers": ANSWERS if answers is None else answers}


def test_answer_checks_are_owned_versioned_one_use_and_do_not_award(
    installed, reviewed_pilot, tmp_path
):
    installed.server_mode = True
    service = Attempts(installed)
    attempt = service.create("linux-audit-discovery")
    assert attempt["started_at"] is None
    service.ready(attempt["id"], attempt["nonce"])
    assert "nonce_hash" not in service.view(attempt["id"])
    for change in (
        {"recipe_version": "other"},
        {"checker_version": "other"},
        {"fixture_id": "other"},
        {"nonce": "0" * 64},
        {"passed": True},
    ):
        with pytest.raises(ValueError):
            service.submit(attempt["id"], {**payload(attempt), **change})
    other = Tracker(Database(tmp_path, user_id=2), clock=installed.clock)
    with pytest.raises(ValueError, match="not found"):
        Attempts(other).submit(attempt["id"], payload(attempt))
    result = service.submit(attempt["id"], payload(attempt))
    assert result["result"]["status"] == "pass"
    assert result["result"]["authority"] == "server-answer"
    assert not result["result"]["satisfies_track_evidence"]
    assert installed.states("test-pack") == {} and installed.entries() == []
    assert timing.summary(installed)["xp"] == 0
    with pytest.raises(ValueError, match="already submitted"):
        service.submit(attempt["id"], payload(attempt))
    other.db.close()


@pytest.mark.parametrize(
    "answer",
    [
        {},
        {**ANSWERS, "discovery_event_id": "92734"},
        {**ANSWERS, "benign_event_ids": []},
        {**ANSWERS, "uid": True},
        {**ANSWERS, "explanation": ""},
    ],
)
def test_bad_or_missing_evidence_fails(tracker, reviewed_pilot, answer):
    service = Attempts(tracker)
    attempt = service.create("linux-audit-discovery", offline=True)
    result = service.submit(attempt["id"], payload(attempt, answer))
    assert result["result"]["status"] == "fail"
    assert result["started_at"] is None and result["origin"] == "offline"
    assert result["result"]["authority"] == "local"


def test_foreground_rules_and_clock_survive_stopping_compute(installed, reviewed_pilot):
    service = Attempts(installed)
    timing.start(installed, "one")
    with pytest.raises(ValueError, match="active session"):
        service.create("linux-audit-discovery")
    timing.end(installed)
    attempt = service.create("linux-audit-discovery")
    service.ready(attempt["id"], attempt["nonce"])
    started = service.view(attempt["id"])["started_at"]
    with pytest.raises(ValueError, match="local lab"):
        timing.start(installed, "small")
    with pytest.raises(ValueError, match="local lab"):
        installed.playground.start("example-access")
    assert "nonce_hash" not in json.dumps(timing.summary(installed))
    service.ready(attempt["id"], attempt["nonce"])
    assert service.view(attempt["id"])["started_at"] == started
    service.abandon(attempt["id"], attempt["nonce"])
    assert timing.start(installed, "small")["status"] == "running"


def test_expired_reservation_releases_session_and_rejects_submission(
    tracker, reviewed_pilot
):
    service = Attempts(tracker)
    old = service.create("linux-audit-discovery")
    stamp = tracker.now()
    tracker.clock = lambda: stamp + timedelta(days=2)
    replacement = service.create("linux-audit-discovery")
    assert service.view(old["id"])["status"] == "abandoned"
    with pytest.raises(ValueError):
        service.submit(old["id"], payload(old))
    assert replacement["id"] != old["id"]


def test_http_bounds_and_client_only_commands(tmp_path, reviewed_pilot):
    with TestClient(create_app(tmp_path, scheduler=False)) as client:
        for args in (
            ["local-lab", "doctor", "linux-audit-discovery"],
            ["local-lab", "start", "linux-audit-discovery"],
            ["local-lab", "cache"],
        ):
            response = client.post("/api/command", json={"argv": args})
            assert response.status_code == 400 and "local-only" in response.text
        assert (
            client.post("/api/lab-attempts", json={"recipe_id": "vampi"}).status_code
            == 400
        )
        a = client.post(
            "/api/lab-attempts",
            json={"recipe_id": "linux-audit-discovery", "offline": True},
        ).json()
        endpoint = f"/api/lab-attempts/{a['id']}/submit"
        assert (
            client.post(
                endpoint,
                content=(chunk for chunk in [b"x" * 600000, b"y" * 600000]),
                headers={"content-type": "application/json"},
            ).status_code
            == 413
        )
        assert (
            client.post(endpoint, json={**payload(a), "passed": True}).status_code
            == 422
        )
        result = client.post(endpoint, json=payload(a))
        assert (
            result.status_code == 200
            and result.json()["result"]["evidence_label"] == "Answer checked"
        )
        assert client.post(endpoint, json=payload(a)).status_code == 400
