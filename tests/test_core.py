from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ascend.application import Tracker
from ascend.engine.packs import dump_toml
from ascend.storage import Database


@pytest.mark.parametrize("learned,proof", [("too short", None), ("a" * 32, None),
    ("I found flag{do-not-store-this} today", None),
    ("I found picoCTF{do-not-store-this}", None),
    ("I found THM{do-not-store-this} today", None),
    ("I explained the whole result today", "X" * 32)])
def test_rejects_invalid_or_secret_entries(installed, learned, proof):
    with pytest.raises(ValueError): installed.log(learned, "Next exercise", proof=proof)
    assert installed.entries() == []


def test_repeat_and_empty_next_rejected(installed):
    text = "I understood the purpose of this example"
    installed.log(text, "Practice again")
    with pytest.raises(ValueError): installed.log(text, "Another next step")
    with pytest.raises(ValueError): installed.log("I explained this different example", " ")


def test_only_one_active_mission(installed):
    with pytest.raises(ValueError): installed.start_mission("test-pack")
    installed.finish_mission()
    installed.start_mission("test-pack")


def test_database_idempotent(tmp_path, now):
    t = Tracker(Database(tmp_path), clock=lambda: now)
    t.new_mission("Learn a new skill")
    t.log("I saved a working example and explained it", "Try the next exercise")
    t.db.close()
    other = Tracker(Database(tmp_path), clock=lambda: now)
    assert len(other.entries()) == 1
    assert (tmp_path / "ascend.db").exists()
    assert other.db.connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert other.db.connection.execute("SELECT version FROM schema_version").fetchone()[0] >= 2


def test_backfill_has_no_streak(installed):
    installed.backfill(["one", "small"])
    assert installed.states("test-pack")["one"]["how"] == "manual"
    assert installed.entries() == []
    assert installed.stats()["current_streak"] == 0


def test_partial_and_complete(installed):
    installed.log("I tried one part of the exercise today", "Finish the remaining part")
    assert installed.states("test-pack").get("one", {}).get("status", "todo") == "todo"
    installed.log("I finished and explained the whole exercise", "Start the second task", complete=True)
    assert installed.states("test-pack")["one"]["status"] == "done"


def test_failing_file_and_force(tracker, pack_data):
    pack_data["node"][0]["verify"] = {"type": "file", "path": "/nonexistent/ascend-test-file"}
    tracker.install_pack(dump_toml(pack_data)); tracker.start_mission("test-pack")
    result = tracker.log("I worked on the first part of this task", "Finish the file", complete=True)
    assert not result["completed"]
    assert tracker.states("test-pack").get("one", {}).get("status", "todo") == "todo"
    tracker.log("I finished this on a different computer", "Continue to task two", complete=True, force="Checked the other machine")
    assert tracker.states("test-pack")["one"]["how"] == "forced"


def test_active_days_and_minutes(installed):
    installed.log("I understood the first worked example", "Another example", minutes=12)
    installed.log("I checked my explanation against the result", "Another exercise", minutes=8)
    assert installed.levels()[0]["active_days"] == 1
    assert installed.levels()[0]["minutes"] == 20


def test_unlock_is_audited(installed):
    installed.unlock("second")
    assert installed.levels()[1]["open"] is True
    assert installed.db.rows("audit")[-1]["action"] == "unlock"


def test_verifier_evidence_uses_actual_day(tracker, pack_data, tmp_path, now):
    import os
    evidence = tmp_path / "evidence.txt"; evidence.write_text("My real working artifact")
    happened = now - timedelta(days=1)
    os.utime(evidence, (happened.timestamp(), happened.timestamp()))
    pack_data["node"][0]["verify"] = {"type": "file", "path": str(evidence)}
    tracker.install_pack(dump_toml(pack_data)); tracker.start_mission("test-pack")
    tracker.check(confirm=True)
    assert tracker.entries()[0]["day"] == "2026-11-04"
    assert tracker.entries()[0]["source"] == "verifier:file"
