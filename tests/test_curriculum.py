"""Structural curriculum contracts, not a claim of measured learner outcomes."""

import json
from pathlib import Path
import zipfile

import pytest

from ascend.engine.levels import next_nodes
from ascend.engine.packs import parse_pack
from ascend.registry import bundled_pack_path, community_root

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENTS = json.loads((ROOT / "docs/curriculum/assessment-map.json").read_text())[
    "assessments"
]
PACK_IDS = sorted({row["pack"] for row in ASSESSMENTS})


def exported_pack_path(pack_id):
    relative = bundled_pack_path(pack_id).relative_to(community_root())
    return ROOT / "tracks/cyber-tracks/packs/community" / relative


@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_curriculum_has_reachable_assessments_and_delayed_practice(pack_id):
    pack = parse_pack(bundled_pack_path(pack_id).read_text())
    nodes = {node.id: node for node in pack.nodes}
    assert pack.version == (5 if pack_id == "defensive-security-and-detection" else 4)
    assert pack.source == "ai-draft" and not pack.reviewed
    assert next_nodes(pack, {})[0].id == "lab-readiness"
    assert next_nodes(pack, {}, 10), "A brief optional session must remain possible"
    for assessment in (row for row in ASSESSMENTS if row["pack"] == pack_id):
        milestone = nodes[assessment["milestone"]]
        assert milestone.milestone
        preparatory = {
            n.id for n in pack.nodes if n.level == milestone.level and not n.milestone
        }
        assert preparatory <= set(milestone.needs), (
            "Assessment must not bypass its preparatory work"
        )
        assert assessment["variant"] in "\n".join(milestone.steps)
        assert assessment["control"] in "\n".join(milestone.steps)
        review = nodes["recall-" + assessment["level"]]
        assert review.needs == (milestone.id,)
        assert review.verify["type"] == "manual", "A file cannot grade delayed recall"
        assert review not in next_nodes(pack, {})
        assert review in next_nodes(pack, {milestone.id: "done"})
    state = {}
    while candidates := next_nodes(pack, state):
        for node in candidates:
            state[node.id] = "done"
    assert len(state) == len(pack.nodes), "No task can become permanently unreachable"
    assert not any(
        n.verify.get("type") == "command" and "--version" in n.verify.get("cmd", "")
        for n in pack.nodes
    )


@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_curriculum_upgrade_preserves_progress_without_certifying_new_checks(
    tracker, pack_id
):
    with zipfile.ZipFile(ROOT / "tracks/cyber-tracks-v2.zip") as archive:
        name = next(
            name
            for name in archive.namelist()
            if name.endswith("/" + pack_id + ".toml")
        )
        previous_text = archive.read(name).decode()
    previous = parse_pack(previous_text)
    tracker.install_pack(previous_text)
    tracker.start_mission(pack_id)
    milestone = next(n for n in previous.nodes if n.milestone)
    tracker.mark(milestone.id, "done")
    before = tracker.states(pack_id)
    text = bundled_pack_path(pack_id).read_text()
    new = parse_pack(text)
    assert {n.id for n in previous.nodes} <= {n.id for n in new.nodes}
    tracker.install_pack(text)
    assert tracker.states(pack_id) == before
    assert "lab-readiness" not in before
    assert not any(key.startswith("recall-") for key in before)
    assert text == exported_pack_path(pack_id).read_text()


def test_assessment_sources_are_traceable_and_coverage_is_complete():
    sources = {
        row["id"]: row
        for row in json.loads((ROOT / "docs/curriculum/sources.json").read_text())[
            "sources"
        ]
    }
    expected = set()
    for pack_id in PACK_IDS:
        pack = parse_pack(bundled_pack_path(pack_id).read_text())
        expected.update((pack.id, n.level, n.id) for n in pack.nodes if n.milestone)
    assert {(r["pack"], r["level"], r["milestone"]) for r in ASSESSMENTS} == expected
    assert len(ASSESSMENTS) == len(expected) == 40
    for row in ASSESSMENTS:
        for source in row["sources"]:
            assert sources[source]["status"] == 200
            assert sources[source]["limits"], (
                "Every alignment claim must carry its evidence limit"
            )


def test_specialist_catalog_has_real_assessments_and_reachable_tasks():
    source = json.loads((ROOT / "docs/curriculum/specialist-paths.json").read_text())
    sources = {
        r["id"]
        for r in json.loads((ROOT / "docs/curriculum/sources.json").read_text())[
            "sources"
        ]
    }
    cases = json.loads((ROOT / "ascend/labs/cases.json").read_text())
    assert len(source["tracks"]) == 19
    for track in source["tracks"]:
        assert set(track["sources"]) <= sources
        text = bundled_pack_path(track["id"]).read_text()
        pack = parse_pack(text)
        assert len([lv for lv in pack.levels if lv.lane == "main"]) == 8
        assert len(pack.nodes) == 34
        assert len([n for n in pack.nodes if n.verify["type"] == "lab"]) == 18
        for node in pack.nodes:
            if node.verify.get("exercise") == "case":
                case = cases[node.verify["case_id"]]
                assert case["correct"] != case["incorrect"]
            if node.milestone:
                assert len(node.steps) >= 4 and "reviewer" in node.done_when
        state = {}
        while candidates := next_nodes(pack, state):
            for node in candidates:
                state[node.id] = "done"
        assert len(state) == len(pack.nodes)
        assert text == exported_pack_path(pack.id).read_text()


def test_public_home_lab_includes_bandit_zero_and_preserves_existing_ids():
    old = parse_pack((ROOT / "tests/fixtures/home-hack-lab-v3.toml").read_text())
    pack = parse_pack(bundled_pack_path("home-hack-lab").read_text())
    nodes = {n.id: n for n in pack.nodes}
    assert {n.id for n in old.nodes} <= nodes.keys()
    assert pack.version == 4
    for i in range(33):
        assert nodes[f"bandit-{i}"].verify == {
            "type": "ctf",
            "provider": "bandit",
            "challenge": f"bandit-{i}",
        }
    assert nodes["bandit-33"].verify["challenge"] == "bandit-32"
    practice = parse_pack(bundled_pack_path("verified-security-lab").read_text())
    assert len(practice.nodes) == 8
    assert all(n.verify["type"] in {"lab", "ctf"} for n in practice.nodes)
