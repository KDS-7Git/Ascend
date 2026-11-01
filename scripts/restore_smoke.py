"""Exercise the documented volume backup/restore using disposable Docker projects."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.request import urlopen
import uuid

ROOT = Path(__file__).resolve().parents[1]

SEED = """
from ascend.application import Tracker
from ascend.engine.packs import dump_toml
from ascend.storage import Database
db = Database()
tracker = Tracker(db)
tracker.install_pack(dump_toml({
    "pack": {"id": "restore-demo", "title": "Restore demonstration",
             "version": 1, "kind": "project", "source": "human", "reviewed": False},
    "level": [{"id": "first", "title": "First"}],
    "node": [{"id": "one", "level": "first", "title": "Synthetic evidence",
              "size": "S", "done_when": "Explain a small result",
              "resource": "https://docs.python.org/3/"}]
}))
tracker.start_mission("restore-demo")
tracker.log("I recorded a synthetic result for a restore drill", "Verify the backup")
tracker.mark("restore-demo:one", "done")
db.set_setting("nudge_enabled", True)
db.connection.execute("INSERT INTO users VALUES (2, 'synthetic', '!disabled', 'UTC', '2026-11-01')")
db.user_id = 2
db.set_setting("nudge_enabled", True)
db.close()
"""

VERIFY = """
from pathlib import Path
from ascend.storage import Database
db = Database()
assert db.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
assert len(db.rows("entries")) == 1
assert db.rows("missions")[0]["status"] == "active"
assert db.rows("node_state")[0]["status"] == "done"
assert Path(db.rows("packs")[0]["path"]).is_file()
for uid in (1, 2):
    db.user_id = uid
    assert db.setting("nudge_enabled") is False
db.close()
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="Already built local Ascend image")
    args = parser.parse_args()
    image_id = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", args.image], text=True
    ).strip()
    # Read the exact notification-disable/integrity program from the guide.
    guide = (ROOT / "docs/latex/deployment.tex").read_text()
    disable = guide.split("ascend - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    unique = "ascend-restore-test-" + uuid.uuid4().hex[:12]
    projects = [unique + "-source", unique + "-copy"]
    with tempfile.TemporaryDirectory(prefix="ascend-restore-smoke-") as directory:
        compose = Path(directory) / "compose.json"
        compose.write_text(
            json.dumps(
                {
                    "services": {
                        "ascend": {
                            "image": image_id,
                            "ports": ["127.0.0.1::8420"],
                            "volumes": ["data:/data"],
                            "environment": {"AUTH_MODE": "single"},
                        }
                    },
                    "volumes": {"data": {}},
                }
            )
        )

        def run(project, *command, data=None):
            return subprocess.run(
                ["docker", "compose", "-p", project, "-f", str(compose), *command],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=90,
            ).stdout

        def python(project, source):
            return run(
                project,
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "--entrypoint",
                "python",
                "ascend",
                "-",
                data=source.encode(),
            )

        try:
            python(projects[0], SEED)
            archive = run(
                projects[0],
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "--entrypoint",
                "tar",
                "ascend",
                "-C",
                "/data",
                "-czf",
                "-",
                ".",
            )
            run(
                projects[1],
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "--entrypoint",
                "tar",
                "ascend",
                "-C",
                "/data",
                "-xzf",
                "-",
                data=archive,
            )
            python(projects[1], disable)
            python(projects[1], VERIFY)
            run(projects[1], "up", "-d")
            address = run(projects[1], "port", "ascend", "8420").decode().strip()
            for attempt in range(60):
                try:
                    with urlopen(
                        "http://" + address + "/api/health", timeout=1
                    ) as response:
                        assert json.load(response)["status"] == "ok"
                    break
                except OSError:
                    if attempt == 59:
                        raise
                    time.sleep(0.2)
        finally:
            # Only these generated, synthetic projects can be removed here.
            for project in projects:
                run(project, "down", "-v", "--remove-orphans")
    result = (
        f"Disposable Docker restore drill, image {args.image} ({image_id}).\n"
        "Verified binary tar stream using -T, new volume ownership, SQLite integrity, "
        "entry/mission/node-state preservation and absolute pack paths at /data.\n"
        "Executed the guide's exact disable-reminders program; both synthetic accounts disabled.\n"
        "Restored HTTP health endpoint passed. Synthetic projects/volumes removed.\n"
        "No production profile, notification transport or arm64 host was used.\n"
        "RESULT: Restore smoke passed.\n"
    )
    (ROOT / "docs/testing/restore-smoke.txt").write_text(result)
    print(result, end="")


if __name__ == "__main__":
    main()
