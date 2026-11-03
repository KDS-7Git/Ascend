"""Narrow Docker operations with owned resources and bounded command output."""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from ascend.local_labs.assets import atomic_json


class Docker:
    def __init__(self, runtime):
        self.runtime = runtime

    def run(self, *args, timeout=30, missing=False):
        # Argument vectors only. No shell, inherited stdin, generic exec API or arbitrary mounts.
        with tempfile.TemporaryFile() as out:
            process = subprocess.Popen(["docker", *args], stdin=subprocess.DEVNULL, stdout=out, stderr=out)
            deadline = time.monotonic() + timeout
            try:
                while process.poll() is None:
                    if time.monotonic() >= deadline or os.fstat(out.fileno()).st_size > 1_048_576:
                        raise ValueError("Docker command exceeded its time or output limit")
                    time.sleep(.05)
                out.seek(0)
                output = out.read(1_048_577).decode("utf-8", errors="replace")
                if len(output.encode()) > 1_048_576:
                    raise ValueError("Docker output exceeds 1 MiB")
                if process.returncode:
                    if missing and any(text in output.lower() for text in ("no such", "not found")):
                        return None
                    raise ValueError("Docker: " + output.strip()[-2000:])
                return output.strip()
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()

    def provider(self):
        explicit = os.environ.get("DOCKER_HOST")
        endpoint = (None if os.environ.get("DOCKER_CONTEXT") else explicit) or json.loads(self.run("context", "inspect", "--format", "{{json .Endpoints.docker.Host}}"))
        if not endpoint.startswith("unix://"):
            raise ValueError("This recipe requires a local Unix-socket Docker context")
        info = json.loads(self.run("info", "--format", "{{json .}}"))
        if info["OSType"] != "linux" or info["Architecture"] not in {"x86_64", "amd64"}:
            raise ValueError("This container recipe is validated only on Linux x86-64")
        if int(info["ServerVersion"].split(".")[0]) < 28:
            raise ValueError("Docker 28 or newer is required for loopback publication behavior")
        root = Path(info["DockerRootDir"])
        inspected = root
        while True:
            try:
                free = shutil.disk_usage(inspected).free
                break
            except OSError:
                if inspected.parent == inspected:
                    raise ValueError("Cannot inspect the Docker storage filesystem") from None
                inspected = inspected.parent
        return {"version": info["ServerVersion"], "memory_bytes": info["MemTotal"], "cpus": info["NCPU"],
                "storage_root": str(root), "free_bytes": free, "free_space_probe": str(inspected),
                "quota_note": "Filesystem free space; per-container SQLite size limits are enforced separately."}

    def inspect(self, kind, name):
        result = self.run(kind, "inspect", name, missing=True)
        return json.loads(result)[0] if result is not None else None

    def labels(self, row):
        return {"org.ascend.owner": row["owner"], "org.ascend.run": row["id"], "org.ascend.recipe": row["recipe"]["id"]}

    def label_args(self, row):
        return [arg for key, value in self.labels(row).items() for arg in ("--label", key + "=" + value)]

    def owned(self, kind, name, row):
        item = self.inspect(kind, name)
        if item:
            labels = (item.get("Config", {}).get("Labels") if kind == "container" else item.get("Labels")) or {}
            if any(labels.get(k) != v for k, v in self.labels(row).items()):
                raise ValueError(f"Refusing to modify unowned {kind}: {name}")
        return item

    def remove(self, kind, name, row):
        if self.owned(kind, name, row):
            self.run(kind, "rm", *( ["-f"] if kind == "container" else []), name)

    def image(self, recipe):
        spec = recipe["image"]
        image = self.inspect("image", spec["reference"])
        path = self.runtime.state / "images" / (spec["reference"].split("sha256:")[1] + ".json")
        if image:
            return image, False
        # Remember acquisition before a pull, so an interrupted command is reconcilable.
        atomic_json(path, {"reference": spec["reference"], "acquired": True, "owner": self.runtime.owner()})
        self.run("pull", "--platform", "linux/amd64", spec["reference"], timeout=600)
        image = self.inspect("image", spec["reference"])
        if not image:
            raise ValueError("Image pull did not produce the pinned image")
        return image, True

    def prune_images(self, protected):
        result = {"removed": [], "retained": [], "errors": []}
        for path in (self.runtime.state / "images").glob("*.json"):
            record = json.loads(path.read_text())
            ref = record["reference"]
            if not record.get("acquired") or record.get("owner") != self.runtime.owner():
                continue
            try:
                if ref in protected or self.run("ps", "-aq", "--filter", "ancestor=" + ref):
                    result["retained"].append(ref)
                    continue
                if self.inspect("image", ref):
                    self.run("image", "rm", ref)  # No force and no global prune.
                path.unlink()
                result["removed"].append(ref)
            except (ValueError, OSError) as error:
                result["errors"].append({"reference": ref, "error": str(error)})
        return result

    def resource_runs(self):
        """Discover late daemon completions after a client was killed."""
        runs = set()
        owner = self.runtime.owner()
        for kind in ("container", "network", "volume"):
            ids = self.run(kind, "ls", *(["-a"] if kind == "container" else []), "-q", "--filter", "label=org.ascend.owner=" + owner).split()
            for name in ids:
                item = self.inspect(kind, name)
                labels = (item.get("Config", {}).get("Labels") if kind == "container" else item.get("Labels")) if item else {}
                if labels and labels.get("org.ascend.owner") == owner:
                    runs.add(labels.get("org.ascend.run"))
        return runs
