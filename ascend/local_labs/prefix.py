"""Local policy workspace and short-lived server-owned model grading."""

import hashlib
import json
import math
import os
import platform
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from ascend.local_labs.assets import AssetStore, atomic_json, digest
from ascend.local_labs.checks import bounded, outcome
from ascend.local_labs.prefix_worker import (
    CHECK_IDS,
    CHECKER_VERSION,
    MAX_INPUT,
    assignment,
    validate_policy,
)

WORKER = Path(__file__).with_name("prefix_worker.py")
WORKER_SLOTS = threading.BoundedSemaphore(2)
WORKER_TIMEOUT = 5
MAX_OUTPUT = 16_384


def assigned_case(case_key=None):
    return assignment(secrets.randbelow(65536) if case_key is None else case_key)


def fixture_id(recipe, case):
    if not isinstance(case, dict) or json.dumps(case, sort_keys=True) != json.dumps(assignment(case.get("case_key")), sort_keys=True):
        raise ValueError("Invalid assigned policy case")
    identity = {"recipe": recipe["id"], "version": recipe["version"], "source": recipe["source"]["revision"],
                "checker": recipe["checker_version"], "worker": recipe["worker_sha256"], "assignment": case}
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def submission_policy(submission):
    bounded(submission, MAX_INPUT)
    if set(submission) != {"files"} or not isinstance(submission["files"], dict) or set(submission["files"]) != {"policy.json"}:
        raise ValueError("Submit exactly one allowlisted file: policy.json (as a JSON object)")
    policy = submission["files"]["policy.json"]
    validate_policy(policy)
    return policy


def run_worker(payload):
    """No submitted code, paths, environment, executables or shell arguments."""
    if platform.system() != "Linux":
        raise ValueError("The policy worker requires Linux resource limits")
    if not WORKER_SLOTS.acquire(blocking=False):
        raise ValueError("Policy workers are busy; retry this submission")
    try:
        with tempfile.TemporaryDirectory(prefix="ascend-policy-worker-") as cwd, tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            source.write(payload)
            source.seek(0)
            process = subprocess.Popen([sys.executable, "-I", "-S", str(WORKER)], stdin=source, stdout=out, stderr=err,
                                       cwd=cwd, env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}, close_fds=True, start_new_session=True)
            deadline = time.monotonic() + WORKER_TIMEOUT
            try:
                while process.poll() is None:
                    if time.monotonic() >= deadline or max(os.fstat(f.fileno()).st_size for f in (out, err)) > MAX_OUTPUT:
                        raise ValueError("Policy worker exceeded its time or output limit")
                    time.sleep(.01)
                if process.returncode:
                    raise ValueError("Policy worker did not complete")
                out.seek(0)
                raw = out.read(MAX_OUTPUT + 1)
                if len(raw) > MAX_OUTPUT:
                    raise ValueError("Policy worker output exceeds its bound")
                try:
                    return json.loads(raw)
                except (ValueError, UnicodeError, RecursionError):
                    raise ValueError("Policy worker returned invalid JSON") from None
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()
    finally:
        WORKER_SLOTS.release()


def validate_result(result):
    if not isinstance(result, dict) or set(result) != {"checker_version", "checks", "counterexample", "intervals_checked", "metrics"}:
        raise ValueError("Incomplete policy worker output")
    checks = result["checks"]
    if result["checker_version"] != CHECKER_VERSION or not isinstance(checks, list) or len(checks) != len(CHECK_IDS):
        raise ValueError("Policy worker version or checkset mismatch")
    if any(not isinstance(c, dict) or set(c) != {"id", "status"} or not isinstance(c["id"], str)
           or not isinstance(c["status"], str) or c["status"] not in {"pass", "fail"} for c in checks):
        raise ValueError("Invalid policy worker check")
    if sorted(c["id"] for c in checks) != sorted(CHECK_IDS):
        raise ValueError("Incomplete policy worker checkset")
    if type(result["intervals_checked"]) is not int or not 33 <= result["intervals_checked"] <= 2211:
        raise ValueError("Invalid policy partition count")
    counterexample = result["counterexample"]
    if counterexample is not None and (not isinstance(counterexample, dict) or set(counterexample) != {"prefix", "expected", "actual"}
                or not isinstance(counterexample["prefix"], str) or len(counterexample["prefix"]) > 18
                or counterexample["expected"] not in ("permit", "deny") or counterexample["actual"] not in ("permit", "deny")
                or counterexample["expected"] == counterexample["actual"]):
        raise ValueError("Invalid policy counterexample")
    all_routes = next(c["status"] for c in checks if c["id"] == "all_ipv4_prefixes")
    if (all_routes == "pass") != (counterexample is None) or (all_routes == "pass" and any(c["status"] != "pass" for c in checks)):
        raise ValueError("Inconsistent policy worker result")
    metrics = result["metrics"]
    if not isinstance(metrics, dict) or set(metrics) != {"wall_seconds", "cpu_seconds", "peak_memory_bytes"}:
        raise ValueError("Missing policy worker measurements")
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in metrics.values()):
        raise ValueError("Invalid policy worker measurements")
    return result


def check_submission(recipe, case, submission, *, trusted=False):
    policy = submission_policy(submission)
    fixture_id(recipe, case)
    payload = json.dumps({"policy": policy, "case_key": case["case_key"]}, allow_nan=False).encode()
    if len(payload) > MAX_INPUT:
        raise ValueError("Policy worker input exceeds 64 KiB")
    if recipe["checker_version"] != CHECKER_VERSION or recipe.get("worker_sha256") != digest(WORKER):
        raise ValueError("Policy worker revision does not match the reviewed recipe")
    try:
        raw = validate_result(run_worker(payload))
    except (ValueError, OSError) as error:
        # Infrastructure errors never become a pass or a fabricated empty checkset.
        return outcome([{"id": name, "status": "error"} for name in CHECK_IDS], detail=str(error),
                       label="Submission test unavailable" if trusted else "Checked on this PC",
                       authority="server-submission" if trusted else "local")
    result = outcome(raw["checks"], label="Submission tested (policy model)" if trusted else "Checked on this PC",
                     authority="server-submission" if trusted else "local",
                     detail="Tests the submitted declarative IPv4 policy against all canonical route prefixes. It does not execute router software or establish prior local actions.")
    result.update(counterexample=raw["counterexample"], intervals_checked=raw["intervals_checked"], worker_metrics=raw["metrics"],
                  submission_sha256=hashlib.sha256(json.dumps(submission, sort_keys=True).encode()).hexdigest())
    return result


class PrefixLab:
    def __init__(self, runtime):
        self.runtime = runtime

    def prepare(self, row):
        recipe = row["recipe"]
        if not row.get("assignment"):
            row["assignment"] = assigned_case()
        row["fixture_id"] = fixture_id(recipe, row["assignment"])
        target, work = self.runtime.runtime_dir(row), self.runtime.work_dir(row)
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        work.mkdir(parents=True, exist_ok=True, mode=0o700)
        downloaded = 0
        for asset in recipe["assets"]:
            source, size = AssetStore(self.runtime.cache).fetch(asset)
            downloaded += size
            # Fixed destination names, never an upstream or submitted path.
            shutil.copyfile(source, target / ("UPSTREAM-LICENSE.txt" if asset["role"] == "license" else "upstream-topology.txt"))
        atomic_json(target / "assignment.json", row["assignment"])
        if not (work / "policy.json").exists():
            atomic_json(work / "policy.json", {"version": 1, "default": "deny", "rules": []})
            (work / "TASK.txt").write_text(recipe["instructions"] + "\n\nAssigned case:\n" + json.dumps(row["assignment"], indent=2) + "\n")
        row["files"] = {"assignment": str(target / "assignment.json"), "policy": str(work / "policy.json"), "task": str(work / "TASK.txt")}
        return {"download_bytes": downloaded, "runtime_bytes": sum(p.stat().st_size for p in target.iterdir())}

    def submission(self, row):
        submission = {"files": {"policy.json": self.runtime.read_work(row, "policy.json", maximum=MAX_INPUT)}}
        submission_policy(submission)
        return {"submission": submission}

    def check(self, row):
        return check_submission(row["recipe"], row["assignment"], self.submission(row)["submission"])

    def alive(self, row):
        return (self.runtime.runtime_dir(row) / "assignment.json").is_file()

    def stop(self, row):
        pass

    def destroy(self, row):
        target = self.runtime.runtime_dir(row)
        if target.is_symlink():
            raise ValueError("Runtime directory is a symlink")
        if target.exists():
            shutil.rmtree(target)
