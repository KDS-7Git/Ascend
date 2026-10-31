import subprocess
from unittest.mock import patch


from ascend.engine.packs import dump_toml
from ascend.verifiers import command, file


def test_file_expands_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "proof.txt").write_text("working example")
    assert file.verify(
        {"path": "{root}/proof.txt", "min_bytes": 10, "contains": "example"},
        {"root": "~"},
    ).ok
    assert not file.verify({"path": "~/proof.txt", "min_bytes": 500}, {}).ok


def test_command_uses_argv_timeout_and_expands_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    with patch("ascend.verifiers.command.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 0, stdout="ok", stderr="")
        assert command.verify({"cmd": "cat {root}/proof.txt"}, {"root": "~"}).ok
        args, kwargs = run.call_args
        assert args[0] == ["cat", str(tmp_path / "proof.txt")]
        assert kwargs["shell"] is False
        assert kwargs["timeout"] == 10


def test_command_timeout():
    with patch(
        "ascend.verifiers.command.subprocess.run",
        side_effect=subprocess.TimeoutExpired("slow", 10),
    ):
        result = command.verify({"cmd": "slow"}, {})
    assert not result.ok
    assert "10" in result.summary


def test_command_vars_cannot_inject_arguments():
    with patch("ascend.verifiers.command.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        command.verify({"cmd": "echo {value}"}, {"value": "hello ; rm -rf /"})
        assert run.call_args.args[0] == ["echo", "hello ; rm -rf /"]


def test_trust_required_and_reset_on_edit(tracker, pack_data):
    pack_data["node"][0]["verify"] = {"type": "command", "cmd": "echo harmless"}
    tracker.install_pack(dump_toml(pack_data))
    tracker.start_mission("test-pack")
    with patch("ascend.verifiers.command.verify") as run:
        assert not tracker.check()["ok"]
        run.assert_not_called()
    tracker.trust_pack("test-pack")
    assert tracker.check()["ok"]
    row = tracker.db.rows("packs")[0]
    from pathlib import Path

    path = Path(row["path"])
    path.write_text(path.read_text() + "\n# edited\n")
    with patch("ascend.verifiers.command.verify") as run:
        assert not tracker.check()["ok"]
        run.assert_not_called()
