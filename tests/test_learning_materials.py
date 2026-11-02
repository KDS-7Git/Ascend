"""Validate packaged learner inputs and execute bounded, local-only recipes."""

import csv
import json
import shutil
import socket
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from ascend.engine.packs import parse_pack
from ascend.registry import bundled_pack_path
from scripts.audit_learning_content import audit
from scripts.build_packet_fixtures import fixtures
from scripts.package_learning_materials import outputs

ROOT = Path(__file__).resolve().parents[1]


def extract(track, destination):
    with zipfile.ZipFile(ROOT / "web/training" / (track + ".zip")) as archive:
        assert archive.testzip() is None
        assert all(
            not p.startswith("/") and ".." not in Path(p).parts
            for p in archive.namelist()
        )
        archive.extractall(destination)
    return destination / track


def run(folder, *args, input=None):
    return subprocess.run(
        [sys.executable, *args],
        cwd=folder,
        input=input,
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )


def test_catalog_guidance_and_archives_cover_every_specialist_practice():
    source = json.loads((ROOT / "docs/curriculum/specialist-paths.json").read_text())
    for track in source["tracks"]:
        pack = parse_pack(bundled_pack_path(track["id"]).read_text())
        for node in pack.nodes:
            assert node.setup and node.resource_label and node.resource_note
            if node.verify["type"] == "file":
                assert node.materials
                assert "```sh" in "\n".join(node.steps), (
                    "Saving evidence must be actionable"
                )
                assert len(node.steps) >= 4
                for material in node.materials:
                    assert (ROOT / "web" / material["url"].lstrip("/")).is_file()
    for path, expected in outputs():
        assert path.read_bytes() == expected, path
    assert audit()["findings"] == [], (
        "Known defects need review; this is not a learning-quality score"
    )


def test_report_writer_saves_observations_but_never_overwrites_notes(tmp_path):
    folder = extract("soc-analyst", tmp_path)
    answers = [
        "synthetic events.csv",
        "Python 3 on Linux",
        "same instant in UTC",
        "query.py",
        "e3 normalized",
        "excluded e7",
        "offset conversion",
        "no process data",
        "Python datetime docs",
    ]
    report = folder / "notes/report.json"
    result = run(folder, "report.py", str(report), input="\n".join(answers) + "\n")
    assert result.returncode == 0, result.stderr
    before = report.read_bytes()
    assert json.loads(before)["observed"] == "e3 normalized"
    assert len(before) >= 300
    assert run(folder, "report.py", str(report), input="different\n").returncode != 0
    assert report.read_bytes() == before
    assert run(folder, "report.py", "empty.json", input="\n" * 9).returncode != 0
    assert not (folder / "empty.json").exists()


def test_synthetic_log_timezones_and_controls_are_solvable(tmp_path):
    folder = extract("soc-analyst", tmp_path)
    with (folder / "events.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    start = datetime(2026, 10, 1, 9, tzinfo=timezone.utc)
    end = datetime(2026, 10, 1, 9, 10, tzinfo=timezone.utc)
    matches = [
        r["id"]
        for r in rows
        if r["user"] == "alice" and start <= datetime.fromisoformat(r["time"]) <= end
    ]
    assert matches == ["e1", "e2", "e3", "e4", "e5", "e11"]
    assert datetime.fromisoformat(rows[2]["time"]).astimezone(timezone.utc).hour == 9


def test_local_marker_policy_and_mock_recipes_match_their_stated_behavior(tmp_path):
    marker = extract("red-team-adversary-emulation", tmp_path)
    (marker / "unrelated.txt").write_text("keep this")
    result = run(marker, "marker.py")
    assert result.returncode == 0 and "Marker absent: True" in result.stdout
    assert [
        json.loads(line)["action"]
        for line in (marker / "marker-events.jsonl").read_text().splitlines()
    ] == ["create", "remove"]
    assert (marker / "unrelated.txt").read_text() == "keep this"
    assert run(marker, "marker.py").returncode != 0
    cloud = extract("cloud-security", tmp_path)
    assert run(cloud, "policy.py").stdout.splitlines() == [
        "reader read True",
        "reader write False",
        "editor read True",
        "editor write True",
        "unknown read False",
        "unknown write False",
    ]
    mock = extract("ai-application-security", tmp_path)
    output = run(mock, "assistant.py")
    assert output.returncode == 0 and "benign Public training note" in output.stdout
    assert "instruction-like text Synthetic Bob note" in output.stdout
    sample = extract("malware-analysis", tmp_path)
    assert "marker selected" in run(sample, "sample.py", "demo").stdout
    assert "no action" in run(sample, "sample.py", "other").stdout


def test_packaged_notes_api_exposes_the_documented_training_defects(tmp_path):
    folder = extract("api-security", tmp_path)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "service.py", "--port", str(port)],
        cwd=folder,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                with urlopen(base + "/health", timeout=1) as response:
                    assert json.load(response)["fixture"] == "ascend-notes-v1"
                break
            except OSError:
                time.sleep(0.03)
        else:
            raise AssertionError("Packaged API failed to start")
        for user in ["alice", "bob"]:
            with urlopen(
                Request(base + "/notes/1", headers={"X-Lab-User": user}), timeout=2
            ) as response:
                assert json.load(response)["owner"] == "alice"
        request = Request(
            base + "/notes/1",
            data=b'{"owner":"bob"}',
            headers={"X-Lab-User": "alice", "Content-Type": "application/json"},
            method="PATCH",
        )
        with urlopen(request, timeout=2) as response:
            assert json.load(response)["owner"] == "bob"
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_packet_fixtures_decode_as_the_advertised_inputs():
    for name, expected in fixtures().items():
        assert (
            ROOT / "tracks/cyber-tracks/materials/networking-for-security" / name
        ).read_bytes() == expected
    if not shutil.which("tshark"):
        pytest.skip("Optional Wireshark decoder is not installed")
    folder = ROOT / "tracks/cyber-tracks/materials/networking-for-security"
    result = subprocess.run(
        [
            "tshark",
            "-r",
            str(folder / "http-training.pcap"),
            "-Y",
            "http.response",
            "-T",
            "fields",
            "-e",
            "http.response.code",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert result.stdout.splitlines() == ["200", "404"]
    beacon = subprocess.run(
        [
            "tshark",
            "-r",
            str(folder / "wifi-beacon.pcap"),
            "-T",
            "fields",
            "-e",
            "wlan.fc.type_subtype",
            "-e",
            "wlan.ds.current_channel",
            "-e",
            "wlan.rsn.version",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert beacon.stdout.strip() == "0x0008\t6\t1"
