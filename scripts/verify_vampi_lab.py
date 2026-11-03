"""Exercise the real reviewed image and lifecycle in an isolated companion profile."""

import argparse
import http.client
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ascend.application import Tracker
from ascend.local_labs.assets import atomic_json
from ascend.local_labs.catalog import DATA
from ascend.local_labs.docker import Docker
from ascend.local_labs.runtime import Runtime
from ascend.local_labs.vampi import request_json
from ascend.storage import Database


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    recipe = json.loads((DATA / "recipes/vampi-ownership.json").read_text())
    with tempfile.TemporaryDirectory(prefix="ascend-vampi-validation-") as tmp:
        root = Path(tmp)
        db = Database(root / "profile")
        runtime = Runtime(Tracker(db), root=root / "labs", recipe_loader=lambda _: recipe)
        docker = Docker(runtime)
        free_before = shutil.disk_usage(root).free
        free_samples = [free_before]
        row = None
        try:
            row = runtime._start(recipe, offline=True, assessment=False)
            print("ready", row["id"], flush=True)
            free_samples.append(shutil.disk_usage(root).free)
            checks = runtime.check(row["id"])
            assert checks["status"] == "pass", checks
            containers = row["resources"]["containers"]
            for name in containers.values():
                container = docker.owned("container", name, runtime.load(row["id"]))
                host = container["HostConfig"]
                assert host["ReadonlyRootfs"] and not host["Privileged"]
                assert host["CapDrop"] == ["ALL"] and not host["CapAdd"]
                assert host["Memory"] == 134217728 and host["PidsLimit"] == 64
                assert container["Config"]["User"] == "10001:10001"
                assert all(m["Type"] == "volume" for m in container["Mounts"] if m["Destination"] != "/tmp")
                assert not any(container["NetworkSettings"]["Ports"].values())
                assert set(container["NetworkSettings"]["Networks"]) == {row["resources"]["network"]}
            proxy = docker.owned("container", row["resources"]["proxy"], runtime.load(row["id"]))
            assert all(p["HostIp"] == "127.0.0.1" for ports in proxy["NetworkSettings"]["Ports"].values() for p in ports)
            assert docker.owned("network", row["resources"]["network"], runtime.load(row["id"]))["Internal"]
            stats = docker.run("stats", "--no-stream", "--format", "{{json .}}", *containers.values(), row["resources"]["proxy"])
            volumes = {}
            for profile, name in containers.items():
                probe = "import json,os,pathlib; print(json.dumps({'bytes':sum(os.path.getsize('/vampi/database/'+n) for n in os.listdir('/vampi/database')),'free_bytes':os.statvfs('/vampi/database').f_bavail*os.statvfs('/vampi/database').f_frsize,'memory_peak_bytes':int(pathlib.Path('/sys/fs/cgroup/memory.peak').read_text()),'pids_peak':int(pathlib.Path('/sys/fs/cgroup/pids.peak').read_text()),'cpu_stat':pathlib.Path('/sys/fs/cgroup/cpu.stat').read_text()}))"
                volumes[profile] = json.loads(docker.run("exec", name, "python", "-c", probe))
            proxy_measurement = json.loads(docker.run("exec", row["resources"]["proxy"], "python", "-c",
                "import json,pathlib;print(json.dumps({'memory_peak_bytes':int(pathlib.Path('/sys/fs/cgroup/memory.peak').read_text()),'pids_peak':int(pathlib.Path('/sys/fs/cgroup/pids.peak').read_text())}))"))
            port = row["ports"]["fixed"]
            token = request_json(port, "/users/v1/login", {"username": "name1", "password": "pass1"})[1]["auth_token"]
            assert request_json(port, "/books/v1", {"book_title": "saved-work-control", "secret": "preserved"}, token)[0] == 200
            work = runtime.work_dir(row)
            (work / "my-report.txt").write_text("My explanation survives both service lifecycles.\n")
            original_ready = row["ready_at"]
            runtime.stop(row["id"])
            started = time.monotonic()
            runtime.resume(row["id"])
            warm_seconds = time.monotonic() - started
            assert runtime.show(row["id"])["ready_at"] == original_ready
            port = runtime.show(row["id"])["ports"]["fixed"]
            assert request_json(port, "/books/v1/saved-work-control", token=token)[1]["secret"] == "preserved"
            assert runtime.check(row["id"])["status"] == "pass"
            free_samples.append(shutil.disk_usage(root).free)
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request("POST", "/books/v1", "{}", {"Origin": "https://unrelated.invalid", "Content-Type": "application/json"})
            assert connection.getresponse().status == 403
            connection.close()
            runtime.export(row["id"])
            assert runtime.finish(row["id"])["status"] == "destroyed"
            assert runtime.destroy(row["id"])["status"] == "destroyed"
            assert (work / "my-report.txt").is_file() and (work / "checks.json").is_file()

            # Actually launch the wrong fixed configuration; the checker must catch it.
            from ascend.local_labs.vampi import PROFILES
            with patch.dict(PROFILES, {"fixed": "1"}):
                broken = runtime._start(recipe, offline=True, assessment=False)
                assert runtime.check(broken["id"])["status"] == "fail"
                runtime.destroy(broken["id"])
            print("bad configuration rejected", flush=True)

            missing = runtime._start(recipe, offline=True, assessment=False)
            missing_row = runtime.load(missing["id"])
            docker.remove("container", missing["resources"]["containers"]["fixed"], missing_row)
            assert runtime.reconcile()[0]["status"] == "destroyed"
            print("missing container reconciled", flush=True)

            # Keep a volume busy with a separately owned test container. Cleanup must
            # retain the failed resource inventory and never delete the holder.
            busy = runtime._start(recipe, offline=True, assessment=False)
            holder = "ascend-validation-holder-" + busy["id"][:12]
            try:
                docker.run("create", "--name", holder, "--label", "org.ascend.validation=vampi-holder",
                           "--network", "none", "--read-only", "--cap-drop", "ALL", "--user", "10001:10001",
                           "--mount", f"type=volume,src={busy['resources']['volumes']['fixed']},dst=/hold,readonly",
                           "--entrypoint", "python", recipe["image"]["reference"], "-c", "pass")
                assert runtime.destroy(busy["id"])["status"] == "cleanup_failed"
                assert docker.inspect("container", holder)
            finally:
                docker.run("container", "rm", "-f", holder)
            assert runtime.reconcile()[0]["status"] == "destroyed"
            print("busy volume retained and cleanup retried", flush=True)

            worker_code = """
import json,sys,time
from pathlib import Path
from ascend.application import Tracker
from ascend.storage import Database
from ascend.local_labs.runtime import Runtime
from ascend.local_labs.catalog import DATA
root=Path(sys.argv[1])
recipe=json.loads((DATA/'recipes/vampi-ownership.json').read_text())
runtime=Runtime(Tracker(Database(root/'profile')),root=root/'labs')
runtime._start(recipe,offline=True,assessment=False)
time.sleep(120)
"""
            before_ids = {r["id"] for r in runtime.rows()}
            child = subprocess.Popen([sys.executable, "-c", worker_code, str(root)], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    new = [r for r in runtime.rows() if r["id"] not in before_ids]
                    if new and new[0]["resources"].get("network") and docker.owned("network", new[0]["resources"]["network"], new[0]):
                        break
                    time.sleep(.1)
                else:
                    raise AssertionError("Child did not begin provisioning")
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=10)
            runtime.reconcile()
            time.sleep(.2)
            runtime.reconcile()
            assert not docker.resource_runs()
            print("killed companion reconciled", flush=True)

            expiring = runtime._start(recipe, offline=True, assessment=False, lifetime=60)
            deadline = time.monotonic() + 70
            while time.monotonic() < deadline and runtime.adapter(runtime.load(expiring["id"])).alive(runtime.load(expiring["id"])):
                time.sleep(1)
            assert time.time() >= expiring["expires_at"]
            assert not runtime.adapter(runtime.load(expiring["id"])).alive(runtime.load(expiring["id"]))
            assert runtime.reconcile()[0]["status"] == "destroyed"
            print("in-container hard deadline enforced", flush=True)
            owner = runtime.owner()
            for kind in ("container", "network", "volume"):
                assert not docker.run(kind, "ls", "-q", "--filter", "label=org.ascend.owner=" + owner), kind
            metrics = {"measured_on": time.strftime("%Y-%m-%d"), "platform": "linux-x86_64", "image": recipe["image"]["reference"],
                       "download_bytes": recipe["image"]["compressed_bytes"] + sum(a["bytes"] for a in recipe["assets"]),
                       "download_scope": "Pinned compressed OCI layers/config plus selected assets; shared layers may already be cached. Not a packet-level traffic measurement.",
                       "image_pulled": row["metrics"]["image_pulled"], "expanded_bytes": row["metrics"]["image_bytes"],
                       "peak_disk_bytes": max(0, free_before - min(free_samples)),
                       "disk_scope": "Observed host filesystem delta at lifecycle checkpoints; includes Docker storage and unrelated concurrent filesystem activity. Image and volume bytes are also recorded independently.",
                       "startup_cold_seconds": row["metrics"]["startup_seconds"], "startup_warm_seconds": warm_seconds,
                       "stats": [json.loads(line) for line in stats.splitlines()], "volumes": volumes,
                       "proxy": proxy_measurement,
                       "peak_memory_bytes": sum(v["memory_peak_bytes"] for v in volumes.values()) + proxy_measurement["memory_peak_bytes"], "memory_limit_bytes": 335544320,
                       "memory_scope": "Sum of per-container cgroup memory.peak; includes the measurement process. Steady-state Docker stats are recorded separately.",
                       "cpu_limit_total": 1.25, "pids_limit_total": 160, "build_cache_bytes": 0,
                       "residual_owned_resources": 0, "saved_work_preserved": True,
                       "scope": "Real image source audit, six comparison probes, wrong fixed configuration, loopback/non-root/limits inspection, cross-origin refusal, volume persistence through stop/resume, export/finish, missing container, busy volume failure/retry, killed companion, hard expiry and idempotent cleanup."}
            print(json.dumps(metrics, indent=2), flush=True)
            if args.record:
                atomic_json(args.record, metrics)
        finally:
            for item in runtime.rows():
                if item["status"] != "destroyed":
                    runtime.destroy(item["id"])
            if docker.resource_runs():
                recovery = root.parent / (root.name + "-recovery")
                shutil.copytree(root, recovery)
                print("Cleanup needs reconciliation; recovery profile:", recovery, flush=True)
            db.close()


if __name__ == "__main__":
    main()
