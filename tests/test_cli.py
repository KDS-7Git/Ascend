import os
import subprocess
import sys


def run_cli(tmp_path, *args):
    return subprocess.run([sys.executable, "-m", "ascend", *args], env={**os.environ, "ASCEND_HOME": str(tmp_path)}, text=True, capture_output=True)


def test_cli_end_to_end(tmp_path):
    assert run_cli(tmp_path, "pack", "install", "home-hack-lab").returncode == 0
    assert run_cli(tmp_path, "mission", "start", "home-hack-lab").returncode == 0
    output = run_cli(tmp_path).stdout
    assert "Next" in output and "Quick win" in output and "[draft]" in output
    assert len(output.splitlines()) <= 6
    assert "split" in run_cli(tmp_path, "20").stdout
    assert run_cli(tmp_path, "remind-check").returncode == 1
    assert run_cli(tmp_path, "done", "I explained SSH authentication in my notes", "Practice with keys").returncode == 0
    assert run_cli(tmp_path, "remind-check").returncode == 0
    assert run_cli(tmp_path, "stats").returncode == 0
    assert run_cli(tmp_path, "levels").returncode == 0
    assert run_cli(tmp_path, "export", str(tmp_path / "log.md")).returncode == 0
    assert "SSH authentication" in (tmp_path / "log.md").read_text()
