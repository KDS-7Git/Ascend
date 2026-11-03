from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from ascend import checkpoints, timing
from ascend.application import Tracker
from ascend.cli import execute, parser
from ascend.engine.packs import PackError, dump_toml, parse_pack
from ascend.server.app import create_app
from ascend.storage import Database


PART = {
    "id": "predict",
    "title": "Predict one result",
    "minutes": 10,
    "done_when": "Write a prediction and compare it against one controlled observation.",
    "next_step": "Complete the remaining observations and review the parent finish line.",
}


def prepare(tracker, pack_data):
    pack_data["node"][0]["checkpoints"] = [PART]
    pack_data["node"][0]["verify"] = {"type": "lab", "exercise": "integrity"}
    tracker.install_pack(dump_toml(pack_data))
    tracker.start_mission("test-pack")
    return tracker


def test_checkpoint_keeps_full_task_clock_receipt_and_reward(tracker, pack_data):
    t = prepare(tracker, pack_data)
    timing.start(t, "one")
    before = {
        name: deepcopy(t.db.rows(name))
        for name in (
            "node_state",
            "task_sessions",
            "lab_runs",
            "xp_awards",
            "level_unlocks",
        )
    }
    overview = t.overview(10)
    assert overview["next"]["estimate"] == 120
    assert overview["checkpoint"]["checkpoint"]["minutes"] == 10
    assert t.overview(5)["checkpoint"] is None
    learned = "I compared one observed outcome against my written prediction."
    result = checkpoints.record(t, "one", "predict", learned, 10)
    assert not result["parent_completed"]
    assert checkpoints.record(t, "one", "predict", learned, 10) == result
    for name, rows in before.items():
        assert t.db.rows(name) == rows
    assert len(t.entries()) == 1 and not t.entries()[0]["complete"]
    assert t.overview(10)["checkpoint"] is None
    assert checkpoints.list_for(t, "one")["checkpoints"][0]["saved"]
    t.undo()
    assert not t.db.rows("node_checkpoints")
    assert t.overview(10)["checkpoint"] is not None


def test_checkpoint_requires_open_parent_and_correct_user(tracker, pack_data):
    t = prepare(tracker, pack_data)
    with pytest.raises(ValueError, match="No such"):
        checkpoints.record(t, "one", "absent", "A sufficiently long observation.")
    t.mark("one", "skipped")
    with pytest.raises(ValueError, match="open, unfinished"):
        checkpoints.record(t, "one", "predict", "A sufficiently long observation.")


@pytest.mark.parametrize(
    "change",
    [
        {"minutes": True},
        {"minutes": 120},
        {"minutes": 0},
        {"id": "invalid id"},
        {"done_when": "done"},
        {"surprise": True},
    ],
)
def test_checkpoint_authoring_rejects_invalid_metadata(pack_data, change):
    pack_data["node"][0]["checkpoints"] = [PART | change]
    with pytest.raises(PackError):
        parse_pack(dump_toml(pack_data))


def test_checkpoint_cli_api_and_private_pack_preservation(tmp_path, pack_data):
    t = prepare(Tracker(Database(tmp_path)), pack_data)
    saved_pack = t.pack("test-pack")
    detail = execute(t, parser().parse_args(["checkpoint", "list", "one"]))
    assert detail["full_minutes"] == 120
    with TestClient(create_app(tmp_path, scheduler=False)) as client:
        assert client.get("/api/nodes/test-pack:one/checkpoints").json() == detail
        result = client.post(
            "/api/nodes/test-pack:one/checkpoints/predict",
            json={
                "learned": "I recorded a prediction with the matching observation.",
                "minutes": 8,
            },
        )
        assert result.json()["saved"]
        assert client.get("/api/me?minutes=10").json()["checkpoint"] is None
    assert t.pack("test-pack") == saved_pack
    t.db.close()
