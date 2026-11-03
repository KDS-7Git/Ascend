import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ascend.cli import execute, parser
from ascend.local_labs.catalog import catalog, detail, executable, review_gaps
from ascend.server.app import create_app


def test_references_are_shared_and_do_not_enable_execution(tracker, tmp_path):
    rows = catalog()
    assert len({r["id"] for r in rows}) == 15
    assert all(not r["automatic_execution"] for r in rows)
    assert all(not r["runnable"] for r in rows if not r["recipes"])
    with pytest.raises(ValueError, match="reference"):
        executable("vampi")
    selected = catalog(track="api-security", level="starter")
    assert "vampi" in {r["id"] for r in selected}
    assert execute(tracker, parser().parse_args(["lab", "catalog", "--track", "api-security", "--level", "starter"])) == selected
    with TestClient(create_app(tmp_path / "api", scheduler=False)) as client:
        assert client.get("/api/lab-catalog?track=api-security&level=starter").json() == selected
        assert client.get("/api/lab-catalog/vampi").json() == detail("vampi")
        assert client.get("/api/lab-catalog?location=server").status_code == 400
        assert client.get("/api/lab-catalog/missing").status_code == 400
        assert client.post("/api/command", json={"argv": ["pack", "install", "api-security"]}).status_code == 200
        assert client.get("/api/packs/api-security").json()["lab_references"] == catalog(track="api-security")


def test_review_claim_cannot_enable_unpinned_untested_recipe():
    gaps = review_gaps({"status": "reviewed", "adapter": "run-readme", "source": {"revision": "main"}})
    assert "No reviewed adapter" in gaps
    assert "Source revision is not pinned" in gaps
    assert "Linux platform has not been measured" in gaps
    assert len(gaps) >= 10


def test_packaged_references_match_research():
    research = json.loads(Path("docs/curriculum/open-source-lab-candidates.json").read_text())
    refs = {r["id"]: r for r in catalog()}
    for source in research["candidates"]:
        row = refs[source["id"]]
        for key in ("repository", "license", "track_ids", "reviewed_revision"):
            assert row[key] == source[key]
