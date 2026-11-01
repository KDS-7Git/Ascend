"""Exercise disposable Docker labs and signed proof end to end; always clean up."""

import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import tempfile
from urllib.request import urlopen
import uuid

from playwright.sync_api import sync_playwright

from ascend.application import Tracker
from ascend.storage import Database
from scripts.collect_lab_proof import initialize, juice
from ascend.verifiers.ctf import canonical
from datetime import datetime, timezone
import hashlib
import hmac

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def mqtt_client(port, name):
    sock = socket.create_connection(("127.0.0.1", port), timeout=5)
    raw = name.encode()
    body = b"\x00\x04MQTT\x04\x02\x00\x0a" + struct.pack("!H", len(raw)) + raw
    sock.sendall(bytes([0x10, len(body)]) + body)
    assert sock.recv(4) == b"\x20\x02\x00\x00"
    return sock


def main():
    project = "ascend-lab-test-" + uuid.uuid4().hex[:10]
    env = {
        **os.environ,
        **dict.fromkeys(
            ["JUICE_PORT", "WEBGOAT_PORT", "WEBWOLF_PORT", "MQTT_PORT"], "0"
        ),
    }
    command = [
        "docker",
        "compose",
        "-p",
        project,
        "-f",
        str(ROOT / "docker/labs.compose.yml"),
    ]

    def cid(service):
        return run([*command, "ps", "-q", service], env=env)

    def port(service, number):
        return int(
            run([*command, "port", service, str(number)], env=env).rsplit(":", 1)[1]
        )

    try:
        subprocess.run(
            [
                *command,
                "--profile",
                "juice-shop",
                "--profile",
                "webgoat",
                "--profile",
                "mqtt",
                "up",
                "-d",
                "--wait",
                "--wait-timeout",
                "240",
            ],
            env=env,
            check=True,
        )
        base = "http://127.0.0.1:" + str(port("juice-gateway", 3000))
        goat = "http://127.0.0.1:" + str(port("goat-gateway", 8080))
        with urlopen(goat + "/WebGoat/login", timeout=5) as response:
            assert response.status == 200
        print(
            "WebGoat: Java health probe and published login route passed.", flush=True
        )
        with mqtt_client(port("mqtt-gateway", 1883), "ascend-sub") as subscriber:
            topic = b"ascend/validation"
            body = b"\x00\x01" + struct.pack("!H", len(topic)) + topic + b"\x00"
            subscriber.sendall(bytes([0x82, len(body)]) + body)
            assert subscriber.recv(5) == b"\x90\x03\x00\x01\x00"
            with mqtt_client(port("mqtt-gateway", 1883), "ascend-pub") as publisher:
                body = struct.pack("!H", len(topic)) + topic + b"controlled-result"
                publisher.sendall(bytes([0x30, len(body)]) + body)
                assert b"controlled-result" in subscriber.recv(512)
        print(
            "MQTT: real publish/subscribe through the loopback gateway passed.",
            flush=True,
        )
        for service in ["juice-shop", "webgoat", "mqtt"]:
            info = json.loads(run(["docker", "inspect", cid(service)]))[0]
            assert info["HostConfig"]["CapDrop"] == ["ALL"]
            assert info["HostConfig"]["Memory"] > 0
            assert not info["HostConfig"]["PortBindings"]
            assert len(info["NetworkSettings"]["Networks"]) == 1
            name = next(iter(info["NetworkSettings"]["Networks"]))
            assert json.loads(run(["docker", "network", "inspect", name]))[0][
                "Internal"
            ]
            assert not any(
                m["Destination"] in ["/data", "/var/run/docker.sock"]
                for m in info["Mounts"]
            )
        js = "const s=require('net').connect({host:'1.1.1.1',port:443});s.setTimeout(1500);s.on('connect',()=>process.exit(1));s.on('error',()=>process.exit(0));s.on('timeout',()=>process.exit(0));"
        subprocess.run(
            ["docker", "exec", cid("juice-shop"), "/nodejs/bin/node", "-e", js],
            check=True,
            timeout=5,
        )
        print(
            "Isolation: internal target networks, no target port publication, dropped capabilities, bounded RAM and blocked public TCP egress passed.",
            flush=True,
        )
        with tempfile.TemporaryDirectory(prefix="ascend-proof-test-") as temp:
            root = Path(temp)
            key = initialize(root)
            initial = juice(project, 1, root)
            assert "scoreBoardChallenge" not in initial["solved"]
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(base + "/#/score-board")
                page.wait_for_function(
                    "document.body.innerText.includes('Score Board')"
                )
                browser.close()
            payload = juice(project, 1, root)
            assert "scoreBoardChallenge" in payload["solved"], payload["solved"]
            try:
                juice(project, 2, root)
            except ValueError:
                pass
            else:
                raise AssertionError("An assigned game was reused for another learner")
            payload["observed_at"] = datetime.now(timezone.utc).isoformat()
            signature = hmac.new(
                bytes.fromhex(key), canonical(payload), hashlib.sha256
            ).hexdigest()
            (root / "receipts/juice-shop-1.json").write_text(
                json.dumps({"payload": payload, "signature": signature})
            )
            os.environ["ASCEND_LAB_SIGNING_KEY"] = key
            os.environ["ASCEND_LAB_RECEIPTS_DIR"] = str(root / "receipts")
            tracker = Tracker(Database(root / "profile"))
            tracker.install_pack(
                (
                    ROOT / "packs/community/practice/verified-security-lab.toml"
                ).read_text()
            )
            assert tracker.check("verified-security-lab:scoreboard", confirm=True)[
                "completed"
            ]
            assert (
                tracker.states("verified-security-lab")["scoreboard"]["how"]
                == "verifier:ctf"
            )
            assert not tracker.check("verified-security-lab:injection")["ok"]
            tracker.db.user_id = 2
            tracker.install_pack(
                (
                    ROOT / "packs/community/practice/verified-security-lab.toml"
                ).read_text()
            )
            assert not tracker.check("verified-security-lab:scoreboard")["ok"]
            tracker.db.close()
        print(
            "Juice Shop: unsolved -> browser solve -> signed observation -> correct-account completion; unsolved challenge and other-account rejection passed.",
            flush=True,
        )
        print(
            "RESULT: All three native AMD64 Docker lab profiles and the real Juice Shop proof bridge passed; no learner data used.",
            flush=True,
        )
    finally:
        subprocess.run(
            [
                *command,
                "--profile",
                "juice-shop",
                "--profile",
                "webgoat",
                "--profile",
                "mqtt",
                "down",
                "--volumes",
                "--remove-orphans",
            ],
            env=env,
            check=True,
        )


if __name__ == "__main__":
    main()
