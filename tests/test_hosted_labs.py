import json
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from test_local_lab_attempts import reviewed_pilot as reviewed_pilot  # noqa: PLC0414
from test_local_lab_runtime import runtime as runtime  # noqa: PLC0414

from ascend.local_labs.hosted import Controller
from ascend.local_labs.runner import create_runner
from ascend.server.app import create_app
from ascend.server.lab_runner import RunnerClient

KEY = "a-private-runner-key-for-tests-123456789"
ALICE, BOB = "a" * 64, "b" * 64


def wait(controller, account=ALICE):
    for _ in range(500):
        job = controller.job(account)
        if job and job["status"] not in {"queued", "running"}:
            return job
        time.sleep(0.01)
    pytest.fail("Runner job did not complete")


@pytest.fixture
def controller(tmp_path, monkeypatch, runtime):
    c = Controller(
        tmp_path / "runner",
        recipes={"linux-audit-discovery"},
        reserve_bytes=0,
        max_active=1,
    )
    # Use the real Runtime/adapter with the pinned synthetic asset fixture.
    from contextlib import contextmanager

    @contextmanager
    def connected(account):
        yield runtime

    monkeypatch.setattr(c, "runtime", connected)
    monkeypatch.setattr(
        c, "rows", lambda account: runtime.rows() if account == ALICE else []
    )
    monkeypatch.setattr(
        c,
        "files",
        lambda account, row: (
            {
                "work/answers.json": runtime.work_dir(row) / "answers.json",
                "input/evidence.log": runtime.runtime_dir(row) / "evidence.log",
            }
            if row["status"] != "destroyed"
            else {"work/answers.json": runtime.work_dir(row) / "answers.json"}
        ),
    )
    yield c
    c.close()


def test_async_lifecycle_files_results_and_account_scope(controller):
    from test_local_lab_attempts import ANSWERS

    controller.queue(ALICE, "start", data={"recipe_id": "linux-audit-discovery"})
    job = wait(controller)
    assert job["status"] == "complete", job
    run = controller.status(ALICE)["runs"][0]
    assert not {"owner", "local_attempt", "resources", "work_dir"} & run.keys()
    assert run["evidence_label"] == "Answer checked on server"
    assert run["xp"] == 0 and not run["satisfies_track_evidence"]
    with pytest.raises(ValueError, match="this account"):
        controller.read(BOB, run["id"], "work/answers.json")
    with pytest.raises(ValueError, match="unavailable"):
        controller.read(ALICE, run["id"], "../../etc/passwd")
    controller.queue(
        ALICE,
        "save",
        run["id"],
        {"name": "work/answers.json", "content": json.dumps(ANSWERS)},
    )
    assert wait(controller)["status"] == "complete"
    controller.queue(ALICE, "check", run["id"])
    assert wait(controller)["result"]["status"] == "pass"
    controller.queue(ALICE, "stop", run["id"])
    assert wait(controller)["status"] == "complete"
    assert not controller.read(ALICE, run["id"], "work/answers.json")["editable"]
    controller.queue(ALICE, "resume", run["id"])
    assert wait(controller)["status"] == "complete"
    controller.queue(ALICE, "finish", run["id"])
    assert wait(controller)["status"] == "complete"
    assert controller.status(ALICE)["runs"][0]["status"] == "destroyed"
    assert (
        json.loads(controller.read(ALICE, run["id"], "work/answers.json")["content"])
        == ANSWERS
    )


def test_admission_auth_body_bounds_and_missing_provider(controller):
    client = TestClient(create_runner(controller.root, KEY, controller=controller))
    assert client.get("/v1/capabilities").status_code == 401
    headers = {"Authorization": "Bearer " + KEY}
    assert client.get("/v1/capabilities", headers=headers).json()["max_active"] == 1
    assert (
        client.get("/v1/accounts/not-a-scope/runs", headers=headers).status_code == 400
    )
    assert (
        client.post(
            f"/v1/accounts/{ALICE}/runs",
            headers=headers,
            json={"recipe_id": "cloudfoxable-secret"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/v1/accounts/{ALICE}/runs", headers=headers, content=b" " * 1048577
        ).status_code
        == 413
    )
    controller.queue(ALICE, "start", data={"recipe_id": "linux-audit-discovery"})
    assert wait(controller)["status"] == "complete"
    with pytest.raises(ValueError, match="slots are full"):
        controller.queue(BOB, "start", data={"recipe_id": "linux-audit-discovery"})
    with pytest.raises(ValueError, match="existing server lab"):
        controller.queue(ALICE, "start", data={"recipe_id": "linux-audit-discovery"})
    controller.reserve_bytes = 2**70
    controller.queue(ALICE, "destroy", controller.status(ALICE)["runs"][0]["id"])
    wait(controller)
    with pytest.raises(ValueError, match="disk"):
        controller.queue(ALICE, "start", data={"recipe_id": "linux-audit-discovery"})


def test_fixed_destination_http_and_router_command_boundary(tmp_path, monkeypatch):
    c = Controller(tmp_path)
    try:
        row = {"endpoints": {"fixed": "http://127.0.0.1:8000"}}
        for path in [
            "http://example.com",
            "//example.com/x",
            "/\\example.com",
            "/x\r\nX: y",
        ]:
            with pytest.raises(ValueError, match="relative path"):
                c.http(ALICE, None, row, {"target": "fixed", "path": path})
        with pytest.raises(ValueError, match="target"):
            c.http(ALICE, None, row, {"target": "http://169.254.169.254"})
        with pytest.raises(ValueError, match="method"):
            c.http(ALICE, None, row, {"target": "fixed", "method": "CONNECT"})
        with pytest.raises(ValueError, match="token"):
            c.http(
                ALICE, None, row, {"target": "fixed", "token": "x\nHost: example.com"}
            )
        adapter = Mock()
        adapter.command.return_value = "BGP summary"
        runtime = SimpleNamespace(adapter=lambda row: adapter)
        row = {
            "recipe": {"adapter": "frr-bgp-v1"},
            "addresses": {"rtr": "10.0.0.1", "x1": "10.0.0.2"},
        }
        assert (
            c.router(
                ALICE, runtime, row, {"commands": ["show bgp ipv4 unicast summary"]}
            )["output"]
            == "BGP summary"
        )
        for command in [
            "start-shell",
            "write file /etc/passwd",
            "show running-config\nstart-shell",
            "neighbor 169.254.169.254 remote-as 65100",
            "router bgp 65100",
            "show bgp ipv4 unicast; id",
        ]:
            with pytest.raises(ValueError, match="command set"):
                c.router(ALICE, runtime, row, {"commands": [command]})
        assert adapter.command.call_count == 1
        c.router(ALICE, runtime, row, {"commands": ["write memory"]})
        assert adapter.command.call_args_list[-2].args[1:] == (
            "rtr",
            "clear bgp ipv4 unicast *",
        )
        assert adapter.command.call_args_list[-1].args[1:] == (
            "x1",
            "clear bgp ipv4 unicast *",
        )
    finally:
        c.close()


def test_web_binds_runner_requests_to_authenticated_account(tmp_path):
    from ascend.server.auth import create_user, login
    from ascend.storage import Database

    db = Database(tmp_path)
    create_user(db, "alice", "long-password-alice", "UTC")
    create_user(db, "bob", "long-password-bob", "UTC")
    alice = login(db, "alice", "long-password-alice")
    bob = login(db, "bob", "long-password-bob")
    db.close()
    app = create_app(tmp_path, auth_mode="multi", scheduler=False)
    runner = RunnerClient("http://127.0.0.1:8421", KEY, "test-site")
    calls = []
    runner.request = lambda path, data=None: (
        calls.append((path, data)) or {"runs": [], "job": None}
    )
    app.state.lab_runner = runner
    client = TestClient(app)
    assert client.get("/api/hosted-labs/runs").status_code == 401
    for token in (alice, bob):
        assert (
            client.get(
                "/api/hosted-labs/runs", headers={"Authorization": "Bearer " + token}
            ).status_code
            == 200
        )
    assert calls[0][0] != calls[1][0]
    assert "alice" not in calls[0][0] and "bob" not in calls[1][0]
    assert (
        client.post(
            "/api/hosted-labs/runs",
            headers={
                "Authorization": "Bearer " + alice,
                "Origin": "https://bad.example",
            },
            json={"recipe_id": "linux-audit-discovery"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/hosted-labs/runs/x/exec",
            headers={"Authorization": "Bearer " + alice},
            json={},
        ).status_code
        == 404
    )
    with pytest.raises(ValueError, match="HTTPS"):
        RunnerClient("http://remote.example:8421", KEY, "test-site")
    with pytest.raises(ValueError, match="key"):
        RunnerClient("http://127.0.0.1:8421", "short", "test-site")


def test_real_manifest_file_allowlist_and_cleanup_retry(tmp_path):
    c = Controller(tmp_path, reserve_bytes=0)
    try:
        with c.runtime(ALICE) as runtime:
            row = {
                "id": "a" * 32,
                "recipe": {
                    "id": "wrongsecrets-basics",
                    "title": "Secrets",
                    "adapter": "wrongsecrets-v1",
                    "assets": [{"filename": "Challenge1.java"}],
                },
                "status": "cleanup_failed",
                "expires_at": time.time() + 10,
                "files": {},
                "cleanup_error": "busy volume",
            }
            root = runtime.runtime_dir(row)
            root.mkdir(parents=True)
            (root / "Challenge1.java").write_text("reviewed input")
            (root / "unreviewed.txt").write_text("do not expose")
            (root / "bad.java").symlink_to("/etc/passwd")
            assert set(c.files(ALICE, row)) == {"input/Challenge1.java"}
            row["recipe"]["assets"].append({"path": "basic/6-protect/topology.yml"})
            (root / "basic-6-protect-topology.yml").write_text("Pinned BGP topology")
            assert "input/basic/6-protect/topology.yml" in c.files(ALICE, row)
        assert c.view(ALICE, row)["cleanup_error"] == "busy volume"
    finally:
        c.close()


def test_runner_recovery_expiry_failed_cleanup_and_duplicate_process(
    tmp_path, monkeypatch
):
    from ascend.local_labs.assets import atomic_json

    c = Controller(tmp_path, reserve_bytes=0)
    try:
        with pytest.raises(ValueError, match="already using"):
            Controller(tmp_path)
        atomic_json(
            c.job_path(ALICE),
            {"id": "interrupted", "action": "start", "status": "running"},
        )
        from contextlib import contextmanager

        stub = Mock()

        @contextmanager
        def connection(account):
            yield stub

        monkeypatch.setattr(c, "runtime", connection)
        c.reconcile(recover=True)
        assert c.job(ALICE)["status"] == "failed"
        assert "restarted" in c.job(ALICE)["error"]
        stub.reconcile.assert_called_once()
        stub.prune.assert_called_once_with(32)
    finally:
        c.close()


def test_deadline_reconciliation_and_failed_deletion_retain_work(
    controller, monkeypatch
):
    controller.queue(ALICE, "start", data={"recipe_id": "linux-audit-discovery"})
    wait(controller)
    run = controller.status(ALICE)["runs"][0]
    from ascend.local_labs.files import FileLab

    original = FileLab.destroy

    def busy(*args):
        raise OSError("Injected busy storage")

    monkeypatch.setattr(FileLab, "destroy", busy)
    controller.queue(ALICE, "destroy", run["id"])
    assert wait(controller)["result"]["status"] == "cleanup_failed"
    assert (
        controller.status(ALICE)["runs"][0]["cleanup_error"] == "Injected busy storage"
    )
    with pytest.raises(ValueError, match="slots are full"):
        controller.queue(BOB, "start", data={"recipe_id": "linux-audit-discovery"})
    monkeypatch.setattr(FileLab, "destroy", original)
    controller.reconcile()
    assert controller.status(ALICE)["runs"][0]["status"] == "destroyed"
    assert controller.read(ALICE, run["id"], "work/answers.json")["content"]
    controller.queue(ALICE, "start", data={"recipe_id": "linux-audit-discovery"})
    wait(controller)
    run = next(
        r for r in controller.status(ALICE)["runs"] if r["status"] != "destroyed"
    )
    with controller.runtime(ALICE) as runtime:
        row = runtime.load(run["id"])
        row["expires_at"] = time.time() - 1
        runtime.save(row)
    controller.reconcile()
    assert controller.load(ALICE, run["id"])["status"] == "destroyed"
    assert controller.read(ALICE, run["id"], "work/answers.json")["content"]
