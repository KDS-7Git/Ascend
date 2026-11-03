import json

import pytest
from fastapi.testclient import TestClient

from ascend.local_labs.catalog import executable
from ascend.local_labs.runtime import Runtime
from ascend.local_labs.upstream import (
    SUPPORTED,
    plan,
    read_report,
    report_recipe,
    validate_report,
)
from ascend.server.app import create_app


def test_external_plans_remain_explicit_and_native_bgp_is_reviewed():
    native_bgp = {"bgp-single-session", "bgp-session-protection", "bgp-prefix-filter"}
    for name in SUPPORTED:
        item = plan(name)
        assert not item["commands_are_executed"]
        assert item["runnable"] == (name in native_bgp)
        assert len(item["source"]["revision"]) == 40
        if item["capability"]:
            assert not item["capability"]["automatic_execution"]
            assert item["capability"]["runtime_acceptance"]
        else:
            assert item["setup"]["requires_vm"]
        if name in native_bgp:
            assert executable(name)["adapter"] == "frr-bgp-v1"
        else:
            with pytest.raises(ValueError, match="reviewed executable"):
                executable(name)


def test_actual_labtainers_shape_uses_only_current_goals(tmp_path):
    recipe = report_recipe("labtainers-telnetlab")
    path = tmp_path / "grades.json"
    data = {
        "learner.telnetlab": {
            "grades": {"telnetview": True, "sshview": True, "historical_goal": True},
            "parameter": {"FSTRING": "synthetic"},
        }
    }
    path.write_text(json.dumps(data))
    report = read_report(recipe, path)
    assert {c["id"] for c in report["checks"]} == {"telnetview", "sshview"}
    result = validate_report(recipe, report)
    assert result["status"] == "pass" and result["authority"] == "local"
    data["learner.telnetlab"]["grades"]["sshview"] = False
    path.write_text(json.dumps(data))
    assert validate_report(recipe, read_report(recipe, path))["status"] == "fail"
    del data["learner.telnetlab"]["grades"]["sshview"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="missing"):
        read_report(recipe, path)


def test_no_goals_or_bare_pytest_failure_never_produce_a_grade():
    recipe = report_recipe("labtainers-network-basics")
    assert (
        validate_report(recipe, {"exercise": "network-basics", "checks": []})["status"]
        == "unsupported"
    )
    recipe = report_recipe("restaurant-profile-repair")
    report = {
        "exercise": recipe["integration"]["exercise"],
        "upstream_exploit_exit": 1,
        "upstream_unit_exit": 0,
    }
    assert validate_report(recipe, report)["status"] == "unsupported"


def test_netlab_exit_contract_and_named_check_set():
    recipe = report_recipe("bgp-prefix-filter")
    report = {
        "exercise": "policy/3-prefix",
        "exit_code": 0,
        "checks": [{"id": name, "status": "pass"} for name in recipe["check_ids"]],
    }
    assert validate_report(recipe, report)["status"] == "pass"
    for code in (2, 3):
        assert (
            validate_report(recipe, {**report, "exit_code": code})["status"]
            == "unsupported"
        )
    assert validate_report(recipe, {**report, "exit_code": 4})["status"] == "error"
    with pytest.raises(ValueError, match="Missing"):
        validate_report(recipe, {**report, "checks": []})
    with pytest.raises(ValueError, match="disagree"):
        validate_report(recipe, {**report, "exit_code": 1})
    report["checks"][-1]["status"] = "fail"
    assert validate_report(recipe, {**report, "exit_code": 1})["status"] == "fail"


def test_record_saves_locally_and_syncs_without_launching(
    tracker, tmp_path, monkeypatch
):
    recipe = report_recipe("bgp-single-session")
    path = tmp_path / "report.json"
    path.write_text(
        json.dumps(
            {
                "exercise": "basic/1-session",
                "exit_code": 0,
                "checks": [{"id": "session.x1", "status": "pass"}],
            }
        )
    )
    runtime = Runtime(tracker, root=tmp_path / "companion", server="http://testserver")
    with TestClient(create_app(tmp_path / "server", scheduler=False)) as client:

        def remote(endpoint, data=None, server=None):
            response = (
                client.get(endpoint)
                if data is None
                else client.post(endpoint, json=data)
            )
            if response.status_code != 200:
                raise ValueError(response.text)
            return response.json()

        monkeypatch.setattr(runtime, "_remote", remote)
        monkeypatch.setattr(
            "subprocess.Popen",
            lambda *_args, **_kwargs: pytest.fail("A runtime was launched"),
        )
        recorded = runtime.record(recipe["id"], path)
        assert (
            recorded["kind"] == "external-report" and recorded["status"] == "recorded"
        )
        assert recorded["resources"] == {} and not recorded["pending_sync"]
        receipt = recorded["remote_receipt"]
        assert receipt["started_at"] is None and receipt["origin"] == "offline"
        assert (
            receipt["result"]["authority"] == "local" and receipt["result"]["xp"] == 0
        )
        assert not receipt["result"]["satisfies_track_evidence"]
        runtime.prune(0)
        assert path.is_file()
        # A native BGP attempt is now allowed, while report imports still launch
        # no provider and keep their offline/local evidence authority.
        assert (
            client.post(
                "/api/lab-attempts", json={"recipe_id": recipe["id"]}
            ).status_code
            == 200
        )
