"""Run real FRR good/bad, persistence and cleanup cycles in disposable profiles."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

from ascend.application import Tracker
from ascend.local_labs.assets import atomic_json
from ascend.local_labs.catalog import detail
from ascend.local_labs.runtime import Runtime
from ascend.storage import Database


def solve(adapter, row):
    name, addresses = row["recipe"]["id"], row["addresses"]
    commands = ["configure terminal", "router bgp 65000"]
    if name == "bgp-single-session":
        commands += [f"neighbor {addresses['x1']} remote-as 65100"]
    elif name == "bgp-session-protection":
        commands += [
            f"neighbor {addresses['x1']} ttl-security hops 1",
            f"neighbor {addresses['x2']} password GuessWhat",
        ]
    else:
        commands = [
            "configure terminal",
            "ip prefix-list CUSTOMER seq 5 permit 192.168.42.0/24",
            "router bgp 65000",
            "address-family ipv4 unicast",
        ]
        commands += [
            f"neighbor {addresses[peer]} prefix-list CUSTOMER out"
            for peer in ("x1", "x2")
        ]
    adapter.command(row, "rtr", *commands, "end", "write memory")
    for node in addresses:
        adapter.command(row, node, "clear bgp ipv4 unicast *")
    for peer in addresses:
        if peer != "rtr":
            assert adapter.wait_session(row, peer, timeout=20), adapter.command(
                row, peer, "show bgp ipv4 unicast summary json"
            )


def verify_failures(runtime, root):
    """Exercise shared FRR recovery with actual owned Docker resources."""
    recipe = detail("bgp-single-session")
    row = runtime._start(recipe, offline=True, assessment=False)
    row = runtime.load(row["id"])
    adapter, work = runtime.adapter(row), runtime.work_dir(row)
    docker = adapter.docker
    holder = "ascend-bgp-validation-holder-" + row["id"][:12]
    try:
        solve(adapter, row)
        assert runtime.check(row["id"])["status"] == "pass"
        (work / "notes.txt").write_text(
            "Retained after interrupted export and cleanup.\n"
        )

        def failed_export(path, content):
            if Path(path).name == "submission.json":
                raise OSError("Injected evidence-disk write failure")
            return atomic_json(path, content)

        with patch("ascend.local_labs.runtime.atomic_json", failed_export):
            try:
                runtime.export(row["id"])
            except OSError:
                pass
            else:
                raise AssertionError("Evidence save failure was not reported")
        assert adapter.alive(row) and (work / "notes.txt").is_file()
        runtime.export(row["id"])

        try:
            docker.run(
                "exec",
                row["resources"]["containers"]["rtr"],
                "dd",
                "if=/dev/zero",
                "of=/tmp/ascend-fill",
                "bs=1048576",
                "count=10",
            )
        except ValueError as error:
            assert "No space left" in str(error), error
        else:
            raise AssertionError("The router tmpfs exceeded its bound")
        docker.run(
            "exec", row["resources"]["containers"]["rtr"], "rm", "/tmp/ascend-fill"
        )
        assert runtime.check(row["id"])["status"] == "pass"

        docker.remove("container", row["resources"]["containers"]["x1"], row)
        assert runtime.check(row["id"])["status"] == "error"
        docker.run(
            "create",
            "--name",
            holder,
            "--label",
            "org.ascend.validation=bgp-holder",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--user",
            "100:101",
            "--mount",
            f"type=volume,src={row['resources']['volumes']['rtr']},dst=/hold,readonly",
            "--entrypoint",
            "/bin/true",
            recipe["image"]["reference"],
        )
        assert runtime.destroy(row["id"])["status"] == "cleanup_failed"
        assert docker.inspect("container", holder)
        assert runtime.load(row["id"])["resources"] == row["resources"]
    finally:
        if docker.inspect("container", holder):
            docker.run("container", "rm", "-f", holder)
        assert runtime.destroy(row["id"])["status"] == "destroyed"
    assert (work / "notes.txt").is_file() and (work / "submission.json").is_file()
    print(
        "Failed export, bounded full tmpfs, missing router and busy-volume retry passed.",
        flush=True,
    )

    worker_code = """
import sys,time
from pathlib import Path
from ascend.application import Tracker
from ascend.storage import Database
from ascend.local_labs.runtime import Runtime
from ascend.local_labs.catalog import detail
root=Path(sys.argv[1])
runtime=Runtime(Tracker(Database(root/'profile')),root=root/'labs',recipe_loader=detail)
runtime._start(detail('bgp-single-session'),offline=True,assessment=False)
time.sleep(120)
"""
    before = {r["id"] for r in runtime.rows()}
    child = subprocess.Popen(
        [sys.executable, "-c", worker_code, str(root)],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            new = [r for r in runtime.rows() if r["id"] not in before]
            if (
                new
                and new[0]["resources"].get("network")
                and docker.owned("network", new[0]["resources"]["network"], new[0])
            ):
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Child did not begin provisioning")
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=10)
    runtime.reconcile()
    time.sleep(0.2)
    runtime.reconcile()
    assert not docker.resource_runs()
    print("Killed BGP companion reconciled.", flush=True)

    expiring = runtime._start(recipe, offline=True, assessment=False, lifetime=60)
    try:
        expiry = expiring["expires_at"]
        time.sleep(10)
        runtime.stop(expiring["id"])
        runtime.resume(expiring["id"])
        assert runtime.load(expiring["id"])["expires_at"] == expiry
        deadline = expiry + 8
        while time.time() < deadline and adapter.alive(runtime.load(expiring["id"])):
            time.sleep(1)
        assert not adapter.alive(runtime.load(expiring["id"]))
        assert runtime.reconcile()[0]["status"] == "destroyed"
    finally:
        assert runtime.destroy(expiring["id"])["status"] == "destroyed"
    assert not docker.resource_runs()
    print(
        "Absolute container expiry survived stop/resume; owned resources removed.",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cold",
        action="store_true",
        help="Remove the unused reviewed FRR image before measuring its acquisition",
    )
    args = parser.parse_args()
    measurements = []
    with tempfile.TemporaryDirectory(prefix="ascend-bgp-verification-") as folder:
        root = Path(folder)
        runtime = Runtime(
            Tracker(Database(root / "profile")),
            root=root / "labs",
            recipe_loader=detail,
        )
        for name in (
            "bgp-single-session",
            "bgp-session-protection",
            "bgp-prefix-filter",
        ):
            from ascend.local_labs.docker import Docker

            docker = Docker(runtime)
            recipe = detail(name)
            if args.cold:
                ref = recipe["image"]["reference"]
                if docker.run("ps", "-aq", "--filter", "ancestor=" + ref):
                    raise ValueError(
                        "The reviewed image is in use; cold acquisition cannot be measured"
                    )
                if docker.inspect("image", ref):
                    docker.run("image", "rm", ref)
            baseline = shutil.disk_usage(root).used
            disk_peak = [baseline]
            finished = threading.Event()

            def sample(finished=finished, disk_peak=disk_peak):
                while not finished.wait(0.05):
                    disk_peak[0] = max(disk_peak[0], shutil.disk_usage(root).used)

            observer = threading.Thread(target=sample)
            observer.start()
            started = time.monotonic()
            try:
                run = runtime._start(recipe, assessment=False)
            except BaseException:
                finished.set()
                observer.join()
                raise
            row = runtime.load(run["id"])
            adapter = runtime.adapter(row)
            try:
                assert adapter.docker.owned(
                    "network", row["resources"]["network"], row
                )["Internal"]
                for container in row["resources"]["containers"].values():
                    info = adapter.docker.owned("container", container, row)
                    host = info["HostConfig"]
                    assert host["ReadonlyRootfs"] and not host["Privileged"]
                    assert host["CapDrop"] == ["ALL"] and not host["CapAdd"]
                    assert host["Memory"] == host["MemorySwap"] == 134217728
                    assert host["NanoCpus"] == 500000000 and host["PidsLimit"] == 32
                    assert info["Config"]["User"] == "100:101"
                    assert not any(info["NetworkSettings"]["Ports"].values())
                    assert set(info["NetworkSettings"]["Networks"]) == {
                        row["resources"]["network"]
                    }
                    assert all(m["Type"] in {"volume", "tmpfs"} for m in info["Mounts"])
                bad = runtime.check(row["id"])
                print(name, "initial:", bad, flush=True)
                assert bad["status"] == "fail"
                solve(adapter, row)
                good = runtime.check(row["id"])
                print(name, "configured:", good, flush=True)
                assert good["status"] == "pass"
                if name == "bgp-session-protection":
                    interrupted = runtime.load(row["id"])
                    interrupted["active_probe"] = "x1"
                    runtime.save(interrupted)
                    adapter.configure_peer(
                        row,
                        "x1",
                        f"no neighbor {row['addresses']['rtr']} ttl-security hops 1",
                        f"neighbor {row['addresses']['rtr']} ebgp-multihop 2",
                    )
                    adapter.command(
                        row,
                        "rtr",
                        "configure terminal",
                        "router bgp 65000",
                        f"neighbor {row['addresses']['x1']} shutdown",
                        "end",
                    )
                    recovered = runtime.check(row["id"])
                    print(name, "interrupted probe recovered:", recovered, flush=True)
                    assert recovered["status"] == "pass"
                    assert "active_probe" not in runtime.load(row["id"])
                    adapter.command(
                        row,
                        "rtr",
                        "configure terminal",
                        "router bgp 65000",
                        f"no neighbor {row['addresses']['x1']} ttl-security hops 1",
                        f"neighbor {row['addresses']['x1']} ebgp-multihop 255",
                        "end",
                    )
                    assert adapter.wait_session(row, "x1", timeout=20)
                    unprotected = runtime.check(row["id"])
                    print(name, "GTSM disabled:", unprotected, flush=True)
                    checks = {c["id"]: c["status"] for c in unprotected["checks"]}
                    assert checks["session.x1"] == checks["prefix.x1"] == "pass"
                    assert checks["gtsm.rejected"] == "fail"
                    adapter.command(
                        row,
                        "rtr",
                        "configure terminal",
                        "router bgp 65000",
                        f"no neighbor {row['addresses']['x1']} ebgp-multihop 255",
                        "end",
                    )
                    solve(adapter, row)
                    restored = runtime.check(row["id"])
                    print(name, "GTSM restored:", restored, flush=True)
                    assert restored["status"] == "pass", json.loads(
                        (runtime.work_dir(row) / "bgp-observations.json").read_text()
                    )
                work = runtime.work_dir(row)
                (work / "notes.txt").write_text(
                    "I compared the expected route and its negative control.\n"
                )
                runtime.stop(row["id"])
                warm = time.monotonic()
                runtime.resume(row["id"])
                warm_seconds = time.monotonic() - warm
                for peer in row["addresses"]:
                    if peer != "rtr":
                        assert adapter.wait_session(row, peer, timeout=20)
                resumed = runtime.check(row["id"])
                print(name, "resumed:", resumed, flush=True)
                assert resumed["status"] == "pass"
                exported = runtime.export(row["id"])
                assert Path(exported["path"]).is_file()
                item = {
                    "recipe_id": name,
                    "startup_seconds": run["metrics"]["startup_seconds"],
                    "startup_warm_seconds": warm_seconds,
                    "cycle_seconds": time.monotonic() - started,
                    "metrics": run["metrics"],
                    "checks": good["checks"],
                    "peak_memory_bytes": sum(
                        int(
                            adapter.docker.run(
                                "exec", container, "cat", "/sys/fs/cgroup/memory.peak"
                            )
                        )
                        for container in row["resources"]["containers"].values()
                    ),
                    "peak_filesystem_delta_bytes": max(0, disk_peak[0] - baseline),
                    "measurement_scope": "Host filesystem sampled every 50 ms; unrelated activity may contribute. Memory is summed cgroup peaks including measurement execs. Images were "
                    + (
                        "absent at each start."
                        if args.cold
                        else "already cached unless image_pulled is true."
                    ),
                }
                measurements.append(item)
                # Exercise the receipt path while the candidate is still gated.
                row = runtime.load(row["id"])
                row["local_attempt"] = runtime.attempts.create(name, offline=True)
                runtime.save(row)
                final = runtime.finish(row["id"])
                assert final["status"] == "destroyed"
                assert final["local_receipt"]["result"]["status"] == "pass"
                assert final["local_receipt"]["result"]["authority"] == "local"
            finally:
                finished.set()
                observer.join()
                assert runtime.destroy(row["id"])["status"] == "destroyed"
                for kind, names in (
                    ("container", row["resources"]["containers"].values()),
                    ("volume", row["resources"]["volumes"].values()),
                    ("network", [row["resources"]["network"]]),
                ):
                    assert all(
                        adapter.docker.inspect(kind, resource) is None
                        for resource in names
                    )
            assert (work / "notes.txt").is_file() and (
                work / "submission.json"
            ).is_file()
        assert runtime.t.stats()["xp"]["total"] == 0
        verify_failures(runtime, root)
        reclaimed = runtime.prune(0, images=True)
        assert reclaimed["cache_bytes"] == 0 and not reclaimed["images"]["errors"]
        if args.cold:
            assert docker.inspect("image", recipe["image"]["reference"]) is None
    Path("docs/testing/local-bgp-measurements.json").write_text(
        json.dumps(measurements, indent=2) + "\n"
    )
    print(
        "Real BGP lifecycle checks passed for all three exercises; saved work retained and owned resources removed."
    )


if __name__ == "__main__":
    main()
