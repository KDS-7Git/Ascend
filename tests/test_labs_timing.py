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


def test_timer_pause_resume_late_reward_and_reminders(tracker, pack_data, now):
    run = exercise(tracker, pack_data, "integrity")
    budget = timing.summary(tracker)["active"]["budget_seconds"]
    tracker.clock = lambda: now + timedelta(seconds=budget * 0.75)
    sent = []
    assert timing.reminders(tracker, lambda m: sent.append(m))["notice"] == 1
    assert not timing.reminders(tracker, lambda m: sent.append(m))["sent"]
    timing.pause(tracker)
    tracker.clock = lambda: now + timedelta(days=1)
    assert timing.summary(tracker)["paused"][0]["elapsed_seconds"] == int(budget * 0.75)
    timing.start(tracker, "test-pack:one", minutes=1)
    assert timing.summary(tracker)["active"]["budget_seconds"] == budget
    tracker.clock = lambda: now + timedelta(days=1, seconds=budget * 0.25)
    assert timing.reminders(tracker, lambda m: sent.append(m))["notice"] == 2
    assert len(sent) == 2
    # A fresh instance preserves accumulated session time while replacing expired exercise data.
    run = labs.start(tracker, "test-pack:one", fresh=True)
    tracker.clock = lambda: now + timedelta(days=1, seconds=budget * 1.25)
    labs.submit(tracker, run["id"], answers(run))
    assert timing.summary(tracker)["xp"] == 50
    assert not timing.reminders(tracker, lambda m: sent.append(m))["sent"]
    assert timing.points(budget * 100, budget) == 25


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
    selected = next(
        k for k, v in run["choices"].items() if v.startswith("Record preparation")
    )
    assert labs.submit(tracker, run["id"], {"choice": selected})["completed"]


def test_boolean_cannot_impersonate_numeric_answer(tracker, pack_data):
    run = exercise(tracker, pack_data, "logging")
    labs.emit(tracker, run["id"], "ok")
    run = labs.emit(tracker, run["id"], "error")
    candidate = answers(run)
    candidate["errors"] = True
    assert not labs.submit(tracker, run["id"], candidate)["ok"]
