from copy import deepcopy
from pathlib import Path

import pytest

from ascend.engine.levels import next_nodes, open_levels
from ascend.engine.packs import PackError, dump_toml, parse_pack


def test_challenge_guidance_is_optional_and_substitutes_variables(pack_data):
    original = parse_pack(dump_toml(pack_data)).nodes[0]
    assert (original.brief, original.steps, original.hints) == ("", (), ())
    pack_data["vars"] = {"lab": "local lab"}
    pack_data["node"][0].update(
        brief="Investigate the {lab}.",
        steps=["Open the {lab}.", "Compare two results."],
        hints=["Inspect one input at a time."],
        resource_label="Free {lab} reference",
        resource_note="This reference is optional.",
        setup="Use the {lab} before starting the timer.",
        preview="Explore the {lab}.",
        requirements="A browser for the {lab}.",
        materials=[{"label": "Inputs for {lab}", "url": "/training/example.zip"}],
    )
    node = parse_pack(dump_toml(pack_data)).nodes[0]
    assert node.brief == "Investigate the local lab."
    assert node.steps == ("Open the local lab.", "Compare two results.")
    assert node.hints == ("Inspect one input at a time.",)
    assert node.resource_label == "Free local lab reference"
    assert node.resource_note == "This reference is optional."
    assert node.setup == "Use the local lab before starting the timer."
    assert node.preview == "Explore the local lab."
    assert node.requirements == "A browser for the local lab."
    assert node.materials == (
        {"label": "Inputs for local lab", "url": "/training/example.zip"},
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("brief", 2),
        ("resource_label", 2),
        ("resource_note", ["not text"]),
        ("setup", 5),
        ("preview", 5),
        ("requirements", []),
        ("materials", "not a list"),
        ("steps", "not a list"),
        ("steps", [""]),
        ("hints", [42]),
        ("hints", [" "]),
    ],
)
def test_invalid_challenge_guidance_is_rejected(pack_data, field, value):
    pack_data["node"][0][field] = value
    with pytest.raises(PackError, match=field):
        parse_pack(dump_toml(pack_data))


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "//example.com/file.zip",
        "/training/../secret.zip",
        "/training/%2e%2e/secret.zip",
        "/private.json",
    ],
)
def test_material_urls_cannot_escape_bundled_training_path(pack_data, url):
    pack_data["node"][0]["materials"] = [{"label": "Inputs", "url": url}]
    with pytest.raises(PackError, match="Materials"):
        parse_pack(dump_toml(pack_data))


@pytest.mark.parametrize(
    "defect",
    [
        "duplicate",
        "done_when",
        "needs",
        "cycle",
        "size",
        "url",
        "level",
        "no-main",
        "kind",
        "missing-kind",
        "verify",
    ],
)
def test_lint_rejects_invalid_packs(pack_data, defect):
    n = pack_data["node"][0]
    if defect == "duplicate":
        pack_data["node"].append(deepcopy(n))
    elif defect == "done_when":
        del n["done_when"]
    elif defect == "needs":
        n["needs"] = ["missing"]
    elif defect == "cycle":
        n["needs"] = ["two"]
        pack_data["node"][1]["needs"] = ["one"]
    elif defect == "size":
        n["size"] = "XXL"
    elif defect == "url":
        n["resource"] = "TODO"
    elif defect == "level":
        n["level"] = "missing"
    elif defect == "no-main":
        for lv in pack_data["level"]:
            lv["lane"] = "side"
    elif defect == "kind":
        pack_data["pack"]["kind"] = "unknown"
    elif defect == "missing-kind":
        del pack_data["pack"]["kind"]
    elif defect == "verify":
        n["verify"] = {"type": "unknown"}
    with pytest.raises(PackError):
        parse_pack(dump_toml(pack_data))


def test_series_expansion(pack_data):
    n = pack_data["node"][2]
    n.update(
        id="bandit",
        series={"from": 13, "to": 15},
        title="Level {n}",
        done_when="I can explain how I got to level {next}",
    )
    nodes = parse_pack(dump_toml(pack_data)).nodes[2:]
    assert [n.id for n in nodes] == ["bandit-13", "bandit-14", "bandit-15"]
    assert [n.needs for n in nodes] == [(), ("bandit-13",), ("bandit-14",)]
    assert nodes[0].title == "Level 13"
    assert nodes[-1].done_when.endswith("16")


def test_next_nodes_filtering(pack_data):
    pack = parse_pack(dump_toml(pack_data))
    assert [n.id for n in next_nodes(pack, {})] == ["one", "small"]
    assert [n.id for n in next_nodes(pack, {"one": "done", "small": "skipped"})] == [
        "two"
    ]
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
    extra = deepcopy(pack_data["node"][0])
    extra["id"] = "extra"
    pack_data["node"].append(extra)
    installed.install_pack(dump_toml(pack_data))
    assert installed.states("test-pack")["one"]["status"] == "done"


def test_engine_is_subject_agnostic():
    for path in Path("ascend/engine").rglob("*.py"):
        source = path.read_text().lower()
        assert all(word not in source for word in ("bandit", "juice", "overthewire")), (
            path
        )


def test_sample_pack_lints_and_keeps_placeholder_vars():
    pack = parse_pack(Path("packs/community/projects/home-hack-lab.toml").read_text())
    assert pack.vars["pi_ip"] == "lab-host.local"
    assert pack.vars["hack_dir"] == "~/ascend-lab"
