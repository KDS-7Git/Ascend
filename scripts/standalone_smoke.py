"""Build and exercise a wheel in a new environment without optional dependencies."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="ascend-standalone-") as directory:
    temp = Path(directory)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(temp),
            str(root),
        ],
        check=True,
        capture_output=True,
    )
    wheel = next(temp.glob("*.whl"))
    venv.create(temp / "env", with_pip=True)
    python = temp / "env" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
        check=True,
        capture_output=True,
    )
    packages = json.loads(
        subprocess.check_output(
            [str(python), "-m", "pip", "list", "--format=json"], text=True
        )
    )
    print("Installed packages:", ", ".join(p["name"] for p in packages))
    assert {p["name"] for p in packages} <= {"ascend-tracker", "pip", "setuptools"}
    env = {**os.environ, "ASCEND_HOME": str(temp / "profile")}
    env.pop("ASCEND_SERVER", None)
    for args in [
        ["pack", "install", "home-hack-lab"],
        ["mission", "start", "home-hack-lab"],
        [],
        ["levels"],
        ["stats"],
    ]:
        result = subprocess.run(
            [str(python), "-m", "ascend", *args],
            cwd=temp,
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr
        print("PASS: ascend " + " ".join(args))
    print("Standalone wheel works without server, push, or test dependencies.")
