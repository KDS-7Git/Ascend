import json

import pytest

from ascend.local_labs import collectors


def test_android_targets_one_emulator_and_redacts_secret_values(monkeypatch):
    commands = []

    def run(argv):
        commands.append(argv)
        return (
            0,
            '<map><string name="username">administrator</string><string name="password">must-not-synchronize</string></map>',
        )

    monkeypatch.setattr(collectors, "run", run)
    result = collectors._android("app_preferences_created", {"serial": "emulator-5554"})
    assert (
        "password" in result["stdout"]
        and "must-not-synchronize" not in result["stdout"]
    )
    assert commands[0][:4] == ["adb", "-s", "emulator-5554", "shell"]
    assert commands[0][-1] == "shared_prefs/key.xml"
    for serial in ("device-serial", "", "emulator-5554;bad"):
        with pytest.raises(ValueError, match="emulator serial"):
            collectors._android("private_storage_observed", {"serial": serial})


def test_android_requires_ordinary_non_root_access_control(monkeypatch):
    monkeypatch.setattr(collectors, "run", lambda _: (0, "0"))
    with pytest.raises(ValueError, match="non-root"):
        collectors._android("ordinary_app_access_denied", {"serial": "emulator-5554"})


def test_kubernetes_observations_are_read_only_and_use_selected_context(
    tmp_path, monkeypatch
):
    kubeconfig = tmp_path / "config"
    kubeconfig.write_text("synthetic config")
    calls = []

    def run(args):
        calls.append(args)
        return (0, "yes") if "can-i" in args else (0, "")

    monkeypatch.setattr(collectors, "run", run)
    config = {
        "context": "ascend-test",
        "kubeconfig": str(kubeconfig),
        "restricted_namespace": "default",
        "restricted_account": "limited",
        "kind_cluster": "ascend-test",
    }
    result = collectors._kubernetes("service_account_permissions_observed", config)
    assert result["stdout"] == "yes"
    assert calls[0][:5] == [
        "kubectl",
        "--kubeconfig",
        str(kubeconfig),
        "--context",
        "ascend-test",
    ]
    assert "--as=system:serviceaccount:kube-system:superadmin" in calls[0]
    result = collectors._kubernetes("cluster_role_binding_removed", config)
    assert result["stdout"] == ""
    assert "--ignore-not-found" in calls[1]
    assert all(not (set(call) & {"delete", "apply", "create"}) for call in calls)


def test_aws_reads_selected_profile_and_excludes_parameter_values(monkeypatch):
    calls = []

    def run(args):
        calls.append(args)
        if "get-caller-identity" in args:
            return 0, json.dumps({"Account": "123456789012"})
        return 0, json.dumps(
            {
                "Parameter": {
                    "Name": "/owned",
                    "ARN": "arn:aws:ssm:test-region:123456789012:parameter/owned",
                    "Type": "String",
                    "Value": "must-not-upload",
                }
            }
        )

    monkeypatch.setattr(collectors, "run", run)
    config = {
        "profile": "disposable",
        "region": "test-region",
        "parameter": "/owned",
        "denied_parameter": "/other",
        "policy_arn": "",
        "iam_user": "",
    }
    result = collectors._aws("assigned_parameter_read_observed", config)
    assert set(result["response"]) == {"Name", "ARN", "Type"}
    assert "must-not-upload" not in json.dumps(result)
    assert all(
        call[:5] == ["aws", "--profile", "disposable", "--region", "test-region"]
        for call in calls
    )
    assert all(
        not any(word.startswith(("create-", "delete-", "put-")) for word in call)
        for call in calls
    )


def test_aws_missing_credentials_are_environment_error_not_a_denied_control(
    monkeypatch,
):
    def run(args):
        return (
            (0, json.dumps({"Account": "123456789012"}))
            if "get-caller-identity" in args
            else (1, "Unable to locate credentials")
        )

    monkeypatch.setattr(collectors, "run", run)
    with pytest.raises(ValueError, match="environment"):
        collectors._aws(
            "unrelated_parameter_denied_observed",
            {
                "profile": "test",
                "region": "test-region",
                "parameter": "/owned",
                "denied_parameter": "/other",
            },
        )
