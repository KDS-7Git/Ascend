import os
import subprocess
import sys


def run_cli(tmp_path, *args):
    return subprocess.run(
        [sys.executable, "-m", "ascend", *args],
        env={**os.environ, "ASCEND_HOME": str(tmp_path)},
        text=True,
        capture_output=True,
    )


def test_cli_end_to_end(tmp_path):
    assert run_cli(tmp_path, "pack", "install", "home-hack-lab").returncode == 0
    assert run_cli(tmp_path, "mission", "start", "home-hack-lab").returncode == 0
    output = run_cli(tmp_path).stdout
    assert "Next" in output and "Quick win" in output and "[draft]" in output
    assert len(output.splitlines()) <= 6
    assert "split" in run_cli(tmp_path, "20").stdout
    assert run_cli(tmp_path, "remind-check").returncode == 1
    assert (
        run_cli(
            tmp_path,
            "done",
            "I explained SSH authentication in my notes",
            "Practice with keys",
        ).returncode
        == 0
    )
    assert run_cli(tmp_path, "remind-check").returncode == 0
    assert run_cli(tmp_path, "stats").returncode == 0
    assert run_cli(tmp_path, "levels").returncode == 0
    assert run_cli(tmp_path, "export", str(tmp_path / "log.md")).returncode == 0
    assert "SSH authentication" in (tmp_path / "log.md").read_text()


def test_time_budget_after_global_json_option(tmp_path):
    result = run_cli(tmp_path, "--json", "20")
    assert result.returncode == 0, result.stderr


def test_pack_new_refuses_to_overwrite(tmp_path):
    path = tmp_path / "existing.toml"
    path.write_text("My existing roadmap")
    result = run_cli(tmp_path, "pack", "new", "Example", "--path", str(path))
    assert result.returncode == 2
    assert path.read_text() == "My existing roadmap"


def test_login_without_posix_fchmod_keeps_password_out_of_profile(
    tmp_path, monkeypatch
):
    from ascend.cli import remote

    monkeypatch.setattr(remote, "default_home", lambda: tmp_path)
    monkeypatch.setattr("builtins.input", lambda prompt: "learner")
    monkeypatch.setattr(remote.getpass, "getpass", lambda prompt: "not-to-be-stored")
    monkeypatch.setattr(remote, "request", lambda *args: {"token": "test-api-token"})
    monkeypatch.delattr(remote.os, "fchmod")
    remote.login("https://example.org")
    assert "test-api-token" in (tmp_path / "token").read_text()
    assert "not-to-be-stored" not in (tmp_path / "token").read_text()
