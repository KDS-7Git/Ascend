"""Explicitly trusted plugins run in a bounded subprocess, not a security sandbox."""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from ascend.engine.validation import guard_secrets
from ascend.engine.verifiers import VerifyResult


def plugin_path(db, name):
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise ValueError("Invalid plugin name")
    root = db.home if db.user_id == 1 else db.home / "users" / str(db.user_id)
    return root / "verifiers" / f"{name}.py"


def trust(db, name):
    path = plugin_path(db, name)
    if not path.is_file():
        raise ValueError("Plugin file not found in your verifiers directory")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    db.set_setting(f"plugin_trust:{name}", digest)
    return {"trusted": name, "sha256": digest}


def verify(db, name, spec, variables):
    path = plugin_path(db, name)
    if not path.is_file():
        return VerifyResult(False, "Plugin file not found")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if db.setting(f"plugin_trust:{name}") != digest:
        return VerifyResult(
            False, f"Run ascend plugin trust {name}; new or edited plugins need trust"
        )
    worker = Path(__file__).with_name("plugin_worker.py")
    try:
        with tempfile.TemporaryFile() as output:
            process = subprocess.run(
                [sys.executable, "-I", str(worker), str(path), digest],
                input=json.dumps({"spec": spec, "vars": variables}).encode(),
                stdout=output,
                stderr=subprocess.DEVNULL,
                timeout=10,
                shell=False,
            )
            if process.returncode:
                return VerifyResult(
                    False, "Plugin failed; check its interface and implementation"
                )
            output.seek(0)
            raw = json.loads(output.read(16385))
        if (
            type(raw["ok"]) is not bool
            or not isinstance(raw["summary"], str)
            or not 1 <= len(raw["summary"]) <= 1000
        ):
            raise ValueError("Invalid result")
        guard_secrets(raw["summary"])
        stamp = (
            datetime.fromisoformat(raw["evidence_time"])
            if raw.get("evidence_time")
            else None
        )
        if stamp and stamp.tzinfo is None:
            raise ValueError("Evidence time must include timezone")
        return VerifyResult(raw["ok"], raw["summary"], stamp)
    except subprocess.TimeoutExpired:
        return VerifyResult(False, "Plugin timed out after 10 seconds")
    except (OSError, ValueError, KeyError, TypeError):
        return VerifyResult(
            False, "Plugin returned invalid evidence or possible secrets"
        )
