import json
from copy import deepcopy

import pytest

from ascend.local_labs import bgp
from ascend.local_labs.catalog import detail, review_gaps


@pytest.mark.parametrize("filtered", [False, True])
def test_route_observation_waits_for_updates_and_stable_controls(monkeypatch, filtered):
    lab = object.__new__(bgp.BgpLab)
    clock = [0.0]
    monkeypatch.setattr(bgp.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        bgp.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    )
    lab.established = lambda *_: True

    def command(*_):
        # Establishment precedes the first route update; a withdrawn route can
        # also reappear briefly while an earlier update is being processed.
        routes = {}
        if clock[0] >= 0.6:
            routes["192.168.42.0/24"] = []
        if filtered and clock[0] < 1.6:
            routes["10.0.0.1/32"] = []
        return json.dumps({"routes": routes})

    lab.command = command
    table, settled = lab.observe_routes({}, "x1", filtered=filtered)
    assert settled and "192.168.42.0/24" in table["routes"]
    assert clock[0] >= (2.6 if filtered else 1.6)


def test_last_moment_route_update_is_not_a_stable_pass(monkeypatch):
    lab = object.__new__(bgp.BgpLab)
    clock = [0.0]
    monkeypatch.setattr(bgp.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        bgp.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    )
    lab.established = lambda *_: True
    lab.command = lambda *_: json.dumps(
        {"routes": {"192.168.42.0/24": []} if clock[0] >= 0.9 else {}}
    )
    _, settled = lab.observe_routes({}, "x1", timeout=1)
    assert not settled


def test_malformed_router_output_is_an_environment_error():
    lab = object.__new__(bgp.BgpLab)
    lab.command = lambda *_: '{"routes": []}'
    with pytest.raises(ValueError, match="route table"):
        lab.observe_routes({}, "x1")


def test_bgp_requires_image_adapter_license_and_lifecycle_review():
    recipe = deepcopy(detail("bgp-single-session"))
    for key, replacement, expected in (
        (
            "image",
            {"reference": "frrouting/frr:latest"},
            "Container image digest is not pinned",
        ),
        ("adapter_sha256", "", "BGP adapter and launcher need reviewed hashes"),
        ("launcher_sha256", "", "BGP adapter and launcher need reviewed hashes"),
        ("frr_source_revision", "main", "FRR image source and license need review"),
        (
            "lifecycle_verified",
            False,
            "Lifecycle and negative/control tests need evidence",
        ),
    ):
        assert expected in review_gaps({**recipe, key: replacement})
