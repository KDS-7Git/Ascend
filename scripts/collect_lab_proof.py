"""Collect signed, account-bound lab observations without exposing Docker to Ascend."""

import argparse
import fcntl
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import subprocess
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def atomic(path, data, mode=0o600):
    temporary = path.with_name(path.name + "." + secrets.token_hex(6))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "w") as stream:
        stream.write(data)
    temporary.replace(path)


def initialize(root):
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    (root / "receipts").mkdir(mode=0o755, exist_ok=True)
    env = root / "proofs.env"
    with (root / "init.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if not env.exists():
            atomic(env, "ASCEND_LAB_SIGNING_KEY=" + secrets.token_hex(32) + "\n")
        return env.read_text().strip().split("=", 1)[1]


def juice(project, owner, root):
    command = [
        "docker",
        "compose",
        "-p",
        project,
        "-f",
        str(ROOT / "docker/labs.compose.yml"),
    ]
    cid = subprocess.check_output(
        [*command, "ps", "-q", "juice-shop"], text=True
    ).strip()
    if not cid or "\n" in cid:
        raise ValueError("Exactly one running Juice Shop is required")
    info = json.loads(subprocess.check_output(["docker", "inspect", cid], text=True))[0]
    if not info["State"]["Running"]:
        raise ValueError("The lab is not running")
    gateway = subprocess.check_output(
        [*command, "ps", "-q", "juice-gateway"], text=True
    ).strip()
    if not gateway or "\n" in gateway:
        raise ValueError("The assigned loopback gateway is not running")
    gateway_info = json.loads(
        subprocess.check_output(["docker", "inspect", gateway], text=True)
    )[0]
    ports = gateway_info["NetworkSettings"]["Ports"].get("3000/tcp") or []
    if len(ports) != 1 or ports[0]["HostIp"] != "127.0.0.1":
        raise ValueError("Lab must have one loopback-only published port")
    assignments = root / "assignments.json"
    recorded = json.loads(assignments.read_text()) if assignments.exists() else {}
    if cid in recorded and recorded[cid] != owner:
        raise ValueError(
            "Reset the lab container before assigning it to another learner"
        )
    recorded[cid] = owner
    atomic(assignments, json.dumps(recorded, indent=2) + "\n")
    with urlopen(
        "http://127.0.0.1:" + ports[0]["HostPort"] + "/api/Challenges", timeout=5
    ) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Lab response is too large")
    rows = json.loads(raw)["data"]
    solved = [
        row["key"]
        for row in rows
        if row.get("solved") is True and isinstance(row.get("key"), str)
    ]
    return {
        "provider": "juice-shop",
        "owner": owner,
        "instance": cid,
        "image": info["Image"],
        "solved": solved,
    }


def bandit(level, owner, root):
    if not 0 <= level <= 32:
        raise ValueError("Bandit challenge level must be between 0 and 32")
    target = "bandit" + str(level + 1)
    result = subprocess.run(
        [
            "ssh",
            "-T",
            "-p",
            "2220",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "ConnectTimeout=10",
            target + "@bandit.labs.overthewire.org",
            "id -un",
        ],
        stdout=subprocess.PIPE,
        timeout=90,
        check=True,
    )
    if result.stdout.decode().strip() != target:
        raise ValueError("The remote identity did not match the required next level")
    # Login proves access to this game account, not independent puzzle solving.
    return {
        "provider": "bandit",
        "owner": owner,
        "instance": "bandit.labs.overthewire.org:2220",
        "solved": ["bandit-" + str(level)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provider", choices=["init", "juice-shop", "bandit"])
    parser.add_argument(
        "--owner",
        type=int,
        default=1,
        help="Ascend account numeric ID; single mode uses 1",
    )
    parser.add_argument("--project", default="ascend-labs")
    parser.add_argument("--level", type=int)
    parser.add_argument("--state-dir", type=Path, default=ROOT / ".ascend-labs")
    args = parser.parse_args()
    if args.owner < 1:
        parser.error("Owner must be a positive account ID")
    key = initialize(args.state_dir)
    if args.provider == "init":
        print("Private proof configuration created. No signing key is printed.")
        return
    if args.provider == "bandit" and args.level is None:
        parser.error("Bandit requires --level")
    with (args.state_dir / "collector.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        collect(args, key)


def collect(args, key):
    payload = (
        juice(args.project, args.owner, args.state_dir)
        if args.provider == "juice-shop"
        else bandit(args.level, args.owner, args.state_dir)
    )
    payload["observed_at"] = datetime.now(timezone.utc).isoformat()
    signature = hmac.new(
        bytes.fromhex(key), canonical(payload), hashlib.sha256
    ).hexdigest()
    atomic(
        args.state_dir / "receipts" / f"{args.provider}-{args.owner}.json",
        json.dumps({"payload": payload, "signature": signature}, indent=2) + "\n",
        0o644,
    )
    print(
        f"Recorded {len(payload['solved'])} observed challenge(s) for account {args.owner}; receipt expires in five minutes."
    )


if __name__ == "__main__":
    main()
