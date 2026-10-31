import base64
import json
from unittest.mock import patch, Mock

import pytest
from fastapi.testclient import TestClient

from ascend.server.app import create_app
from ascend.nudge.channels import telegram, webpush
from ascend.server.telegram import process_update


def test_telegram_post_has_inline_action(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    with patch("ascend.nudge.channels.telegram.urlopen") as opener:
        opener.return_value.__enter__.return_value.read.return_value = b'{"ok":true}'
        telegram.send("A small step is enough")
        data = json.loads(opener.call_args.args[0].data)
        assert data["chat_id"] == "42"
        assert data["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "ascend-log"


def test_telegram_requires_real_learning_and_deduplicates(installed):
    callback = {"update_id": 1, "callback_query": {"id": "click", "data": "ascend-log", "message": {"chat": {"id": 42}}}}
    assert "What" in process_update(installed, callback)["reply"]
    short = {"update_id": 2, "message": {"chat": {"id": 42}, "text": "too short"}}
    assert "20" in process_update(installed, short)["reply"]
    learned = {"update_id": 3, "message": {"chat": {"id": 42}, "text": "I explained the whole example in my own words"}}
    assert "next" in process_update(installed, learned)["reply"].lower()
    next_step = {"update_id": 4, "message": {"chat": {"id": 42}, "text": "Try the next exercise"}}
    assert process_update(installed, next_step)["logged"]
    assert not process_update(installed, next_step).get("logged")
    assert len(installed.entries()) == 1


def test_telegram_webhook_auth_and_unknown_chat(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "a-secret-for-tests")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    with TestClient(create_app(tmp_path, scheduler=False)) as client:
        assert client.post("/api/telegram/webhook", json={}).status_code == 401
        result = client.post("/api/telegram/webhook", headers={"X-Telegram-Bot-Api-Secret-Token": "a-secret-for-tests"}, json={"update_id": 1, "message": {"chat": {"id": 99}, "text": "hello"}})
        assert result.status_code == 200 and result.json()["ignored"]


def test_missing_telegram_credentials_falls_back_once(installed, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    installed.configure("nudge-channel", "telegram")
    from ascend.nudge import NudgeRunner
    with patch("ascend.nudge.send") as send:
        with pytest.warns(RuntimeWarning, match="Telegram"):
            NudgeRunner(installed).run(test=True)
        NudgeRunner(installed).run(test=True)
        assert send.call_count == 2


def test_public_streak_is_opt_in_and_reveals_no_entries(tmp_path):
    with TestClient(create_app(tmp_path, scheduler=False)) as client:
        assert client.get("/api/public/local/streak").status_code == 404
        assert client.post("/api/command", json={"argv": ["config", "public-streak", "true"]}).status_code == 200
        result = client.get("/api/public/local/streak").json()
        assert set(result) == {"username", "current_streak", "best_streak", "today_logged"}
        badge = client.get("/api/public/local/badge.svg")
        assert badge.status_code == 200 and "image/svg+xml" in badge.headers["content-type"]


def test_push_keys_subscription_and_real_encryption(tmp_path, monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    private = tmp_path / "vapid.pem"
    public = webpush.generate_keys(private)
    assert len(base64.urlsafe_b64decode(public + "==")) == 65
    assert private.stat().st_mode & 0o777 == 0o600
    monkeypatch.setenv("VAPID_PRIVATE_KEY", str(private))
    monkeypatch.setenv("VAPID_SUBJECT", "mailto:test@example.org")
    key = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    b64 = lambda data: base64.urlsafe_b64encode(data).decode().rstrip("=")
    subscription = {"endpoint": "https://fcm.googleapis.com/fcm/send/test", "keys": {"p256dh": b64(key), "auth": b64(b"1234567890123456")}}
    with TestClient(create_app(tmp_path, scheduler=False)) as client:
        assert client.get("/api/push/key").json()["public_key"] == public
        assert client.post("/api/push/subscriptions", json=subscription).status_code == 200
        bad = {**subscription, "endpoint": "http://127.0.0.1/internal"}
        assert client.post("/api/push/subscriptions", json=bad).status_code == 400
    from ascend.storage import Database
    db = Database(tmp_path)
    with patch("requests.post") as post:
        post.return_value.status_code = 201
        webpush.send_to_user(db, "A private reminder")
        assert post.called
        assert b"A private reminder" not in post.call_args.kwargs["data"]
        assert "authorization" in {k.lower() for k in post.call_args.kwargs["headers"]}
    db.close()
