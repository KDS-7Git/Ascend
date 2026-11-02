from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from ascend.engine.streak import logical_date
from ascend.engine.packs import dump_toml
from ascend.server.app import create_app
from ascend.server.auth import create_user
from ascend.storage import Database
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(tmp_path, auth_mode="single", scheduler=False)
    ) as client:
        yield client


def test_api_health_pack_mission_log_and_stats(client, pack_data):
    assert client.get("/api/health").status_code == 200
    assert (
        client.post(
            "/api/packs",
            files={"file": ("pack.toml", dump_toml(pack_data), "application/toml")},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/command", json={"argv": ["mission", "start", "test-pack"]}
        ).status_code
        == 200
    )
    me = client.get("/api/me").json()
    assert me["next"]["id"] == "one"
    assert me["quick_win"]["id"] == "small"
    assert (
        client.post(
            "/api/entries", json={"learned": "short", "next_step": "next"}
        ).status_code
        == 400
    )
    result = client.post(
        "/api/entries",
        json={
            "learned": "I can explain the whole exercise clearly",
            "next_step": "Continue",
            "complete": True,
        },
    )
    assert result.status_code == 200 and result.json()["completed"]
    assert client.get("/api/stats").json()["current_streak"] == 1
    assert client.get("/api/levels").json()[0]["done"] == 1
    assert (
        client.get("/api/search", params={"q": "explain"})
        .json()[0]["learned"]
        .startswith("I can")
    )


def test_task_details_only_open_after_start_and_survive_end(client, pack_data):
    pack_data["node"][0].update(
        preview="Compare two local observations.",
        requirements="Python 3 and a browser.",
        brief="Detailed introduction with a named input.",
        setup="Detailed workspace setup.",
        steps=["Inspect the private-to-the-attempt input."],
        hints=["A detailed hint."],
        materials=[{"label": "Input", "url": "/training/example.zip"}],
    )
    client.post(
        "/api/packs", files={"file": ("pack.toml", dump_toml(pack_data))}
    ).raise_for_status()
    client.post(
        "/api/command", json={"argv": ["mission", "start", "test-pack"]}
    ).raise_for_status()
    nodes = [
        client.get("/api/me").json()["next"],
        client.get("/api/me").json()["level"]["nodes"][0],
        client.get("/api/levels").json()[0]["nodes"][0],
        client.get("/api/packs/test-pack").json()["nodes"][0],
        client.get("/api/challenges/test-pack:one").json()["node"],
        client.post("/api/command", json={"argv": ["today"]}).json()["next"],
        client.post("/api/command", json={"argv": ["levels"]}).json()[0]["nodes"][0],
    ]
    for node in nodes:
        assert node["preview"] == "Compare two local observations."
        assert node["requirements"] == "Python 3 and a browser."
        assert not node["details_available"]
        assert not (
            {"steps", "hints", "materials", "done_when", "brief", "setup", "resource"}
            & node.keys()
        )
    client.post(
        "/api/command", json={"argv": ["session", "start", "test-pack:one"]}
    ).raise_for_status()
    started = client.get("/api/challenges/test-pack:one").json()
    assert started["node"]["details_available"]
    assert started["node"]["steps"] == pack_data["node"][0]["steps"]
    assert started["node"]["materials"] == pack_data["node"][0]["materials"]
    client.post("/api/command", json={"argv": ["session", "end"]}).raise_for_status()
    ended = client.get("/api/challenges/test-pack:one").json()
    assert ended["session"]["id"] == started["session"]["id"]
    assert ended["session"]["status"] == "finished"
    assert ended["node"]["details_available"]
    other = client.get("/api/challenges/test-pack:two").json()
    assert not other["node"]["details_available"]


def test_multi_user_isolation_and_tokens(tmp_path, pack_data):
    db = Database(tmp_path)
    create_user(db, "alice", "a strong password for testing", "Asia/Kolkata")
    create_user(db, "bob", "another strong password for testing", "America/New_York")
    db.close()
    with TestClient(create_app(tmp_path, auth_mode="multi", scheduler=False)) as client:
        assert client.get("/api/me").status_code == 401
        assert (
            client.post(
                "/api/login", json={"username": "alice", "password": "wrong"}
            ).status_code
            == 401
        )
        tokens = [
            client.post(
                "/api/login", json={"username": name, "password": password}
            ).json()["token"]
            for name, password in [
                ("alice", "a strong password for testing"),
                ("bob", "another strong password for testing"),
            ]
        ]
        alice, bob = [{"Authorization": "Bearer " + token} for token in tokens]
        assert (
            client.post(
                "/api/packs",
                headers=alice,
                files={"file": ("p.toml", dump_toml(pack_data))},
            ).status_code
            == 200
        )
        assert client.get("/api/packs", headers=bob).json() == []
        assert client.get("/api/packs/test-pack", headers=bob).status_code == 404
        assert (
            client.post(
                "/api/entries",
                headers=alice,
                json={
                    "learned": "I learned something and explained it well",
                    "next_step": "Tomorrow",
                },
            ).status_code
            == 200
        )
        assert client.get("/api/stats", headers=bob).json()["current_streak"] == 0
        assert (
            client.post(
                "/api/nodes/test-pack:one/mark", headers=bob, json={"status": "done"}
            ).status_code
            == 400
        )
        client.post(
            "/api/packs",
            headers=bob,
            files={"file": ("p.toml", dump_toml(pack_data))},
        ).raise_for_status()
        client.post(
            "/api/command",
            headers=alice,
            json={"argv": ["session", "start", "test-pack:one"]},
        ).raise_for_status()
        assert client.get("/api/challenges/test-pack:one", headers=alice).json()[
            "node"
        ]["details_available"]
        assert not client.get("/api/challenges/test-pack:one", headers=bob).json()[
            "node"
        ]["details_available"]
        db = Database(tmp_path)
        stored = [r[0] for r in db.connection.execute("SELECT token FROM api_tokens")]
        assert all(token not in stored for token in tokens)
        assert (
            "strong password"
            not in db.connection.execute(
                "SELECT password_hash FROM users WHERE username='alice'"
            ).fetchone()[0]
        )
        db.close()


def test_remote_command_validation_no_arbitrary_file_reads(client):
    assert (
        client.post(
            "/api/command", json={"argv": ["pack", "install", "/etc/passwd"]}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/command", json={"argv": ["pack", "new", "arbitrary"]}
        ).status_code
        == 400
    )
    assert client.post("/api/command", json={"argv": ["nonsense"]}).status_code == 400


def test_timezone_and_dst_rollover():
    now = datetime(2026, 11, 5, 0, tzinfo=timezone.utc)
    assert logical_date(now, "Asia/Kolkata").isoformat() == "2026-11-05"
    assert logical_date(now, "America/New_York").isoformat() == "2026-11-04"
    assert (
        logical_date(
            datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc), "America/New_York"
        ).isoformat()
        == "2026-10-31"
    )


def test_edit_undo_are_audited_and_undo_window(installed, now):
    entry = installed.log(
        "I explained the original exercise today", "Continue tomorrow", complete=True
    )
    installed.edit(entry["id"], learned="I explained the corrected exercise today")
    assert installed.search("corrected")[0]["id"] == entry["id"]
    installed.undo()
    assert installed.entries() == []
    assert installed.states("test-pack").get("one", {}).get("status", "todo") == "todo"
    assert {a["action"] for a in installed.db.rows("audit")} >= {"edit", "undo"}
    installed.log("I explained a different example today", "Continue tomorrow")
    installed.clock = lambda: now + timedelta(minutes=11)
    with pytest.raises(ValueError, match="10 minutes"):
        installed.undo()


def test_split_does_not_touch_pack_and_unlocks_dependents(installed):
    original = installed.db.rows("packs")[0]
    from pathlib import Path

    before = Path(original["path"]).read_text()
    installed.split("one", ["Make a small example", "Explain the result in writing"])
    assert Path(original["path"]).read_text() == before
    assert installed.overview(20)["next"]["id"] == "one-part-1"
    installed.mark("one-part-1", "done")
    installed.mark("one-part-2", "done")
    assert installed.states("test-pack")["one"]["status"] == "done"


def test_ntfy_encodes_utf8_and_keeps_topic_out_of_db():
    from ascend.nudge.channels.ntfy import send

    with patch("ascend.nudge.channels.ntfy.urlopen") as opener:
        send("Streak 3 — a small step", topic="test-topic", server="https://ntfy.sh")
        request = opener.call_args.args[0]
        assert request.full_url == "https://ntfy.sh/test-topic"
        assert request.data.decode() == "Streak 3 — a small step"
        assert opener.call_args.kwargs["timeout"] == 10


def test_sync_proposes_and_accepts_file_evidence(installed, tmp_path):
    from ascend.engine.packs import dump_toml
    import tomllib

    row = installed.db.rows("packs")[0]
    from pathlib import Path

    raw = tomllib.loads(Path(row["path"]).read_text())
    artifact = tmp_path / "proof"
    artifact.write_text("A working example")
    import os

    os.utime(artifact, (installed.now().timestamp(), installed.now().timestamp()))
    raw["node"][0]["verify"] = {"type": "file", "path": str(artifact)}
    installed.install_pack(dump_toml(raw))
    proposals = installed.sync()
    assert proposals[0]["node"] == "one"
    assert installed.states("test-pack").get("one", {}).get("status", "todo") == "todo"
    assert installed.accept()[0]["completed"]


def test_web_assets_and_no_cache_of_private_api(client):
    assert client.get("/").status_code == 200
    assert client.get("/manifest.webmanifest").json()["display"] == "standalone"
    assert "Today" in client.get("/").text
    assert client.get("/api/me").headers["cache-control"] == "no-store"
