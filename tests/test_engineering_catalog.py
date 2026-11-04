"""Exercise domain discovery, independent entry and downloadable practice bundles."""

import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ascend.registry import registry_entries
from ascend.server.app import create_app
from scripts import build_registry, package_learning_materials

ENGINEERING = {"Infrastructure": 9, "DevOps": 3}


def command(client, *args):
    response = client.post("/api/command", json={"argv": list(args)})
    assert response.status_code == 200, response.text
    return response.json()


def test_domains_install_and_start_later_tracks_without_completing_earlier_ones(
    tmp_path,
):
    entries = [row for row in registry_entries() if row.get("category") in ENGINEERING]
    assert len(entries) == 12
    with TestClient(create_app(tmp_path, scheduler=False)) as client:
        for category, count in ENGINEERING.items():
            group = sorted(
                (row for row in entries if row["category"] == category),
                key=lambda row: row["track_order"],
            )
            assert [row["track_order"] for row in group] == list(range(1, count + 1))
            for row in reversed(group):
                command(client, "pack", "install", row["id"])
            installed = {row["id"]: row for row in client.get("/api/packs").json()}
            for row in group:
                actual = installed[row["id"]]
                assert actual["category"] == category
                assert actual["domain"] == category.lower()
                assert actual["track_order"] == row["track_order"]
                assert actual["recommended_after"] == row.get("recommended_after", [])
                assert actual["levels"] == 8 and actual["valid"]
            # Recommendations must not become an undocumented whole-track gate.
            command(client, "mission", "start", group[-1]["id"])
            overview = client.get("/api/me").json()
            assert overview["mission"]["pack_id"] == group[-1]["id"]
            command(client, "mission", "pause")


def test_every_engineering_bundle_serves_its_real_lessons_and_shared_service(tmp_path):
    entries = [row for row in registry_entries() if row.get("category") in ENGINEERING]
    assert len(entries) == 12
    with TestClient(create_app(tmp_path, scheduler=False)) as client:
        for row in entries:
            response = client.get(f"/training/{row['id']}.zip")
            assert response.status_code == 200, row["id"]
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                assert archive.testzip() is None
                names = archive.namelist()
                prefix = row["id"] + "/"
                assert all(
                    name.startswith(prefix) and ".." not in Path(name).parts
                    for name in names
                )
                assert prefix + "README.md" in names
                assert prefix + "shared/relay.py" in names
                assert prefix + "LICENSE" in names
                assert not any(
                    "__pycache__" in name or name.endswith(".pyc") for name in names
                )
                assert (
                    len(
                        [
                            name
                            for name in names
                            if name.startswith(prefix + "lessons/")
                            and name.endswith(".md")
                        ]
                    )
                    >= 8
                )


def test_domain_fragments_cannot_replace_existing_catalog_identity(tmp_path):
    root = tmp_path / "community"
    domain = root / "devops"
    domain.mkdir(parents=True)
    pack = domain / "demo.toml"
    pack.write_text('[pack]\nid="demo"\ntitle="Demo"\nversion=1\n')
    row = {"id": "demo", "category": "DevOps", "track_order": 1}
    (domain / "catalog.json").write_text(json.dumps({"tracks": [row]}))
    assert build_registry.document(root)["packs"][0]["track_order"] == 1
    (root / "catalog.json").write_text(json.dumps({"tracks": [row]}))
    with pytest.raises(ValueError, match="Duplicate catalog ID"):
        build_registry.document(root)


def test_packaging_preserves_existing_cyber_bytes_and_rejects_linked_private_files(
    tmp_path,
):
    # The original cyber bundles must not change when another domain is added.
    for path, expected in package_learning_materials.outputs("cyber"):
        assert path.read_bytes() == expected, path
    material = tmp_path / "material"
    material.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_text("This file does not belong to the lab")
    (material / "outside.txt").symlink_to(outside)
    with pytest.raises(ValueError, match="regular files"):
        package_learning_materials.source_files(material)
    linked_folder = tmp_path / "linked-material"
    linked_folder.symlink_to(material, target_is_directory=True)
    with pytest.raises(ValueError, match="regular files"):
        package_learning_materials.source_files(linked_folder)
