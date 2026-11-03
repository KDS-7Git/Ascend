"""Linux companion lifecycle. Explicit CLI calls only; never imported by API routes."""

import fcntl
import json
import os
import platform
import re
import secrets
import shutil
import time
from contextlib import contextmanager
from pathlib import Path

from ascend.local_labs.assets import AssetStore, atomic_json
from ascend.local_labs.attempts import Attempts
from ascend.local_labs.catalog import detail, executable
from ascend.local_labs.checks import MAX_RESULT_BYTES, bounded

TERMINAL = {"destroyed"}


class Runtime:
    def __init__(self, tracker, *, root=None, server=None, recipe_loader=None):
        if getattr(tracker, "server_mode", False):
            raise ValueError("Local lab operations must run on the learner PC")
        self.t, self.server = tracker, server
        self.resolve = recipe_loader or executable
        base = root or os.environ.get("ASCEND_LAB_HOME")
        if base:
            base = Path(base).expanduser()
            self.state, self.cache, self.work = base / "state", base / "cache", base / "work"
        else:
            data = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser() / "ascend"
            self.state = data / "labs"
            self.work = data / "lab-work"
            self.cache = Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")).expanduser() / "ascend/labs"
        for path in (self.state, self.cache, self.work):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.attempts = Attempts(tracker)
        # An explicit/shared lab directory must never attach another profile's
        # resources to the new profile's attempt IDs.
        with self.lock():
            self.owner()

    @contextmanager
    def lock(self):
        with (self.state / ".lock").open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def owner(self):
        path = self.state / "owner.json"
        profile = {"home": str(self.t.db.home.resolve()), "user_id": self.t.db.user_id}
        if path.is_symlink():
            raise ValueError("Local lab owner file is a symlink")
        if not path.exists():
            atomic_json(path, {"id": secrets.token_hex(16), "profile": profile})
        owner = json.loads(path.read_text())
        if "profile" not in owner:
            # Upgrade existing records only when their nonces match this DB.
            for run in (self.state / "runs").glob("*.json"):
                attempt = json.loads(run.read_text()).get("local_attempt")
                if attempt:
                    try:
                        self.attempts.authorize(attempt["id"], attempt["nonce"])
                    except ValueError:
                        raise ValueError("Existing lab state belongs to a different Ascend profile; restore ASCEND_HOME or choose another ASCEND_LAB_HOME") from None
            owner["profile"] = profile
            atomic_json(path, owner)
        if owner["profile"] != profile:
            raise ValueError("Lab state belongs to a different Ascend profile; restore ASCEND_HOME or choose another ASCEND_LAB_HOME")
        return owner["id"]

    def state_path(self, run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise ValueError("Invalid local run ID")
        return self.state / "runs" / (run_id + ".json")

    def load(self, run_id):
        path = self.state_path(run_id)
        if not path.is_file() or path.is_symlink():
            raise ValueError("Local lab run not found")
        row = json.loads(path.read_text())
        if row["id"] != run_id or row["owner"] != self.owner():
            raise ValueError("Local lab ownership mismatch")
        return row

    def save(self, row):
        row["updated_at"] = time.time()
        atomic_json(self.state_path(row["id"]), row)

    def rows(self):
        return [self.load(p.stem) for p in sorted((self.state / "runs").glob("*.json"))]

    def runtime_dir(self, row):
        self.state_path(row["id"])
        return self.state / "runtime" / row["id"]

    def work_dir(self, row):
        self.state_path(row["id"])
        return self.work / row["id"]

    def adapter(self, row):
        if row.get("evidence_only"):
            from ascend.local_labs.upstream import EvidenceOnly

            return EvidenceOnly(self)
        if row["recipe"]["adapter"] == "security-audit-v1":
            from ascend.local_labs.files import FileLab

            return FileLab(self)
        if row["recipe"]["adapter"] == "vampi-v1":
            from ascend.local_labs.vampi import Vampi

            return Vampi(self)
        if row["recipe"]["adapter"] == "prefix-policy-v1":
            from ascend.local_labs.prefix import PrefixLab

            return PrefixLab(self)
        if row["recipe"]["adapter"] == "wrongsecrets-v1":
            from ascend.local_labs.wrongsecrets import WrongSecrets

            return WrongSecrets(self)
        if row["recipe"]["adapter"] == "frr-bgp-v1":
            from ascend.local_labs.bgp import BgpLab

            return BgpLab(self)
        raise ValueError("Adapter is not installed; keep the run record for reconciliation")

    def public(self, row):
        result = {k: v for k, v in row.items() if k not in {"local_attempt", "remote_attempt", "owner"}} | {"work_dir": str(self.work_dir(row))}
        if row.get("evidence_only"):
            result["kind"], result["status"] = "external-report", "recorded"
        if row.get("external_workspace"):
            result["kind"] = "local-evidence-workspace"
            result["status"] = "archived" if row.get("archived") else "recorded" if row.get("finished_at") else "prepared"
        return result

    def show(self, run_id):
        return self.public(self.load(run_id))

    def history(self):
        return [self.public(r) for r in self.rows()]

    def prepare(self, recipe_id):
        from ascend.local_labs.workspaces import prepare

        return prepare(self, recipe_id)

    def capture(self, run_id, name, path):
        from ascend.local_labs.workspaces import capture

        return capture(self, run_id, name, path)

    def record(self, recipe_id, report_path):
        from ascend.local_labs.upstream import read_report, report_recipe

        recipe = report_recipe(recipe_id)
        report = read_report(recipe, report_path)
        with self.lock():
            row = {"schema_version": 1, "id": secrets.token_hex(16), "owner": self.owner(), "recipe": recipe,
                   "status": "destroyed", "resources": {}, "evidence_only": True,
                   "created_at": time.time(), "expires_at": time.time(), "finished_at": time.time(),
                   "server": self.server, "offline": True, "pending_sync": bool(self.server)}
            atomic_json(self.work_dir(row) / "upstream-report.json", report)
            self.save(row)
            data = self._export(row)
            attempt = self.attempts.create(recipe_id, offline=True)
            row["local_attempt"] = attempt
            row["local_receipt"] = self.attempts.submit(attempt["id"], self._payload(row, attempt, data))
            self.save(row)
        if self.server:
            try:
                return self.sync(row["id"])
            except (ValueError, OSError) as error:
                with self.lock():
                    row = self.load(row["id"])
                    row["sync_error"] = str(error)
                    self.save(row)
        return self.public(row)

    def doctor(self, recipe_id):
        recipe = detail(recipe_id)
        tested = recipe.get("tested_platforms", [])
        current = platform.system().lower() + "-" + platform.machine().lower()
        issues = list(recipe.get("review_gaps", []))
        if not recipe.get("adapter"):
            issues.append("Choose a reviewed recipe ID from lab detail")
        if current not in tested:
            issues.append(f"Platform {current} is not validated for this recipe")
        for name in recipe.get("required_tools", []):
            if not shutil.which(name):
                issues.append(f"Required tool is missing: {name}")
        free = min(shutil.disk_usage(path).free for path in (self.cache, self.state, self.work))
        needed = recipe.get("minimum_free_bytes", 1024 * 1024)
        if free < needed:
            issues.append(f"Needs {needed} free bytes; found {free}")
        provider = None
        if recipe.get("adapter") in {"vampi-v1", "wrongsecrets-v1", "frr-bgp-v1"} and shutil.which("docker"):
            from ascend.local_labs.docker import Docker

            try:
                provider = Docker(self).provider()
                memory = recipe.get("minimum_provider_memory_bytes", 536870912)
                if provider["free_bytes"] < needed or provider["memory_bytes"] < memory:
                    issues.append(f"Docker needs at least {memory // 1048576} MiB RAM and the recipe's minimum free disk")
            except (ValueError, OSError) as error:
                issues.append(str(error))
        return {"recipe_id": recipe_id, "platform": current, "status": "unsupported" if issues else "pass", "issues": issues,
                "free_bytes": free, "minimum_free_bytes": needed, "cache": str(self.cache), "work": str(self.work),
                "provider": provider,
                "first_download_bytes": sum(a["bytes"] for a in recipe.get("assets", [])) + sum(recipe.get(k, {}).get("compressed_bytes", 0) for k in ("image", "helper_image"))}

    def _remote(self, path, data=None, server=None):
        from ascend.cli.remote import request

        return request(server or self.server, path, data)

    def start(self, recipe_id, *, offline=False, lifetime=7200, on_prepare=None):
        recipe = self.resolve(recipe_id)
        report = self.doctor(recipe_id)
        if report["status"] != "pass":
            raise ValueError("; ".join(report["issues"]))
        if on_prepare:
            on_prepare(report)
        return self._start(recipe, offline=offline, lifetime=lifetime)

    def _start(self, recipe, *, offline=False, lifetime=7200, assessment=True):
        """Review harness can measure a candidate with assessment=False. No CLI bypass."""
        if type(lifetime) is not int or not 60 <= lifetime <= 86400:
            raise ValueError("Lifetime must be between 60 and 86400 seconds")
        with self.lock():
            if any(r["status"] not in TERMINAL for r in self.rows()):
                raise ValueError("Stop and finish/destroy the existing local lab, or reconcile an interrupted run")
            row = {"schema_version": 1, "id": secrets.token_hex(16), "owner": self.owner(),
                   "recipe": recipe, "status": "preparing", "resources": {},
                   "created_at": time.time(), "expires_at": time.time() + lifetime,
                   "server": self.server, "offline": offline, "pending_sync": False}
            self.save(row)  # Inventory exists before downloading/provisioning.
            started = time.monotonic()
            try:
                if assessment:
                    row["local_attempt"] = self.attempts.create(recipe["id"])
                    self.save(row)
                    if self.server and not offline:
                        row["remote_attempt"] = self._remote("/api/lab-attempts", {"recipe_id": recipe["id"], "offline": False})
                        self.save(row)
                        self._validate_remote(row, row["remote_attempt"], adopt=True)
                    if row["local_attempt"].get("assignment"):
                        row["assignment"] = row["local_attempt"]["assignment"]
                        row["fixture_id"] = row["local_attempt"]["fixture_id"]
                    self.save(row)
                row["metrics"] = self.adapter(row).prepare(row)
                if not self.adapter(row).alive(row):
                    raise ValueError("Lab did not become ready")
                if assessment:
                    attempt = row["local_attempt"]
                    self.attempts.ready(attempt["id"], attempt["nonce"])
                    if remote := row.get("remote_attempt"):
                        self._remote(f"/api/lab-attempts/{remote['id']}/ready", {"nonce": remote["nonce"]})
                row["status"], row["ready_at"] = "ready", time.time()
                row["metrics"]["startup_seconds"] = time.monotonic() - started
                self.save(row)
            except BaseException as error:
                row["error"] = str(error)[:2000]
                self._destroy(row)
                raise
            return self.public(row)

    def read_work(self, row, name, *, maximum=MAX_RESULT_BYTES):
        path = self.work_dir(row) / name
        if not path.is_file() or path.is_symlink() or path.stat().st_size > maximum:
            raise ValueError(f"Work must be a regular JSON file no larger than {maximum} bytes")
        try:
            with path.open("rb") as stream:
                content = stream.read(maximum + 1)
            if len(content) > maximum:
                raise ValueError("Work exceeds its allowed size")
            return bounded(json.loads(content), maximum)
        except (json.JSONDecodeError, UnicodeError, RecursionError):
            raise ValueError("Work must contain valid JSON") from None

    def check(self, run_id):
        with self.lock():
            row = self.load(run_id)
            if row.get("external_workspace"):
                if row.get("finished_at"):
                    return row["local_receipt"]["result"]
                from ascend.local_labs.workspaces import review

                return review(self, row)
            if row["status"] != "ready" or row["expires_at"] <= time.time():
                raise ValueError("Resume a non-expired lab before checking")
            row["last_check"] = self.adapter(row).check(row)
            self.save(row)
            return row["last_check"]

    def stop(self, run_id):
        with self.lock():
            row = self.load(run_id)
            if row["status"] == "stopped":
                return self.public(row)
            if row["status"] != "ready":
                raise ValueError("Only a ready lab can be stopped")
            self.adapter(row).stop(row)
            row["status"] = "stopped"
            self.save(row)
            return self.public(row)

    def resume(self, run_id):
        with self.lock():
            row = self.load(run_id)
            if row["status"] == "ready":
                return self.public(row)
            if row["status"] != "stopped" or row["expires_at"] <= time.time():
                raise ValueError("Only a stopped, non-expired lab can resume")
            current = self.resolve(row["recipe"]["id"])
            if current["version"] != row["recipe"]["version"]:
                raise ValueError("Recipe has changed; export old work and reset")
            try:
                row["metrics"] = self.adapter(row).prepare(row)
                if not self.adapter(row).alive(row):
                    raise ValueError("Lab did not become ready")
                row["status"] = "ready"
                self.save(row)
            except BaseException as error:
                row["error"] = str(error)[:2000]
                self._destroy(row)
                raise
            return self.public(row)

    def _export(self, row):
        data = {"schema_version": 1, "run_id": row["id"], "recipe_id": row["recipe"]["id"],
                "recipe_version": row["recipe"]["version"], "checker_version": row["recipe"]["checker_version"],
                "fixture_id": row.get("fixture_id", row["recipe"]["fixture_id"]), "authority": "local",
                **self.adapter(row).submission(row)}
        if row.get("assignment"):
            data["case_key"] = row["assignment"]["case_key"]
        bounded(data)
        path = self.work_dir(row) / "submission.json"
        atomic_json(path, data)  # If export fails, nothing is destroyed.
        row["export"] = str(path)
        self.save(row)
        return data

    def export(self, run_id):
        with self.lock():
            row = self.load(run_id)
            if row.get("external_workspace") and row.get("finished_at"):
                data = self.read_work(row, "submission.json")
                return {"path": str(self.work_dir(row) / "submission.json"), "bytes": len(json.dumps(data).encode()), "authority": "local"}
            data = self._export(row)
            return {"path": row["export"], "bytes": len(json.dumps(data).encode()), "authority": "local"}

    def _payload(self, row, attempt, data):
        return {"nonce": attempt["nonce"], **{k: data[k] for k in ("recipe_version", "checker_version", "fixture_id")},
                **{k: data[k] for k in ("answers", "report", "submission") if k in data}}

    def _validate_remote(self, row, remote, *, adopt=False):
        recipe = row["recipe"]
        if any(remote.get(k) != v for k, v in (("recipe_id", recipe["id"]), ("recipe_version", recipe["version"]), ("checker_version", recipe["checker_version"]))):
            raise ValueError("Remote recipe or checker version mismatch")
        if recipe["grading"] == "prefix-policy-v1":
            from ascend.local_labs.prefix import fixture_id

            if adopt:
                local = row["local_attempt"]
                row["local_attempt"] = self.attempts.adopt_local_assignment(local["id"], local["nonce"], remote)
                return
            if remote.get("assignment") != row.get("assignment") or fixture_id(recipe, remote.get("assignment")) != remote.get("fixture_id"):
                raise ValueError("Remote policy assignment mismatch")
        if remote.get("fixture_id") != row.get("fixture_id", recipe["fixture_id"]):
            raise ValueError("Remote fixture version mismatch")

    def finish(self, run_id):
        if self.load(run_id).get("external_workspace"):
            from ascend.local_labs.workspaces import finish

            return finish(self, run_id)
        with self.lock():
            row = self.load(run_id)
            if row["status"] not in {"ready", "stopped"}:
                raise ValueError("Only a ready or stopped lab can finish")
            data = self._export(row)
            if attempt := row.get("local_attempt"):
                row["local_receipt"] = self.attempts.submit(attempt["id"], self._payload(row, attempt, data))
            row["pending_sync"] = bool(row.get("server") or self.server)
            row["finished_at"] = time.time()
            self.save(row)
            self._destroy(row, abandon=False)
            if row["status"] != "destroyed":
                return self.public(row)
        if row["pending_sync"] and not row["offline"]:
            try:
                return self.sync(run_id)
            except (ValueError, OSError) as error:
                with self.lock():
                    row = self.load(run_id)
                    row["sync_error"] = str(error)[:1000]
                    self.save(row)
                return self.public(row)
        return self.public(row)

    def _destroy(self, row, *, abandon=True):
        row["status"] = "destroying"
        self.save(row)
        try:
            self.adapter(row).destroy(row)
            row["status"] = "destroyed"
            row.pop("cleanup_error", None)
        except (ValueError, OSError) as error:
            row["status"], row["cleanup_error"] = "cleanup_failed", str(error)[:2000]
        if abandon:
            if local := row.get("local_attempt"):
                self.attempts.abandon(local["id"], local["nonce"])
            if remote := row.get("remote_attempt"):
                try:
                    self._remote(f"/api/lab-attempts/{remote['id']}/abandon", {"nonce": remote["nonce"]}, server=row["server"])
                except (ValueError, OSError) as error:
                    row["pending_abandon"] = True
                    row["sync_error"] = str(error)[:1000]
        self.save(row)

    def destroy(self, run_id):
        with self.lock():
            row = self.load(run_id)
            if row.get("external_workspace"):
                row["archived"] = True
                self.save(row)
                return self.public(row)
            self._destroy(row, abandon=not row.get("finished_at"))
            return self.public(row)

    def reset(self, run_id):
        row = self.load(run_id)
        if row.get("external_workspace"):
            return self.prepare(row["recipe"]["id"])
        result = self.destroy(run_id)
        if result["status"] != "destroyed":
            raise ValueError("Cleanup failed; reconcile before resetting")
        return self.start(row["recipe"]["id"], offline=row["offline"])

    def reconcile(self):
        with self.lock():
            results = []
            rows = self.rows()
            late_runs = set()
            if any(r["recipe"]["adapter"] in {"vampi-v1", "wrongsecrets-v1", "frr-bgp-v1"} for r in rows):
                from ascend.local_labs.docker import Docker

                docker = Docker(self)
                docker.provider()
                late_runs = docker.resource_runs()
            for row in rows:
                if row["status"] in TERMINAL and row["id"] not in late_runs:
                    continue
                if (row["status"] not in {"ready", "stopped"} or row["expires_at"] <= time.time() or
                        (row["status"] == "ready" and not self.adapter(row).alive(row))):
                    self._destroy(row, abandon=not row.get("finished_at"))
                    results.append(self.public(row))
            unknown = late_runs - {r["id"] for r in rows}
            if unknown:
                results.append({"status": "cleanup_failed", "orphaned_runs": sorted(str(i) for i in unknown),
                                "error": "Owned provider resources lack their run manifest. Restore the manifest before deleting them."})
            return results

    def prune(self, budget_mib=128, images=False):
        if type(budget_mib) is not int or budget_mib < 0:
            raise ValueError("Cache budget must be non-negative MiB")
        with self.lock():
            protected = {a["sha256"] for row in self.rows() if row["status"] not in TERMINAL for a in row["recipe"]["assets"]}
            result = AssetStore(self.cache).prune(protected, budget_mib * 1048576)
            if images:
                from ascend.local_labs.docker import Docker

                docker = Docker(self)
                docker.provider()
                protected_images = {row["recipe"][key]["reference"] for row in self.rows() if row["status"] not in TERMINAL
                                    for key in ("image", "helper_image") if row["recipe"].get(key)}
                result["images"] = docker.prune_images(protected_images)
            return result

    def sync(self, run_id):
        with self.lock():
            row = self.load(run_id)
            server = row.get("server") or self.server
            if not server:
                raise ValueError("Configure an Ascend server before synchronizing")
            if self.server and self.server != server:
                raise ValueError("This run belongs to a different Ascend server")
            if row.get("pending_abandon"):
                remote = row["remote_attempt"]
                self._remote(f"/api/lab-attempts/{remote['id']}/abandon", {"nonce": remote["nonce"]}, server)
                row["pending_abandon"] = False
            elif row.get("finished_at") and not row.get("remote_receipt"):
                data = self.read_work(row, "submission.json")
                if not row.get("remote_attempt"):
                    row["server"] = server
                    request = {"recipe_id": row["recipe"]["id"], "offline": True}
                    if row.get("assignment"):
                        request["case_key"] = row["assignment"]["case_key"]
                    row["remote_attempt"] = self._remote("/api/lab-attempts", request, server)
                    self.save(row)
                remote = row["remote_attempt"]
                self._validate_remote(row, remote)
                existing = self._remote(f"/api/lab-attempts/{remote['id']}", server=server)
                # A response lost after commit is recovered by reading the owned receipt.
                row["remote_receipt"] = existing if existing["status"] == "finished" else self._remote(
                    f"/api/lab-attempts/{remote['id']}/submit", self._payload(row, remote, data), server)
                row["pending_sync"] = False
            else:
                raise ValueError("Finish the lab before synchronizing, or it is already synchronized")
            row.pop("sync_error", None)
            self.save(row)
            return self.public(row)
