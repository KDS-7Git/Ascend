"""Cross-subject reasoning, observed review behavior and bounded track sessions."""

from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient

from ascend.playground import catalog, fixtures
from ascend.server.app import create_app


def complete(t, activity_id):
    run = t.playground.start(activity_id, deliberate=True)
    fixture = json.loads(t.playground.owned(run["id"])["fixture"])
    return t.playground.submit(
        run["id"],
        fixture["expected"],
        f"I tested the controls for {activity_id}",
        "Try a new condition",
    )


@pytest.mark.parametrize(
    "domain,skill,easy,changed,mystery",
    [
        ("python", "python", "python-trace", "python-boundary", "desk-39"),
        ("3d", "spatial", "spatial-translate", "spatial-order", "studio-52"),
    ],
)
def test_subjects_prepare_then_apply_without_changing_track(
    installed, domain, skill, easy, changed, mystery
):
    t = installed
    before = t.active_mission(), deepcopy(t.states("test-pack"))
    result = t.playground.recommendations(5, domain=domain)
    assert result["activities"][0]["id"] == f"example-{skill}"
    assert all(a["domain"] == domain for a in result["activities"])
    assert not t.playground.detail(mystery)["recommended_ready"]
    complete(t, f"example-{skill}")
    complete(t, easy)
    complete(t, changed)
    assert t.playground.detail(mystery)["recommended_ready"]
    assert not t.playground.detail("room-63")["recommended_ready"]
    assert (t.active_mission(), t.states("test-pack")) == before
    assert (
        t.playground.list(domain=domain, minutes=1)["alternatives"][0]["domain"]
        == domain
    )


@pytest.mark.parametrize("iteration", range(10))
def test_python_exercises_match_the_authored_program(now, iteration):
    fixture = fixtures.generate(catalog.get("python-boundary"), now)
    public = fixture["public"]
    printed = []
    scope = {
        "values": public["data"]["values"],
        "print": printed.append,
        "__builtins__": {},
    }
    exec(public["data"]["code"], scope)
    selected = printed[0]
    assert fixture["expected"]["count"] == len(selected)
    assert fixture["expected"]["total"] == sum(selected)
    assert fixture["expected"]["first"] == selected[0]
    printed.clear()
    exec(public["data"]["code"].replace(">=", ">"), scope)
    assert fixture["expected"]["strict_count"] == len(printed[0])


@pytest.mark.parametrize("variant", range(3))
def test_programming_mystery_observations_and_predictions_are_reproducible(
    now, variant
):
    fixture = fixtures.generate(catalog.get("desk-39"), now, variant)
    scope = {"__builtins__": {}}
    exec(fixture["public"]["data"]["code"], scope)
    for test in fixture["public"]["data"]["captured_tests"]:
        assert len(scope["images"](test["input"])) == test["output_count"]
    assert (
        len(scope["images"](["x.png", "y.PNG", "z.png"]))
        == fixture["expected"]["prediction"]
    )
    assert fixture["expected"]["control"] == 0


@pytest.mark.parametrize("iteration", range(10))
def test_spatial_composition_and_framing_match_homogeneous_coordinates(now, iteration):
    fixture = fixtures.generate(catalog.get("spatial-order"), now)
    data = fixture["public"]["data"]
    point = [*data["local_xyz"], 1]
    s, delta = data["scale"], data["translation_xyz"]
    transform = [
        [s, 0, 0, delta[0]],
        [0, s, 0, delta[1]],
        [0, 0, s, delta[2]],
        [0, 0, 0, 1],
    ]
    expected = [sum(a * b for a, b in zip(row, point)) for row in transform]
    assert [fixture["expected"][axis] for axis in ("x", "y", "z")] == expected[:3]
    changed = [fixture["expected"][f"changed_{axis}"] for axis in ("x", "y", "z")]
    assert changed != expected[:3]
    scene = fixtures.generate(catalog.get("scene-layout"), now)
    data = scene["public"]["data"]
    world = [
        [
            v * data["scale"] + d
            for v, d in zip(obj["local_xyz"], data["translation_xyz"])
        ]
        for obj in data["objects"]
    ]
    assert scene["expected"]["visible_count"] == sum(
        -5 <= p[0] <= 5 and -5 <= p[1] <= 5 for p in world
    )


@pytest.mark.parametrize("id", ["desk-39", "studio-52"])
def test_new_mysteries_keep_rubrics_private_and_preserve_reveals(tracker, id):
    t = tracker
    for _ in range(3):
        run = t.playground.start(id, deliberate=True)
        assert not run["familiar"] and "solution" not in run and "debrief" not in run
        t.playground.end(run["id"])
        t.playground.reveal(run["id"])
    replay = t.playground.start(id, deliberate=True)
    assert replay["familiar"]
    t.playground.end(replay["id"])
    assert complete(t, id)["result"]["xp"] == 0


def test_domain_filters_work_through_http_and_remote_command(tmp_path):
    client = TestClient(create_app(tmp_path, scheduler=False))
    listing = client.get("/api/playground?domain=python").json()["activities"]
    assert len(listing) == 6 and all(a["domain"] == "python" for a in listing)
    listing = client.post(
        "/api/command", json={"argv": ["playground", "list", "--domain", "3d"]}
    ).json()["activities"]
    assert len(listing) == 6 and all(a["domain"] == "3d" for a in listing)
    recommendation = client.post(
        "/api/command", json={"argv": ["practice", "5", "--domain", "3d"]}
    ).json()
    assert recommendation["activities"][0]["id"] == "example-spatial"
