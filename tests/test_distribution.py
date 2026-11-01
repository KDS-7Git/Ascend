import os
import subprocess
import sys
import zipfile


def test_built_wheel_contains_and_serves_bundled_assets(tmp_path):
    build = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(tmp_path),
            ".",
        ],
        text=True,
        capture_output=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    wheel = next(tmp_path.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        assert "ascend/web/index.html" in archive.namelist()
        assert "ascend/web/guide.json" in archive.namelist()
        assert "ascend/web/fonts/InterVariable.woff2" in archive.namelist()
        assert "ascend/web/fonts/OFL.txt" in archive.namelist()
        assert "ascend/community/home-hack-lab.toml" in archive.namelist()
        archive.extractall(tmp_path / "installed")
    code = "from ascend.server.app import create_app; from fastapi.testclient import TestClient; from pathlib import Path; c=TestClient(create_app(Path('data'), scheduler=False)); assert c.get('/').status_code == 200; assert c.get('/app.js').status_code == 200; assert len(c.get('/guide.json').json()['topics']) == 10; assert c.get('/fonts/InterVariable.woff2').content.startswith(b'wOF2'); assert c.get('/theme.js').status_code == 200"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path / "installed")},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
