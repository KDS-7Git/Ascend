"""Read-only, explicitly targeted local observations; no generic command API."""

import json
import os
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from ascend.local_labs import evidence
from ascend.local_labs.workspaces import workspace


def config_template(recipe):
    profile = evidence.PROFILES[recipe["id"]]
    return {
        "kubernetes": {
            "kubeconfig": "",
            "context": "",
            "restricted_namespace": "default",
            "restricted_account": "",
            "kind_cluster": "",
        },
        "android": {"serial": "emulator-"},
        "bgp": {"containers": {"x1": "", "x2": ""}, "router_address": ""},
        "labtainers": {"report_path": ""},
        "aws": {
            "profile": "",
            "region": "",
            "parameter": "",
            "denied_parameter": "",
            "policy_arn": "",
            "iam_user": "",
        },
        "binary": {"observation_path": ""},
        "llm": {"observation_path": ""},
        "http": {"observation_path": ""},
    }[profile]


def run(args, timeout=15):
    """Keep subprocess output bounded while the process is running."""
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(
            args, stdin=subprocess.DEVNULL, stdout=output, stderr=output
        )
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                if (
                    time.monotonic() >= deadline
                    or os.fstat(output.fileno()).st_size > evidence.LIMIT
                ):
                    raise ValueError(
                        "Local observation exceeded its time or output limit"
                    )
                time.sleep(0.05)
            output.seek(0)
            content = output.read(evidence.LIMIT + 1)
            if len(content) > evidence.LIMIT:
                raise ValueError("Local observation exceeds 64 KiB")
            return process.returncode, content.decode("utf-8", errors="replace")
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()


def _name(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[a-zA-Z0-9][a-zA-Z0-9_.:/@-]{0,255}", value
    ):
        raise ValueError("Fill the selected environment identifiers in collector.json")
    return value


def _read(path):
    path = Path(path).expanduser()
    if not path.is_file() or path.is_symlink() or path.stat().st_size > evidence.LIMIT:
        raise ValueError("Use a regular JSON observation file of at most 64 KiB")
    try:
        return evidence.bounded(json.loads(path.read_bytes()), evidence.LIMIT)
    except (ValueError, RecursionError):
        raise ValueError(
            "Observation file must contain a bounded JSON object"
        ) from None


def _kubernetes(name, config):
    context = _name(config["context"])
    kubeconfig = Path(config["kubeconfig"]).expanduser()
    if not kubeconfig.is_file():
        raise ValueError("Select the dedicated lab kubeconfig in collector.json")
    base = ["kubectl", "--kubeconfig", str(kubeconfig), "--context", context]
    result = {
        "context": context,
        "namespace": "kube-system",
        "service_account": "superadmin",
        "verb": "*",
        "resource": "*",
        "stdout": "",
        "exit_code": 0,
    }
    if name in {
        "service_account_permissions_observed",
        "restricted_account_control_observed",
    }:
        if name.startswith("restricted"):
            result.update(
                namespace=_name(config["restricted_namespace"]),
                service_account=_name(config["restricted_account"]),
            )
        actor = (
            "system:serviceaccount:"
            + result["namespace"]
            + ":"
            + result["service_account"]
        )
        code, text = run([*base, "auth", "can-i", "*", "*", "--as=" + actor])
        if text.strip() not in {"yes", "no"}:
            raise ValueError("kubectl could not observe authorization: " + text[-500:])
    elif name == "cluster_role_binding_removed":
        result["resource"] = "clusterrolebinding/superadmin"
        code, text = run(
            [
                *base,
                "get",
                "clusterrolebinding",
                "superadmin",
                "--ignore-not-found",
                "-o",
                "name",
            ]
        )
        if code:
            raise ValueError(
                "kubectl could not inspect binding removal: " + text[-500:]
            )
    else:
        cluster = _name(config["kind_cluster"])
        code, text = run(["kind", "get", "clusters"])
        if code:
            raise ValueError("kind could not inspect the owned cluster inventory")
        result["resource"] = "owned-cluster"
        text = "absent" if cluster not in text.splitlines() else "present"
    result.update(stdout=text, exit_code=code)
    return result


def _android(name, config):
    serial = config["serial"]
    if not isinstance(serial, str) or not re.fullmatch(r"emulator-[0-9]+", serial):
        raise ValueError(
            "Select an explicit disposable emulator serial; physical devices are not accepted"
        )
    package = "sg.vp.owasp_mobile.omtg_android"
    base = ["adb", "-s", serial, "shell"]
    preferences = "shared_prefs/key.xml"
    result = {
        "serial": serial,
        "package": package,
        "uid": "app-debug",
        "mode": "",
        "stdout": "",
        "exit_code": 0,
    }
    if name == "app_preferences_created":
        code, text = run([*base, "run-as", package, "cat", preferences])
        if code:
            raise ValueError(
                "Open the SharedPreferences activity on the selected emulator first; debug access failed"
            )
        try:
            # Retain keys only; upstream demo secret values never synchronize.
            parsed = ET.fromstring(text)
            text = "".join(
                f'<string name="{key}">[redacted]</string>'
                for key in ("username", "password")
                if any(e.attrib.get("name") == key for e in parsed)
            )
        except ET.ParseError:
            raise ValueError("The app did not return valid preference XML") from None
    elif name == "private_storage_observed":
        code, text = run([*base, "run-as", package, "stat", "-c", "%a", preferences])
        if code:
            raise ValueError("Could not inspect the app's preference permissions")
        result["mode"] = text.strip()
    elif name == "ordinary_app_access_denied":
        code, uid = run([*base, "id", "-u"])
        if code or not uid.strip().isdigit() or uid.strip() == "0":
            raise ValueError(
                "Use an ordinary non-root emulator shell for the access control"
            )
        result["uid"] = "shell-" + uid.strip()
        code, text = run([*base, "cat", f"/data/data/{package}/{preferences}"])
    else:
        code, text = run([*base, "pm", "list", "packages", package])
        if code:
            raise ValueError(
                "Could not inspect package removal on the selected emulator"
            )
        text = (
            "package absent"
            if "package:" + package not in text.splitlines()
            else "package present"
        )
    result.update(stdout=text, exit_code=code)
    return result


def _bgp(name, config):
    peer = name.split(".")[-1]
    if peer not in {"x1", "x2"}:
        raise ValueError(
            "Capture paired baseline/broken/restored observations for the BGP negative probes"
        )
    container = _name(config["containers"].get(peer))
    address = _name(config["router_address"])
    code, summary = run(
        [
            "docker",
            "exec",
            container,
            "vtysh",
            "-d",
            "bgpd",
            "-c",
            "show bgp ipv4 unicast summary json",
        ]
    )
    code2, routes = run(
        [
            "docker",
            "exec",
            container,
            "vtysh",
            "-d",
            "bgpd",
            "-c",
            "show bgp ipv4 unicast json",
        ]
    )
    if code or code2:
        raise ValueError("The selected FRR router could not return BGP observations")
    try:
        summary, routes = json.loads(summary), json.loads(routes)
        peers = summary.get("ipv4Unicast", summary).get("peers", {})
        return {
            "peer": address,
            "summary": peers.get(address, {}),
            "routes": routes.get("routes", {}),
        }
    except (ValueError, AttributeError):
        raise ValueError("FRR returned an unsupported observation format") from None


def _aws(name, config):
    base = [
        "aws",
        "--profile",
        _name(config["profile"]),
        "--region",
        _name(config["region"]),
        "--output",
        "json",
        "--no-cli-pager",
    ]
    code, identity = run([*base, "sts", "get-caller-identity"])
    if code:
        raise ValueError("The selected AWS profile could not identify its account")
    account = json.loads(identity).get("Account")
    if not isinstance(account, str) or not re.fullmatch(r"[0-9]{12}", account):
        raise ValueError("AWS returned no account identity")
    parameter = (
        config["denied_parameter"]
        if name == "unrelated_parameter_denied_observed"
        else config["parameter"]
    )
    if not isinstance(parameter, str) or not re.fullmatch(
        r"/?[a-zA-Z0-9][a-zA-Z0-9_./-]{0,255}", parameter
    ):
        raise ValueError("Select the lab's parameter name in collector.json")
    arn = f"arn:aws:ssm:{config['region']}:{account}:parameter/" + parameter.lstrip("/")
    result = {
        "account_id": account,
        "region": config["region"],
        "action": "ssm:GetParameter",
        "resource_arn": arn,
        "response": {},
        "error_code": "",
    }
    if name == "attached_policy_recorded":
        policy_arn, user = _name(config["policy_arn"]), _name(config["iam_user"])
        code, attached = run(
            [*base, "iam", "list-attached-user-policies", "--user-name", user]
        )
        if code or policy_arn not in {
            p["PolicyArn"] for p in json.loads(attached).get("AttachedPolicies", [])
        }:
            raise ValueError(
                "The selected lab policy is not attached to the selected user"
            )
        code, policy = run([*base, "iam", "get-policy", "--policy-arn", policy_arn])
        if code:
            raise ValueError("Could not read the selected lab policy")
        version = json.loads(policy)["Policy"]["DefaultVersionId"]
        code, document = run(
            [
                *base,
                "iam",
                "get-policy-version",
                "--policy-arn",
                policy_arn,
                "--version-id",
                version,
            ]
        )
        if code:
            raise ValueError("Could not read the selected policy version")
        document = json.loads(document)["PolicyVersion"]["Document"]
        statements = document.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]
        matched = any(
            s.get("Effect") == "Allow"
            and "ssm:GetParameter"
            in (
                [s.get("Action")]
                if isinstance(s.get("Action"), str)
                else s.get("Action", [])
            )
            and arn
            in (
                [s.get("Resource")]
                if isinstance(s.get("Resource"), str)
                else s.get("Resource", [])
            )
            for s in statements
        )
        result.update(
            action="iam:GetPolicyVersion",
            response={
                "allowed_action": "ssm:GetParameter" if matched else "unsupported",
                "allowed_resource": arn,
                "policy_sha256": evidence.content_hash(document),
            },
        )
        return result
    code, text = run([*base, "ssm", "get-parameter", "--name", parameter])
    if not code:
        p = json.loads(text)["Parameter"]
        # Exclude Parameter.Value, credentials and complete policy/state dumps.
        result["response"] = {k: p[k] for k in ("Name", "ARN", "Type")}
    else:
        match = re.search(
            r"\((AccessDeniedException|AccessDenied|ParameterNotFound)\)", text
        )
        if not match:
            raise ValueError(
                "AWS could not observe the selected parameter; check the environment"
            )
        result["error_code"] = match[1]
    return result


def observe(runtime, run_id, name):
    row = workspace(runtime, run_id)
    if row.get("finished_at") or name not in evidence.artifact_names(row["recipe"]):
        raise ValueError("Choose an unfinished workspace and one of its artifact names")
    config = runtime.read_work(row, "collector.json")
    expected = config_template(row["recipe"])
    if set(config) != set(expected):
        raise ValueError("collector.json does not match the selected lab")
    profile = evidence.PROFILES[row["recipe"]["id"]]
    if profile == "labtainers":
        raw = _read(config["report_path"])
        exercise = row["recipe"]["integration"]["exercise"]
        records = {
            k: {
                "grades": {
                    n: v.get("grades", {}).get(n) for n in row["recipe"]["check_ids"]
                }
            }
            for k, v in raw.items()
            if k.endswith("." + exercise) and isinstance(v, dict)
        }
        content = records
    elif profile in {"http", "binary", "llm"}:
        # Actual repair/debugger/agent traces use their explicit saved schema;
        # executable submissions are never run on Ascend's application server.
        content = _read(config["observation_path"])
    else:
        content = {
            "kubernetes": _kubernetes,
            "android": _android,
            "bgp": _bgp,
            "aws": _aws,
        }[profile](name, config)
    evidence.bounded(content, evidence.LIMIT)
    with tempfile.TemporaryDirectory(prefix="ascend-observation-") as folder:
        path = Path(folder) / "observation.json"
        path.write_text(json.dumps(content))
        return runtime.capture(run_id, name, path)
