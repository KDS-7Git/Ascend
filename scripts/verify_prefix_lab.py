"""Measure the real file lifecycle and ephemeral policy worker before activation."""

import argparse
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ascend.application import Tracker
from ascend.local_labs.assets import atomic_json
from ascend.local_labs.catalog import DATA
from ascend.local_labs.prefix import check_submission
from ascend.local_labs.runtime import Runtime
from ascend.storage import Database


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    recipe = json.loads((DATA / "recipes/bgp-export-policy.json").read_text())
    with tempfile.TemporaryDirectory(prefix="ascend-prefix-validation-") as tmp:
        root = Path(tmp)
        db = Database(root / "profile")
        tracker = Tracker(db)
        runtime = Runtime(tracker, root=root / "labs", recipe_loader=lambda _: recipe)
        disk_samples, workers = [], []
        stop = threading.Event()

        def sample():
            logical = allocated = 0
            for path in (root / "labs").rglob("*"):
                try:
                    if path.is_file():
                        size = path.stat()
                        logical += size.st_size
                        allocated += size.st_blocks * 512
                except FileNotFoundError:
                    pass
            disk_samples.append((logical, allocated))

        def monitor():
            while not stop.wait(0.005):
                sample()

        sampler = threading.Thread(target=monitor, daemon=True)
        sampler.start()
        try:
            cold = runtime._start(recipe, assessment=False, offline=True)
            assert runtime.check(cold["id"])["status"] == "fail"
            row = runtime.load(cold["id"])
            work = runtime.work_dir(row)
            case = row["assignment"]
            policy = {
                "version": 1,
                "default": "deny",
                "rules": [
                    {
                        "action": "permit",
                        "prefix": case["customer_prefix"],
                        "min_prefix": 24,
                        "max_prefix": 26,
                    }
                ],
            }
            atomic_json(work / "policy.json", policy)
            (work / "notes.txt").write_text(
                "Retain the policy and notes after resource cleanup.\n"
            )
            result = runtime.check(row["id"])
            assert result["status"] == "pass"
            workers.append(result["worker_metrics"])
            trusted = check_submission(
                recipe, case, {"files": {"policy.json": policy}}, trusted=True
            )
            assert (
                trusted["status"] == "pass"
                and trusted["authority"] == "server-submission"
            )
            workers.append(trusted["worker_metrics"])
            leaky = {
                **policy,
                "rules": [
                    *policy["rules"],
                    *[
                        {
                            "action": "permit",
                            "prefix": f"198.51.100.{i}/32",
                            "min_prefix": 32,
                            "max_prefix": 32,
                        }
                        for i in range(1, 32)
                    ],
                ],
            }
            bad = check_submission(
                recipe, case, {"files": {"policy.json": leaky}}, trusted=True
            )
            assert bad["status"] == "fail" and bad["counterexample"]
            workers.append(bad["worker_metrics"])
            sample()
            runtime.stop(row["id"])
            assert runtime.prune(0)["protected_objects"] == 2
            runtime = Runtime(
                tracker, root=root / "labs", recipe_loader=lambda _: recipe
            )
            runtime.resume(row["id"])
            assert runtime.check(row["id"])["status"] == "pass"
            runtime.export(row["id"])
            sample()
            assert runtime.finish(row["id"])["status"] == "destroyed"
            warm = runtime._start(recipe, assessment=False, offline=True)
            assert warm["metrics"]["download_bytes"] == 0
            runtime.destroy(warm["id"])
            runtime.destroy(warm["id"])
            # Recover missing runtime and interrupted preparation manifests.
            broken = runtime._start(recipe, assessment=False, offline=True)
            runtime.adapter(broken).destroy(broken)
            assert runtime.reconcile()[0]["status"] == "destroyed"
            interrupted = runtime._start(recipe, assessment=False, offline=True)
            interrupted = runtime.load(interrupted["id"])
            interrupted["status"] = "preparing"
            runtime.save(interrupted)
            assert runtime.reconcile()[0]["status"] == "destroyed"
            assert runtime.prune(0)["cache_bytes"] == 0
            assert all(
                (work / name).is_file()
                for name in ("policy.json", "TASK.txt", "notes.txt", "submission.json")
            )
            assert not any((runtime.state / "runtime").iterdir())
            sample()
        finally:
            stop.set()
            sampler.join()
            db.close()
        metrics = {
            "measured_on": time.strftime("%Y-%m-%d"),
            "platform": "linux-x86_64",
            "download_bytes": cold["metrics"]["download_bytes"],
            "expanded_bytes": cold["metrics"]["runtime_bytes"],
            "peak_disk_bytes": max(s[0] for s in disk_samples),
            "peak_allocated_disk_bytes": max(s[1] for s in disk_samples),
            "startup_cold_seconds": cold["metrics"]["startup_seconds"],
            "startup_warm_seconds": warm["metrics"]["startup_seconds"],
            "peak_memory_bytes": max(w["peak_memory_bytes"] for w in workers),
            "worker_samples": workers,
            "worker_cpu_seconds_limit": 2,
            "worker_address_space_bytes_limit": 134217728,
            "worker_wall_seconds_limit": 5,
            "worker_child_processes_limit": 0,
            "persistent_processes": 0,
            "after_prune_cache_bytes": 0,
            "scope": "Actual pinned downloads and local prepare/check/stop/resume/export/finish/destroy/reconcile/cache lifecycle. Worker samples use correct policy and a 32-rule policy with route leaks. CPU and memory are measured inside each fresh data-only worker; no router software runs. Disk includes retained work in four disposable attempts, sampled every 5ms. Server assignment, HTTP sync, resource timeout and malformed-result handling are tested separately.",
        }
        print(json.dumps(metrics, indent=2))
        if args.record:
            atomic_json(args.record, metrics)


if __name__ == "__main__":
    main()
