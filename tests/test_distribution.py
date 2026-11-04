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
        check=False,
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
        assert "ascend/web/rewards.js" in archive.namelist()
        assert "ascend/web/rewards.css" in archive.namelist()
        assert "ascend/web/accounts.js" in archive.namelist()
        assert "ascend/web/workspace-ui.js" in archive.namelist()
        assert "ascend/web/workspace-ui.css" in archive.namelist()
        assert "ascend/web/boot.css" in archive.namelist()
        assert "ascend/web/fonts/InterVariable.woff2" in archive.namelist()
        assert "ascend/web/fonts/OFL.txt" in archive.namelist()
        assert "ascend/community/projects/home-hack-lab.toml" in archive.namelist()
        assert "ascend/community/offensive/api-security.toml" in archive.namelist()
        assert (
            "ascend/community/infrastructure/io-linux-network.toml"
            in archive.namelist()
        )
        assert (
            "ascend/community/devops/devops-reliability-orchestration.toml"
            in archive.namelist()
        )
        assert (
            "ascend/web/training/devops-reliability-orchestration.zip"
            in archive.namelist()
        )
        assert "ascend/community/README.md" in archive.namelist()
        assert "ascend/local_labs/resources/catalog.json" in archive.namelist()
        assert "ascend/web/local-labs.js" in archive.namelist()
        archive.extractall(tmp_path / "installed")
    code = """
from pathlib import Path
import hashlib
from fastapi.testclient import TestClient
from ascend.cli import pack_text
from ascend.engine.packs import parse_pack
from ascend.registry import registry_entries
from ascend.server.app import create_app
from ascend.local_labs.catalog import DATA, detail
from ascend.local_labs import bgp

for entry in registry_entries():
    assert parse_pack(pack_text(entry['id'])).id == entry['id']
engineering = [entry for entry in registry_entries() if entry.get('domain') in ('devops', 'infrastructure')]
assert len(engineering) == 12
c = TestClient(create_app(Path('data'), scheduler=False))
assert c.get('/').status_code == 200
assert c.get('/app.js').status_code == 200
assert any(t['id'] == 'playground' for t in c.get('/guide.json').json()['topics'])
assert c.get('/playground.js').status_code == 200
assert c.get('/api/playground').json()['activities']
assert c.get('/api/lab-catalog/vampi').json()['repository'] == 'https://github.com/erev0s/VAmPI'
assert c.get('/local-labs.js').status_code == 200
assert c.get('/api/lab-catalog/wrongsecrets-basics').json()['runnable']
for name in ('bgp-single-session', 'bgp-session-protection', 'bgp-prefix-filter'):
    recipe = detail(name)
    assert recipe['runnable']
    assert hashlib.sha256(Path(bgp.__file__).read_bytes()).hexdigest() == recipe['adapter_sha256']
    assert hashlib.sha256((DATA / 'bgp-launcher.txt').read_bytes()).hexdigest() == recipe['launcher_sha256']
assert c.get('/api/rewards').json()['practice']['total'] == 0
attempt = c.post('/api/lab-attempts', json={'recipe_id': 'bgp-export-policy', 'offline': True}).json()
policy = {'version': 1, 'default': 'deny', 'rules': [
    {'action': 'permit', 'prefix': attempt['assignment']['customer_prefix'], 'min_prefix': 24, 'max_prefix': 26}]}
payload = {k: attempt[k] for k in ('nonce', 'recipe_version', 'checker_version', 'fixture_id')}
payload['submission'] = {'files': {'policy.json': policy}}
receipt = c.post('/api/lab-attempts/' + attempt['id'] + '/submit', json=payload).json()
assert receipt['result']['status'] == 'pass'
assert receipt['result']['authority'] == 'server-submission'
assert c.get('/fonts/InterVariable.woff2').content.startswith(b'wOF2')
assert c.get('/theme.js').status_code == 200
assert c.get('/effects.js').status_code == 200
assert c.get('/effects.css').status_code == 200
assert c.get('/rewards.js').status_code == 200
assert c.get('/rewards.css').status_code == 200
assert c.get('/accounts.js').status_code == 200
assert c.get('/workspace-ui.js').status_code == 200
assert c.get('/workspace-ui.css').status_code == 200
assert c.get('/api/rewards').json()['practice']['total'] == 5
assert c.get('/api/account').json()['account_management'] is False
for entry in engineering:
    assert c.get('/training/' + entry['id'] + '.zip').status_code == 200
assert c.post('/api/command', json={'argv': ['pack', 'install', 'api-security']}).status_code == 200
assert c.get('/api/packs').json()[0]['category'] == 'Offensive'
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path / "installed")},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
