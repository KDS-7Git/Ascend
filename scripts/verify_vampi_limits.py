"""Measure acquisition and exercise actual request/database limits of the local API."""

import argparse
import http.client
import json
import shutil
import sys
import tempfile
from pathlib import Path

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
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument(
        "--cold",
        action="store_true",
        help="Require the selected image to be absent before the test",
    )
    args = parser.parse_args()
    recipe = json.loads((DATA / "recipes/vampi-ownership.json").read_text())
    root = Path(tempfile.mkdtemp(prefix="ascend-vampi-limits-"))
    db = Database(root / "profile")
    runtime = Runtime(Tracker(db), root=root / "labs", recipe_loader=lambda _: recipe)
    docker = Docker(runtime)
    free = shutil.disk_usage(root).free
    try:
        if args.cold and docker.inspect("image", recipe["image"]["reference"]):
            raise ValueError(
                "Cold test needs an absent image; it never deletes preexisting images"
            )
        row = runtime._start(recipe, offline=True, assessment=False)
        print("ready", row["metrics"], flush=True)
        assert runtime.check(row["id"])["status"] == "pass", "Initial comparison"
        port = row["ports"]["vulnerable"]
        token = request_json(
            port, "/users/v1/login", {"username": "name1", "password": "pass1"}
        )[1]["auth_token"]
        failure = None
        for n in range(400):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            body = json.dumps({"book_title": f"quota-{n}", "secret": "x" * 60000})
            connection.request(
                "POST",
                "/books/v1",
                body,
                {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token,
                },
            )
            response = connection.getresponse()
            status = response.status
            response.read()
            connection.close()
            if status != 200:
                failure = {"book_count": n, "http_status": status}
                break
        print("quota response", failure, flush=True)
        assert failure and failure["http_status"] == 500, failure
        target = row["resources"]["containers"]["vulnerable"]
        size = int(
            docker.run(
                "exec",
                target,
                "python",
                "-c",
                "import os;print(os.path.getsize('/vampi/database/database.db'))",
            )
        )
        assert size <= 16 * 1024 * 1024, ("SQLite size", size)
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        connection.request(
            "POST", "/books/v1", "x" * 65537, {"Content-Type": "application/json"}
        )
        assert connection.getresponse().status == 413, "Request bound"
        connection.close()
        memory = sum(
            int(
                docker.run(
                    "exec",
                    name,
                    "python",
                    "-c",
                    "from pathlib import Path;print(Path('/sys/fs/cgroup/memory.peak').read_text())",
                )
            )
            for name in [
                *row["resources"]["containers"].values(),
                row["resources"]["proxy"],
            ]
        )
        result = {
            "startup_seconds": row["metrics"]["startup_seconds"],
            "image_pulled": row["metrics"]["image_pulled"],
            "observed_disk_delta_bytes": max(0, free - shutil.disk_usage(root).free),
            "cgroup_peak_memory_sum_bytes": memory,
            "quota_failure": failure,
            "database_bytes_at_limit": size,
        }
        docker.remove("container", target, runtime.load(row["id"]))
        assert runtime.check(row["id"])["status"] == "error", (
            "Missing target must not pass"
        )
        assert runtime.destroy(row["id"])["status"] == "destroyed"
        assert not docker.resource_runs()
        result["cache_cleanup"] = runtime.prune(0, images=True)
        metrics = json.loads(args.record.read_text())
        metrics["cold_acquisition_and_quota_test"] = result
        if result["image_pulled"]:
            metrics["startup_cold_seconds"], metrics["image_pulled"] = (
                result["startup_seconds"],
                True,
            )
        metrics["peak_disk_bytes"] = max(
            metrics["peak_disk_bytes"], result["observed_disk_delta_bytes"]
        )
        metrics["peak_memory_bytes"] = max(metrics["peak_memory_bytes"], memory)
        metrics["scope"] += (
            " SQLite exhaustion at the 16 MiB limit, request size bound, error for a missing target, and acquired-image cache cleanup."
        )
        atomic_json(args.record, metrics)
        print(json.dumps(result, indent=2), flush=True)
    finally:
        for row in runtime.rows():
            if row["status"] != "destroyed":
                runtime.destroy(row["id"])
        db.close()
        if docker.resource_runs():
            print("Recovery profile:", root)
        else:
            shutil.rmtree(root)


if __name__ == "__main__":
    main()
