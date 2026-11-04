"""Validate authored infrastructure packs and the portable workshop boundaries.

These tests do not provision VMs, alter networking, deliver external mail or
benchmark the shared server. The real-service test uses one temporary loopback
endpoint and its named synthetic records, then restores into a new local file.
"""

from contextlib import contextmanager
from copy import deepcopy
import base64
import configparser
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest

from ascend.engine.levels import next_nodes, open_levels
from ascend.engine.packs import parse_pack
from scripts import build_infrastructure_tracks

ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "tracks/infrastructure-tracks/materials"
SOURCE = json.loads((ROOT / "docs/curriculum/infrastructure-paths.json").read_text())
TRACKS = SOURCE["tracks"]
CASES = sorted(MATERIALS.glob("io-*/cases/*.json"))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


LAB = module("infrastructure_lab", MATERIALS / "shared/lab.py")


def test_all_generated_materials_are_current():
    expected = build_infrastructure_tracks.outputs()
    assert len(TRACKS) == 9 and len(CASES) == 144
    for relative, content in expected.items():
        assert (ROOT / relative).read_text() == content, relative
    result = subprocess.run(
        [sys.executable, "scripts/build_infrastructure_tracks.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("track", TRACKS, ids=lambda track: track["id"])
def test_sequence_can_be_completed_by_native_milestones_or_entered_early(track):
    pack = parse_pack(
        (ROOT / f"packs/community/infrastructure/{track['id']}.toml").read_text()
    )
    main = [level for level in pack.levels if level.lane == "main"]
    assert len(main) == 8 and len(pack.nodes) == 25
    assert pack.source == "ai-draft" and not pack.reviewed
    done = set()
    for number, level in enumerate(main, 1):
        assert level.id == f"{track['id']}-{number:02d}"
        assert level.id in open_levels(pack, done)
        milestone = next(
            node for node in pack.nodes if node.level == level.id and node.milestone
        )
        assert milestone.id in {
            node.id for node in next_nodes(pack, dict.fromkeys(done, "done"))
        }
        assert milestone.size in {"M", "L"} and not milestone.needs
        done.add(milestone.id)
    assert {level.id for level in main} <= open_levels(pack, done)
    early = next_nodes(pack, {}, overrides={main[-1].id})
    assert any(node.level == main[-1].id and node.milestone for node in early)
    for node in pack.nodes:
        assert node.verify == {"type": "manual"} and not node.auto_complete
        assert node.preview and node.requirements and node.setup
        assert node.materials[0]["url"] == f"/training/{track['id']}.zip"
    assert len(list((MATERIALS / track["id"] / "lessons").glob("*.md"))) == 8


def test_catalog_recommendations_are_metadata_not_cross_pack_prerequisites():
    rows = json.loads(
        (ROOT / "packs/community/infrastructure/catalog.json").read_text()
    )["tracks"]
    assert [row["track_order"] for row in rows] == list(range(1, 10))
    for index, row in enumerate(rows):
        assert row["domain"] == "infrastructure" and row["category"] == "Infrastructure"
        assert row["recommended_after"] == (
            [] if index == 0 else [rows[index - 1]["id"]]
        )
        assert row["limits"] and row["entry"] and row["aliases"]
    assert SOURCE["hardware"]["shared_runner"]["max_simultaneous_hosted_labs"] == 2


@pytest.mark.parametrize(
    "path", CASES, ids=lambda path: f"{path.parents[1].name}:{path.stem}"
)
def test_every_broken_case_fails_and_its_reference_satisfies_each_control(path):
    case = json.loads(path.read_text())
    assert case["starting"] != case["reference"]
    assert not LAB.evaluate(case["starting"], case["rules"])["passed"]
    result = LAB.evaluate(case["reference"], case["rules"])
    assert result["passed"], (path, result)
    assert "native operational checks remain separate" in result["scope"]
    # Every authored field affects a control; a missing observation is not a pass.
    for field in case["reference"]:
        missing = deepcopy(case["reference"])
        del missing[field]
        assert not LAB.evaluate(missing, case["rules"])["passed"], (path, field)


@pytest.mark.parametrize("track", TRACKS, ids=lambda track: track["id"])
def test_transfer_cases_change_the_diagnostic_condition(track):
    for number in range(1, 9):
        parent = MATERIALS / track["id"] / "cases"
        guided = json.loads((parent / f"{number:02d}-guided.json").read_text())
        transfer = json.loads((parent / f"{number:02d}-transfer.json").read_text())
        assert guided["starting"] != transfer["starting"]
        assert guided["reference"] == transfer["reference"]
        assert guided["scope"] == transfer["scope"]


def test_resource_constraints_allow_feasible_alternatives_and_reject_overcommit():
    case = json.loads(
        (MATERIALS / "io-vm-administration/cases/08-guided.json").read_text()
    )
    candidate = case["reference"] | {"lab_ram_gib": 6, "host_reserve_gib": 10}
    assert LAB.evaluate(candidate, case["rules"])["passed"]
    for changed in [
        {"lab_ram_gib": 12, "host_reserve_gib": 8},
        {"lab_ram_gib": 14, "host_reserve_gib": 2},
        {"lab_ram_gib": -1},
        {"lab_ram_gib": True},
    ]:
        assert not LAB.evaluate(candidate | changed, case["rules"])["passed"]
    near = json.loads(
        (MATERIALS / "io-traffic-capacity/cases/07-guided.json").read_text()
    )
    assert LAB.evaluate(
        near["reference"] | {"component_cpu_budget": 0.4923076923}, near["rules"]
    )["passed"]
    assert not LAB.evaluate(
        near["reference"] | {"component_cpu_budget": 6}, near["rules"]
    )["passed"]


def test_prepare_reports_local_files_and_preserves_existing_workspace(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(LAB, "ROOT", MATERIALS / "io-private-access")
    args = SimpleNamespace(level="08", variant="guided", out=str(tmp_path / "practice"))
    LAB.prepare(args)
    output = capsys.readouterr().out
    assert str(tmp_path / "practice") in output
    assignment = json.loads((tmp_path / "practice/assignment.json").read_text())
    assert (
        assignment["contract"]
        and "not live operational evidence" in assignment["scope"]
    )
    assert (tmp_path / "practice/inputs/framing.py").is_file()
    original = (tmp_path / "practice/candidate.json").read_bytes()
    with pytest.raises(FileExistsError):
        LAB.prepare(args, reference=True)
    assert (tmp_path / "practice/candidate.json").read_bytes() == original
    args.out = str(tmp_path / "reference")
    LAB.prepare(args, reference=True)
    assert (
        "help used"
        in json.loads((tmp_path / "reference/assignment.json").read_text())[
            "starting_point"
        ]
    )
    with pytest.raises(ValueError):
        LAB.case_for("08", "../../outside")


def test_cli_broken_then_repaired_case_retains_evidence_scope(tmp_path):
    lab = MATERIALS / "io-linux-network/lab.py"
    workspace = tmp_path / "work"
    prepared = subprocess.run(
        [sys.executable, str(lab), "prepare", "01", "--out", str(workspace)],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert prepared.returncode == 0, prepared.stderr
    result = subprocess.run(
        [sys.executable, str(lab), "check", str(workspace)],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 1 and not json.loads(result.stdout)["passed"]
    path = workspace / "candidate.json"
    candidate = json.loads(path.read_text())
    candidate["client_port"] = 8000
    path.write_text(json.dumps(candidate))
    result = subprocess.run(
        [sys.executable, str(lab), "check", str(workspace)],
        capture_output=True,
        text=True,
        timeout=5,
    )
    report = json.loads(result.stdout)
    assert result.returncode == 0 and report["passed"]
    assert "reasoning only" in report["scope"]


def test_csv_metrics_include_failures_and_real_window(capsys):
    LAB.analyze(MATERIALS / "io-traffic-capacity/inputs/01/requests.csv")
    observed = json.loads(capsys.readouterr().out)
    assert (
        observed["requests"] == 10
        and observed["successes"] == 9
        and observed["errors"] == 1
    )
    assert observed["all_request_mean_ms"] == 65.5
    assert observed["all_request_p95_ms"] == 100
    assert observed["observation_window_ms"] == 325
    assert observed["successful_rps"] == pytest.approx(9 / 0.325)
    LAB.analyze(MATERIALS / "io-traffic-capacity/inputs/08/after.csv")
    after = json.loads(capsys.readouterr().out)
    assert after["all_request_mean_ms"] < observed["all_request_mean_ms"]
    assert after["successful_rps"] < observed["successful_rps"]


@pytest.mark.parametrize(
    "row",
    [
        "0,nan,200",
        "0,inf,200",
        "-1,5,200",
        "0,-2,200",
        "0,0,200",
        "0,1,999",
        "0,1,no-status",
    ],
)
def test_csv_rejects_invalid_measurements(tmp_path, row):
    path = tmp_path / "invalid.csv"
    path.write_text("arrival_ms,duration_ms,status\n" + row + "\n")
    with pytest.raises((ValueError, KeyError)):
        LAB.analyze(path)


def test_definition_and_mail_inspection_keep_limited_claims(tmp_path, capsys):
    LAB.inspect_vm(MATERIALS / "io-vm-administration/inputs/01/guest.xml")
    result = json.loads(capsys.readouterr().out)
    assert result["name"] == "relay-a" and result["vcpus"] == "2"
    assert result["configured_current_vcpus"] == "1"
    assert "does not create" in result["scope"]
    LAB.inspect_mail(MATERIALS / "io-mail-state/inputs/01/message.eml")
    result = json.loads(capsys.readouterr().out)
    assert result["Message-ID"] == "<synthetic-event-1@relay.test>"
    assert "not independently verified" in result["scope"]
    invalid = tmp_path / "entity.xml"
    invalid.write_text(
        '<!DOCTYPE domain [<!ENTITY x "sample">]><domain><name>&x;</name></domain>'
    )
    with pytest.raises(ValueError, match="entity"):
        LAB.inspect_vm(invalid)
    invalid.write_bytes("<domain/>".encode("utf-16"))
    with pytest.raises(UnicodeError):
        LAB.inspect_vm(invalid)
    invalid.write_text("<not-a-domain/>")
    with pytest.raises(ValueError, match="domain"):
        LAB.inspect_vm(invalid)
    oversized = tmp_path / "oversized.eml"
    oversized.write_bytes(b"x" * (LAB.MAX_INPUT + 1))
    with pytest.raises(ValueError, match="bound"):
        LAB.inspect_mail(oversized)


def test_framing_roundtrip_bounds_and_truncated_inputs():
    framing = module(
        "infrastructure_framing", MATERIALS / "io-private-access/inputs/08/framing.py"
    )
    for payload in (b"", b"relay", b"x" * framing.MAX):
        assert framing.decode(framing.encode(payload)) == payload
    with pytest.raises(ValueError):
        framing.encode(b"x" * (framing.MAX + 1))
    for bad in (
        b"",
        b"abc",
        struct.pack("!I", 5) + b"xx",
        struct.pack("!I", 1) + b"xy",
        struct.pack("!I", framing.MAX + 1),
    ):
        with pytest.raises(ValueError):
            framing.decode(bad)


def test_local_dkim_dns_input_is_chunked_and_preserves_existing_file(tmp_path):
    # Synthetic bytes exercise DNS TXT serialization, not key validity/signing.
    destination = tmp_path / "work/dkim"
    destination.mkdir(parents=True)
    key = base64.b64encode(bytes(range(256)) * 2).decode()
    (destination / "lab-public.b64").write_text(key)
    script = MATERIALS / "io-mail-state/inputs/04/make_local_dns.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
    config = destination / "dnsmasq.conf"
    original = config.read_text()
    record = next(
        line
        for line in original.splitlines()
        if line.startswith("txt-record=lab._domainkey.")
    )
    chunks = record.split(",", 1)[1].split(",")
    assert all(
        chunk.startswith('"') and chunk.endswith('"') and len(chunk[1:-1]) <= 255
        for chunk in chunks
    )
    assert "".join(chunk[1:-1] for chunk in chunks) == "v=DKIM1; k=rsa; p=" + key
    if binary := shutil.which("dnsmasq"):
        checked = subprocess.run(
            [binary, "--test", "--conf-file=" + str(config)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert checked.returncode == 0, checked.stderr
    repeated = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert repeated.returncode != 0 and config.read_text() == original


def test_authored_native_python_and_shell_inputs_parse():
    for track in TRACKS:
        for number, level in enumerate(track["levels"], 1):
            for name, content in level["lesson"]["files"].items():
                if name.endswith(".py"):
                    compile(content, f"{track['id']}/{number:02d}/{name}", "exec")
            for command in level["lesson"]["native_commands"]:
                # Parse only: bash -n never executes the VM/provider/guest recipe.
                checked = subprocess.run(
                    ["bash", "-n"],
                    input=command,
                    text=True,
                    capture_output=True,
                    timeout=3,
                )
                assert checked.returncode == 0, (track["id"], number, checked.stderr)


def test_native_commands_reference_inputs_present_in_their_own_bundle():
    for track in TRACKS:
        for level in track["levels"]:
            for command in level["lesson"]["native_commands"]:
                references = re.findall(r"\binputs/\d{2}/[A-Za-z0-9_./-]+", command)
                for relative in references:
                    assert (MATERIALS / track["id"] / relative).exists(), (
                        track["id"],
                        level["id"],
                        relative,
                    )


@contextmanager
def relay_on_loopback(data, *, release="infra-v1", ready_file=None):
    relay = module("infrastructure_relay", ROOT / "tracks/engineering-common/relay.py")
    server = relay.RelayServer(
        ("127.0.0.1", 0),
        data=data,
        release=release,
        ready_file=ready_file,
        quiet=True,
    )
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.02}
    )
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()


def test_device_unit_arguments_support_the_authored_readiness_and_state_controls(
    tmp_path,
):
    # Parse the actual input unit, then exercise its service arguments on one
    # ephemeral loopback listener. This does not claim a systemd/Pi boot replay.
    unit_path = MATERIALS / "io-resilient-hardware/inputs/05/ascend-device.service"
    unit = configparser.ConfigParser(interpolation=None)
    unit.read(unit_path)
    command = shlex.split(unit["Service"]["ExecStart"])
    relay = module("device_unit_relay", ROOT / "tracks/engineering-common/relay.py")
    checker = module(
        "device_unit_check", ROOT / "tracks/engineering-common/check_service.py"
    )
    backup = module("device_unit_backup", ROOT / "tracks/engineering-common/backup.py")
    args = relay.parser().parse_args(command[2:])
    assert args.host == "127.0.0.1"
    data = tmp_path / Path(args.data).relative_to("/opt/ascend-device")
    ready = tmp_path / Path(args.ready_file).relative_to("/opt/ascend-device")
    ready.parent.mkdir(parents=True)
    ready.write_text("ready\n")
    with relay_on_loopback(data, release=args.release, ready_file=ready) as url:
        assert checker.observe(url, expected_release=args.release, write=True)["passed"]
        before = backup.inspect(data)["records_sha256"]
        ready.write_text("")
        rejected = checker.observe(url, expected_release=args.release)
        assert not rejected["passed"]
        assert (
            next(row for row in rejected["checks"] if row["path"] == "/ready")["status"]
            == 503
        )
        ready.write_text("ready\n")
        assert checker.observe(url, expected_release=args.release)["passed"]
        assert backup.inspect(data)["records_sha256"] == before


def test_real_local_request_version_and_restore_controls(tmp_path):
    checker = module(
        "infrastructure_check_service",
        ROOT / "tracks/engineering-common/check_service.py",
    )
    backup = module(
        "infrastructure_backup", ROOT / "tracks/engineering-common/backup.py"
    )
    live = tmp_path / "live.sqlite"
    copy = tmp_path / "independent.sqlite"
    restored = tmp_path / "restored.sqlite"
    with relay_on_loopback(live) as url:
        report = checker.observe(url, expected_release="infra-v1", write=True)
        assert report["passed"] and report["authority"] == "learner-local observation"
        assert report["satisfies_track_evidence"] is False
        assert not checker.observe(url, expected_release="wrong-release")["passed"]
        original = backup.inspect(live)
        snapshot = backup.copy_database(live, copy)
        assert (
            snapshot["records"] > 0
            and snapshot["records_sha256"] == original["records_sha256"]
        )
    # The source endpoint is stopped before the restored instance starts.
    backup.copy_database(copy, restored)
    with relay_on_loopback(restored) as url:
        assert checker.observe(url, expected_release="infra-v1")["passed"]
        assert backup.inspect(restored)["records_sha256"] == snapshot["records_sha256"]
    with pytest.raises(FileExistsError):
        backup.copy_database(copy, restored)
