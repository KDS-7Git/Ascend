import json
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from ascend.local_labs.catalog import executable
from ascend.local_labs.runtime import Runtime
from ascend.local_labs.upstream import plan, report_recipe, validate_report
from ascend.server.app import create_app

NAMES = ["kubernetes-goat-rbac", "cloudfoxable-secret", "mastg-android-storage", "mbe-intro-reversing", "llm-agent-transactions"]


def observations(recipe):
    report = deepcopy(recipe["report_template"])
    for field in recipe["environment_fields"]:
        if field != "source_revision":
            report["environment"][field] = "a" * 64 if field in recipe["digest_environment_fields"] else "test environment"
    if "trial_count" in report["environment"]:
        report["environment"]["trial_count"] = "3"
    for check in report["checks"]:
        check["status"] = "pass"
    return report


@pytest.mark.parametrize("name", NAMES)
def test_specialist_reports_are_manual_and_cannot_enable_runtime(name):
    recipe = report_recipe(name)
    assert not plan(name)["commands_are_executed"] and not plan(name)["runnable"]
    with pytest.raises(ValueError, match="reviewed executable"):
        executable(name)
    report = observations(recipe)
    result = validate_report(recipe, report)
    assert result["status"] == "pass"
    assert result["evidence_label"] == "Practice recorded (manual observations)"
    assert result["authority"] == "local" and result["xp"] == 0 and not result["satisfies_track_evidence"]
    for bad in ({**report, "exit_code": 0}, {**report, "checks": []}, {**report, "passed": True}, {**report, "environment": {}},
                {**report, "environment": {**report["environment"], "source_revision": "0" * 40}},
                {**report, "environment": {**report["environment"], "api_key": "must stay local"}}):
        with pytest.raises(ValueError):
            validate_report(recipe, bad)


def test_model_observations_require_pins_and_repeated_trials():
    recipe = report_recipe("llm-agent-transactions")
    report = observations(recipe)
    for change in ({"model_sha256": "latest"}, {"trial_count": "1"}, {"trial_count": True}, {"dependency_lock_sha256": "unlocked"}):
        with pytest.raises(ValueError):
            validate_report(recipe, {**report, "environment": {**report["environment"], **change}})
    report["checks"][0]["status"] = "unsupported"
    assert validate_report(recipe, report)["status"] == "unsupported"


def test_cloud_report_sync_does_not_launch_or_contact_a_provider(tracker, tmp_path, monkeypatch):
    recipe = report_recipe("cloudfoxable-secret")
    path = tmp_path / "observations.json"
    path.write_text(json.dumps(observations(recipe)))
    runtime = Runtime(tracker, root=tmp_path / "labs", server="http://testserver")
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: pytest.fail("A provider process was launched"))
    with TestClient(create_app(tmp_path / "remote", scheduler=False)) as client:
        def remote(endpoint, data=None, server=None):
            response = client.get(endpoint) if data is None else client.post(endpoint, json=data)
            assert response.status_code == 200, response.text
            return response.json()
        monkeypatch.setattr(runtime, "_remote", remote)
        result = runtime.record(recipe["id"], path)
        assert result["kind"] == "external-report" and result["resources"] == {}
        assert result["remote_receipt"]["result"]["evidence_label"] == "Practice recorded (manual observations)"
        assert result["remote_receipt"]["started_at"] is None
        assert client.get("/api/stats").json()["xp"]["total"] == 0
        assert client.post("/api/lab-attempts", json={"recipe_id": recipe["id"]}).status_code == 400
        runtime.prune(0)
        assert path.is_file()
