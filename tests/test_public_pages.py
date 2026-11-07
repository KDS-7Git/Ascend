"""Public discovery, account provisioning, and one-use recovery boundaries."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from ascend.application import Tracker
from ascend.engine.packs import dump_toml
from ascend.server import auth
from ascend.server.app import create_app
from ascend.storage import Database

PASSWORD = "a synthetic registration password"
NEW_PASSWORD = "a different synthetic reset password"


def signup(client, username="learner"):
    response = client.post(
        "/api/register",
        json={"username": username, "password": PASSWORD, "timezone": "Asia/Kolkata"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def bearer(token):
    return {"Authorization": "Bearer " + token}


def test_public_pages_and_shared_assets_are_available_without_auth(tmp_path):
    with TestClient(create_app(tmp_path, auth_mode="multi", scheduler=False)) as client:
        for path in (
            "/",
            "/welcome",
            "/tracks",
            "/how-it-works",
            "/privacy",
            "/auth",
            "/login",
            "/signup",
            "/app",
        ):
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/html")
            assert response.headers["cache-control"] == "no-cache"
            assert "/theme.css" in response.text and "/theme.js" in response.text
        for name in (
            "theme.css",
            "session.js",
            "site-router.js",
            "site.js",
            "site.css",
            "auth.js",
            "art.js",
            "product.css",
            "profile.css",
        ):
            assert client.get("/" + name).status_code == 200
        assert client.get("/api/account").status_code == 401
        assert client.get("/api/site").headers["cache-control"] == "no-store"
        assert client.get("/tracks/devops-service-foundations").status_code == 200
        assert client.get("/tracks/no-such-track").status_code == 404
        assert client.get("/manifest.webmanifest").json()["start_url"] == "/app#today"


@pytest.mark.parametrize("mode", ["single", "multi"])
def test_registration_stays_opt_in_and_local_mode_never_exposes_it(tmp_path, mode):
    with TestClient(
        create_app(
            tmp_path, auth_mode=mode, registration=mode == "single", scheduler=False
        )
    ) as client:
        options = client.get("/api/site").json()
        assert options["registration"] is False
        assert options["recovery"] is False
        assert "/api/register" not in client.get("/openapi.json").json()["paths"]
        assert "/api/recover" not in client.get("/openapi.json").json()["paths"]
        assert client.post("/api/register", json={}).status_code in (404, 405)


def test_catalog_publishes_bundled_metadata_without_private_learning(
    tmp_path, pack_data
):
    db = Database(tmp_path)
    db.user_id = auth.create_user(db, "private-learner", PASSWORD, "UTC")
    pack_data["pack"]["id"] = "private-roadmap"
    pack_data["pack"]["title"] = "A private unpublished roadmap"
    Tracker(db).install_pack(dump_toml(pack_data))
    db.close()
    with TestClient(create_app(tmp_path, auth_mode="multi", scheduler=False)) as client:
        catalog = client.get("/api/catalog").json()
        assert len(catalog["tracks"]) > 20
        assert {"DevOps", "Infrastructure", "Projects"} <= set(catalog["categories"])
        encoded = json.dumps(catalog)
        for private in (
            "private-learner",
            "private-roadmap",
            "password_hash",
            "sha256",
            str(tmp_path),
        ):
            assert private not in encoded
        assert client.get("/api/catalog/private-roadmap").status_code == 404
        detail = client.get("/api/catalog/devops-service-foundations").json()
        assert detail["main_levels"] == len(
            [level for level in detail["levels"] if level["lane"] == "main"]
        )
        assert detail["nodes"] == sum(
            len(level["challenges"]) for level in detail["levels"]
        )
        assert "verify" not in json.dumps(detail)


def test_registration_creates_an_isolated_account_with_hashed_credentials(tmp_path):
    with TestClient(
        create_app(tmp_path, auth_mode="multi", registration=True, scheduler=False)
    ) as client:
        result = signup(client)
        account = client.get("/api/account", headers=bearer(result["token"])).json()
        assert account["username"] == "learner" and account["id"] != 1
        assert account["timezone"] == "Asia/Kolkata"
        assert account["account_management"] is True
        assert client.get("/api/packs", headers=bearer(result["token"])).json() == []
        assert client.get(
            "/api/account/security", headers=bearer(result["token"])
        ).json()["recovery_code_configured"]
        db = Database(tmp_path)
        row = db.connection.execute(
            "SELECT * FROM users WHERE id=?", (account["id"],)
        ).fetchone()
        assert (
            row["password_hash"].startswith("scrypt$")
            and PASSWORD not in row["password_hash"]
        )
        stored = db.connection.execute(
            "SELECT code_hash FROM account_recovery WHERE user_id=?", (account["id"],)
        ).fetchone()[0]
        assert stored == auth.recovery_hash(result["recovery_code"])
        assert result["recovery_code"] not in stored
        token = db.connection.execute(
            "SELECT token FROM api_tokens WHERE user_id=?", (account["id"],)
        ).fetchone()[0]
        assert token == hashlib.sha256(result["token"].encode()).hexdigest()
        db.close()


def test_registration_validates_fields_duplicates_and_cross_origin_writes(tmp_path):
    with TestClient(
        create_app(tmp_path, auth_mode="multi", registration=True, scheduler=False)
    ) as client:
        signup(client)
        for username in ("learner", "LEARNER", "local"):
            assert (
                client.post(
                    "/api/register", json={"username": username, "password": PASSWORD}
                ).status_code
                == 409
            )
        for payload in (
            {"username": "ab", "password": PASSWORD},
            {"username": "bad name", "password": PASSWORD},
            {"username": "valid-name", "password": "too short"},
            {
                "username": "valid-name",
                "password": PASSWORD,
                "email": "unused@example.test",
            },
        ):
            assert client.post("/api/register", json=payload).status_code == 422
        assert (
            client.post(
                "/api/register",
                json={
                    "username": "new-learner",
                    "password": PASSWORD,
                    "timezone": "No/Such_Zone",
                },
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/api/register",
                json={"username": "other", "password": PASSWORD},
                headers={"Origin": "https://another.example"},
            ).status_code
            == 403
        )


def test_recovery_rotates_code_revokes_all_sessions_and_keeps_learning(tmp_path):
    with TestClient(
        create_app(tmp_path, auth_mode="multi", registration=True, scheduler=False)
    ) as client:
        alice = signup(client, "alice")
        bob = signup(client, "bob")
        second = client.post(
            "/api/login", json={"username": "alice", "password": PASSWORD}
        ).json()["token"]
        assert client.post(
            "/api/entries",
            json={"learned": "My saved observation", "next_step": "Another small step"},
            headers=bearer(alice["token"]),
        ).is_success
        before = client.get("/api/account", headers=bearer(alice["token"])).json()
        reset = client.post(
            "/api/recover",
            json={
                "username": "alice",
                "recovery_code": alice["recovery_code"].lower(),
                "new_password": NEW_PASSWORD,
            },
        )
        assert reset.status_code == 200, reset.text
        replacement = reset.json()["recovery_code"]
        assert replacement != alice["recovery_code"]
        for token in (alice["token"], second):
            assert client.get("/api/account", headers=bearer(token)).status_code == 401
        assert (
            client.get("/api/account", headers=bearer(bob["token"])).status_code == 200
        )
        replay = client.post(
            "/api/recover",
            json={
                "username": "alice",
                "recovery_code": alice["recovery_code"],
                "new_password": PASSWORD,
            },
        )
        assert replay.status_code == 400
        assert (
            client.post(
                "/api/login", json={"username": "alice", "password": PASSWORD}
            ).status_code
            == 401
        )
        login = client.post(
            "/api/login", json={"username": "alice", "password": NEW_PASSWORD}
        ).json()["token"]
        assert (
            client.get("/api/account", headers=bearer(login)).json()["id"]
            == before["id"]
        )
        assert (
            client.get("/api/search?q=observation", headers=bearer(login)).json()[0][
                "learned"
            ]
            == "My saved observation"
        )


def test_recovery_codes_require_own_password_and_cannot_recover_other_users(tmp_path):
    with TestClient(
        create_app(tmp_path, auth_mode="multi", registration=True, scheduler=False)
    ) as client:
        alice = signup(client, "alice")
        bob = signup(client, "bob")
        assert (
            client.post(
                "/api/account/recovery-code", json={"current_password": PASSWORD}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/account/recovery-code",
                json={"current_password": "incorrect"},
                headers=bearer(alice["token"]),
            ).status_code
            == 400
        )
        for username, code in (
            ("missing", alice["recovery_code"]),
            ("alice", bob["recovery_code"]),
            ("local", alice["recovery_code"]),
        ):
            result = client.post(
                "/api/recover",
                json={
                    "username": username,
                    "recovery_code": code,
                    "new_password": NEW_PASSWORD,
                },
            )
            assert result.status_code == 400
            assert (
                result.json()["detail"]
                == "Recovery details are incorrect or the code has already been used"
            )
        replacement = client.post(
            "/api/account/recovery-code",
            json={"current_password": PASSWORD},
            headers=bearer(alice["token"]),
        )
        assert replacement.is_success
        assert (
            client.get("/api/account", headers=bearer(alice["token"])).status_code
            == 200
        )
        assert (
            client.post(
                "/api/recover",
                json={
                    "username": "alice",
                    "recovery_code": alice["recovery_code"],
                    "new_password": NEW_PASSWORD,
                },
            ).status_code
            == 400
        )


def test_operator_reset_invalidates_recovery_and_disabled_account_cannot_recover(
    tmp_path,
):
    with TestClient(
        create_app(tmp_path, auth_mode="multi", registration=True, scheduler=False)
    ) as client:
        alice = signup(client, "alice")
        db = Database(tmp_path)
        auth.set_enabled(db, "alice", False)
        assert (
            client.post(
                "/api/recover",
                json={
                    "username": "alice",
                    "recovery_code": alice["recovery_code"],
                    "new_password": NEW_PASSWORD,
                },
            ).status_code
            == 400
        )
        auth.reset_password(db, "alice", NEW_PASSWORD)
        assert not db.connection.execute(
            "SELECT 1 FROM account_recovery WHERE user_id=?",
            (auth.managed_user(db, "alice")["id"],),
        ).fetchone()
        db.close()
        assert (
            client.post(
                "/api/recover",
                json={
                    "username": "alice",
                    "recovery_code": alice["recovery_code"],
                    "new_password": PASSWORD,
                },
            ).status_code
            == 400
        )


def test_recovery_rechecks_code_after_concurrent_rotation(tmp_path, monkeypatch):
    with TestClient(
        create_app(tmp_path, auth_mode="multi", registration=True, scheduler=False)
    ) as client:
        alice = signup(client, "alice")
        original = auth.password_hash

        def rotate_during_hash(password, salt=None):
            if password == NEW_PASSWORD:
                db = Database(tmp_path)
                auth.replace_recovery_code(
                    db, auth.managed_user(db, "alice")["id"], PASSWORD
                )
                db.close()
            return original(password, salt)

        monkeypatch.setattr(auth, "password_hash", rotate_during_hash)
        response = client.post(
            "/api/recover",
            json={
                "username": "alice",
                "recovery_code": alice["recovery_code"],
                "new_password": NEW_PASSWORD,
            },
        )
        assert response.status_code == 400
        assert (
            client.get("/api/account", headers=bearer(alice["token"])).status_code
            == 200
        )


def test_recovery_attempts_are_bounded_without_account_disclosure(tmp_path):
    with TestClient(
        create_app(tmp_path, auth_mode="multi", registration=True, scheduler=False)
    ) as client:
        for _ in range(12):
            assert (
                client.post(
                    "/api/recover",
                    json={
                        "username": "missing",
                        "recovery_code": "wrong",
                        "new_password": NEW_PASSWORD,
                    },
                ).status_code
                == 400
            )
        response = client.post(
            "/api/recover",
            json={
                "username": "missing",
                "recovery_code": "wrong",
                "new_password": NEW_PASSWORD,
            },
        )
        assert response.status_code == 429 and response.headers["retry-after"] == "900"
