from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ascend.server.app import create_app


def test_stats_include_minutes_per_level(installed):
    installed.log("I tested and explained the first task", "Continue", minutes=17)
    assert installed.stats()["minutes_by_level"][0]["minutes"] == 17


def test_config_missing_value_is_actionable(installed):
    with pytest.raises(ValueError, match="value"): installed.configure("nudge-time", None)


@pytest.mark.parametrize("body", [{"endpoint": 42}, {"endpoint": "https://fcm.googleapis.com/test", "keys": None}])
def test_malformed_push_input_returns_400(tmp_path, body):
    with TestClient(create_app(tmp_path, scheduler=False)) as client:
        assert client.post("/api/push/subscriptions", json=body).status_code == 400


def test_cross_origin_write_is_rejected(tmp_path):
    with TestClient(create_app(tmp_path, scheduler=False)) as client:
        response = client.post("/api/entries", headers={"Origin": "https://unrelated.example"}, json={"learned": "A valid note from an unrelated website", "next_step": "Continue"})
        assert response.status_code == 403


def test_undo_preserves_later_manual_node_change(installed):
    installed.log("I finished this exercise and can explain it", "Continue", complete=True)
    installed.mark("one", "skipped", "Changed my decision after logging")
    installed.undo()
    assert installed.states("test-pack")["one"]["status"] == "skipped"


def test_default_view_stays_six_lines_for_multiline_notes(installed):
    import argparse
    from ascend.cli import render
    installed.log("I wrote an explanation across several lines", "First line\nSecond line\nThird line")
    args = argparse.Namespace(json=False, command=None)
    assert len(render(args, installed.overview()).splitlines()) <= 6


def test_http_verifier_against_live_server():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from ascend.verifiers.http import verify
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self): self.send_response(204); self.end_headers()
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        assert verify({"url": f"http://127.0.0.1:{server.server_port}", "status": 204}, {}).ok
        assert not verify({"url": "file:///etc/passwd"}, {}).ok
    finally: server.shutdown(); server.server_close(); thread.join()


def test_git_verifier_uses_commit_time(tmp_path):
    from ascend.verifiers.git import verify
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=Test", "-c", "user.email=test@example.org", "commit", "--allow-empty", "-m", "Finish a working example"], check=True, capture_output=True)
    result = verify({"path": str(tmp_path), "pattern": "working example"}, {})
    assert result.ok and result.evidence_time.tzinfo is not None
    assert not verify({"path": str(tmp_path), "pattern": "not in any commit"}, {}).ok


def test_expired_push_subscriptions_removed_during_nudge(installed, now, monkeypatch):
    from ascend.nudge import NudgeRunner
    from pywebpush import WebPushException
    from unittest.mock import Mock
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "/unused/key.pem")
    monkeypatch.setenv("VAPID_SUBJECT", "mailto:test@example.org")
    installed.configure("nudge-channel", "webpush")
    installed.clock = lambda: now.replace(hour=22)
    installed.db.insert("push_subscriptions", endpoint="https://fcm.googleapis.com/expired", subscription=json.dumps({"endpoint": "https://fcm.googleapis.com/expired"}), created_at=now.isoformat())
    response = Mock(status_code=410)
    with patch("pywebpush.webpush", side_effect=WebPushException("Expired", response=response)):
        assert not NudgeRunner(installed).run()["sent"]
    assert installed.db.rows("push_subscriptions") == []
