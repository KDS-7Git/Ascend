import pytest
from fastapi.testclient import TestClient

from ascend import challenge_work, timing
from ascend.application import Tracker
from ascend.engine.packs import dump_toml
from ascend.server.app import create_app
from ascend.server.auth import create_user
from ascend.storage import Database


@pytest.fixture
def work_client(tmp_path, pack_data):
    pack_data["node"][0]["verify"] = {
        "type": "file",
        "path": "/unavailable/server/report.json",
        "min_bytes": 15,
    }
    db = Database(tmp_path)
    t = Tracker(db)
    t.install_pack(dump_toml(pack_data))
    t.start_mission("test-pack")
    timing.start(t, "test-pack:one")
    db.close()
    with TestClient(create_app(tmp_path, scheduler=False)) as c:
        yield c


BASE = "/api/challenges/test-pack:one"
NOTE = "I observed both HTTP responses and explained the difference."


def test_ended_lab_restores_edits_and_completes_existing_note(work_client, tmp_path):
    c = work_client
    saved = c.post(
        "/api/entries",
        json={
            "learned": NOTE,
            "next_step": "Compare the missing page",
            "node_id": "test-pack:one",
        },
    ).json()
    c.post("/api/command", json={"argv": ["session", "end"]}).raise_for_status()
    initial = c.get(BASE).json()
    assert initial["session"]["status"] == "finished"
    assert initial["work"]["learned"] == NOTE
    update = c.post(
        BASE + "/notes",
        json={
            "learned": NOTE + " I also saved my actual observations.",
            "next_step": "Continue",
            "revision": 0,
        },
    )
    update.raise_for_status()
    assert len(c.get("/api/entries").json()) == 1
    assert c.get(BASE).json()["work"]["learned"].endswith("observations.")
    upload = c.post(
        BASE + "/evidence",
        files={
            "file": ("report.json", b'{"observations":"two different HTTP responses"}')
        },
    )
    upload.raise_for_status()
    assert c.get(BASE).json()["node"]["status"] == "todo"
    checked = c.post(BASE + "/check").json()
    assert checked["ok"]
    assert c.get(BASE).json()["node"]["status"] == "todo"
    result = c.post(BASE + "/complete", json={"revision": update.json()["revision"]})
    result.raise_for_status()
    assert result.json()["completed"]
    after = c.get(BASE).json()
    assert after["node"]["status"] == "done"
    assert after["session"]["status"] == "finished"
    assert after["session"]["elapsed_seconds"] == initial["session"]["elapsed_seconds"]
    entries = c.get("/api/entries").json()
    assert len(entries) == 1
    assert entries[0]["id"] == saved["id"] and entries[0]["complete"] == 1
    assert c.get("/api/levels").json()[1]["open"]
    assert (
        c.post("/api/command", json={"argv": ["session", "status"]}).json()["xp"] == 0
    )
    c.post(
        BASE + "/complete", json={"revision": after["work"]["revision"]}
    ).raise_for_status()
    assert len(c.get("/api/entries").json()) == 1
    # Completed work remains editable without reopening its score or progression.
    c.post(
        BASE + "/notes",
        json={
            "learned": NOTE + " Added a limitation.",
            "next_step": "Practice",
            "revision": after["work"]["revision"],
            "log_progress": True,
        },
    ).raise_for_status()
    assert c.get(BASE).json()["node"]["status"] == "done"


def test_draft_conflict_preserves_newer_saved_text(work_client):
    c = work_client
    first = c.post(
        BASE + "/notes", json={"learned": "Small draft", "next_step": "", "revision": 0}
    )
    first.raise_for_status()
    assert not c.get("/api/entries").json()
    conflict = c.post(
        BASE + "/notes",
        json={"learned": "Old tab draft", "next_step": "", "revision": 0},
    )
    assert conflict.status_code == 409
    assert c.get(BASE).json()["work"]["learned"] == "Small draft"
    assert c.post(BASE + "/complete", json={"revision": 1}).status_code == 400
    assert c.get(BASE).json()["node"]["status"] == "todo"


def test_upload_validates_without_writing_a_pack_path(work_client, tmp_path):
    c = work_client
    assert (
        c.post(BASE + "/evidence", files={"file": ("x.json", b"not JSON")}).status_code
        == 400
    )
    assert (
        c.post(BASE + "/evidence", files={"file": ("x.json", b"{}")}).status_code == 400
    )
    content = b'{"observations":"a valid report from the learner"}'
    result = c.post(BASE + "/evidence", files={"file": ("../../host.json", content)})
    result.raise_for_status()
    assert result.json()["work"]["attachment"]["name"] == "host.json"
    assert c.get(BASE + "/evidence").content == content
    assert not (tmp_path / "host.json").exists()
    assert len(list((tmp_path / "uploads").rglob("*"))) >= 1
    assert (
        c.post(
            BASE + "/evidence",
            files={"file": ("big.json", b" " * (challenge_work.MAX_UPLOAD + 1))},
        ).status_code
        == 413
    )
    assert (
        c.get(BASE + "/evidence").content == content
    )  # failed replacement preserves accepted upload
    db = Database(tmp_path)
    t = Tracker(db)
    pack, node = t.resolve_node("test-pack:one")
    manifest = db.setting(challenge_work.key("attachment", pack, node))
    stored = challenge_work.artifact_path(t, pack, node, manifest["token"])
    secret = tmp_path / "private"
    secret.write_text("private contents")
    stored.unlink()
    stored.symlink_to(secret)
    assert not t.verify_node(pack, node).ok
    db.close()


def test_unscored_retry_preserves_attempt_and_cannot_reset_reward(
    work_client, tmp_path
):
    c = work_client
    c.post("/api/command", json={"argv": ["session", "end"]}).raise_for_status()
    before = c.get(BASE).json()["session"]
    c.post(BASE + "/practice", json={"minutes": 12}).raise_for_status()
    after = c.get(BASE).json()["session"]
    assert (
        after["status"] == "running"
        and after["practice"]
        and after["potential_xp"] == 0
    )
    assert after["budget_seconds"] == 720
    db = Database(tmp_path)
    t = Tracker(db)
    pack, node = t.resolve_node("test-pack:one")
    assert (
        db.setting(challenge_work.key("session-history-1", pack, node))["finished_at"]
        == before["finished_at"]
    )
    timing.finish(t, pack, node, "verifier:ctf")
    assert not db.rows("xp_awards")
    db.close()
    assert (
        c.post("/api/challenges/test-pack:small/practice", json={}).status_code == 400
    )


def test_notes_and_uploads_are_account_scoped(tmp_path, pack_data):
    db = Database(tmp_path)
    for name in ["alice", "bob"]:
        uid = create_user(db, name, "long test password only", "UTC")
        db.user_id = uid
        t = Tracker(db)
        pack_data["node"][0]["verify"] = {
            "type": "file",
            "path": "/not/accessible/report.json",
        }
        t.install_pack(dump_toml(pack_data))
        t.start_mission("test-pack")
        timing.start(t, "test-pack:one")
    db.close()
    with TestClient(create_app(tmp_path, auth_mode="multi", scheduler=False)) as c:
        tokens = {
            name: c.post(
                "/api/login",
                json={"username": name, "password": "long test password only"},
            ).json()["token"]
            for name in ["alice", "bob"]
        }
        alice = {"Authorization": "Bearer " + tokens["alice"]}
        bob = {"Authorization": "Bearer " + tokens["bob"]}
        assert (
            c.post(
                BASE + "/notes",
                headers=alice,
                json={"learned": NOTE, "next_step": "Next", "revision": 0},
            ).status_code
            == 200
        )
        assert (
            c.post(
                BASE + "/evidence",
                headers=alice,
                files={"file": ("report.json", b'{"observation":"owned by alice"}')},
            ).status_code
            == 200
        )
        assert c.get(BASE, headers=bob).json()["work"]["learned"] == ""
        assert c.get(BASE + "/evidence", headers=bob).status_code == 404
        assert c.post(BASE + "/check", headers=alice).json()["ok"]
        assert not c.post(BASE + "/check", headers=bob).json()["ok"]
        assert (
            c.post(BASE + "/complete", headers=bob, json={"revision": 0}).status_code
            == 400
        )
        assert (
            c.post(
                BASE + "/notes",
                json={"learned": NOTE, "next_step": "Next", "revision": 0},
            ).status_code
            == 401
        )
