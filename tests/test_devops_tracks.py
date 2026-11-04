"""Verify DevOps progression and real behaviour from extracted learner bundles."""

import importlib.util
import io
import json
import queue
import re
import shutil
import ssl
import subprocess
import sys
import threading
import zipfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from ascend.engine.levels import next_nodes
from ascend.engine.packs import parse_pack
from scripts import build_devops_tracks, package_learning_materials

ROOT = Path(__file__).resolve().parents[1]
IDS = [
    "devops-service-foundations",
    "devops-delivery-automation",
    "devops-reliability-orchestration",
]


@pytest.fixture
def bundles(tmp_path):
    result = {}
    for path, raw in package_learning_materials.outputs("devops"):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            assert archive.testzip() is None
            archive.extractall(tmp_path)
        result[path.stem] = tmp_path / path.stem
    assert set(result) == set(IDS)
    return result


def command(folder, *args, expected=0):
    result = subprocess.run(
        [sys.executable, *map(str, args)],
        cwd=folder,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == expected, result.stdout + result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else result


@contextmanager
def selected_service(folder, data, extra=()):
    process = subprocess.Popen(
        [
            sys.executable,
            "shared/release.py",
            "serve",
            "--state",
            "work/current.json",
            "--",
            "--port",
            "0",
            "--data",
            data,
            "--quiet",
            *extra,
        ],
        cwd=folder,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    lines = queue.Queue()
    reader = threading.Thread(
        target=lambda: lines.put(process.stdout.readline()), daemon=True
    )
    reader.start()
    try:
        line = lines.get(timeout=5)
        assert line, "Selected service failed before its listening record"
        started = json.loads(line)
        assert started["event"] == "listening"
        yield f"http://127.0.0.1:{started['port']}", started
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
        process.stdout.close()
        process.stderr.close()
        reader.join(timeout=1)


def test_generated_outputs_are_current_and_represent_all_designed_capabilities():
    for relative, content in build_devops_tracks.outputs().items():
        assert (ROOT / relative).read_text() == content, relative
    source = json.loads((ROOT / build_devops_tracks.SOURCE).read_text())
    levels = [level for track in source["tracks"] for level in track["levels"]]
    assert len(levels) == 24
    assert {
        number for level in levels for number in level["original_design_levels"]
    } == set(range(1, 14))
    catalog = json.loads((ROOT / "packs/community/devops/catalog.json").read_text())[
        "tracks"
    ]
    assert [row["id"] for row in catalog] == IDS
    assert [row["track_order"] for row in catalog] == [1, 2, 3]
    assert all(
        row["category"] == "DevOps" and row["domain"] == "devops" for row in catalog
    )
    assert not catalog[0]["recommended_after"]
    assert catalog[-1]["recommended_after"] == IDS[:2]


@pytest.mark.parametrize("pid", IDS)
def test_progression_reaches_every_task_and_experienced_entry_is_independent(pid):
    pack = parse_pack((ROOT / f"packs/community/devops/{pid}.toml").read_text())
    assert len([level for level in pack.levels if level.lane == "main"]) == 8
    assert len(pack.nodes) == 25
    state = {}
    for _ in range(len(pack.nodes)):
        available = next_nodes(pack, state)
        if not available:
            break
        state.update({node.id: "done" for node in available})
    assert set(state) == {node.id for node in pack.nodes}
    for level in (level for level in pack.levels if level.lane == "main"):
        milestone = next(
            node for node in pack.nodes if node.level == level.id and node.milestone
        )
        assert milestone in next_nodes(pack, {}, overrides={level.id})
        assert milestone.verify == {"type": "manual"} and not milestone.auto_complete
        assert milestone.size in {"M", "L"}
    assert all(
        node.preview and node.setup and node.steps and node.materials
        for node in pack.nodes
    )
    assert all("Operate and explain " not in node.preview for node in pack.nodes)


def test_referenced_static_inputs_exist_in_each_standalone_bundle(bundles):
    source = json.loads((ROOT / build_devops_tracks.SOURCE).read_text())
    for track in source["tracks"]:
        folder = bundles[track["id"]]
        assert (folder / "README.md").is_file()
        assert (folder / "LICENSE").is_file()
        for level in track["levels"]:
            lesson = folder / "lessons" / f"{level['id']}.md"
            assert lesson.is_file()
            text = lesson.read_text()
            for ref in re.findall(
                r"\b(?:configs|fixtures|shared|tools)/[A-Za-z0-9_./-]+", text
            ):
                assert (folder / ref.rstrip(".")).exists(), (
                    track["id"],
                    level["id"],
                    ref,
                )


def test_extracted_reference_checks_run_without_repo_imports(bundles):
    result = subprocess.run(
        [sys.executable, "shared/selfcheck.py"],
        cwd=bundles[IDS[0]],
        capture_output=True,
        text=True,
        timeout=25,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Ran 8 tests" in result.stderr
    assert "test_edge_diagnosis" in result.stderr
    assert "test_bounded_admission" in result.stderr


def test_selected_artifact_activation_rollback_and_fresh_restore_are_real(bundles):
    folder = bundles[IDS[0]]
    for version in ("v1", "v2"):
        command(
            folder,
            "shared/release.py",
            "build",
            "--source",
            "shared/relay.py",
            "--out",
            f"work/releases/{version}",
            "--release",
            version,
            "--revision",
            f"reviewed-{version}",
        )
    command(
        folder,
        "shared/release.py",
        "select",
        "--artifact",
        "work/releases/v1",
        "--state",
        "work/current.json",
    )
    with selected_service(folder, "work/runtime.sqlite") as (url, started):
        assert Path(started["data"]) == folder / "work/runtime.sqlite"
        first = command(
            folder,
            "shared/check_service.py",
            "--url",
            url,
            "--expect-release",
            "v1",
            "--write",
        )
        assert first["passed"] and first["satisfies_track_evidence"] is False
        snapshot = command(
            folder,
            "shared/backup.py",
            "create",
            "--source",
            "work/runtime.sqlite",
            "--destination",
            "backups/first.sqlite",
        )
        command(
            folder,
            "shared/check_service.py",
            "--url",
            url,
            "--expect-release",
            "v1",
            "--write",
        )
        command(
            folder,
            "shared/release.py",
            "select",
            "--artifact",
            "work/releases/v2",
            "--state",
            "work/current.json",
        )
        command(
            folder, "shared/check_service.py", "--url", url, "--expect-release", "v1"
        )
        wrong = command(
            folder,
            "shared/check_service.py",
            "--url",
            url,
            "--expect-release",
            "v2",
            expected=1,
        )
        assert not wrong["passed"]
    with selected_service(folder, "work/runtime.sqlite") as (url, _):
        report = command(
            folder, "shared/check_service.py", "--url", url, "--expect-release", "v2"
        )
        records = next(
            check["observed"]["updates"]
            for check in report["checks"]
            if check["path"] == "/api/updates"
        )
        assert len(records) == 2
    command(
        folder,
        "shared/release.py",
        "select",
        "--artifact",
        "work/releases/v1",
        "--state",
        "work/current.json",
    )
    restored = command(
        folder,
        "shared/backup.py",
        "restore",
        "--source",
        "backups/first.sqlite",
        "--destination",
        "restored/relay.sqlite",
    )
    assert restored["records"] == snapshot["records"] == 1
    assert restored["records_sha256"] == snapshot["records_sha256"]
    with selected_service(folder, "restored/relay.sqlite", ("--read-only",)) as (
        url,
        _,
    ):
        command(
            folder, "shared/check_service.py", "--url", url, "--expect-release", "v1"
        )
        denied = command(
            folder,
            "shared/check_service.py",
            "--url",
            url,
            "--expect-release",
            "v1",
            "--write",
            expected=1,
        )
        assert denied["checks"][-1]["statuses"] == [405, 405, 405]
    original = command(
        folder, "shared/backup.py", "inspect", "--source", "work/runtime.sqlite"
    )
    assert original["records"] == 2
    command(
        folder,
        "shared/backup.py",
        "restore",
        "--source",
        "backups/first.sqlite",
        "--destination",
        "work/runtime.sqlite",
        expected=1,
    )


def test_release_command_rejects_tampering_without_replacing_prior_selection(bundles):
    folder = bundles[IDS[1]]
    command(
        folder,
        "shared/release.py",
        "build",
        "--source",
        "shared/relay.py",
        "--out",
        "work/v1",
        "--release",
        "v1",
        "--revision",
        "reviewed-local",
    )
    command(
        folder,
        "shared/release.py",
        "select",
        "--artifact",
        "work/v1",
        "--state",
        "work/current.json",
    )
    state = folder / "work/current.json"
    before = state.read_bytes()
    command(
        folder,
        "shared/release.py",
        "serve",
        "--state",
        "work/current.json",
        "--",
        "--rele",
        "bad-override",
        expected=2,
    )
    shutil.copytree(folder / "work/v1", folder / "work/tampered")
    with (folder / "work/tampered/relay.py").open("a") as stream:
        stream.write("\n# different artifact content\n")
    command(
        folder,
        "shared/release.py",
        "select",
        "--artifact",
        "work/tampered",
        "--state",
        "work/current.json",
        expected=1,
    )
    assert state.read_bytes() == before
    assert (
        command(folder, "shared/release.py", "resolve", "--state", "work/current.json")[
            "release"
        ]
        == "v1"
    )


def test_pipeline_rule_rejects_failed_untrusted_and_mismatched_candidates(bundles):
    folder = bundles[IDS[1]]
    base = (
        "tools/pipeline_policy.py",
        "fixtures/pipeline.json",
        "--expected-revision",
        "commit-a",
    )
    rejected = command(folder, *base, expected=1)
    assert "tests did not pass" in " ".join(rejected["denial_reasons"])
    allowed = command(
        folder, *base, "--candidate", "commit-a", "--artifact", "sha256:aaa"
    )
    assert allowed["allowed_by_rule"] and not allowed["satisfies_track_evidence"]
    untrusted = command(
        folder,
        "tools/pipeline_policy.py",
        "fixtures/pipeline.json",
        "--expected-revision",
        "commit-c",
        "--candidate",
        "commit-c",
        "--artifact",
        "sha256:ccc",
        expected=1,
    )
    assert "trust condition" in " ".join(untrusted["denial_reasons"])
    mismatch = command(
        folder, *base, "--candidate", "commit-a", "--artifact", "sha256:bbb", expected=1
    )
    assert "artifact differs" in " ".join(mismatch["denial_reasons"])


def test_recorded_measurements_keep_failures_and_enforce_selected_objectives(bundles):
    folder = bundles[IDS[2]]
    baseline = command(
        folder, "shared/analyze.py", "fixtures/baseline.csv", "--window-seconds", "60"
    )
    incident = command(
        folder,
        "shared/analyze.py",
        "fixtures/incident.csv",
        "--window-seconds",
        "60",
        expected=1,
    )
    assert baseline["attempts"] == incident["attempts"] == 50
    assert (
        baseline["meets_selected_thresholds"]
        and not incident["meets_selected_thresholds"]
    )
    assert incident["failed"] == 10 and incident["error_rate"] == 0.2
    assert incident["successful_requests_per_second"] == 40 / 60


@pytest.mark.skipif(
    shutil.which("openssl") is None, reason="Local TLS tool is unavailable"
)
def test_real_tls_accepts_private_ca_and_hostname_and_rejects_negative_controls(
    bundles,
):
    folder = bundles[IDS[0]]
    cert, key = folder / "cert.pem", folder / "key.pem"
    result = subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    spec = importlib.util.spec_from_file_location(
        "extracted_tls_relay", folder / "shared/relay.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = module.RelayServer(
        ("127.0.0.1", 0), data=folder / "tls.sqlite", quiet=True
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        correct = f"https://localhost:{server.server_port}"
        command(
            folder,
            "shared/check_service.py",
            "--url",
            correct,
            "--ca-file",
            "cert.pem",
            "--expect-release",
            "v1",
        )
        untrusted = command(
            folder,
            "shared/check_service.py",
            "--url",
            correct,
            "--expect-release",
            "v1",
            expected=1,
        )
        assert "CERTIFICATE_VERIFY_FAILED" in untrusted.stderr
        wrong_name = command(
            folder,
            "shared/check_service.py",
            "--url",
            f"https://127.0.0.1:{server.server_port}",
            "--ca-file",
            "cert.pem",
            expected=1,
        )
        assert "CERTIFICATE_VERIFY_FAILED" in wrong_name.stderr
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
