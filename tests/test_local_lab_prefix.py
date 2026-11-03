import json
import subprocess
import sys
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from ascend import timing
from ascend.application import Tracker
from ascend.local_labs import catalog, prefix
from ascend.local_labs.assets import atomic_json
from ascend.local_labs.attempts import Attempts
from ascend.local_labs.prefix_worker import grade
from ascend.local_labs.runtime import Runtime
from ascend.server.app import create_app
from ascend.storage import Database


@pytest.fixture
def policy_recipe(monkeypatch):
    recipe = deepcopy(next(r for r in catalog.recipes() if r["id"] == "bgp-export-policy"))
    recipe.update(status="reviewed", lifecycle_verified=True, tested_platforms=["linux-x86_64"],
                  measurements={k: 1 for k in ("download_bytes", "expanded_bytes", "peak_disk_bytes", "startup_cold_seconds", "startup_warm_seconds", "peak_memory_bytes")})
    monkeypatch.setattr(catalog, "recipes", lambda: [recipe])
    return recipe


def correct(case):
    return {"version": 1, "default": "deny", "rules": [{"action": "permit", "prefix": case["customer_prefix"], "min_prefix": 24, "max_prefix": 26}]}


def submitted(policy):
    return {"files": {"policy.json": policy}}


def payload(attempt, policy=None):
    return {k: attempt[k] for k in ("nonce", "recipe_version", "checker_version", "fixture_id")} | {
        "submission": submitted(correct(attempt["assignment"]) if policy is None else policy)}


def test_server_worker_accepts_correct_policy_and_rejects_hidden_route_leak(policy_recipe):
    case = prefix.assigned_case(16416)
    policy = correct(case)
    result = prefix.check_submission(policy_recipe, case, submitted(policy), trusted=True)
    assert result["status"] == "pass" and result["evidence_label"] == "Submission tested (policy model)"
    assert result["authority"] == "server-submission" and result["worker_metrics"]["peak_memory_bytes"] < 134217728
    policy["rules"].append({"action": "permit", "prefix": "198.51.100.73/32", "min_prefix": 32, "max_prefix": 32})
    result = prefix.check_submission(policy_recipe, case, submitted(policy), trusted=True)
    assert result["status"] == "fail"
    assert result["counterexample"] == {"prefix": "198.51.100.73/32", "actual": "permit", "expected": "deny"}
    assert all(c["status"] == "pass" for c in result["checks"] if c["id"] != "all_ipv4_prefixes")


def test_policy_semantics_include_first_match_ranges_and_equivalent_rules():
    case = prefix.assigned_case(16416)
    policy = correct(case)
    policy["rules"].insert(0, {"action": "deny", "prefix": "10.64.32.128/25", "min_prefix": 25, "max_prefix": 26})
    checks = {c["id"]: c["status"] for c in grade(policy, case["case_key"])["checks"]}
    assert checks["customer_aggregate"] == "pass" and checks["customer_halves"] == "fail"
    policy["rules"] = [{"action": "permit", "prefix": "10.64.32.0/24", "min_prefix": 24, "max_prefix": 24},
                       {"action": "permit", "prefix": "10.64.32.0/25", "min_prefix": 25, "max_prefix": 26},
                       {"action": "permit", "prefix": "10.64.32.128/25", "min_prefix": 25, "max_prefix": 26}]
    assert all(c["status"] == "pass" for c in grade(policy, case["case_key"])["checks"])
    for wrong in ({"version": 1, "default": "permit", "rules": []}, {"version": 1, "default": "deny", "rules": []}):
        assert any(c["status"] == "fail" for c in grade(wrong, case["case_key"])["checks"])


@pytest.mark.parametrize("artifact", [
    {}, {"files": {}}, {"files": {"../policy.json": {}}}, {"files": {"/tmp/policy.json": {}}},
    {"files": {"policy.json": {}, "helper.py": "print('pass')"}}, {"files": {"policy.json": "__import__('os').system('id')"}},
    {"files": {"policy.json": {"version": True, "default": "deny", "rules": []}}},
    {"files": {"policy.json": {"version": 1, "default": "deny", "rules": [], "passed": True}}},
    {"files": {"policy.json": {"version": 1, "default": "deny", "rules": [None] * 33}}},
    {"files": {"policy.json": {"version": 1, "default": "deny", "rules": [{"action": "permit", "prefix": "10.64.32.1/24", "min_prefix": 24, "max_prefix": 26}]}}},
    {"files": {"policy.json": {"version": 1, "default": "deny", "rules": [{"action": "permit", "prefix": "::/0", "min_prefix": 24, "max_prefix": 26}]}}},
    {"files": {"policy.json": {"version": 1, "default": "deny", "rules": [{"action": "permit", "prefix": "0.0.0.0/0", "min_prefix": False, "max_prefix": 32}]}}},
    {"files": {"policy.json": "x" * 65536}},
])
def test_submission_schema_rejects_paths_code_claims_and_oversize(artifact):
    with pytest.raises(ValueError):
        prefix.submission_policy(artifact)


def test_attempt_binds_account_versions_case_nonce_and_preserves_rewards(installed, policy_recipe, tmp_path):
    installed.server_mode = True
    service = Attempts(installed)
    attempt = service.create(policy_recipe["id"])
    service.ready(attempt["id"], attempt["nonce"])
    for change in ({"recipe_version": "2"}, {"checker_version": "other"}, {"fixture_id": "old-case"}, {"nonce": "0" * 64}, {"passed": True}, {"report": {"passed": True}}):
        with pytest.raises(ValueError):
            service.submit(attempt["id"], {**payload(attempt), **change})
    other = Tracker(Database(tmp_path / "other", user_id=2))
    with pytest.raises(ValueError, match="not found"):
        Attempts(other).submit(attempt["id"], payload(attempt))
    result = service.submit(attempt["id"], payload(attempt))
    assert result["result"]["status"] == "pass" and result["result"]["xp"] == 0
    assert not result["satisfies_track_evidence"] and installed.states("test-pack") == {}
    assert timing.summary(installed)["xp"] == 0 and installed.entries() == []
    with pytest.raises(ValueError, match="already submitted"):
        service.submit(attempt["id"], payload(attempt))
    other.db.close()


def test_server_derives_offline_case_and_refuses_online_case_selection(tracker, policy_recipe):
    service = Attempts(tracker)
    for key in (True, -1, 65536, "2"):
        with pytest.raises(ValueError):
            service.create(policy_recipe["id"], offline=True, case_key=key)
    with pytest.raises(ValueError, match="offline"):
        service.create(policy_recipe["id"], case_key=1)
    first = service.create(policy_recipe["id"], offline=True, case_key=1)
    second = service.create(policy_recipe["id"], offline=True, case_key=2)
    assert first["fixture_id"] != second["fixture_id"]
    assert service.submit(second["id"], payload(second, correct(first["assignment"])))["result"]["status"] == "fail"
    tracker.server_mode = True
    with pytest.raises(ValueError, match="cannot be replaced"):
        service.adopt_local_assignment(first["id"], first["nonce"], second)


def test_incomplete_worker_output_never_passes_and_attempt_remains_retryable(tracker, policy_recipe, monkeypatch):
    service = Attempts(tracker)
    attempt = service.create(policy_recipe["id"], offline=True)
    original = prefix.run_worker
    raw = original(json.dumps({"case_key": 1, "policy": correct(prefix.assigned_case(1))}).encode())
    for broken in ({**raw, "checks": []}, {**raw, "checker_version": "forged"}, {**raw, "checks": raw["checks"][:-1]}, {**raw, "counterexample": {}}):
        monkeypatch.setattr(prefix, "run_worker", lambda _, reply=broken: reply)
        with pytest.raises(ValueError, match="unavailable"):
            service.submit(attempt["id"], payload(attempt))
        assert service.view(attempt["id"])["status"] == "imported"
    monkeypatch.setattr(prefix, "run_worker", original)
    assert service.submit(attempt["id"], payload(attempt))["result"]["status"] == "pass"


def test_worker_timeout_kills_and_reaps_child(policy_recipe, monkeypatch):
    real_popen, children = subprocess.Popen, []
    def stalled(*args, **kwargs):
        process = real_popen([sys.executable, "-I", "-S", "-c", "import time; time.sleep(10)"], **kwargs)
        children.append(process)
        return process
    monkeypatch.setattr(prefix.subprocess, "Popen", stalled)
    monkeypatch.setattr(prefix, "WORKER_TIMEOUT", .05)
    case = prefix.assigned_case(1)
    result = prefix.check_submission(policy_recipe, case, submitted(correct(case)))
    assert result["status"] == "error" and all(c["status"] == "error" for c in result["checks"])
    assert children[0].poll() is not None


@pytest.mark.parametrize("offline", [False, True])
def test_local_workspace_adopts_server_case_and_syncs_small_submission(tracker, policy_recipe, tmp_path, monkeypatch, offline):
    # Downloads/lifecycle are measured separately against actual pinned assets.
    policy_recipe["assets"] = []
    runtime = Runtime(tracker, root=tmp_path / "labs", server="http://testserver")
    with TestClient(create_app(tmp_path / "server", scheduler=False)) as client:
        def request(path, data=None, server=None):
            response = client.get(path) if data is None else client.post(path, json=data)
            if response.status_code != 200:
                raise ValueError(response.text)
            return response.json()
        monkeypatch.setattr(runtime, "_remote", request)
        # Use a private pre-activation review entry point with a normal attempt.
        monkeypatch.setattr(runtime.attempts, "recipe", lambda *args: policy_recipe)
        monkeypatch.setattr(Attempts, "recipe", lambda *args: policy_recipe)
        row = runtime._start(policy_recipe, offline=offline)
        assert runtime.check(row["id"])["status"] == "fail"
        atomic_json(runtime.work_dir(row) / "policy.json", correct(row["assignment"]))
        assert runtime.check(row["id"])["status"] == "pass"
        runtime.stop(row["id"])
        monkeypatch.setattr(runtime, "resolve", lambda _: policy_recipe)
        runtime.resume(row["id"])
        result = runtime.finish(row["id"])
        if offline:
            assert result["pending_sync"] and "remote_receipt" not in result
            result = runtime.sync(row["id"])
        assert result["status"] == "destroyed" and not result["pending_sync"]
        receipt = result["remote_receipt"]
        assert receipt["assignment"] == row["assignment"] and receipt["result"]["status"] == "pass"
        assert receipt["result"]["authority"] == "server-submission"
        assert (receipt["started_at"] is None) == offline
        assert json.loads((runtime.work_dir(row) / "submission.json").read_text())["case_key"] == row["assignment"]["case_key"]
        assert client.get("/api/stats").json()["xp"]["total"] == 0


def test_http_rejects_fabricated_receipts_case_and_artifact_paths(policy_recipe, tmp_path):
    with TestClient(create_app(tmp_path, scheduler=False)) as client:
        base = {"recipe_id": policy_recipe["id"]}
        for bad in ({**base, "case_key": 1}, {**base, "offline": True, "assignment": {}}, {**base, "offline": True, "case_key": True}):
            assert client.post("/api/lab-attempts", json=bad).status_code in (400, 422)
        a = client.post("/api/lab-attempts", json={**base, "offline": True, "case_key": 42}).json()
        endpoint = f"/api/lab-attempts/{a['id']}/submit"
        assert client.post(endpoint, json={**payload(a), "passed": True}).status_code == 422
        assert client.post(endpoint, json={**payload(a), "submission": {"files": {"../policy.json": {}}}}).status_code == 400
        assert client.post(endpoint, json=payload(a)).json()["result"]["status"] == "pass"


def test_profile_mismatch_is_rejected_before_work_or_resources_change(tracker, tmp_path):
    root = tmp_path / "labs"
    Runtime(tracker, root=root)
    before = (root / "state/owner.json").read_bytes()
    other = Tracker(Database(tmp_path / "other"))
    with pytest.raises(ValueError, match="different Ascend profile"):
        Runtime(other, root=root)
    assert (root / "state/owner.json").read_bytes() == before
    other.db.close()
