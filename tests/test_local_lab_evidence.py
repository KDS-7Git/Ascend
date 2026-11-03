import copy

import pytest
from fastapi.testclient import TestClient

from ascend.local_labs import evidence
from ascend.local_labs.assets import atomic_json
from ascend.local_labs.catalog import detail
from ascend.local_labs.runtime import Runtime
from ascend.local_labs.upstream import validate_report
from ascend.server.app import create_app


def fixture(recipe):
    sample = evidence.template(recipe)
    env = sample["environment"]
    for key in env:
        if not env[key]:
            env[key] = (
                "a" * 64
                if key in recipe.get("digest_environment_fields", [])
                else "3"
                if key == "trial_count"
                else "test-environment"
            )
    profile = evidence.PROFILES[recipe["id"]]
    artifacts = {}
    for name in evidence.artifact_names(recipe):
        data = copy.deepcopy(sample["artifacts"][name])
        if profile == "labtainers":
            data = {
                "learner." + recipe["integration"]["exercise"]: {
                    "grades": {"telnetview": True, "sshview": True}
                }
            }
        elif profile == "http":
            data["request"].update(
                actor_id="owner", owner_id="owner", object_id="first"
            )
            data.update(
                response_status=200,
                before={"email": "old"},
                after={"email": "new"},
                submitted_email="new",
            )
            if name == "changed_object_owner_allowed":
                data["request"]["object_id"] = "second"
            if name in {"cross_user_update_denied", "anonymous_denied"}:
                data["request"]["actor_id"] = (
                    "other" if name.startswith("cross") else "anonymous"
                )
                data["response_status"] = 403
                data["after"] = {"email": "old"}
        elif profile == "kubernetes":
            data.update(
                context="owned-test-cluster", service_account="superadmin", stdout="yes"
            )
            if name == "restricted_account_control_observed":
                data.update(service_account="limited", stdout="no")
            elif name == "cluster_role_binding_removed":
                data.update(resource="clusterrolebinding/superadmin", stdout="")
            elif name == "cluster_teardown_recorded":
                data.update(resource="owned-cluster", stdout="absent")
        elif profile == "aws":
            arn = "arn:aws:ssm:test-region:123456789012:parameter/owned"
            data.update(
                account_id="123456789012",
                region="test-region",
                action="ssm:GetParameter",
                resource_arn=arn,
            )
            if name == "assigned_parameter_read_observed":
                data["response"] = {"Name": "/owned", "ARN": arn, "Type": "String"}
            elif name == "unrelated_parameter_denied_observed":
                data.update(resource_arn=arn + "-other", error_code="AccessDenied")
            elif name == "attached_policy_recorded":
                data.update(
                    action="iam:GetPolicyVersion",
                    response={
                        "allowed_action": "ssm:GetParameter",
                        "allowed_resource": arn,
                        "policy_sha256": "a" * 64,
                    },
                )
            else:
                data["error_code"] = "ParameterNotFound"
        elif profile == "android":
            data.update(
                serial="emulator-5554",
                uid="app-debug",
                mode="600",
                stdout='<string name="username">synthetic</string><string name="password">synthetic</string>',
            )
            if name == "ordinary_app_access_denied":
                data.update(uid="shell-2000", stdout="Permission denied", exit_code=1)
            elif name == "test_app_data_removed":
                data["stdout"] = "package absent"
        elif profile == "binary":
            data.update(binary_sha256="a" * 64, input="correct", stdout="accepted")
            if name == "lab_identity_recorded":
                data["stdout"] = "lab1C: ELF 32-bit"
            elif name == "negative_input_observed":
                data.update(input="incorrect", stdout="rejected")
            elif name == "notes_exported":
                data["stdout"] = (
                    "I compared these two inputs and recorded their distinct results."
                )
        elif profile == "llm":
            cases = (
                ["baseline", "injection"]
                if name in {"tool_trace_saved", "repeated_trials_recorded"}
                else [
                    "injection" if name == "injected_request_recorded" else "baseline"
                ]
            )
            data["trials"] = [
                {
                    "trial": number,
                    "case": case,
                    "prompt_sha256": "b" * 64,
                    "calls": [
                        {
                            "tool": "GetUserTransactions",
                            "user_id": "1",
                            "result": "synthetic own-account transactions",
                        }
                    ],
                    "outcome": "own-account",
                }
                for case in cases
                for number in range(1, 4)
            ]
        elif profile == "bgp":
            data.update(
                peer="192.0.2.10",
                summary={"state": "Established"},
                routes={"192.168.42.0/24": []},
            )
            if name in {"gtsm.rejected", "md5.rejected"}:
                data["summary"] = {
                    "state": "Active",
                    "baseline_state": "Established",
                    "restored_state": "Established",
                }
        artifacts[name] = {"content": data, "sha256": evidence.content_hash(data)}
    return {
        "schema_version": evidence.VERSION,
        "recipe_id": recipe["id"],
        "source_revision": recipe["source"]["revision"],
        "environment": env,
        "artifacts": artifacts,
    }


@pytest.mark.parametrize("name", evidence.PROFILES)
def test_all_local_artifact_contracts_and_missing_evidence(name):
    recipe = detail(name)
    data = fixture(recipe)
    result = validate_report(recipe, {"evidence": data})
    assert result["status"] == (
        "unsupported" if name == "labtainers-network-basics" else "pass"
    )
    assert result["authority"] == "local" and result["xp"] == 0
    assert not result["satisfies_track_evidence"]
    assert "authenticity" in result["detail"] or name == "labtainers-network-basics"
    missing = copy.deepcopy(data)
    missing["artifacts"] = {}
    assert evidence.validate(recipe, missing)["status"] == "unsupported"
    invalid = copy.deepcopy(data)
    first = next(iter(invalid["artifacts"].values()))
    first["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash"):
        evidence.validate(recipe, invalid)


def test_repair_negative_control_requires_unchanged_object_and_second_owner():
    recipe = detail("restaurant-profile-repair")
    data = fixture(recipe)
    item = data["artifacts"]["cross_user_update_denied"]
    item["content"]["after"]["email"] = "new"
    item["sha256"] = evidence.content_hash(item["content"])
    assert evidence.validate(recipe, data)["status"] == "fail"
    data = fixture(recipe)
    item = data["artifacts"]["changed_object_owner_allowed"]
    item["content"]["request"]["object_id"] = "first"
    item["sha256"] = evidence.content_hash(item["content"])
    with pytest.raises(ValueError, match="distinct"):
        evidence.validate(recipe, data)


def test_declared_pass_wrong_source_and_secret_fields_are_rejected():
    recipe = detail("cloudfoxable-secret")
    data = fixture(recipe)
    item = data["artifacts"]["assigned_parameter_read_observed"]
    item["content"] = {"passed": True}
    item["sha256"] = evidence.content_hash(item["content"])
    with pytest.raises(ValueError, match="fields"):
        evidence.validate(recipe, data)
    data = fixture(recipe)
    data["source_revision"] = "0" * 40
    with pytest.raises(ValueError, match="source version"):
        evidence.validate(recipe, data)
    data = fixture(recipe)
    data["environment"]["AWS_SECRET_ACCESS_KEY"] = "must-not-upload"
    with pytest.raises(ValueError, match="environment fields"):
        evidence.validate(recipe, data)


def test_aws_denied_control_is_a_distinct_parameter_in_the_same_account():
    recipe = detail("cloudfoxable-secret")
    data = fixture(recipe)
    item = data["artifacts"]["unrelated_parameter_denied_observed"]
    item["content"]["resource_arn"] = data["artifacts"][
        "assigned_parameter_read_observed"
    ]["content"]["resource_arn"]
    item["sha256"] = evidence.content_hash(item["content"])
    with pytest.raises(ValueError, match="distinct denied"):
        evidence.validate(recipe, data)


def test_mobile_root_access_and_model_text_are_not_negative_or_tool_evidence():
    recipe = detail("mastg-android-storage")
    data = fixture(recipe)
    item = data["artifacts"]["ordinary_app_access_denied"]
    item["content"]["uid"] = "root"
    item["sha256"] = evidence.content_hash(item["content"])
    assert evidence.validate(recipe, data)["status"] == "fail"
    recipe = detail("llm-agent-transactions")
    data = fixture(recipe)
    item = data["artifacts"]["injected_request_recorded"]
    item["content"]["trials"][0]["calls"] = []
    item["sha256"] = evidence.content_hash(item["content"])
    assert evidence.validate(recipe, data)["status"] == "fail"


def test_prepared_workspace_capture_finish_sync_and_ownership(
    tracker, tmp_path, monkeypatch
):
    def fetch(_store, asset):
        path = tmp_path / asset["sha256"]
        path.write_text("synthetic reference for workspace tests")
        return path, 0

    monkeypatch.setattr("ascend.local_labs.assets.AssetStore.fetch", fetch)
    runtime = Runtime(tracker, root=tmp_path / "labs", server="http://testserver")
    row = runtime.prepare("restaurant-profile-repair")
    assert row["kind"] == "local-evidence-workspace" and row["status"] == "prepared"
    assert row["resources"] == {} and row["metrics"]["runtime_started"] is False
    work = runtime.work_dir(row)
    data = fixture(row["recipe"])
    atomic_json(work / "environment.json", data["environment"])
    for name, value in data["artifacts"].items():
        path = tmp_path / (name + ".json")
        atomic_json(path, value["content"])
        runtime.capture(row["id"], name, path)
    assert runtime.check(row["id"])["status"] == "pass"
    with pytest.raises(ValueError, match="Unknown artifact"):
        runtime.capture(row["id"], "../escape", path)
    path.unlink()
    path.symlink_to(work / "environment.json")
    with pytest.raises(ValueError, match="regular"):
        runtime.capture(row["id"], "owner_update_allowed", path)
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
        final = runtime.finish(row["id"])
        assert (
            final["pending_sync"]
            and final["local_receipt"]["result"]["status"] == "pass"
        )
        assert (
            runtime.finish(row["id"])["local_receipt"]["id"]
            == final["local_receipt"]["id"]
        )
        with pytest.raises(ValueError, match="final"):
            runtime.capture(
                row["id"], "owner_update_allowed", work / "environment.json"
            )
        result = runtime.sync(row["id"])
        receipt = result["remote_receipt"]
        assert (
            receipt["result"]["status"] == "pass"
            and receipt["result"]["authority"] == "local"
        )
        assert receipt["origin"] == "offline" and receipt["started_at"] is None
        assert client.get("/api/stats").json()["xp"]["total"] == 0
    assert runtime.reset(row["id"])["id"] != row["id"]
    assert (work / "submission.json").is_file()
    assert runtime.prune(0)["saved_work_removed"] is False
