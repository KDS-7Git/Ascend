"""Account-scoped controller for a separate, administrator-owned lab host.

The web process only talks to the authenticated runner API. The runner reuses
reviewed local adapters with its own databases, inventory and absolute deadlines.
"""

import fcntl
import json
import os
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from ascend.application import Tracker
from ascend.local_labs.assets import atomic_json
from ascend.local_labs.catalog import executable
from ascend.local_labs.runner_protocol import ACTIONS, NoRedirect
from ascend.local_labs.runtime import Runtime
from ascend.storage import Database

RECIPES = frozenset(
    {
        "linux-audit-discovery",
        "vampi-ownership",
        "wrongsecrets-basics",
        "bgp-export-policy",
        "bgp-single-session",
        "bgp-session-protection",
        "bgp-prefix-filter",
    }
)
MAX_TEXT = 262144


class Controller:
    def __init__(
        self,
        root,
        *,
        recipes=RECIPES,
        max_active=2,
        reserve_bytes=10 * 1024**3,
        lifetime=7200,
    ):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.recipes = frozenset(recipes)
        if not self.recipes <= RECIPES or not self.recipes:
            raise ValueError("Runner recipes must be from the reviewed allowlist")
        if (
            not 1 <= max_active <= 16
            or not 60 <= lifetime <= 86400
            or reserve_bytes < 0
        ):
            raise ValueError("Invalid runner capacity or lifetime")
        self.max_active, self.reserve_bytes, self.lifetime = (
            max_active,
            reserve_bytes,
            lifetime,
        )
        self.service_lock = (self.root / ".service.lock").open("a")
        try:
            fcntl.flock(self.service_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.service_lock.close()
            raise ValueError("A runner is already using this home") from None
        self.executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="ascend-labs"
        )
        self.stopping = threading.Event()

    def account(self, account):
        if not isinstance(account, str) or not re.fullmatch(r"[a-f0-9]{64}", account):
            raise ValueError("Invalid runner account scope")
        path = self.root / "accounts" / account
        if path.is_symlink():
            raise ValueError("Account path is a symlink")
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path

    @contextmanager
    def lock(self, name):
        with (self.root / (name + ".lock")).open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    @contextmanager
    def runtime(self, account):
        home = self.account(account)
        db = Database(home / "tracker")
        try:
            yield Runtime(Tracker(db), root=home / "labs")
        finally:
            db.close()

    def job_path(self, account):
        return self.account(account) / "job.json"

    def job(self, account):
        path = self.job_path(account)
        return json.loads(path.read_text()) if path.exists() else None

    def rows(self, account):
        root = self.account(account) / "labs/state/runs"
        return sorted(
            [
                json.loads(p.read_text())
                for p in root.glob("*.json")
                if not p.is_symlink()
            ],
            key=lambda row: row["created_at"],
        )

    def load(self, account, run_id):
        if not re.fullmatch(r"[a-f0-9]{32}", run_id or ""):
            raise ValueError("Invalid run ID")
        for row in self.rows(account):
            if row["id"] == run_id:
                return row
        raise ValueError("Lab run not found for this account")

    def files(self, account, row):
        base = self.account(account) / "labs"
        work = base / "work" / row["id"]
        runtime = base / "state/runtime" / row["id"]
        result = {}
        for name in (
            "answers.json",
            "policy.json",
            "notes.txt",
            "TASK.txt",
            "submission.json",
        ):
            path = work / name
            if path.is_file() and not path.is_symlink():
                result["work/" + name] = path
        # Only reviewed input files, never launchers, cache contents or arbitrary host paths.
        for name, raw in row.get("files", {}).items():
            path = Path(raw)
            if (
                path.is_file()
                and path.resolve().is_relative_to(runtime)
                and not path.is_symlink()
            ):
                result["input/" + path.name] = path
        for asset in row["recipe"].get("assets", []):
            name = asset.get("path") or asset.get("filename")
            if name:
                for path in (
                    runtime / name,
                    runtime / Path(name).name,
                    runtime / name.replace("/", "-"),
                ):
                    if (
                        path.is_file()
                        and not path.is_symlink()
                        and path.resolve().is_relative_to(runtime)
                    ):
                        result["input/" + name] = path
        return result

    def view(self, account, row):
        adapter = row["recipe"]["adapter"]
        label = {
            "security-audit-v1": "Answer checked on server",
            "prefix-policy-v1": "Submission tested on server (policy model)",
        }.get(adapter, "Checked on server (live observations)")
        result = (
            {**row["last_check"], "authority": "server-runner", "evidence_label": label}
            if row.get("last_check")
            else None
        )
        return {
            "id": row["id"],
            "recipe_id": row["recipe"]["id"],
            "title": row["recipe"]["title"],
            "status": row["status"],
            "expires_at": row["expires_at"],
            "finished_at": row.get("finished_at"),
            "files": list(self.files(account, row)),
            "targets": list(row.get("endpoints", {})),
            "router": adapter == "frr-bgp-v1",
            "addresses": row.get("addresses", {}),
            "fixture": row.get("fixture", {}),
            "result": result,
            "cleanup_error": row.get("cleanup_error"),
            "evidence_label": label,
            "xp": 0,
            "satisfies_track_evidence": False,
        }

    def status(self, account):
        job = self.job(account)
        return {"runs": [self.view(account, r) for r in self.rows(account)], "job": job}

    def capabilities(self):
        free = shutil.disk_usage(self.root).free
        return {
            "configured": True,
            "recipes": sorted(self.recipes),
            "max_active": self.max_active,
            "lifetime_seconds": self.lifetime,
            "free_bytes": free,
            "reserve_bytes": self.reserve_bytes,
        }

    def queue(self, account, action, run_id=None, data=None):
        if action not in ACTIONS:
            raise ValueError("Unknown runner action")
        data = data or {}
        if len(json.dumps(data).encode()) > MAX_TEXT + 8192:
            raise ValueError("Runner input is too large")
        with self.lock("reservations"):
            previous = self.job(account)
            if previous and previous["status"] in {"queued", "running"}:
                raise ValueError(
                    "A lab operation is already running; wait for its result"
                )
            if action == "start":
                recipe_id = data.get("recipe_id")
                if recipe_id not in self.recipes:
                    raise ValueError("Recipe is not enabled on this runner")
                recipe = executable(recipe_id)
                active = set()
                for path in (self.root / "accounts").iterdir():
                    scope = path.name
                    if any(r["status"] != "destroyed" for r in self.rows(scope)):
                        active.add(scope)
                    job = self.job(scope)
                    if (
                        job
                        and job["action"] == "start"
                        and job["status"] in {"queued", "running"}
                    ):
                        active.add(scope)
                if account in active:
                    raise ValueError("Finish or destroy your existing server lab first")
                if len(active) >= self.max_active:
                    raise ValueError("The server lab slots are full; try again later")
                if shutil.disk_usage(self.root).free < self.reserve_bytes + recipe.get(
                    "minimum_free_bytes", 1048576
                ):
                    raise ValueError("The runner has insufficient free disk space")
            else:
                self.load(account, run_id)
            job = {
                "id": os.urandom(16).hex(),
                "action": action,
                "run_id": run_id,
                "status": "queued",
                "created_at": time.time(),
            }
            atomic_json(self.job_path(account), job)
            self.executor.submit(self.perform, account, job, data)
            return job

    def perform(self, account, job, data):
        with self.lock("operations"):
            job["status"] = "running"
            atomic_json(self.job_path(account), job)
            try:
                with self.runtime(account) as runtime:
                    action, run_id = job["action"], job["run_id"]
                    if action == "start":
                        result = runtime.start(
                            data["recipe_id"], offline=True, lifetime=self.lifetime
                        )
                        job["run_id"] = result["id"]
                    elif action in {"save", "http", "router"}:
                        with runtime.lock():
                            row = runtime.load(run_id)
                            if (
                                row["status"] != "ready"
                                or row["expires_at"] <= time.time()
                            ):
                                raise ValueError(
                                    "Resume a non-expired server lab before using its workspace"
                                )
                            result = getattr(self, action)(account, runtime, row, data)
                            if action in {"save", "http", "router"}:
                                row.pop("last_check", None)
                                runtime.save(row)
                    else:
                        result = getattr(runtime, action)(run_id)
                    # Runtime public records contain host paths/inventory; expose only bounded operation output.
                    if action == "check":
                        result = {
                            **result,
                            "authority": "server-runner",
                            "evidence_label": self.view(account, runtime.load(run_id))[
                                "evidence_label"
                            ],
                        }
                    job["result"] = (
                        result
                        if action in {"check", "http", "router", "save"}
                        else {"run_id": job["run_id"], "status": result["status"]}
                    )
                    job["status"] = "complete"
            except Exception as error:  # noqa: BLE001 - every queued job must reach a recorded terminal state.
                job["status"], job["error"] = "failed", str(error)[:2000]
            job["completed_at"] = time.time()
            atomic_json(self.job_path(account), job)

    def read(self, account, run_id, name):
        row = self.load(account, run_id)
        path = self.files(account, row).get(name)
        if not path or path.is_symlink() or path.stat().st_size > MAX_TEXT:
            raise ValueError("File is unavailable or exceeds 256 KiB")
        content = path.read_bytes()[: MAX_TEXT + 1]
        if len(content) > MAX_TEXT:
            raise ValueError("File exceeds 256 KiB")
        return {
            "name": name,
            "content": content.decode("utf-8"),
            "editable": name
            in {"work/answers.json", "work/policy.json", "work/notes.txt"}
            and row["status"] == "ready"
            and row["expires_at"] > time.time(),
        }

    def save(self, account, runtime, row, data):
        name, content = data.get("name"), data.get("content")
        if (
            name not in {"work/answers.json", "work/policy.json", "work/notes.txt"}
            or not isinstance(content, str)
            or len(content.encode()) > MAX_TEXT
        ):
            raise ValueError(
                "Only bounded answers, policy and notes files may be edited"
            )
        path = self.files(account, row).get(name)
        if not path or path.is_symlink():
            raise ValueError("File is unavailable")
        if name.endswith(".json"):
            atomic_json(path, json.loads(content))
        else:
            # Notes use the same atomic replace as structured work.
            import tempfile

            fd, tmp = tempfile.mkstemp(dir=path.parent)
            try:
                with os.fdopen(fd, "w") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(tmp, path)
            finally:
                Path(tmp).unlink(missing_ok=True)
        return {"saved": name}

    def http(self, account, runtime, row, data):
        target, path, method = (
            data.get("target"),
            data.get("path", "/"),
            data.get("method", "GET"),
        )
        endpoint = row.get("endpoints", {}).get(target)
        if not endpoint or not re.fullmatch(r"http://127\.0\.0\.1:[0-9]+", endpoint):
            raise ValueError("Unknown fixed lab target")
        if (
            not isinstance(path, str)
            or len(path) > 2048
            or not path.startswith("/")
            or path.startswith("//")
            or any(ord(c) < 32 for c in path)
            or urlsplit(path).netloc
            or "\\" in path
        ):
            raise ValueError("Use a relative path on the selected lab target")
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("Unsupported lab HTTP method")
        body, token = data.get("body", ""), data.get("token", "")
        if (
            not isinstance(body, str)
            or len(body.encode()) > 65536
            or not isinstance(token, str)
            or len(token) > 4096
            or "\r" in token
            or "\n" in token
        ):
            raise ValueError("Invalid request body or token")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = Request(
            endpoint + path,
            data=body.encode() if body else None,
            headers=headers,
            method=method,
        )
        opener = build_opener(NoRedirect())
        try:
            response = opener.open(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            content = response.read(MAX_TEXT + 1)
            if len(content) > MAX_TEXT:
                raise ValueError("Lab response exceeds 256 KiB")
            return {
                "status": response.code,
                "content_type": response.headers.get("Content-Type", ""),
                "body": content.decode("utf-8", errors="replace"),
            }

    def router(self, account, runtime, row, data):
        if row["recipe"]["adapter"] != "frr-bgp-v1":
            raise ValueError("This is not a BGP workspace")
        commands = data.get("commands")
        if not isinstance(commands, list) or not 1 <= len(commands) <= 40:
            raise ValueError("Submit between 1 and 40 router commands")
        peers = [re.escape(v) for k, v in row["addresses"].items() if k != "rtr"]
        peer = "(?:" + "|".join(peers) + ")"
        # Complete command matches: no shell, file/daemon controls, external peer edits or paths.
        patterns = [
            r"(?:show running-config|show bgp ipv4 unicast(?: summary)?(?: json)?|show ip prefix-list|configure terminal|end|exit|write memory)",
            r"router bgp 65000",
            r"address-family ipv4 unicast",
            r"exit-address-family",
            r"(?:no )?bgp ebgp-requires-policy",
            r"(?:no )?network (?:192\.168\.42\.0/24|10\.0\.0\.1/32)",
            rf"(?:no )?neighbor {peer} (?:remote-as 6510[01]|activate|shutdown|ttl-security hops [1-9]|password [A-Za-z0-9_-]{{1,64}}|prefix-list [A-Za-z][A-Za-z0-9_-]{{0,31}} (?:in|out))",
            r"(?:no )?ip prefix-list [A-Za-z][A-Za-z0-9_-]{0,31}(?: seq [0-9]{1,4})? (?:permit|deny) (?:192\.168\.42\.0/24|10\.0\.0\.1/32|0\.0\.0\.0/0)(?: (?:le|ge) (?:[1-9]|[12][0-9]|3[0-2]))?",
            r"clear bgp \* soft out",
            r"clear bgp ipv4 unicast \*",
        ]
        if any(
            not isinstance(c, str) or not any(re.fullmatch(p, c) for p in patterns)
            for c in commands
        ):
            raise ValueError(
                "A command is outside the supported BGP exercise command set"
            )
        adapter = runtime.adapter(row)
        output = adapter.command(row, "rtr", *commands)
        if "write memory" in commands:
            # Authentication changes need fresh sockets on both ends. Reset
            # only this run's sessions, preserving all external control rules.
            for node in row["addresses"]:
                adapter.command(row, node, "clear bgp ipv4 unicast *")
        if len(output.encode()) > MAX_TEXT:
            raise ValueError("Router output exceeds 256 KiB")
        return {"output": output}

    def reconcile(self, recover=False):
        with self.lock("operations"):
            for path in (self.root / "accounts").glob("*"):
                account = path.name
                try:
                    if recover:
                        job = self.job(account)
                        if job and job["status"] in {"queued", "running"}:
                            job.update(
                                status="failed",
                                error="Runner restarted during this operation; inspect the retained run and retry cleanup.",
                            )
                            atomic_json(self.job_path(account), job)
                    with self.runtime(account) as runtime:
                        runtime.reconcile()
                        runtime.prune(32)
                except (ValueError, OSError):
                    # Failed deletion remains in its inventory and counts toward capacity.
                    import logging

                    logging.getLogger(__name__).exception(
                        "Runner reconciliation failed for scope %s", account
                    )

    def close(self):
        self.stopping.set()
        self.executor.shutdown(wait=True)
        self.service_lock.close()
