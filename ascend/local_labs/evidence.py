"""Interpret bounded artifacts from learner-owned environments.

The server repeats these checks on the submitted artifact, never runs its code,
and never treats artifact hashes or local tool output as remote attestation.
"""

import hashlib
import json

from ascend.local_labs.checks import bounded, outcome

VERSION = "local-artifacts-v1"
LIMIT = 65536
PROFILES = {
    "labtainers-network-basics": "labtainers",
    "labtainers-telnetlab": "labtainers",
    "restaurant-profile-repair": "http",
    "bgp-single-session": "bgp",
    "bgp-session-protection": "bgp",
    "bgp-prefix-filter": "bgp",
    "kubernetes-goat-rbac": "kubernetes",
    "cloudfoxable-secret": "aws",
    "mastg-android-storage": "android",
    "mbe-intro-reversing": "binary",
    "llm-agent-transactions": "llm",
}


def content_hash(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def artifact_names(recipe):
    return (
        ["upstream"]
        if PROFILES[recipe["id"]] == "labtainers"
        else list(recipe["check_ids"])
    )


def template(recipe):
    """Concrete artifact shapes, with unfilled observations explicitly absent."""
    profile = PROFILES[recipe["id"]]
    examples = {
        "http": {
            "request": {
                "actor_id": "",
                "owner_id": "",
                "object_id": "",
                "method": "PATCH",
            },
            "response_status": 0,
            "before": {"email": ""},
            "after": {"email": ""},
            "submitted_email": "",
        },
        "kubernetes": {
            "context": "",
            "namespace": "kube-system",
            "service_account": "",
            "verb": "*",
            "resource": "*",
            "stdout": "",
            "exit_code": 0,
        },
        "aws": {
            "account_id": "",
            "region": "",
            "action": "",
            "resource_arn": "",
            "response": {},
            "error_code": "",
        },
        "android": {
            "serial": "emulator-",
            "package": "sg.vp.owasp_mobile.omtg_android",
            "uid": "",
            "mode": "",
            "stdout": "",
            "exit_code": 0,
        },
        "binary": {"binary_sha256": "", "input": "", "stdout": "", "exit_code": 0},
        "llm": {
            "trials": [
                {
                    "trial": 1,
                    "case": "baseline",
                    "prompt_sha256": "",
                    "calls": [
                        {"tool": "GetUserTransactions", "user_id": "", "result": ""}
                    ],
                    "outcome": "",
                }
            ]
        },
        "bgp": {"peer": "", "summary": {}, "routes": {}},
        "labtainers": {
            "learner.telnetlab": {"grades": {"telnetview": False, "sshview": False}}
        },
    }
    environment = dict(recipe.get("report_template", {}).get("environment", {}))
    environment["source_revision"] = recipe["source"]["revision"]
    return {
        "schema_version": VERSION,
        "recipe_id": recipe["id"],
        "environment": environment,
        "artifacts": {name: examples[profile] for name in artifact_names(recipe)},
    }


def _require(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError("Artifact fields do not match this observation's template")


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 4096


def _sha(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def _http(name, data):
    _require(data, {"request", "response_status", "before", "after", "submitted_email"})
    _require(data["request"], {"actor_id", "owner_id", "object_id", "method"})
    _require(data["before"], {"email"})
    _require(data["after"], {"email"})
    req, status = data["request"], data["response_status"]
    if (
        type(status) is not int
        or req["method"] != "PATCH"
        or not all(_text(req[k]) for k in ("owner_id", "object_id"))
    ):
        return False
    if (
        not _text(data["submitted_email"])
        or data["submitted_email"] == data["before"]["email"]
    ):
        return False
    if name in {"owner_update_allowed", "changed_object_owner_allowed"}:
        return (
            _text(req["actor_id"])
            and req["actor_id"] == req["owner_id"]
            and status == 200
            and data["after"]["email"] == data["submitted_email"]
        )
    if name == "cross_user_update_denied":
        return (
            _text(req["actor_id"])
            and req["actor_id"] != req["owner_id"]
            and status in {403, 404}
            and data["after"] == data["before"]
        )
    return (
        req["actor_id"] == "anonymous"
        and status in {401, 403}
        and data["after"] == data["before"]
    )


def _kubernetes(name, data):
    _require(
        data,
        {
            "context",
            "namespace",
            "service_account",
            "verb",
            "resource",
            "stdout",
            "exit_code",
        },
    )
    if (
        not _text(data["context"])
        or type(data["exit_code"]) is not int
        or not isinstance(data["stdout"], str)
    ):
        return False
    if name == "service_account_permissions_observed":
        return (
            data["namespace"] == "kube-system"
            and data["service_account"] == "superadmin"
            and data["verb"] == "*"
            and data["resource"] == "*"
            and data["stdout"].strip() == "yes"
            and data["exit_code"] == 0
        )
    if name == "restricted_account_control_observed":
        return (
            _text(data["service_account"])
            and data["service_account"] != "superadmin"
            and data["verb"] == "*"
            and data["resource"] == "*"
            and data["stdout"].strip() == "no"
            and data["exit_code"] in {0, 1}
        )
    if name == "cluster_role_binding_removed":
        return (
            data["resource"] == "clusterrolebinding/superadmin"
            and data["stdout"].strip() == ""
            and data["exit_code"] == 0
        )
    return (
        data["resource"] == "owned-cluster"
        and data["stdout"].strip() == "absent"
        and data["exit_code"] == 0
    )


def _aws(name, data):
    _require(
        data,
        {"account_id", "region", "action", "resource_arn", "response", "error_code"},
    )
    if (
        not isinstance(data["account_id"], str)
        or len(data["account_id"]) != 12
        or not data["account_id"].isdigit()
        or not _text(data["region"])
        or not isinstance(data["response"], dict)
    ):
        return False
    arn = data["resource_arn"]
    if not isinstance(arn, str) or not arn.startswith(
        f"arn:aws:ssm:{data['region']}:{data['account_id']}:parameter/"
    ):
        return False
    if name == "assigned_parameter_read_observed":
        _require(data["response"], {"Name", "ARN", "Type"})
        return (
            data["action"] == "ssm:GetParameter"
            and not data["error_code"]
            and data["response"]["ARN"] == arn
            and data["response"]["Type"] in {"String", "SecureString"}
            and _text(data["response"]["Name"])
        )
    if name == "unrelated_parameter_denied_observed":
        return (
            data["action"] == "ssm:GetParameter"
            and data["error_code"] in {"AccessDenied", "AccessDeniedException"}
            and not data["response"]
        )
    if name == "attached_policy_recorded":
        _require(
            data["response"], {"allowed_action", "allowed_resource", "policy_sha256"}
        )
        return (
            data["action"] == "iam:GetPolicyVersion"
            and data["response"]["allowed_action"] == "ssm:GetParameter"
            and data["response"]["allowed_resource"] == arn
            and _sha(data["response"]["policy_sha256"])
        )
    return (
        data["action"] == "ssm:GetParameter"
        and data["error_code"] == "ParameterNotFound"
        and not data["response"]
    )


def _android(name, data):
    _require(data, {"serial", "package", "uid", "mode", "stdout", "exit_code"})
    if (
        not isinstance(data["serial"], str)
        or not data["serial"].startswith("emulator-")
        or data["package"] != "sg.vp.owasp_mobile.omtg_android"
        or type(data["exit_code"]) is not int
        or not isinstance(data["stdout"], str)
    ):
        return False
    if name == "app_preferences_created":
        return (
            data["uid"] == "app-debug"
            and data["exit_code"] == 0
            and all(
                key in data["stdout"] for key in ('name="username"', 'name="password"')
            )
        )
    if name == "private_storage_observed":
        return (
            data["uid"] == "app-debug"
            and data["mode"] in {"600", "660"}
            and data["exit_code"] == 0
        )
    if name == "ordinary_app_access_denied":
        return (
            _text(data["uid"])
            and data["uid"] not in {"app-debug", "root", "0"}
            and data["exit_code"] != 0
            and "Permission denied" in data["stdout"]
        )
    return data["exit_code"] == 0 and data["stdout"].strip() == "package absent"


def _binary(name, data, artifacts):
    _require(data, {"binary_sha256", "input", "stdout", "exit_code"})
    if (
        not _sha(data["binary_sha256"])
        or type(data["exit_code"]) is not int
        or not isinstance(data["stdout"], str)
    ):
        return False
    if name == "lab_identity_recorded":
        return (
            "lab1C" in data["stdout"]
            and "ELF 32-bit" in data["stdout"]
            and data["exit_code"] == 0
        )
    if name == "binary_behavior_observed":
        return _text(data["input"]) and _text(data["stdout"]) and data["exit_code"] == 0
    if name == "negative_input_observed":
        correct = artifacts.get("binary_behavior_observed", {}).get("content", {})
        return (
            _text(data["input"])
            and _text(data["stdout"])
            and data["input"] != correct.get("input")
            and data["stdout"] != correct.get("stdout")
            and data["binary_sha256"] == correct.get("binary_sha256")
        )
    return len(data["stdout"].strip()) >= 20 and data["exit_code"] == 0


def _llm(name, data):
    _require(data, {"trials"})
    trials = data["trials"]
    if not isinstance(trials, list) or not 3 <= len(trials) <= 20:
        return False
    for trial in trials:
        _require(trial, {"trial", "case", "prompt_sha256", "calls", "outcome"})
        if (
            type(trial["trial"]) is not int
            or not 1 <= trial["trial"] <= 20
            or trial["case"] not in {"baseline", "injection"}
            or not isinstance(trial["calls"], list)
            or not trial["calls"]
            or not _sha(trial["prompt_sha256"])
        ):
            return False
        for call in trial["calls"]:
            _require(call, {"tool", "user_id", "result"})
            if (
                call["tool"] not in {"GetCurrentUser", "GetUserTransactions"}
                or not isinstance(call["user_id"], str)
                or not _text(call["result"])
            ):
                return False
        if trial["outcome"] not in {"own-account", "cross-account", "denied"}:
            return False
        transactions = [c for c in trial["calls"] if c["tool"] == "GetUserTransactions"]
        if trial["outcome"] == "own-account" and not any(
            c["user_id"] == "1" for c in transactions
        ):
            return False
        if trial["outcome"] == "cross-account" and not any(
            c["user_id"] != "1" for c in transactions
        ):
            return False
        if name == "own_account_baseline_recorded" and (
            trial["case"] != "baseline"
            or trial["outcome"] != "own-account"
            or not any(
                c["tool"] == "GetUserTransactions" and c["user_id"] == "1"
                for c in trial["calls"]
            )
        ):
            return False
        if name == "injected_request_recorded" and trial["case"] != "injection":
            return False
    identifiers = [(t["case"], t["trial"]) for t in trials]
    if len(set(identifiers)) != len(identifiers):
        return False
    return name not in {"tool_trace_saved", "repeated_trials_recorded"} or all(
        sum(t["case"] == case for t in trials) >= 3
        for case in ("baseline", "injection")
    )


def _bgp(name, data):
    _require(data, {"peer", "summary", "routes"})
    if (
        not _text(data["peer"])
        or not isinstance(data["summary"], dict)
        or not isinstance(data["routes"], dict)
    ):
        return False
    established = data["summary"].get("state") == "Established"
    if name.startswith("session."):
        return established
    if name.startswith(("prefix.", "adv_pfx.")):
        return established and "192.168.42.0/24" in data["routes"]
    if name.startswith("drop_pfx."):
        return established and "10.0.0.1/32" not in data["routes"]
    return (
        data["summary"].get("state") in {"Idle", "Active", "Connect"}
        and data["summary"].get("baseline_state") == "Established"
        and data["summary"].get("restored_state") == "Established"
    )


def validate(recipe, evidence):
    bounded(evidence)
    _require(
        evidence,
        {"schema_version", "recipe_id", "source_revision", "environment", "artifacts"},
    )
    if (
        evidence["schema_version"] != VERSION
        or evidence["recipe_id"] != recipe["id"]
        or evidence["source_revision"] != recipe["source"]["revision"]
    ):
        raise ValueError("Local evidence uses a different recipe or source version")
    if (
        not isinstance(evidence["environment"], dict)
        or evidence["environment"].get("source_revision")
        != recipe["source"]["revision"]
    ):
        raise ValueError("Record the selected source revision in the environment")
    expected_environment = set(recipe.get("environment_fields", [])) | {
        "source_revision"
    }
    if set(evidence["environment"]) != expected_environment or any(
        not isinstance(v, str) or not 1 <= len(v.strip()) <= 256
        for v in evidence["environment"].values()
    ):
        raise ValueError(
            "Fill exactly the selected environment fields with nonempty text"
        )
    for field in recipe.get("digest_environment_fields", []):
        value = evidence["environment"][field]
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("Invalid environment artifact hash")
    artifacts = evidence["artifacts"]
    names = artifact_names(recipe)
    if not isinstance(artifacts, dict) or set(artifacts) - set(names):
        raise ValueError("Unknown local artifact")
    for artifact in artifacts.values():
        _require(artifact, {"sha256", "content"})
        bounded(artifact["content"], LIMIT)
        if artifact["sha256"] != content_hash(artifact["content"]):
            raise ValueError("Local artifact hash mismatch")
    profile = PROFILES[recipe["id"]]
    checks = []
    if profile == "labtainers":
        if not recipe["check_ids"]:
            return outcome(
                [],
                label="Local evidence reviewed",
                detail="The selected network-basics goals.config is empty. Imported artifacts require instructor review; no automatic grade is available.",
            )
        grades = None
        if "upstream" in artifacts:
            records = [
                v
                for k, v in artifacts["upstream"]["content"].items()
                if k.endswith("." + recipe["integration"]["exercise"])
                and isinstance(v, dict)
            ]
            if len(records) != 1 or not isinstance(records[0].get("grades"), dict):
                raise ValueError(
                    "Capture the real instructor JSON for the selected Labtainers exercise"
                )
            grades = records[0]["grades"]
        for name in recipe["check_ids"]:
            value = grades.get(name) if grades else None
            if value is not None and type(value) is not bool:
                raise ValueError("Labtainers goal value must be a boolean")
            checks.append(
                {
                    "id": name,
                    "status": "unsupported"
                    if value is None
                    else "pass"
                    if value
                    else "fail",
                }
            )
    else:
        functions = {
            "http": _http,
            "kubernetes": _kubernetes,
            "aws": _aws,
            "android": _android,
            "llm": _llm,
            "bgp": _bgp,
        }
        for name in recipe["check_ids"]:
            if name not in artifacts:
                status = "unsupported"
            else:
                content = artifacts[name]["content"]
                passed = (
                    _binary(name, content, artifacts)
                    if profile == "binary"
                    else functions[profile](name, content)
                )
                status = "pass" if passed else "fail"
            checks.append({"id": name, "status": status})
    # Pair controls to the same local environment and distinct target objects.
    if profile == "http" and all(n in artifacts for n in recipe["check_ids"]):
        rows = {n: artifacts[n]["content"]["request"] for n in recipe["check_ids"]}
        if (
            rows["owner_update_allowed"]["object_id"]
            == rows["changed_object_owner_allowed"]["object_id"]
            or rows["cross_user_update_denied"]["object_id"]
            != rows["owner_update_allowed"]["object_id"]
        ):
            raise ValueError(
                "Repair controls require the same attacked object and a distinct second owner object"
            )
    if profile == "aws" and all(n in artifacts for n in recipe["check_ids"]):
        rows = [artifacts[n]["content"] for n in recipe["check_ids"]]
        if (
            len({(r["account_id"], r["region"]) for r in rows}) != 1
            or rows[0]["resource_arn"] != rows[2]["resource_arn"]
            or rows[0]["resource_arn"] != rows[3]["resource_arn"]
            or rows[0]["resource_arn"] == rows[1]["resource_arn"]
        ):
            raise ValueError(
                "AWS observations require the same account/region, assigned parameter, and distinct denied control"
            )
    if profile in {"android", "kubernetes", "binary"} and artifacts:
        field = {
            "android": "serial",
            "kubernetes": "context",
            "binary": "binary_sha256",
        }[profile]
        if len({a["content"][field] for a in artifacts.values()}) != 1:
            raise ValueError("Paired controls must refer to the same local environment")
    if profile == "binary" and any(
        a["content"]["binary_sha256"] != evidence["environment"]["binary_sha256"]
        for a in artifacts.values()
    ):
        raise ValueError("Binary observations do not match the recorded binary hash")
    if profile == "llm":
        count = evidence["environment"].get("trial_count", "")
        if not count.isdigit() or not 3 <= int(count) <= 20:
            raise ValueError("Record between three and twenty paired model trials")
    return outcome(
        checks,
        label="Local evidence reviewed",
        detail="Checks were derived from submitted artifacts, including their negative controls. Artifacts and environment identifiers are learner-controlled; hashes check consistency, not authenticity. This is not a trusted observation or a track completion.",
    )
