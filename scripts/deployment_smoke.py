"""Validate the shipped hardened tracker Compose and optional receipt mount."""

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.request import Request, urlopen
import uuid

from scripts.collect_lab_proof import initialize
from ascend.verifiers.ctf import canonical

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="ascend-compose-test-") as folder:
        root = Path(folder)
        key = initialize(root / "proof")
        payload = {
            "provider": "juice-shop",
            "owner": 1,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "solved": ["scoreBoardChallenge"],
        }
        signature = hmac.new(
            bytes.fromhex(key), canonical(payload), hashlib.sha256
        ).hexdigest()
        (root / "proof/receipts/juice-shop-1.json").write_text(
            json.dumps({"payload": payload, "signature": signature})
        )
        override = root / "image.yml"
        override.write_text("services:\n  ascend:\n    image: ascend:verified-labs\n")
        project = "ascend-compose-test-" + uuid.uuid4().hex[:8]
        env = {
            **os.environ,
            "ASCEND_PORT": "0",
            "AUTH_MODE": "single",
            "ASCEND_LAB_STATE_DIR": str(root / "proof"),
        }
        args = [
            "docker",
            "compose",
            "-p",
            project,
            "-f",
            str(ROOT / "docker/docker-compose.yml"),
            "-f",
            str(ROOT / "docker/lab-proofs.compose.yml"),
            "-f",
            str(override),
        ]
        try:
            subprocess.run(
                [*args, "up", "-d", "--no-build", "--wait", "--wait-timeout", "90"],
                env=env,
                check=True,
            )
            cid = subprocess.check_output(
                [*args, "ps", "-q", "ascend"], env=env, text=True
            ).strip()
            info = json.loads(
                subprocess.check_output(["docker", "inspect", cid], text=True)
            )[0]
            assert info["HostConfig"]["ReadonlyRootfs"]
            assert info["HostConfig"]["CapDrop"] == ["ALL"]
            assert info["Config"]["User"] == "ascend"
            assert all(
                m["Destination"] != "/var/run/docker.sock" for m in info["Mounts"]
            )
            proof = next(m for m in info["Mounts"] if m["Destination"] == "/lab-proofs")
            assert not proof["RW"]
            port = info["NetworkSettings"]["Ports"]["8420/tcp"][0]
            assert port["HostIp"] == "127.0.0.1"
            base = "http://127.0.0.1:" + port["HostPort"]

            def command(argv):
                request = Request(
                    base + "/api/command",
                    data=json.dumps({"argv": argv}).encode(),
                    headers={"Content-Type": "application/json"},
                )
                with urlopen(request, timeout=10) as response:
                    return json.load(response)

            with urlopen(base) as response:
                assert response.status == 200
            command(["pack", "install", "verified-security-lab"])
            command(["mission", "start", "verified-security-lab"])
            run = command(["lab", "start", "verified-security-lab:lab-readiness"])
            command(["lab", "emit", run["id"], "ok"])
            run = command(["lab", "emit", run["id"], "error"])
            event = next(
                e
                for e in run["data"]["events"]
                if e["marker"] == run["marker"] and e["status"] >= 400
            )
            result = command(
                [
                    "lab",
                    "submit",
                    run["id"],
                    json.dumps({"request_id": event["request_id"], "errors": 1}),
                ]
            )
            assert result["completed"] and result["timer"]["xp"] == 100
            assert command(["check", "verified-security-lab:scoreboard", "--complete"])[
                "completed"
            ]
            assert not command(["check", "verified-security-lab:injection"])["ok"]
            subprocess.run([*args, "restart", "ascend"], env=env, check=True)
            subprocess.run(
                [*args, "up", "-d", "--no-build", "--wait", "--wait-timeout", "90"],
                env=env,
                check=True,
            )
            # Docker may assign a different ephemeral host port on restart.
            address = subprocess.check_output(
                [*args, "port", "ascend", "8420"], env=env, text=True
            ).strip()
            base = "http://" + address
            assert command(["session", "status"])["xp"] == 100
            print(
                "RESULT: Hardened Compose, native grading, persistent XP after restart and read-only signed receipt overlay passed on AMD64. Synthetic temporary data only.",
                flush=True,
            )
        finally:
            subprocess.run(
                [*args, "down", "--volumes", "--remove-orphans"], env=env, check=True
            )


if __name__ == "__main__":
    main()
