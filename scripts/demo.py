"""Record the requested CLI demo in a disposable profile, with desktop delivery mocked."""

from pathlib import Path
import os
import shlex
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
commands = [
    ["pack", "install", "home-hack-lab"],
    ["mission", "start", "home-hack-lab"],
    ["backfill", "pi-reachable", "ssh-key-login"],
    ["levels"],
    [],
    ["20"],
    [
        "done",
        "I can explain how file permissions affect access",
        "Continue with the next small exercise",
        "--node",
        "bandit-13",
        "--complete",
        "--minutes",
        "20",
    ],
    ["stats"],
    ["config", "nudge-time", "21:30"],
    ["config", "nudge-test"],
    ["install-nudge", "--dry-run"],
]
lines = [
    "# Ascend CLI demonstration",
    "",
    "These are synthetic demonstration records in a disposable profile, not the owner's learning log.",
    "Desktop notification delivery is replaced by a local stub; no live desktop delivery is claimed.",
    "",
]
with tempfile.TemporaryDirectory(prefix="ascend-demo-") as directory:
    home = Path(directory)
    bin_dir = home / "bin"
    bin_dir.mkdir()
    notifier = bin_dir / "notify-send"
    notifier.write_text("#!/bin/sh\nexit 0\n")
    notifier.chmod(0o700)
    env = {
        **os.environ,
        "ASCEND_HOME": str(home / "profile"),
        "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", ""),
    }
    env.pop("ASCEND_SERVER", None)
    for args in commands:
        result = subprocess.run(
            [sys.executable, "-m", "ascend", *args],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
        lines += [
            "```console",
            "$ " + shlex.join(["ascend", *args]),
            result.stdout.rstrip().replace(directory, "<demo-home>"),
            "```",
            "",
        ]
(root / "docs/testing/cli-demo.md").write_text("\n".join(lines))
print("Wrote docs/testing/cli-demo.md")
