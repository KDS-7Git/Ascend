from copy import deepcopy

import pytest

from ascend.local_labs.catalog import detail, review_gaps
from ascend.local_labs.checks import local_report, outcome
from ascend.local_labs.docker import Docker
from ascend.local_labs.runtime import Runtime


def test_foreign_resources_cannot_be_deleted(tracker, tmp_path, monkeypatch):
    runtime = Runtime(tracker, root=tmp_path / "labs")
    docker = Docker(runtime)
    row = {"owner": "this-profile", "id": "a" * 32, "recipe": {"id": "vampi-ownership"}}
    monkeypatch.setattr(docker, "inspect", lambda *_: {"Config": {"Labels": {"org.ascend.owner": "other-profile"}}})
    monkeypatch.setattr(docker, "run", lambda *_: pytest.fail("Unowned resource was modified"))
    with pytest.raises(ValueError, match="unowned"):
        docker.remove("container", "some-container", row)


def test_remote_docker_context_is_rejected(tracker, tmp_path, monkeypatch):
    docker = Docker(Runtime(tracker, root=tmp_path / "labs"))
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    monkeypatch.setenv("DOCKER_HOST", "tcp://remote.invalid:2375")
    monkeypatch.setattr(docker, "run", lambda *_: pytest.fail("Remote daemon was contacted"))
    with pytest.raises(ValueError, match="local Unix-socket"):
        docker.provider()


def test_missing_image_pins_and_incomplete_reports_cannot_pass():
    recipe = deepcopy(detail("vampi-ownership"))
    recipe["image"]["reference"] = "erev0s/vampi:latest"
    assert "Container image digest is not pinned" in review_gaps(recipe)
    for checks in ([], [{"id": "made-up", "status": "pass"}], [{"id": name, "status": True} for name in recipe["check_ids"]]):
        with pytest.raises(ValueError):
            local_report({"checks": checks}, recipe)
    result = local_report({"checks": [{"id": name, "status": "pass"} for name in recipe["check_ids"]]}, recipe)
    assert result["status"] == "pass" and result["authority"] == "local"
    assert not result["satisfies_track_evidence"]
    assert outcome([])["status"] == "unsupported"
    assert outcome([{"id": "check", "status": "unrecognized"}])["status"] == "error"
