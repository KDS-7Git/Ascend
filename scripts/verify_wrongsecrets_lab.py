"""Real WrongSecrets lifecycle, isolation limits and cold/warm measurements.

Uses disposable profiles and only owned Docker resources. --cold requires the
two image references to be absent; it never removes preexisting images to start.
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ascend.application import Tracker
from ascend.local_labs.assets import atomic_json
from ascend.local_labs.catalog import DATA
from ascend.local_labs.docker import Docker
from ascend.local_labs.runtime import Runtime
from ascend.local_labs.wrongsecrets import request
from ascend.storage import Database


@contextmanager
def validation_directory():
    root = tempfile.mkdtemp(prefix="ascend-wrongsecrets-validation-")
    try:
        yield root
    except BaseException:
        print("Validation state and saved work retained at " + root, flush=True)
        raise
    else:
        shutil.rmtree(root)


def answers(runtime, row):
    source = runtime.runtime_dir(row)
    values = {
        "challenge_1": re.search(r'password\s*=\s*"([^"]+)"', (source / "WrongSecretsConstants.java").read_text()).group(1),
        "challenge_2": re.search(r"^password=(.+)$", (source / "application.properties").read_text(), re.MULTILINE).group(1),
        "challenge_3": re.search(r'ENV DOCKER_ENV_PASSWORD="([^"]+)"', (source / "Dockerfile").read_text()).group(1),
        "explanation": "Source constants, configuration and image environment variables expose secrets to readers; use a scoped secret store and rotate exposed values.",
    }
    atomic_json(runtime.work_dir(row) / "answers.json", values)
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cold", action="store_true")
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    recipe = json.loads((DATA / "recipes/wrongsecrets-basics.json").read_text())
    with validation_directory() as directory:
        root = Path(directory)
        db = Database(root / "profile")
        tracker = Tracker(db)
        runtime = Runtime(tracker, root=root / "labs", recipe_loader=lambda _: recipe)
        d = Docker(runtime)
        d.provider()
        if args.cold and any(d.inspect("image", recipe[key]["reference"]) for key in ("image", "helper_image")):
            raise SystemExit("Cold measurement requires absent references; do not remove preexisting images")
        initial_free = shutil.disk_usage(root).free
        disk_samples, memory_samples, checks = [], [], []
        stop = threading.Event()

        def monitor():
            while not stop.wait(.05):
                disk_samples.append(initial_free - shutil.disk_usage(root).free)

        def memory(row):
            values = {}
            for name in [*row["resources"]["containers"].values(), row["resources"]["proxy"]]:
                info = d.owned("container", name, row)
                assert info["HostConfig"]["ReadonlyRootfs"] and info["HostConfig"]["CapDrop"] == ["ALL"]
                assert all(m["Type"] == "tmpfs" for m in info["Mounts"])
                values[name.rsplit("-", 1)[-1]] = int(d.run("exec", name, "cat", "/sys/fs/cgroup/memory.peak"))
            memory_samples.append(values)

        sampler = threading.Thread(target=monitor, daemon=True)
        sampler.start()
        try:
            print("Starting cold WrongSecrets lifecycle.", flush=True)
            cold = runtime._start(recipe, assessment=False)
            row = runtime.load(cold["id"])
            assert runtime.check(row["id"])["status"] == "fail"
            values = answers(runtime, row)
            assert runtime.check(row["id"])["status"] == "pass"
            port = row["port"]
            for path, code in [("/challenge/challenge-4", 404), ("/mcp", 404), ("/actuator/env", 404), ("/challenge/%63hallenge-1", 400)]:
                assert request(port, path)[0] == code
            assert request(port, "/", headers={"Origin": "https://unrelated.invalid"})[0] == 403
            assert request(port, "/challenge/challenge-1", data="x" * 65537)[0] == 413
            app = row["resources"]["containers"]["app"]
            info = d.owned("container", app, row)
            assert "CHALLENGE59_SLACK_WEBHOOK_URL=" in info["Config"]["Env"]
            assert d.owned("network", row["resources"]["network"], row)["Internal"]
            assert not info["NetworkSettings"]["Ports"]
            try:
                d.run("exec", app, "dd", "if=/dev/zero", "of=/tmp/ascend-quota-probe", "bs=1048576", "count=80")
            except ValueError as error:
                assert "space" in str(error).lower()
            else:
                raise AssertionError("tmpfs quota did not reject the oversized write")
            d.run("exec", app, "rm", "/tmp/ascend-quota-probe")
            assert runtime.check(row["id"])["status"] == "pass"
            memory(row)
            checks.extend(["correct-and-wrong-answers", "subset-origin-request-guards", "internal-network", "tmpfs-full-recovery"])
            print("Answer, boundary and disk-limit checks passed.", flush=True)
            runtime.stop(row["id"])
            started = time.monotonic()
            runtime.resume(row["id"])
            warm_seconds = time.monotonic() - started
            assert runtime.load(row["id"])["expires_at"] == row["expires_at"]
            assert json.loads((runtime.work_dir(row) / "answers.json").read_text()) == values
            assert runtime.check(row["id"])["status"] == "pass"
            runtime.export(row["id"])
            assert runtime.finish(row["id"])["status"] == "destroyed"
            assert runtime.destroy(row["id"])["status"] == "destroyed"
            saved = runtime.work_dir(row)
            assert all((saved / name).exists() for name in ("answers.json", "notes.txt", "submission.json", "checks.json"))
            checks.append("stop-resume-export-finish-retains-work")

            missing = runtime._start(recipe, assessment=False)
            d.remove("container", missing["resources"]["containers"]["app"], runtime.load(missing["id"]))
            assert runtime.check(missing["id"])["status"] == "error"
            assert runtime.reconcile()[0]["status"] == "destroyed"
            checks.append("missing-target-error-and-recovery")

            # Another owner keeps an endpoint attached; cleanup must stay visible.
            busy = runtime._start(recipe, assessment=False)
            busy = runtime.load(busy["id"])
            holder = "ascend-validation-holder-" + busy["id"][:12]
            holder_id = d.run("create", "--name", holder, "--label", "org.ascend.validation=" + busy["id"],
                              "--network", busy["resources"]["network"], "--read-only", "--cap-drop", "ALL",
                              "--memory", "32m", "--pids-limit", "8", "--user", "10001:10001", "--entrypoint", "python",
                              recipe["helper_image"]["reference"], "-c", "import time; time.sleep(90)")
            try:
                d.run("start", holder_id)
                assert runtime.destroy(busy["id"])["status"] == "cleanup_failed"
                assert d.inspect("container", holder_id)["State"]["Running"]
            finally:
                d.run("container", "rm", "-f", holder_id)
            assert runtime.reconcile()[0]["status"] == "destroyed"
            checks.append("busy-network-cleanup-failure-and-retry")
            print("Saved work, missing target and cleanup retry checks passed.", flush=True)

            # Kill the real companion after starting its target, before readiness.
            marker = root / "crash-marker"
            script = """import json,sys,time
from pathlib import Path
from ascend.application import Tracker
from ascend.storage import Database
from ascend.local_labs.catalog import DATA
from ascend.local_labs.docker import Docker
from ascend.local_labs.runtime import Runtime
root=Path(sys.argv[1]); recipe=json.loads((DATA/'recipes/wrongsecrets-basics.json').read_text())
r=Runtime(Tracker(Database(root/'profile')),root=root/'labs',recipe_loader=lambda _:recipe)
original=Docker.run
def crash_point(self,*args,**kwargs):
    result=original(self,*args,**kwargs)
    if args[0]=='start' and args[-1].endswith('-app'):
        (root/'crash-marker').write_text('started')
        time.sleep(60)
    return result
Docker.run=crash_point
r._start(recipe,assessment=False)
"""
            process = subprocess.Popen([sys.executable, "-c", script, str(root)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 60
                while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(.1)
                assert marker.exists(), "Companion did not reach the crash point"
                os.kill(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stderr.close()
            assert runtime.reconcile()[0]["status"] == "destroyed"
            checks.append("sigkill-during-start-reconciles")

            expiry = runtime._start(recipe, assessment=False, lifetime=60)
            expiry = runtime.load(expiry["id"])
            print("Waiting for the target's own deadline; the companion is idle.", flush=True)
            while time.time() <= expiry["expires_at"] + 2:
                time.sleep(.5)
            for name in [*expiry["resources"]["containers"].values(), expiry["resources"]["proxy"]]:
                assert not d.owned("container", name, expiry)["State"]["Running"]
            assert runtime.reconcile()[0]["status"] == "destroyed"
            checks.append("internal-hard-expiry")
            assert not d.resource_runs()
            pruned = runtime.prune(0, images=True)
            assert not pruned["images"]["errors"] and pruned["cache_bytes"] == 0
            assert (saved / "answers.json").is_file() and (saved / "submission.json").is_file()
            checks.append("no-resources-and-owned-image-cache-eviction")
        finally:
            stop.set()
            sampler.join()
            # Keep resources discoverable if a check fails; attempt cleanup while
            # their manifest still exists, and fail visibly if it cannot complete.
            for row in runtime.rows():
                if row["status"] != "destroyed":
                    runtime.destroy(row["id"])
            if d.resource_runs():
                raise RuntimeError("Validation left resources; restore its manifest before retrying")
            db.close()
        metrics = {"measured_on": time.strftime("%Y-%m-%d"), "platform": "linux-x86_64",
                   "cold_images_absent": args.cold,
                   "download_bytes": sum(recipe[k]["compressed_bytes"] for k in ("image", "helper_image")) + cold["metrics"]["download_bytes"],
                   "download_scope": "Compressed OCI layer/config sizes plus actual selected source downloads; not wire traffic.",
                   "expanded_bytes": cold["metrics"]["image_bytes"] + cold["metrics"]["runtime_bytes"],
                   "image_bytes": cold["metrics"]["image_bytes"], "build_cache_bytes": 0,
                   "peak_disk_bytes": max(disk_samples), "startup_cold_seconds": cold["metrics"]["startup_seconds"],
                   "startup_warm_seconds": warm_seconds, "peak_memory_bytes": max(sum(v.values()) for v in memory_samples),
                   "memory_samples": memory_samples, "memory_limits": {"target": 805306368, "proxy": 67108864},
                   "cpu_limits": {"target": 1, "proxy": .25}, "pid_limits": {"target": 128, "proxy": 16},
                   "tmpfs_bytes_limit": 67108864, "after_prune_cache_bytes": 0, "remaining_owned_resources": 0,
                   "checks": checks,
                   "scope": "Real Linux Docker runtime. Filesystem disk delta sampled every 50ms during cold pulls and all lifecycle checks; unrelated host activity can affect it. Sum of cgroup memory peaks includes the quota probe and measurement execs. Saved work survives cleanup; upstream browser badges are temporary. A separate browser test exercised correct/incorrect form submissions with no JavaScript exceptions."}
        print(json.dumps(metrics, indent=2), flush=True)
        if args.record:
            atomic_json(args.record, metrics)


if __name__ == "__main__":
    main()
