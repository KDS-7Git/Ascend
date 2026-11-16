"""Shared lifecycle for fixed HTTP services with explicitly owned Docker resources."""

import shutil

from ascend.local_labs.assets import atomic_json
from ascend.local_labs.docker import Docker


class ServiceLab:
    def __init__(self, runtime):
        self.runtime, self.docker = runtime, Docker(runtime)

    def alive(self, row):
        for name in [
            *row["resources"].get("containers", {}).values(),
            row["resources"].get("proxy"),
        ]:
            if not name:
                return False
            info = self.docker.owned("container", name, row)
            if not info or not info["State"]["Running"]:
                return False
        return bool(row["resources"].get("containers"))

    def stop(self, row):
        for name in [
            row["resources"]["proxy"],
            *row["resources"]["containers"].values(),
        ]:
            if self.docker.owned("container", name, row):
                self.docker.run("stop", "--time", "5", name)

    def destroy(self, row):
        errors = []
        resources = row.get("resources", {})
        groups = [
            (
                "container",
                ([resources["proxy"]] if resources.get("proxy") else [])
                + list(resources.get("containers", {}).values())
                + list(resources.get("initializers", {}).values()),
            ),
            ("volume", list(resources.get("volumes", {}).values())),
            (
                "network",
                [
                    resources[k]
                    for k in ("network", "front_network")
                    if resources.get(k)
                ],
            ),
        ]
        for kind, names in groups:
            for name in names:
                try:
                    self.docker.remove(kind, name, row)
                except (ValueError, OSError) as error:
                    errors.append(str(error))
        if errors:
            raise ValueError("; ".join(errors))
        path = self.runtime.runtime_dir(row)
        if path.is_symlink():
            raise ValueError("Runtime directory is a symlink")
        if path.exists():
            shutil.rmtree(path)

    def submission(self, row):
        if not row.get("last_check"):
            raise ValueError("Run local-lab check before exporting a service report")
        result = {"report": {"checks": row["last_check"]["checks"]}}
        atomic_json(self.runtime.work_dir(row) / "checks.json", row["last_check"])
        return result
