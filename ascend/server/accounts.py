"""Optional account controls; the default single-user dashboard does not mount them."""

import hashlib
import threading
import time
from collections import deque

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from ascend.server import auth


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)


class LoginThrottle:
    """Bound expensive login checks per process without storing raw identities."""

    def __init__(self):
        self.attempts = {}
        self.lock = threading.Lock()

    def check(self, host, username):
        now = time.monotonic()
        identity = hashlib.sha256(
            (host + "\0" + username.casefold()).encode()
        ).hexdigest()
        source = hashlib.sha256(host.encode()).hexdigest()
        with self.lock:
            for key in list(self.attempts):
                values = self.attempts[key]
                while values and values[0] <= now - 900:
                    values.popleft()
                if not values:
                    del self.attempts[key]
            keys = [("account:" + identity, 12), ("source:" + source, 100)]
            if any(len(self.attempts.get(key, ())) >= limit for key, limit in keys):
                raise HTTPException(
                    429,
                    "Too many sign-in attempts. Try again in 15 minutes.",
                    headers={"Retry-After": "900"},
                )
            # Prevent unbounded metadata even if many source addresses reach one worker.
            if len(self.attempts) >= 4096:
                raise HTTPException(
                    429,
                    "Sign-in is busy. Try again shortly.",
                    headers={"Retry-After": "60"},
                )
            for key, _ in keys:
                self.attempts.setdefault(key, deque()).append(now)
        return "account:" + identity

    def succeeded(self, identity):
        with self.lock:
            self.attempts.pop(identity, None)


def bearer(request):
    header = request.headers.get("authorization", "")
    return header[7:] if header.startswith("Bearer ") else ""


def mount(app, tracker, enabled):
    if not enabled:
        return
    dependency = Depends(tracker)
    password_throttle = LoginThrottle()

    @app.get("/api/account/security")
    def security(request: Request, t=dependency):
        return {
            "sessions": auth.sessions(t.db, t.db.user_id, bearer(request)),
            "session_lifetime_days": auth.SESSION_LIFETIME.days,
            "max_sessions": auth.MAX_SESSIONS,
            "provisioning": "operator",
        }

    @app.post("/api/account/password")
    def password(body: PasswordChange, request: Request, t=dependency):
        identity = password_throttle.check(
            request.client.host if request.client else "unknown",
            "password:" + str(t.db.user_id),
        )
        token = auth.change_password(
            t.db, t.db.user_id, body.current_password, body.new_password
        )
        password_throttle.succeeded(identity)
        return {"changed": True, "token": token, "other_sessions_revoked": True}

    @app.post("/api/account/sessions/revoke-others")
    def revoke_others(request: Request, t=dependency):
        return {
            "revoked": auth.revoke_other_sessions(t.db, t.db.user_id, bearer(request))
        }

    @app.delete("/api/account/sessions/{session_id}")
    def revoke(session_id: str, request: Request, t=dependency):
        own = next(
            (
                row
                for row in auth.sessions(t.db, t.db.user_id, bearer(request))
                if row["id"] == session_id
            ),
            None,
        )
        if own is None or not auth.revoke_session(t.db, t.db.user_id, session_id):
            raise HTTPException(404, "Session not found")
        return {"revoked": True, "logged_out": own["current"]}
