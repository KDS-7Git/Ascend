"""Smoke-test a local image on a random loopback port; always remove the container."""

import argparse
import json
import subprocess
import time
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument("image", nargs="?", default="ascend:phase2")
args = parser.parse_args()
container = subprocess.check_output(
    ["docker", "run", "--rm", "-d", "-p", "127.0.0.1::8420", args.image], text=True
).strip()
try:
    port = (
        subprocess.check_output(["docker", "port", container, "8420"], text=True)
        .strip()
        .split(":")[-1]
    )
    url = "http://127.0.0.1:" + port
    for _ in range(60):
        try:
            with urlopen(url + "/api/health", timeout=1) as response:
                print("Container health:", response.status, response.read().decode())
            break
        except OSError:
            time.sleep(0.2)
    else:
        raise RuntimeError("Container failed to become healthy")
    with urlopen(url) as response:
        print("PWA:", response.status)
    data = json.dumps({"argv": ["pack", "install", "home-hack-lab"]}).encode()
    with urlopen(
        Request(
            url + "/api/command",
            data=data,
            headers={"Content-Type": "application/json"},
        )
    ) as response:
        print("Bundled pack install:", response.status, json.load(response)["id"])
    print(
        "Runtime user:",
        subprocess.check_output(
            ["docker", "exec", container, "id", "-u"], text=True
        ).strip(),
    )
finally:
    subprocess.run(
        ["docker", "rm", "-f", container], stdout=subprocess.DEVNULL, check=True
    )
