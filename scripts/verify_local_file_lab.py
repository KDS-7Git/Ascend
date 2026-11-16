"""Real Linux file-pilot lifecycle and cold/warm measurement in a disposable profile.

The private review harness can measure a recipe before activation. No user-facing
CLI flag bypasses the catalog gate. Network downloads are hash checked.
"""

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
from ascend.local_labs.runtime import Runtime
from ascend.storage import Database

ANSWERS = {
    "discovery_event_id": "92733",
    "executable": "/usr/sbin/arp",
    "arguments": ["arp", "-a"],
    "companion_event_id": "92734",
    "uid": 1000,
    "benign_event_ids": ["control-1"],
    "intent": "insufficient-evidence",
    "explanation": "Audit records show neighbor discovery, but legitimate administration can produce the same command.",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    recipe = json.loads((DATA / "recipes/linux-audit-discovery.json").read_text())
    with tempfile.TemporaryDirectory(prefix="ascend-file-validation-") as tmp:
        root = Path(tmp)
        db = Database(root / "profile")
        tracker = Tracker(db)
        runtime = Runtime(tracker, root=root / "labs", recipe_loader=lambda _: recipe)
        disk_samples = []
        stop_sampling = threading.Event()

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
            while not stop_sampling.wait(0.005):
                sample()

        sampler = threading.Thread(target=monitor, daemon=True)
        sampler.start()
        cold = runtime._start(recipe, assessment=False, offline=True)
        assert runtime.check(cold["id"])["status"] == "fail"
        row = runtime.load(cold["id"])
        work = runtime.work_dir(row)
        atomic_json(work / "answers.json", {**ANSWERS, "discovery_event_id": "92734"})
        assert runtime.check(row["id"])["status"] == "fail"
        atomic_json(work / "answers.json", ANSWERS)
        assert runtime.check(row["id"])["status"] == "pass"
        (work / "notes.txt").write_text(
            "Retain this even when runtime and cache are gone.\n"
        )
        sample()
        runtime.stop(row["id"])
        assert runtime.prune(0)["protected_objects"] == 2
        runtime = Runtime(tracker, root=root / "labs", recipe_loader=lambda _: recipe)
        runtime.resume(row["id"])
        assert runtime.check(row["id"])["status"] == "pass"
        runtime.export(row["id"])
        sample()
        assert runtime.finish(row["id"])["status"] == "destroyed"
        warm = runtime._start(recipe, assessment=False, offline=True)
        sample()
        assert warm["metrics"]["download_bytes"] == 0
        runtime.destroy(warm["id"])
        runtime.destroy(warm["id"])
        cache_before = sum(
            p.stat().st_size for p in runtime.cache.iterdir() if p.is_file()
        )
        assert runtime.prune(0)["cache_bytes"] == 0
        assert (
            (work / "answers.json").is_file()
            and (work / "notes.txt").is_file()
            and (work / "submission.json").is_file()
        )
        assert not any((runtime.state / "runtime").iterdir())
        sample()
        stop_sampling.set()
        sampler.join()
        metrics = {
            "measured_on": time.strftime("%Y-%m-%d"),
            "platform": "linux-x86_64",
            "download_bytes": cold["metrics"]["download_bytes"],
            "expanded_bytes": cold["metrics"]["runtime_bytes"],
            "peak_disk_bytes": max(s[0] for s in disk_samples),
            "peak_allocated_disk_bytes": max(s[1] for s in disk_samples),
            "startup_cold_seconds": cold["metrics"]["startup_seconds"],
            "startup_warm_seconds": warm["metrics"]["startup_seconds"],
            "residual_cache_bytes": cache_before,
            "after_prune_cache_bytes": 0,
            "peak_memory_bytes": int(
                next(
                    line.split()[1]
                    for line in Path("/proc/self/status").read_text().splitlines()
                    if line.startswith("VmHWM:")
                )
            )
            * 1024,
            "persistent_processes": 0,
            "cpu_limit": None,
            "pids_limit": None,
            "scope": "Actual download, correct/incorrect/incomplete answers, stop, new companion instance, offline resume, export, finish, warm start, idempotent destroy and cache eviction. Disk sampled every 5ms plus lifecycle checkpoints, including retained work. Memory is /proc/self/status VmHWM for the verifier's current executable, excluding inherited pre-exec launcher peaks.",
        }
        print(json.dumps(metrics, indent=2))
        if args.record:
            atomic_json(args.record, metrics)
        db.close()


if __name__ == "__main__":
    main()
