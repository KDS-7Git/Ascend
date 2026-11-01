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
        assert "ascend/web/effects.js" in archive.namelist()
        assert "ascend/web/effects.css" in archive.namelist()
        assert "ascend/web/boot.css" in archive.namelist()
        assert "ascend/web/fonts/InterVariable.woff2" in archive.namelist()
        assert "ascend/web/fonts/OFL.txt" in archive.namelist()
        assert "ascend/community/projects/home-hack-lab.toml" in archive.namelist()
        assert "ascend/community/offensive/api-security.toml" in archive.namelist()
        assert "ascend/community/README.md" in archive.namelist()
        archive.extractall(tmp_path / "installed")
    code = """
from pathlib import Path
from fastapi.testclient import TestClient
from ascend.cli import pack_text
from ascend.engine.packs import parse_pack
from ascend.registry import registry_entries
from ascend.server.app import create_app

for entry in registry_entries():
    assert parse_pack(pack_text(entry['id'])).id == entry['id']
c = TestClient(create_app(Path('data'), scheduler=False))
assert c.get('/').status_code == 200
assert c.get('/app.js').status_code == 200
assert len(c.get('/guide.json').json()['topics']) == 10
assert c.get('/fonts/InterVariable.woff2').content.startswith(b'wOF2')
assert c.get('/theme.js').status_code == 200
assert c.get('/effects.js').status_code == 200
assert c.get('/effects.css').status_code == 200
assert c.post('/api/command', json={'argv': ['pack', 'install', 'api-security']}).status_code == 200
assert c.get('/api/packs').json()[0]['category'] == 'Offensive'
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path / "installed")},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
