import hashlib
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ascend.engine.packs import dump_toml
from ascend.registry import fetch_pack, registry_entries


def test_plugin_never_imported_before_trust_and_edits_revoke(
    tracker, pack_data, tmp_path
):
    root = tracker.db.home / "verifiers"
    root.mkdir()
    marker = tmp_path / "executed"
    source = f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\nfrom ascend.engine.verifiers import VerifyResult\ndef verify(spec, vars):\n    return VerifyResult(True, 'My custom evidence passed')\n"
    plugin = root / "example.py"
    plugin.write_text(source)
    pack_data["node"][0]["verify"] = {"type": "plugin:example"}
    installed = tracker.install_pack(dump_toml(pack_data))
    assert installed["plugins"] == ["example"]
    tracker.start_mission("test-pack")
    assert not tracker.check()["ok"] and not marker.exists()
    tracker.trust_plugin("example")
    assert not marker.exists()
    assert tracker.check()["ok"] and marker.exists()
    marker.unlink()
    plugin.write_text(source + "\n# changed\n")
    assert not tracker.check()["ok"] and not marker.exists()


def test_plugin_bad_shape_and_secrets_are_rejected(tracker, pack_data):
    root = tracker.db.home / "verifiers"
    root.mkdir()
    path = root / "unsafe.py"
    path.write_text(
        "def verify(spec, vars): return (True, 'flag{never-store-this}', None)\n"
    )
    pack_data["node"][0]["verify"] = {"type": "plugin:unsafe"}
    tracker.install_pack(dump_toml(pack_data))
    tracker.start_mission("test-pack")
    tracker.trust_plugin("unsafe")
    assert not tracker.check(confirm=True)["ok"]
    assert tracker.entries() == []


def test_registry_requires_matching_hash(pack_data):
    data = dump_toml(pack_data).encode()
    manifest = {
        "packs": [
            {
                "id": "test-pack",
                "url": "https://example.org/test.toml",
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        ]
    }
    with patch(
        "ascend.registry.urlopen",
        side_effect=[io.BytesIO(json.dumps(manifest).encode()), io.BytesIO(data)],
    ):
        assert (
            fetch_pack("test-pack", "https://example.org/registry.json")
            == data.decode()
        )
    manifest["packs"][0]["sha256"] = "0" * 64
    with patch(
        "ascend.registry.urlopen",
        side_effect=[io.BytesIO(json.dumps(manifest).encode()), io.BytesIO(data)],
    ):
        with pytest.raises(ValueError, match="checksum"):
            fetch_pack("test-pack", "https://example.org/registry.json")


def test_all_community_packs_lint_and_registry_matches():
    from ascend.cli import pack_text
    from ascend.engine.packs import parse_pack

    entries = registry_entries()
    assert len(entries) >= 3
    root = Path("packs/community")
    assert not list(root.glob("*.toml"))
    assert {root / entry["file"] for entry in entries} == set(root.rglob("*.toml"))
    for entry in entries:
        assert (
            Path(entry["file"]).parent.name == entry.get("category", "Projects").lower()
        )
        text = (root / entry["file"]).read_text()
        assert parse_pack(text).id == entry["id"]
        assert hashlib.sha256(text.encode()).hexdigest() == entry["sha256"]
        assert pack_text(entry["id"]) == text


@pytest.mark.parametrize("head_status", [404, 405, 501])
def test_link_checker_falls_back_when_head_unsupported(head_status):
    from urllib.error import HTTPError
    from ascend.registry import check_link

    response = io.BytesIO(b"")
    response.status = 200
    with patch(
        "ascend.registry.urlopen",
        side_effect=[
            HTTPError("https://example.org", head_status, "", {}, None),
            response,
        ],
    ) as open_url:
        assert check_link("https://example.org")["ok"]
        assert open_url.call_args.args[0].method == "GET"
