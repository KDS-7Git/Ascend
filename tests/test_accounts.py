"""Account controls stay hidden by default and isolate sessions and recovery."""

import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from ascend.server import auth
from ascend.server.app import create_app
from ascend.storage import Database

PASSWORD = "a long synthetic test password"
NEW_PASSWORD = "a different synthetic test password"


@pytest.fixture
def account_home(tmp_path):
    db = Database(tmp_path)
    for name in ("alice", "bob"):
        auth.create_user(db, name, PASSWORD, "UTC")
    db.close()
    return tmp_path


def sign_in(client, username="alice", password=PASSWORD, label="Test browser"):
    response = client.post(
        "/api/login", json={"username": username, "password": password, "label": label}
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def bearer(token):
    return {"Authorization": "Bearer " + token}


def test_single_user_dashboard_does_not_enable_account_controls(
    account_home, monkeypatch
):
    monkeypatch.setenv("ASCEND_ACCOUNT_MANAGEMENT", "1")
    with TestClient(
        create_app(account_home, auth_mode="single", scheduler=False)
    ) as client:
        account = client.get("/api/account").json()
        assert account["username"] == "local" and account["id"] == 1
        assert account["account_management"] is False
        assert client.get("/api/health").json()["account_management"] is False
        assert client.get("/api/account/security").status_code == 404
        assert (
            "/api/account/password" not in client.get("/openapi.json").json()["paths"]
        )
        assert (
            client.post(
                "/api/account/password",
                json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            ).status_code
            == 405
        )
        assert (
            client.post(
                "/api/login", json={"username": "alice", "password": PASSWORD}
            ).status_code
            == 404
        )


def test_multiuser_controls_need_explicit_feature_setting(account_home):
    with TestClient(
        create_app(
            account_home, auth_mode="multi", scheduler=False, account_management=False
        )
    ) as client:
        token = sign_in(client)
        assert (
            client.get("/api/account", headers=bearer(token)).json()[
                "account_management"
            ]
            is False
        )
        assert (
            client.get("/api/account/security", headers=bearer(token)).status_code
            == 404
        )
        assert client.get("/api/account").status_code == 401


def test_sessions_can_only_be_seen_and_revoked_by_their_owner(account_home):
    with TestClient(
        create_app(
            account_home, auth_mode="multi", scheduler=False, account_management=True
        )
    ) as client:
        first = sign_in(client, label="Browser one")
        second = sign_in(client, label="CLI two")
        bob = sign_in(client, "bob")
        rows = client.get("/api/account/security", headers=bearer(first)).json()[
            "sessions"
        ]
        assert len(rows) == 2 and sum(row["current"] for row in rows) == 1
        encoded = json.dumps(rows)
        for token in (first, second, bob):
            assert token not in encoded
            assert hashlib.sha256(token.encode()).hexdigest() not in encoded
        target = next(row["id"] for row in rows if not row["current"])
        assert (
            client.delete(
                "/api/account/sessions/" + target, headers=bearer(bob)
            ).status_code
            == 404
        )
        assert client.get("/api/account", headers=bearer(second)).status_code == 200
        assert client.delete(
            "/api/account/sessions/" + target, headers=bearer(first)
        ).json() == {"revoked": True, "logged_out": False}
        assert client.get("/api/account", headers=bearer(second)).status_code == 401
        assert client.get("/api/account", headers=bearer(bob)).status_code == 200
        third = sign_in(client, label="Another browser")
        assert (
            client.post(
                "/api/account/sessions/revoke-others", headers=bearer(first)
            ).json()["revoked"]
            == 1
        )
        assert client.get("/api/account", headers=bearer(third)).status_code == 401
        current = next(row["id"] for row in rows if row["current"])
        assert client.delete(
            "/api/account/sessions/" + current, headers=bearer(first)
        ).json()["logged_out"]
        assert client.get("/api/account", headers=bearer(first)).status_code == 401


def test_password_change_rotates_all_sessions_and_preserves_learning_data(account_home):
    with TestClient(
        create_app(
            account_home, auth_mode="multi", scheduler=False, account_management=True
        )
    ) as client:
        first, second, bob = sign_in(client), sign_in(client), sign_in(client, "bob")
        learned = "I traced a request through the local service and its listening port."
        assert (
            client.post(
                "/api/entries",
                headers=bearer(first),
                json={"learned": learned, "next_step": "Change the port"},
            ).status_code
            == 200
        )
        bad = client.post(
            "/api/account/password",
            headers=bearer(first),
            json={"current_password": "wrong", "new_password": NEW_PASSWORD},
        )
        assert bad.status_code == 400
        assert client.get("/api/account", headers=bearer(second)).status_code == 200
        response = client.post(
            "/api/account/password",
            headers=bearer(first),
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 200, response.text
        replacement = response.json()["token"]
        for token in (first, second):
            assert client.get("/api/account", headers=bearer(token)).status_code == 401
        assert (
            client.get("/api/account", headers=bearer(replacement)).json()["username"]
            == "alice"
        )
        assert client.get("/api/account", headers=bearer(bob)).status_code == 200
        assert (
            client.get("/api/entries", headers=bearer(replacement)).json()[0]["learned"]
            == learned
        )
        assert (
            client.post(
                "/api/login", json={"username": "alice", "password": PASSWORD}
            ).status_code
            == 401
        )
        sign_in(client, password=NEW_PASSWORD)


def test_operator_recovery_disable_and_enable_keep_identity_and_data(account_home):
    db = Database(account_home)
    try:
        row = auth.managed_user(db, "alice")
        db.user_id = row["id"]
        db.set_setting("retained-note", "Private learning state")
        token = auth.login(db, "alice", PASSWORD)
        auth.set_enabled(db, "alice", False)
        assert auth.authenticate(db, token) is None
        with pytest.raises(ValueError, match="Invalid username"):
            auth.login(db, "alice", PASSWORD)
        auth.set_enabled(db, "alice", True)
        token = auth.login(db, "alice", PASSWORD)
        auth.reset_password(db, "alice", NEW_PASSWORD)
        assert auth.authenticate(db, token) is None
        assert (
            auth.authenticate(db, auth.login(db, "alice", NEW_PASSWORD))["id"]
            == row["id"]
        )
        assert db.setting("retained-note") == "Private learning state"
        for operation in (
            lambda: auth.reset_password(db, "local", NEW_PASSWORD),
            lambda: auth.set_enabled(db, "local", True),
        ):
            with pytest.raises(ValueError, match="local testing account"):
                operation()
        public = json.dumps(auth.list_users(db))
        assert (
            "password_hash" not in public
            and "scrypt" not in public
            and PASSWORD not in public
        )
    finally:
        db.close()


def test_expiration_and_session_limit_bound_old_credentials(account_home):
    db = Database(account_home)
    try:
        user_id = auth.managed_user(db, "alice")["id"]
        tokens = [auth.issue_token(db, user_id) for _ in range(auth.MAX_SESSIONS + 1)]
        assert auth.authenticate(db, tokens[0]) is None
        assert len(auth.sessions(db, user_id)) == auth.MAX_SESSIONS
        assert auth.authenticate(db, tokens[-1]) is not None
        db.connection.execute(
            "UPDATE api_tokens SET created_at=? WHERE token=?",
            (
                (datetime.now(UTC) - timedelta(days=31)).isoformat(),
                hashlib.sha256(tokens[-1].encode()).hexdigest(),
            ),
        )
        assert auth.authenticate(db, tokens[-1]) is None
        assert all(
            row["id"]
            != auth.session_id(hashlib.sha256(tokens[-1].encode()).hexdigest())
            for row in auth.sessions(db, user_id)
        )
    finally:
        db.close()


def test_login_cannot_issue_a_token_after_a_concurrent_password_reset(
    account_home, monkeypatch
):
    db = Database(account_home)
    original = auth.password_matches

    def reset_during_check(password, encoded):
        matches = original(password, encoded)
        auth.reset_password(db, "alice", NEW_PASSWORD)
        return matches

    monkeypatch.setattr(auth, "password_matches", reset_during_check)
    try:
        with pytest.raises(ValueError, match="Invalid username"):
            auth.login(db, "alice", PASSWORD)
        assert not auth.sessions(db, auth.managed_user(db, "alice")["id"])
    finally:
        db.close()


def test_login_throttle_bounds_expensive_failures_without_disclosing_users(
    account_home,
):
    with TestClient(
        create_app(account_home, auth_mode="multi", scheduler=False)
    ) as client:
        for _ in range(12):
            assert (
                client.post(
                    "/api/login", json={"username": "missing", "password": "wrong"}
                ).status_code
                == 401
            )
        blocked = client.post(
            "/api/login", json={"username": "missing", "password": "wrong"}
        )
        assert blocked.status_code == 429 and blocked.headers["Retry-After"] == "900"
        sign_in(client, "bob")


def test_password_change_throttles_guesses_without_holding_the_database_lock(
    account_home, monkeypatch
):
    with TestClient(
        create_app(
            account_home, auth_mode="multi", scheduler=False, account_management=True
        )
    ) as client:
        token = sign_in(client)
        original = auth.password_matches
        calls = []

        def observed(password, encoded):
            calls.append(password)
            return original(password, encoded)

        monkeypatch.setattr(auth, "password_matches", observed)
        for _ in range(12):
            response = client.post(
                "/api/account/password",
                headers=bearer(token),
                json={"current_password": "wrong", "new_password": NEW_PASSWORD},
            )
            assert response.status_code == 400
        response = client.post(
            "/api/account/password",
            headers=bearer(token),
            json={"current_password": "wrong", "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 429 and len(calls) == 12
        assert client.get("/api/account", headers=bearer(token)).status_code == 200


def test_operator_cli_prompts_for_password_and_never_prints_it(
    account_home, monkeypatch, capsys
):
    from ascend.server.__main__ import main

    monkeypatch.setattr(
        sys,
        "argv",
        ["ascend-server", "--home", str(account_home), "user-password", "alice"],
    )
    monkeypatch.setattr("getpass.getpass", lambda prompt: NEW_PASSWORD)
    main()
    output = capsys.readouterr().out
    assert NEW_PASSWORD not in output and "all existing sessions signed out" in output
    monkeypatch.setattr(
        sys, "argv", ["ascend-server", "--home", str(account_home), "user-list"]
    )
    main()
    users = json.loads(capsys.readouterr().out)
    assert [row["username"] for row in users] == ["alice", "bob"]
