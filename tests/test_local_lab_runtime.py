import hashlib
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_local_lab_attempts import ANSWERS
from test_local_lab_attempts import reviewed_pilot as reviewed_pilot  # noqa: PLC0414 - pytest fixture.

from ascend.cli import main
from ascend.local_labs.assets import AssetStore, atomic_json
from ascend.local_labs.runtime import Runtime


@pytest.fixture
def runtime(tracker, reviewed_pilot, monkeypatch, tmp_path):
    # Synthetic input for lifecycle fault tests; real upstream input has a separate smoke harness.
    contents = b"Synthetic audit input for lifecycle testing.\n"
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("sample.log", contents)
    blob = archive.getvalue()
    asset = {
        "role": "evidence",
        "url": "https://fixture.invalid/sample.zip",
        "sha256": hashlib.sha256(blob).hexdigest(),
        "bytes": len(blob),
        "member": "sample.log",
        "expanded_bytes": len(contents),
        "expanded_sha256": hashlib.sha256(contents).hexdigest(),
    }
    reviewed_pilot["assets"] = [asset]

    def open_source(req, timeout):
        result = io.BytesIO(blob)
        result.url = req.full_url
        return result

    monkeypatch.setattr("ascend.local_labs.assets.urlopen", open_source)
    return Runtime(tracker, root=tmp_path / "companion")


def test_offline_lifecycle_preserves_work_and_cache_references(runtime):
    run = runtime.start("linux-audit-discovery", offline=True)
    row = runtime.load(run["id"])
    work = runtime.work_dir(row)
    assert runtime.check(row["id"])["status"] == "fail"
    atomic_json(work / "answers.json", ANSWERS)
    assert runtime.check(row["id"])["status"] == "pass"
    assert runtime.prune(0)["cache_bytes"] > 0
    with pytest.raises(ValueError, match="existing local lab"):
        runtime.start("linux-audit-discovery")
    started = runtime.attempts.view(row["local_attempt"]["id"])["started_at"]
    runtime.stop(row["id"])
    with pytest.raises(ValueError, match="Resume"):
        runtime.check(row["id"])
    runtime.resume(row["id"])
    assert runtime.attempts.view(row["local_attempt"]["id"])["started_at"] == started
    assert runtime.export(row["id"])["authority"] == "local"
    assert runtime.finish(row["id"])["status"] == "destroyed"
    assert runtime.prune(0)["cache_bytes"] == 0
    assert json.loads((work / "answers.json").read_text()) == ANSWERS
    assert (work / "submission.json").is_file()
    assert runtime.destroy(row["id"])["status"] == "destroyed"


def test_export_failure_keeps_runtime_and_work(runtime, monkeypatch):
    row = runtime.start("linux-audit-discovery", offline=True)
    atomic_json(runtime.work_dir(row) / "answers.json", ANSWERS)
    original = __import__(
        "ascend.local_labs.runtime", fromlist=["atomic_json"]
    ).atomic_json

    def fail_export(path, data):
        if Path(path).name == "submission.json":
            raise OSError("disk full during evidence save")
        return original(path, data)

    monkeypatch.setattr("ascend.local_labs.runtime.atomic_json", fail_export)
    with pytest.raises(OSError, match="disk full"):
        runtime.finish(row["id"])
    assert runtime.show(row["id"])["status"] == "ready"
    assert runtime.runtime_dir(row).is_dir()


def test_cleanup_failure_and_crash_reconciliation(runtime, monkeypatch):
    row = runtime.start("linux-audit-discovery", offline=True)
    from ascend.local_labs.files import FileLab

    real_destroy = FileLab.destroy
    monkeypatch.setattr(
        FileLab, "destroy", lambda *_: (_ for _ in ()).throw(OSError("busy"))
    )
    assert runtime.destroy(row["id"])["status"] == "cleanup_failed"
    assert runtime.prune(0)["cache_bytes"] > 0
    monkeypatch.setattr(FileLab, "destroy", real_destroy)
    assert runtime.reconcile()[0]["status"] == "destroyed"
    second = runtime.start("linux-audit-discovery", offline=True)
    state = runtime.load(second["id"])
    state["status"] = "preparing"  # A process died after the inventory write.
    runtime.save(state)
    assert runtime.reconcile()[0]["status"] == "destroyed"
    third = runtime.start("linux-audit-discovery", offline=True)
    state = runtime.load(third["id"])
    state["expires_at"] = 0
    runtime.save(state)
    assert runtime.reconcile()[0]["status"] == "destroyed"


def test_unreachable_server_preserves_pending_result(runtime, monkeypatch):
    runtime.server = "https://ascend.invalid"
    requests = []

    def offline(*args, **kwargs):
        requests.append(args)
        raise ValueError("Cannot reach the Ascend server")

    monkeypatch.setattr(runtime, "_remote", offline)
    row = runtime.start("linux-audit-discovery", offline=True)
    atomic_json(runtime.work_dir(row) / "answers.json", ANSWERS)
    result = runtime.finish(row["id"])
    assert result["status"] == "destroyed" and result["pending_sync"]
    assert "remote_receipt" not in result and Path(result["export"]).is_file()
    assert requests == []  # Explicit offline practice waits for an explicit sync.
    with pytest.raises(ValueError, match="Cannot reach"):
        runtime.sync(row["id"])
    assert requests


def test_download_failures_and_cache_tamper(runtime, monkeypatch):
    from ascend.local_labs import assets

    recipe = runtime.resolve("linux-audit-discovery")
    asset = recipe["assets"][0]
    store = AssetStore(runtime.cache)
    path, _ = store.fetch(asset)
    path.write_bytes(b"corrupt")
    assert store.fetch(asset)[1] == asset["bytes"]
    path.unlink()
    real_open = assets.urlopen

    def interrupted(*args, **kwargs):
        raise OSError("interrupted download")

    monkeypatch.setattr(assets, "urlopen", interrupted)
    with pytest.raises(OSError):
        store.fetch(asset)
    assert not list(runtime.cache.glob(".part-*")) and not path.exists()
    monkeypatch.setattr(assets, "urlopen", real_open)
    with pytest.raises(ValueError, match="size"):
        store.fetch({**asset, "bytes": 1})
    monkeypatch.setattr(assets.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
    with pytest.raises(ValueError, match="disk space"):
        store.fetch(asset)


def test_unsafe_work_paths_archives_and_unowned_cache_are_rejected(runtime, tmp_path):
    with pytest.raises(ValueError, match="run ID"):
        runtime.show("../outside")
    row = runtime.start("linux-audit-discovery", offline=True)
    answers = runtime.work_dir(row) / "answers.json"
    answers.unlink()
    target = tmp_path / "outside.json"
    atomic_json(target, ANSWERS)
    answers.symlink_to(target)
    with pytest.raises(ValueError, match="regular"):
        runtime.check(row["id"])
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("../escaped", "bad")
    with pytest.raises(ValueError, match="Unexpected"):
        AssetStore(runtime.cache).selected_zip(
            archive, row["recipe"]["assets"][0], tmp_path / "extracted"
        )
    (runtime.cache / "personal-notes.txt").write_text("keep")
    runtime.destroy(row["id"])
    runtime.prune(0)
    assert (runtime.cache / "personal-notes.txt").read_text() == "keep"
    assert not (tmp_path / "escaped").exists()


def test_configured_remote_does_not_forward_client_operations(
    monkeypatch, tmp_path, capsys, reviewed_pilot
):
    monkeypatch.setenv("ASCEND_HOME", str(tmp_path / "profile"))
    monkeypatch.setenv("ASCEND_LAB_HOME", str(tmp_path / "labs"))
    monkeypatch.setenv("ASCEND_SERVER", "https://ascend.invalid")
    monkeypatch.setattr(
        "ascend.cli.remote.request",
        lambda *_: (_ for _ in ()).throw(AssertionError("forwarded")),
    )
    assert main(["--json", "local-lab", "doctor", "linux-audit-discovery"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "pass"


def test_offline_result_synchronizes_with_server_owned_rubric(
    runtime, tmp_path, monkeypatch
):
    from fastapi.testclient import TestClient

    from ascend.server.app import create_app

    runtime.server = "http://testserver"
    with TestClient(create_app(tmp_path / "remote", scheduler=False)) as client:

        def request(path, data=None, server=None):
            response = (
                client.get(path) if data is None else client.post(path, json=data)
            )
            if response.status_code != 200:
                raise ValueError(response.text)
            return response.json()

        monkeypatch.setattr(runtime, "_remote", request)
        row = runtime.start("linux-audit-discovery", offline=True)
        atomic_json(runtime.work_dir(row) / "answers.json", ANSWERS)
        assert runtime.finish(row["id"])["pending_sync"]
        result = runtime.sync(row["id"])
        assert result["status"] == "destroyed" and not result["pending_sync"]
        receipt = result["remote_receipt"]
        assert receipt["origin"] == "offline" and receipt["started_at"] is None
        assert (
            receipt["result"]["status"] == "pass"
            and receipt["result"]["authority"] == "server-answer"
        )
        assert not receipt["result"]["satisfies_track_evidence"]
        assert client.get("/api/stats").json()["xp"]["total"] == 0
