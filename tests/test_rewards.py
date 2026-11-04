"""Reward identity, authority and participation boundaries, across real flows."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from test_local_lab_attempts import ANSWERS, payload
from test_local_lab_attempts import reviewed_pilot as reviewed_pilot_fixture

from ascend import challenge_work, labs, rewards, timing
from ascend.application import Tracker
from ascend.engine.packs import dump_toml
from ascend.local_labs.attempts import Attempts
from ascend.storage import Database

reviewed_pilot = reviewed_pilot_fixture


def start_lab(t, data, *, case=False):
    data["node"][0]["verify"] = {"type": "lab", "exercise": "integrity"}
    if case:
        data["node"][0]["verify"] = {
            "type": "lab",
            "exercise": "case",
            "case_id": "ethical-hacking-foundations:foundations",
        }
    t.install_pack(dump_toml(data))
    t.start_mission("test-pack")
    run = labs.start(t, "test-pack:one")
    answers = json.loads(t.db.rows("lab_runs", "id=?", (run["id"],))[0]["challenge"])[
        "expected"
    ]
    return run, answers


def test_worked_example_rewards_participation_but_keeps_scored_xp_zero(tracker, now):
    p = tracker.playground
    run = p.start("example-access")
    p.save(
        run["id"],
        {"notes": "A browser draft is not a submitted reflection."},
        pause=False,
    )
    p.tour(run["id"], 1)
    assert rewards.practice_summary(tracker)["total"] == 0
    with pytest.raises(ValueError):
        p.submit(run["id"], {}, "short")
    assert rewards.practice_summary(tracker)["total"] == 0
    result = p.submit(
        run["id"], {}, "The owner check matters even when a user is enabled."
    )
    assert result["result"]["xp"] == 0
    assert result["result"]["practice_reward"]["points"] == 5
    assert result["result"]["practice_reward"]["newly_awarded"]
    assert not p.view(run["id"])["result"]["practice_reward"]["newly_awarded"]
    assert tracker.xp_totals()["total"] == 0
    tracker.clock = lambda: now + timedelta(days=1)
    assert (
        p.submit(run["id"], {}, "This replay cannot create a second earning event.")[
            "status"
        ]
        == "passed"
    )
    assert rewards.practice_summary(tracker)["today"] == 0
    new = p.start("example-access")
    p.submit(
        new["id"], {}, "I checked a changed caller against the saved request rule."
    )
    assert rewards.practice_summary(tracker)["total"] == 10


def test_manual_progress_completion_and_drafts_do_not_double_award(tracker, pack_data):
    pack_data["node"][0]["milestone"] = True
    tracker.install_pack(dump_toml(pack_data))
    tracker.start_mission("test-pack")
    timing.start(tracker, "test-pack:one")
    note = "I restarted the service and confirmed that its stored update survived."
    draft = challenge_work.save(
        tracker, "test-pack:one", note, "Check a fresh failure", 0
    )
    assert rewards.practice_summary(tracker)["total"] == 0
    saved = challenge_work.save(
        tracker,
        "test-pack:one",
        note,
        "Check a fresh failure",
        draft["revision"],
        log_progress=True,
    )
    assert saved["practice_reward"]["points"] == 5
    assert saved["practice_reward"]["newly_awarded"]
    again = challenge_work.save(
        tracker,
        "test-pack:one",
        note,
        "Check a fresh failure",
        saved["revision"],
        log_progress=True,
    )
    assert not again["practice_reward"]["newly_awarded"]
    done = challenge_work.complete(tracker, "test-pack:one", again["revision"])
    assert done["completed"] and done["practice_reward"]["points"] == 0
    assert done["practice_reward"]["reason"] == "already-counted-today"
    assert rewards.practice_summary(tracker)["total"] == 5
    assert tracker.xp_totals()["total"] == 0
    achievement = rewards.summary(tracker)["milestones"]["items"][0]
    assert achievement["reference"] == "test-pack:one"
    assert achievement["evidence_label"] == "Completion recorded by you"


def test_invalid_submissions_earn_nothing_but_a_recorded_wrong_answer_counts_effort(
    tracker, pack_data
):
    run, expected = start_lab(tracker, pack_data, case=True)
    with pytest.raises(ValueError):
        labs.submit(tracker, run["id"], {})
    assert not tracker.db.rows("practice_rewards")
    wrong = next(value for value in run["choices"] if value != expected["choice"])
    result = labs.submit(tracker, run["id"], {"choice": wrong})
    assert not result["completed"] and result["terminal"]
    assert result["practice_reward"]["points"] == 5
    assert result["reward"]["xp"] == 0 and not result["reward"]["recorded"]
    assert rewards.summary(tracker)["milestones"]["total"] == 0
    assert not tracker.states("test-pack")


def test_playground_requires_complete_typed_answers_before_participation(tracker):
    p = tracker.playground
    run = p.start("request-decisions", deliberate=True)
    expected = json.loads(p.owned(run["id"])["fixture"])["expected"]
    with pytest.raises(ValueError, match="Answer every"):
        p.submit(run["id"], {})
    with pytest.raises(ValueError, match="requires"):
        p.submit(run["id"], dict.fromkeys(expected, "false"))
    assert rewards.practice_summary(tracker)["total"] == 0
    wrong = p.submit(run["id"], {key: not value for key, value in expected.items()})
    assert not wrong["result"]["passed"]
    assert wrong["result"]["practice_reward"]["points"] == 5
    assert tracker.xp_totals()["total"] == 0
    correct = p.submit(run["id"], expected)
    assert correct["result"]["passed"]
    assert not correct["result"]["practice_reward"]["newly_awarded"]
    assert rewards.practice_summary(tracker)["total"] == 5
    assert tracker.xp_totals()["total"] == 10


def test_assessment_receipt_is_specific_and_replays_never_reaward(
    tracker, pack_data, now
):
    run, expected = start_lab(tracker, pack_data)
    result = labs.submit(tracker, run["id"], expected)
    assert result["reward"]["xp"] == 100 and result["reward"]["newly_awarded"]
    # Another independent source changes the dashboard, never this receipt.
    practice = tracker.playground.start("event-filter", deliberate=True)
    answer = json.loads(tracker.playground.owned(practice["id"])["fixture"])["expected"]
    tracker.playground.submit(practice["id"], answer)
    assert tracker.xp_totals()["total"] == 110
    tracker.clock = lambda: now + timedelta(days=1)
    repeat = labs.submit(tracker, run["id"], expected)
    assert repeat["reward"]["xp"] == 100 and not repeat["reward"]["newly_awarded"]
    assert not repeat["practice_reward"]["newly_awarded"]
    assert rewards.practice_summary(tracker)["today"] == 0


def test_capped_and_duplicate_events_stay_spent_across_days(tracker, now):
    one = rewards.award(
        tracker,
        "hosted-lab",
        "first",
        "First lab",
        "lab-result-recorded",
        event_key="finished-run-1",
    )
    duplicate = rewards.award(
        tracker,
        "hosted-lab",
        "first",
        "First lab",
        "lab-result-recorded",
        event_key="finished-run-2",
    )
    assert one["points"] == 5 and duplicate["points"] == 0
    for number in range(1, 7):
        capped = rewards.award(
            tracker,
            "track",
            str(number),
            f"Task {number}",
            "assessment-submitted",
            event_key=f"run-{number}",
        )
    assert capped["points"] == 0 and capped["reason"] == "daily-cap"
    assert rewards.practice_summary(tracker)["total"] == 30
    tracker.clock = lambda: now + timedelta(days=1)
    assert (
        rewards.award(
            tracker,
            "hosted-lab",
            "first",
            "First lab",
            "lab-result-recorded",
            event_key="finished-run-2",
        )["points"]
        == 0
    )
    assert (
        rewards.award(
            tracker, "track", "6", "Task 6", "assessment-submitted", event_key="run-6"
        )["points"]
        == 0
    )
    assert rewards.practice_summary(tracker)["today"] == 0
    assert (
        rewards.award(
            tracker,
            "track",
            "6",
            "Task 6",
            "assessment-submitted",
            event_key="new-run-6",
        )["points"]
        == 5
    )


def test_concurrent_credit_is_capped_and_account_scoped(tmp_path, now):
    Database(tmp_path).close()
    barrier = Barrier(9)

    def finish(number):
        t = Tracker(Database(tmp_path), clock=lambda: now)
        try:
            barrier.wait()
            return rewards.award(
                t,
                "track",
                str(number),
                f"Task {number}",
                "assessment-submitted",
                event_key=f"concurrent-{number}",
            )
        finally:
            t.db.close()

    with ThreadPoolExecutor(max_workers=9) as pool:
        receipts = list(pool.map(finish, range(9)))
    assert sum(item["points"] for item in receipts) == 30
    other = Tracker(Database(tmp_path, user_id=2), clock=lambda: now)
    try:
        assert rewards.summary(other)["practice"]["total"] == 0
        assert rewards.summary(other)["recent"] == []
        assert rewards.receipt(other, event_key="concurrent-0") is None
        assert (
            rewards.award(
                other,
                "track",
                "0",
                "Task 0",
                "assessment-submitted",
                event_key="concurrent-0",
            )["points"]
            == 5
        )
    finally:
        other.db.close()


def test_unchanged_reflection_cannot_mint_again_on_a_later_day(tracker, now):
    note, next_step = (
        "I compared the observed port to the expected listener.",
        "Inspect the changed port",
    )
    first = tracker.log(note, next_step)
    assert first["practice_reward"]["points"] == 5
    tracker.clock = lambda: now + timedelta(days=1)
    # Direct bookkeeping identity also protects edited/retained old notes.
    repeated = rewards.award(
        tracker,
        "learning-note",
        "personal",
        "Learning reflection",
        "learning-note-saved",
        event_key=rewards.note_event("learning-note", "personal", note, next_step),
    )
    assert not repeated["newly_awarded"]
    assert rewards.practice_summary(tracker)["today"] == 0


def test_local_results_preserve_authority_and_require_meaningful_input(
    tracker, reviewed_pilot, now
):
    service = Attempts(tracker)
    empty = service.create("linux-audit-discovery", offline=True)
    rejected = service.submit(empty["id"], payload(empty, {}))
    assert rejected["result"]["status"] == "fail"
    assert "practice_reward" not in rejected["result"]
    attempt = service.create("linux-audit-discovery", offline=True)
    wrong = {**ANSWERS, "discovery_event_id": "wrong-but-filled"}
    result = service.submit(attempt["id"], payload(attempt, wrong))
    assert result["result"]["status"] == "fail"
    assert result["result"]["authority"] == "local"
    assert result["result"]["practice_reward"]["points"] == 5
    assert result["result"]["practice_reward"]["newly_awarded"]
    assert not service.view(attempt["id"])["result"]["practice_reward"]["newly_awarded"]
    assert tracker.xp_totals()["total"] == 0
    tracker.clock = lambda: now + timedelta(days=1)
    with pytest.raises(ValueError, match="already submitted"):
        service.submit(attempt["id"], payload(attempt, wrong))
    assert rewards.practice_summary(tracker)["today"] == 0


def test_free_workspace_rewards_a_real_repair_once(tracker, now):
    p = tracker.playground
    baseline = p.start("policy-workspace")
    example = p.start("example-access")
    p.submit(
        example["id"],
        {},
        "An enabled owner still needs the correct operation on the requested object.",
    )
    faulty = p.copy(baseline["id"], fault=True)
    fixture = json.loads(p.owned(faulty["id"])["fixture"])
    wrong = next(
        rule
        for rule in faulty["work"]["workspace"]["policy"]
        if rule != fixture["fault"]
    )
    assert not p.repair(faulty["id"], wrong)["repaired"]
    assert rewards.practice_summary(tracker)["total"] == 5
    result = p.repair(faulty["id"], fixture["fault"])
    assert result["practice_reward"]["points"] == 5
    assert result["practice_reward"]["newly_awarded"]
    assert tracker.xp_totals()["total"] == 0
    tracker.clock = lambda: now + timedelta(days=1)
    assert not p.repair(faulty["id"], fixture["fault"])["practice_reward"][
        "newly_awarded"
    ]
    assert rewards.practice_summary(tracker)["today"] == 0


def test_copying_a_repaired_workspace_does_not_create_a_repair_event(tracker, now):
    p = tracker.playground
    example = p.start("example-access")
    p.submit(
        example["id"],
        {},
        "The owner, administrator and disabled-user controls test separate rules.",
    )
    baseline = p.start("policy-workspace")
    faulty = p.copy(baseline["id"], fault=True)
    rule = json.loads(p.owned(faulty["id"])["fixture"])["fault"]
    p.repair(faulty["id"], rule)

    tracker.clock = lambda: now + timedelta(days=1)
    copied = p.copy(faulty["id"])
    assert not copied["hidden_fault"]
    result = p.repair(copied["id"], rule)
    assert result["repaired"]
    assert result["practice_reward"] is None
    assert rewards.practice_summary(tracker)["today"] == 0

    # A new unknown fault still requires a real repair and can earn today's credit.
    fresh = p.copy(copied["id"], fault=True)
    fresh_rule = json.loads(p.owned(fresh["id"])["fixture"])["fault"]
    assert fresh["hidden_fault"]
    assert p.repair(fresh["id"], fresh_rule)["practice_reward"]["newly_awarded"]
    assert rewards.practice_summary(tracker)["today"] == 5
