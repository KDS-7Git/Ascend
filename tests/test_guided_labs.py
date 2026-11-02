"""Exercise the published beginner recipe without touching a learner profile."""

import json
import os
import re
import signal
import socket
import subprocess
import time
from urllib.request import urlopen

from ascend.engine.packs import parse_pack
from ascend.registry import bundled_pack_path


def test_http_walkthrough_commands_produce_real_responses_and_preserve_notes(tmp_path):
    pack = parse_pack(
        bundled_pack_path("ethical-hacking-foundations").read_text(),
        {"lab_dir": str(tmp_path / "notes")},
    )
    node = next(n for n in pack.nodes if n.id == "foundations-experiment")
    blocks = re.findall(r"```sh\n(.*?)```", "\n".join(node.steps), re.S)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    setup = blocks[1].replace("/tmp/ascend-http.XXXXXX", str(tmp_path / "site.XXXXXX"))
    setup = setup.replace("server 8765", f"server {port}")
    process = subprocess.Popen(
        ["bash", "-c", setup],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        for _ in range(100):
            try:
                with urlopen(f"http://127.0.0.1:{port}", timeout=1):
                    break
            except OSError:
                time.sleep(0.03)
        else:
            raise AssertionError("The published server command did not start")
        for block, expected in [(blocks[2], "200"), (blocks[3], "404")]:
            result = subprocess.run(
                ["bash", "-c", block.replace(":8765", f":{port}")],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            assert expected in result.stdout.splitlines()[0]
            if expected == "200":
                assert "My first lab" in result.stdout
        observations = (
            "\n".join(
                [
                    f"http://127.0.0.1:{port}/",
                    "200",
                    "<h1>My first lab</h1>",
                    "404",
                    "The loopback address points to this computer.",
                    "The port identifies this running HTTP service.",
                    "The first file exists; the second path does not.",
                    "I did not test any vulnerability or another computer.",
                ]
            )
            + "\n"
        )
        result = subprocess.run(
            ["bash", "-c", blocks[4]],
            input=observations,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        report = tmp_path / "notes/foundations-experiment.json"
        before = report.read_bytes()
        assert json.loads(before)["missing_status"] == "404"
        retry = subprocess.run(
            ["bash", "-c", blocks[4]],
            input=observations,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        assert retry.returncode != 0 and "already exists" in retry.stderr
        assert report.read_bytes() == before
    finally:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
