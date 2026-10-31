from copy import deepcopy
from pathlib import Path

import pytest

from ascend.engine.packs import PackError, dump_toml, parse_pack
from ascend.engine.levels import next_nodes, open_levels


@pytest.mark.parametrize("defect", ["duplicate", "done_when", "needs", "cycle", "size", "url", "level", "no-main", "kind", "missing-kind", "verify"])
def test_lint_rejects_invalid_packs(pack_data, defect):
    n = pack_data["node"][0]
    if defect == "duplicate": pack_data["node"].append(deepcopy(n))
    elif defect == "done_when": del n["done_when"]
    elif defect == "needs": n["needs"] = ["missing"]
    elif defect == "cycle": n["needs"] = ["two"]; pack_data["node"][1]["needs"] = ["one"]
    elif defect == "size": n["size"] = "XXL"
    elif defect == "url": n["resource"] = "TODO"
    elif defect == "level": n["level"] = "missing"
    elif defect == "no-main":
        for lv in pack_data["level"]: lv["lane"] = "side"
    elif defect == "kind": pack_data["pack"]["kind"] = "unknown"
    elif defect == "missing-kind": del pack_data["pack"]["kind"]
    elif defect == "verify": n["verify"] = {"type": "unknown"}
    with pytest.raises(PackError): parse_pack(dump_toml(pack_data))


def test_series_expansion(pack_data):
    n = pack_data["node"][2]
    n.update(id="bandit", series={"from": 13, "to": 15}, title="Level {n}",
             done_when="I can explain how I got to level {next}")
    nodes = parse_pack(dump_toml(pack_data)).nodes[2:]
    assert [n.id for n in nodes] == ["bandit-13", "bandit-14", "bandit-15"]
    assert [n.needs for n in nodes] == [(), ("bandit-13",), ("bandit-14",)]
    assert nodes[0].title == "Level 13"
    assert nodes[-1].done_when.endswith("16")


def test_next_nodes_filtering(pack_data):
    pack = parse_pack(dump_toml(pack_data))
    assert [n.id for n in next_nodes(pack, {})] == ["one", "small"]
    assert [n.id for n in next_nodes(pack, {"one": "done", "small": "skipped"})] == ["two"]
    assert [n.id for n in next_nodes(pack, {}, 30)] == ["small"]
    assert next_nodes(pack, {}, 20) == []


def test_gates_and_side_lane(pack_data):
    pack = parse_pack(dump_toml(pack_data))
    assert open_levels(pack, set()) == {"first", "anytime"}
    assert "second" not in open_levels(pack, {"small"})
    assert "second" in open_levels(pack, {"one"})
    assert "second" in open_levels(pack, set(), {"second"})
    pack_data["level"][1]["gate"] = False
    assert "second" in open_levels(parse_pack(dump_toml(pack_data)), set())


def test_milestone_gate_does_not_require_every_exercise(pack_data):
    milestone = deepcopy(pack_data["node"][0])
    milestone.update(id="exam", milestone=True)
    pack_data["node"].append(milestone)
    pack = parse_pack(dump_toml(pack_data))
    assert "second" not in open_levels(pack, {"one"})
    assert "second" in open_levels(pack, {"exam"})


def test_proficiency_needs_milestones(pack_data):
    pack_data["pack"]["kind"] = "proficiency"
    with pytest.raises(PackError, match="milestone|8"):
        parse_pack(dump_toml(pack_data))


def test_pack_update_preserves_progress(installed, pack_data):
    installed.backfill(["one"])
    pack_data["node"].reverse()
    extra = deepcopy(pack_data["node"][0]); extra["id"] = "extra"
    pack_data["node"].append(extra)
    installed.install_pack(dump_toml(pack_data))
    assert installed.states("test-pack")["one"]["status"] == "done"


def test_engine_is_subject_agnostic():
    for path in Path("ascend/engine").rglob("*.py"):
        source = path.read_text().lower()
        assert all(word not in source for word in ("bandit", "juice", "overthewire")), path


def test_sample_pack_lints_and_keeps_placeholder_vars():
    pack = parse_pack(Path("packs/community/home-hack-lab.toml").read_text())
    assert pack.vars["pi_ip"] == "192.168.1.50"
    assert pack.vars["hack_dir"] == "~/hack"
