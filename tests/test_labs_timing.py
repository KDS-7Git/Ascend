from datetime import timedelta
import hashlib
import ipaddress
import json

import pytest

from ascend import labs, timing
from ascend.application import Tracker
from ascend.engine.packs import dump_toml
from ascend.storage import Database


def exercise(tracker, pack_data, kind="logging"):
    pack_data["node"][0]["verify"] = {"type": "lab", "exercise": kind}
    tracker.install_pack(dump_toml(pack_data))
    tracker.start_mission("test-pack")
    return labs.start(tracker, "test-pack:one")


def answers(run):
    data = run["data"]
    if run["exercise"] == "logging":
        events = [
            e
            for e in data["events"]
            if e["marker"] == run["marker"] and e["status"] >= 400
        ]
        return {"request_id": events[0]["request_id"], "errors": len(events)}
    if run["exercise"] == "integrity":
        return {"sha256": hashlib.sha256(data["content"].encode("utf-8")).hexdigest()}
    if run["exercise"] == "subnet":
        network = ipaddress.ip_interface(data["interface"]).network
        return {
            "network": str(network),
            "broadcast": str(network.broadcast_address),
            "usable_hosts": network.num_addresses - 2,
        }
    if run["exercise"] == "access-policy":
        return {
            r["id"]: bool(
                r["enabled"]
                and (
                    r["caller"] == r["owner"]
                    or (r["action"] == "read" and r["role"] == "admin")
                )
            )
            for r in data["requests"]
        }
    if run["exercise"] == "timeline":
        failures = {
            e["actor"]: sum(
                v["status"] == "failure" and v["actor"] == e["actor"]
                for v in data["events"]
            )
            for e in data["events"]
        }
        actor = next(k for k, v in failures.items() if v >= 5)
        return {
            "actor": actor,
            "failures": failures[actor],
            "success_time": next(
                e["time"]
                for e in data["events"]
                if e["actor"] == actor and e["status"] == "success"
            ),
        }


@pytest.mark.parametrize(
    "kind", ["logging", "subnet", "integrity", "access-policy", "timeline"]
)
def test_only_correct_observed_results_complete_and_reward(tracker, pack_data, kind):
    run = exercise(tracker, pack_data, kind)
    assert "expected" not in run and "correct" not in json.dumps(run)
    if kind == "access-policy":
        with pytest.raises(ValueError, match="every request"):
            labs.submit(tracker, run["id"], {})
    else:
        assert not labs.submit(tracker, run["id"], {})["ok"]
    assert not tracker.states("test-pack") and timing.summary(tracker)["xp"] == 0
    if kind == "logging":
        labs.emit(tracker, run["id"], "ok")
        run = labs.emit(tracker, run["id"], "error")
    result = labs.submit(tracker, run["id"], answers(run))
    assert result["ok"] and result["completed"]
    assert tracker.states("test-pack")["one"]["how"] == "verifier:lab"
    assert timing.summary(tracker)["xp"] == 100
    assert len(tracker.entries()) == 1
    labs.submit(tracker, run["id"], answers(run))
    tracker.check("test-pack:one", confirm=True)
    assert timing.summary(tracker)["xp"] == 100 and len(tracker.entries()) == 1


def test_verification_cannot_be_bypassed_by_manual_force_split_or_other_user(
    tracker, pack_data, tmp_path
):
    run = exercise(tracker, pack_data)
    for action in [
        lambda: tracker.mark("one", "done"),
        lambda: tracker.backfill(["one"]),
        lambda: tracker.log(
            "I tried the server logging exercise",
            "Find the required records",
            node_id="one",
            complete=True,
            force="pretend it passed",
        ),
        lambda: tracker.split("one", ["First part", "Second part"]),
    ]:
        with pytest.raises(ValueError):
            action()
    assert tracker.entries() == [] and timing.summary(tracker)["xp"] == 0
    other = Tracker(Database(tmp_path, user_id=2), clock=tracker.clock)
    other.install_pack(dump_toml(pack_data))
    with pytest.raises(ValueError, match="not found"):
        labs.view(other, run["id"])
    assert not other.check("test-pack:one")["ok"]
    other.db.close()


def test_changed_pack_and_superseded_instances_cannot_replay(tracker, pack_data):
    old = exercise(tracker, pack_data, "integrity")
    current = labs.start(tracker, "test-pack:one", fresh=True)
    with pytest.raises(ValueError):
        labs.submit(tracker, old["id"], answers(old))
    pack_data["node"][0]["done_when"] = "A newly defined evidence integrity objective"
    tracker.install_pack(dump_toml(pack_data))
    with pytest.raises(ValueError, match="Pack changed"):
        labs.submit(tracker, current["id"], answers(current))


def test_timer_runs_continuously_with_late_reward_and_reminders(
    tracker, pack_data, now
):
    run = exercise(tracker, pack_data, "integrity")
    budget = timing.summary(tracker)["active"]["budget_seconds"]
    tracker.clock = lambda: now + timedelta(seconds=budget * 0.75)
    sent = []
    assert timing.reminders(tracker, lambda m: sent.append(m))["notice"] == 1
    assert not timing.reminders(tracker, lambda m: sent.append(m))["sent"]
    tracker.clock = lambda: now + timedelta(seconds=budget)
    timing.start(tracker, "test-pack:one", minutes=1)
    assert timing.summary(tracker)["active"]["budget_seconds"] == budget
    assert timing.reminders(tracker, lambda m: sent.append(m))["notice"] == 2
    assert len(sent) == 2
    # A fresh instance preserves accumulated session time while replacing expired exercise data.
    run = labs.start(tracker, "test-pack:one", fresh=True)
    tracker.clock = lambda: now + timedelta(seconds=budget * 2)
    labs.submit(tracker, run["id"], answers(run))
    assert timing.summary(tracker)["xp"] == 50
    assert not timing.reminders(tracker, lambda m: sent.append(m))["sent"]
    assert timing.points(budget * 100, budget) == 25


def test_ending_session_cannot_freeze_time_for_a_later_reward(tracker, pack_data, now):
    run = exercise(tracker, pack_data, "integrity")
    tracker.clock = lambda: now + timedelta(seconds=30)
    assert timing.end(tracker)["active"] is None
    assert not tracker.states("test-pack")
    ended = timing.start(tracker, "test-pack:one", minutes=1440)
    assert ended["status"] == "finished" and ended["elapsed_seconds"] == 30
    assert labs.current(tracker, "test-pack:one")["id"] == run["id"]
    tracker.clock = lambda: now + timedelta(hours=1)
    assert labs.submit(tracker, run["id"], answers(run))["completed"]
    assert timing.summary(tracker)["xp"] == 0


def test_legacy_paused_attempt_is_readable_but_cannot_resume_or_gain_xp(
    tracker, pack_data
):
    run = exercise(tracker, pack_data, "integrity")
    tracker.db.update(
        "task_sessions", "node_id=?", ("one",), status="paused", running_since=None
    )
    assert labs.current(tracker, "test-pack:one")["id"] == run["id"]
    with pytest.raises(ValueError, match="legacy session"):
        timing.start(tracker, "test-pack:one")
    assert labs.submit(tracker, run["id"], answers(run))["completed"]
    assert timing.summary(tracker)["xp"] == 0


def test_exercise_setup_and_timer_start_are_atomic(tracker, pack_data, monkeypatch):
    pack_data["node"][0]["verify"] = {"type": "lab", "exercise": "integrity"}
    tracker.install_pack(dump_toml(pack_data))
    tracker.start_mission("test-pack")
    generate = labs.generate

    def failed_setup(*args):
        raise ValueError("Fixture setup failed")

    monkeypatch.setattr(labs, "generate", failed_setup)
    with pytest.raises(ValueError, match="Fixture setup failed"):
        labs.start(tracker, "test-pack:one", minutes=7)
    assert not tracker.db.rows("task_sessions")
    assert not tracker.db.rows("lab_runs")
    monkeypatch.setattr(labs, "generate", generate)
    run = labs.start(tracker, "test-pack:one", minutes=7)
    assert run["timer"]["active"]["budget_seconds"] == 420


def test_reasoning_cases_grade_decisions_but_do_not_expose_the_answer_key(
    tracker, pack_data
):
    pack_data["node"][0]["verify"] = {
        "type": "lab",
        "exercise": "case",
        "case_id": "ethical-hacking-foundations:foundations",
    }
    tracker.install_pack(dump_toml(pack_data))
    tracker.start_mission("test-pack")
    run = labs.start(tracker, "one")
    selected = next(k for k, v in run["choices"].items() if v.startswith("Not yet."))
    assert labs.submit(tracker, run["id"], {"choice": selected})["completed"]


def test_boolean_cannot_impersonate_numeric_answer(tracker, pack_data):
    run = exercise(tracker, pack_data, "logging")
    labs.emit(tracker, run["id"], "ok")
    run = labs.emit(tracker, run["id"], "error")
    candidate = answers(run)
    candidate["errors"] = True
    assert not labs.submit(tracker, run["id"], candidate)["ok"]


def start_case(tracker, pack_data):
    pack_data["node"][0]["verify"] = {
        "type": "lab",
        "exercise": "case",
        "case_id": "ethical-hacking-foundations:foundations",
    }
    tracker.install_pack(dump_toml(pack_data))
    tracker.start_mission("test-pack")
    run = labs.start(tracker, "test-pack:one")
    correct = next(k for k, v in run["choices"].items() if v.startswith("Not yet."))
    return run, correct


def test_mcq_one_submission_survives_reload_fresh_instance_and_pack_changes(
    tracker, pack_data, now
):
    run, correct = start_case(tracker, pack_data)
    assert "feedback" not in run and "explanation" not in run
    with pytest.raises(ValueError, match="Choose one"):
        labs.submit(tracker, run["id"], {"choice": "invalid"})
    assert not tracker.db.rows("case_attempts")
    wrong = next(k for k in run["choices"] if k != correct)
    tracker.clock = lambda: now + timedelta(seconds=42)
    first = labs.submit(tracker, run["id"], {"choice": wrong})
    assert not first["completed"] and first["terminal"]
    assert first["exercise"]["feedback"]["selected"] == wrong
    assert first["exercise"]["feedback"]["correct_choice"] == correct
    assert "version command" in first["exercise"]["feedback"]["explanation"]
    assert timing.summary(tracker)["active"] is None
    assert timing.summary(tracker)["recent"]["outcome"] == "incorrect"
    assert timing.summary(tracker)["recent"]["elapsed_seconds"] == 42
    # A second submission returns the recorded result, never regrades another choice.
    assert not labs.submit(tracker, run["id"], {"choice": correct})["completed"]
    assert labs.current(tracker, "one")["terminal"]
    assert labs.start(tracker, "one")["id"] == run["id"]
    with pytest.raises(ValueError, match="already been submitted"):
        labs.start(tracker, "one", fresh=True)
    pack_data["node"][0]["done_when"] = "Reworded completion description"
    tracker.install_pack(dump_toml(pack_data))
    assert labs.current(tracker, "one")["feedback"]["selected"] == wrong
    assert timing.summary(tracker)["xp"] == 0
    assert not tracker.states("test-pack")
    assert len(tracker.db.rows("case_attempts")) == 1


def test_mcq_correct_receipt_is_idempotent_and_account_scoped(
    tracker, pack_data, tmp_path
):
    run, correct = start_case(tracker, pack_data)
    first = labs.submit(tracker, run["id"], {"choice": correct})
    assert first["completed"] and first["exercise"]["terminal"]
    assert timing.summary(tracker)["recent"]["outcome"] == "completed"
    assert timing.summary(tracker)["recent"]["xp_earned"] == 100
    assert labs.submit(tracker, run["id"], {"choice": "ignored"})["completed"]
    assert len(tracker.entries()) == 1
    other = Tracker(Database(tmp_path, user_id=2), clock=tracker.clock)
    other.install_pack(dump_toml(pack_data))
    with pytest.raises(ValueError, match="not found"):
        labs.submit(other, run["id"], {"choice": correct})
    other.db.close()


def test_mcq_concurrent_submissions_record_only_the_first_decision(tracker, pack_data):
    from concurrent.futures import ThreadPoolExecutor

    run, correct = start_case(tracker, pack_data)
    wrong = next(k for k in run["choices"] if k != correct)

    def submit(choice):
        client = Tracker(Database(tracker.db.home), clock=tracker.clock)
        try:
            return labs.submit(client, run["id"], {"choice": choice})
        finally:
            client.db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, [correct, wrong]))
    assert results[0]["completed"] == results[1]["completed"]
    assert len(tracker.db.rows("case_attempts")) == 1
    assert tracker.db.rows("lab_runs")[0]["attempts"] == 1
    assert timing.summary(tracker)["xp"] == (100 if results[0]["completed"] else 0)


def test_legacy_mcq_migration_preserves_progress_and_locks_recorded_result(
    tracker, pack_data
):
    run, correct = start_case(tracker, pack_data)
    labs.submit(tracker, run["id"], {"choice": correct})
    protected = {
        name: tracker.db.rows(name)
        for name in ["lab_runs", "task_sessions", "xp_awards", "node_state", "entries"]
    }
    tracker.db.connection.execute("DROP TABLE case_attempts")
    tracker.db.connection.execute("DROP TABLE permission_attempts")
    tracker.db.connection.execute("UPDATE schema_version SET version=5")
    tracker.db.migrate()
    assert all(tracker.db.rows(name) == rows for name, rows in protected.items())
    restored = labs.current(tracker, "one")
    assert restored["terminal"] and restored["passed"]
    assert restored["feedback"]["selected"] is None
    assert timing.summary(tracker)["xp"] == 100


@pytest.mark.parametrize("correct_count", [0, 1, 4, 6])
def test_permission_final_score_explanations_and_no_retries(
    tracker, pack_data, now, correct_count
):
    run = exercise(tracker, pack_data, "access-policy")
    expected = answers(run)
    selected = {
        key: value if i < correct_count else not value
        for i, (key, value) in enumerate(expected.items())
    }
    assert "feedback" not in run and run["attempt_limit"] == 1
    result = labs.submit(tracker, run["id"], selected)
    assert result["terminal"] and result["completed"] == (correct_count == 6)
    receipt = result["exercise"]
    assert receipt["score"] == {
        "correct": correct_count,
        "total": 6,
        "xp": 100 * correct_count // 6,
    }
    assert timing.summary(tracker)["active"] is None
    assert timing.summary(tracker)["verified_awards"] == (correct_count == 6)
    assert all(item["explanation"] for item in receipt["feedback"])
    assert (
        labs.submit(tracker, run["id"], expected)["exercise"]["score"]
        == receipt["score"]
    )
    with pytest.raises(ValueError, match="already been submitted"):
        labs.start(tracker, "one", fresh=True)
    tracker.clock = lambda: now + timedelta(days=2)
    pack_data["node"][0]["title"] = "Updated permission task"
    tracker.install_pack(dump_toml(pack_data))
    assert labs.current(tracker, "one")["score"] == receipt["score"]
    assert len(tracker.db.rows("permission_attempts")) == 1


def test_permission_disabled_owner_rule_and_late_partial_reward(
    tracker, pack_data, now
):
    for role in ["user", "admin"]:
        allowed, explanation = labs.access_decision(
            {
                "enabled": False,
                "caller": "owner",
                "owner": "owner",
                "role": role,
                "action": "read",
            }
        )
        assert not allowed and "always denied" in explanation
    run = exercise(tracker, pack_data, "access-policy")
    selected = answers(run)
    selected["r1"] = not selected["r1"]
    selected["r2"] = not selected["r2"]
    budget = run["timer"]["active"]["budget_seconds"]
    tracker.clock = lambda: now + timedelta(seconds=budget * 2)
    result = labs.submit(tracker, run["id"], selected)
    assert result["exercise"]["score"] == {"correct": 4, "total": 6, "xp": 33}


def test_permission_invalid_choices_and_ended_session_cannot_earn(tracker, pack_data):
    run = exercise(tracker, pack_data, "access-policy")
    selected = answers(run)
    selected["r1"] = 1
    with pytest.raises(ValueError, match="every request"):
        labs.submit(tracker, run["id"], selected)
    assert not tracker.db.rows("permission_attempts")
    # An unfinished legacy puzzle gets one final submission under the new policy.
    tracker.db.update("lab_runs", "id=?", (run["id"],), attempts=10)
    timing.end(tracker)
    selected = answers(run)
    selected["r1"] = not selected["r1"]
    assert labs.submit(tracker, run["id"], selected)["exercise"]["score"]["xp"] == 0


def test_permission_concurrency_and_account_boundaries(tracker, pack_data, tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    run = exercise(tracker, pack_data, "access-policy")
    selected = answers(run)
    other = Tracker(Database(tmp_path, user_id=2), clock=tracker.clock)
    other.install_pack(dump_toml(pack_data))
    with pytest.raises(ValueError, match="not found"):
        labs.view(other, run["id"])
    other.db.close()

    def submit(values):
        client = Tracker(Database(tracker.db.home), clock=tracker.clock)
        try:
            return labs.submit(client, run["id"], values)["exercise"]["score"]
        finally:
            client.db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(submit, [selected, {k: not v for k, v in selected.items()}])
        )
    assert results[0] == results[1]
    assert len(tracker.db.rows("permission_attempts")) == 1
    assert len(tracker.db.rows("xp_awards")) == 1


def test_permission_migration_preserves_existing_completion_and_xp(tracker, pack_data):
    run = exercise(tracker, pack_data, "access-policy")
    labs.submit(tracker, run["id"], answers(run))
    protected = {
        name: tracker.db.rows(name)
        for name in ["lab_runs", "task_sessions", "xp_awards", "node_state", "entries"]
    }
    tracker.db.connection.execute("DROP TABLE permission_attempts")
    tracker.db.connection.execute("UPDATE schema_version SET version=6")
    tracker.db.migrate()
    assert all(tracker.db.rows(name) == rows for name, rows in protected.items())
    receipt = labs.current(tracker, "one")
    assert receipt["passed"] and receipt["score"]["xp"] == 100
    assert all(item["selected"] is None for item in receipt["feedback"])
