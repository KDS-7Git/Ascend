import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict
import logging
import hashlib
import hmac
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from ascend.application import Tracker
from ascend.cli import execute, parser
from ascend.nudge import NudgeRunner
from ascend.server.auth import authenticate, login
from ascend.storage import Database, default_home


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Model):
    username: str = Field(max_length=100)
    password: str = Field(max_length=1024)


class Entry(Model):
    learned: str = Field(max_length=10000)
    next_step: str = Field(max_length=10000)
    node_id: str | None = None
    proof: str | None = Field(default=None, max_length=4000)
    minutes: int | None = Field(default=None, strict=True)
    complete: bool = False
    force: str | None = None
    mission_id: int | None = None


class Mark(Model):
    status: str
    note: str | None = None


class Command(Model):
    argv: list[str] = Field(max_length=100)
    pack_text: str | None = Field(default=None, max_length=2_000_000)


def create_app(home=None, auth_mode=None, scheduler=True):
    home = Path(home or default_home())
    auth_mode = auth_mode or os.environ.get("AUTH_MODE", "single")
    if auth_mode not in {"single", "multi"}:
        raise ValueError("AUTH_MODE must be single or multi")
    Database(home).close()

    def tick():
        db = Database(home)
        try:
            users = [dict(r) for r in db.connection.execute("SELECT * FROM users")]
            for user in users:
                if auth_mode == "single" and user["id"] != 1:
                    continue
                if auth_mode == "multi" and user["id"] == 1:
                    continue
                db.user_id = user["id"]
                if not db.setting("nudge_enabled", False):
                    continue
                if auth_mode == "multi":
                    db.set_setting("timezone", user["timezone"])
                if db.setting("nudge_channel") is None:
                    db.set_setting("nudge_channel", "ntfy")
                try:
                    from ascend import timing

                    task_tracker = Tracker(db)
                    runner = NudgeRunner(task_tracker)
                    timing.reminders(task_tracker, runner.sender)
                    runner.run()
                except (ValueError, OSError):
                    logging.getLogger("ascend.nudge").warning(
                        "Reminder delivery failed for user %s; check channel configuration",
                        user["id"],
                    )
        finally:
            db.close()

    async def nudge_loop():
        while True:
            await asyncio.to_thread(tick)
            await asyncio.sleep(30)

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(nudge_loop()) if scheduler else None
        yield
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="Ascend API", version="0.2.0", lifespan=lifespan)
    app.state.home = home
    app.state.nudge_tick = tick

    @app.middleware("http")
    async def headers(request, call_next):
        origin = request.headers.get("origin")
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and origin
            and urlparse(origin).netloc != request.url.netloc
        ):
            return JSONResponse(
                {"detail": "Cross-origin writes are not allowed"}, status_code=403
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path in {"/docs", "/redoc"}:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "frame-ancestors 'none'; base-uri 'self'"
            )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ValueError)
    async def validation_error(request, error):
        return JSONResponse({"detail": str(error)}, status_code=400)

    @app.exception_handler(sqlite3.IntegrityError)
    async def conflict_error(request, error):
        return JSONResponse(
            {"detail": "This change conflicts with existing data"}, status_code=409
        )

    def tracker(request: Request):
        db = Database(home)
        try:
            if auth_mode == "multi":
                auth = request.headers.get("authorization", "")
                user = authenticate(
                    db, auth[7:] if auth.startswith("Bearer ") else None
                )
                if not user:
                    raise HTTPException(401, "Login required")
                db.user_id = user["id"]
                db.set_setting("timezone", user["timezone"])
            result = Tracker(db)
            result.restricted = (
                auth_mode == "multi" and os.environ.get("ASCEND_ALLOW_CODE") != "1"
            )
            result.server_mode = True
            if db.setting("nudge_channel") is None:
                db.set_setting("nudge_channel", "ntfy")
            yield result
        finally:
            db.close()

    @app.get("/api/health")
    def health():
        return {"status": "ok", "auth_mode": auth_mode}

    @app.post("/api/login")
    def sign_in(body: Login):
        db = Database(home)
        try:
            try:
                token = login(db, body.username, body.password)
            except ValueError:
                raise HTTPException(401, "Invalid username or password") from None
            return {"token": token}
        finally:
            db.close()

    @app.get("/api/account")
    def account(t=Depends(tracker)):
        row = t.db.connection.execute(
            "SELECT username,timezone FROM users WHERE id=?", (t.db.user_id,)
        ).fetchone()
        return {
            **dict(row),
            "auth_mode": auth_mode,
            "settings": {
                r["key"]: t.db.setting(r["key"])
                for r in t.db.rows("settings")
                if r["key"]
                in {
                    "nudge_time",
                    "nudge_channel",
                    "ntfy_topic",
                    "nudge_enabled",
                    "public_streak",
                }
            },
        }

    @app.post("/api/logout")
    def logout(request: Request, t=Depends(tracker)):
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            t.db.connection.execute(
                "DELETE FROM api_tokens WHERE user_id=? AND token=?",
                (t.db.user_id, hashlib.sha256(auth[7:].encode()).hexdigest()),
            )
        return {"logged_out": True}

    @app.get("/api/push/key")
    def push_key(t=Depends(tracker)):
        from ascend.nudge.channels.webpush import public_key

        return {"public_key": public_key()}

    @app.post("/api/push/subscriptions")
    def subscribe(body: dict, t=Depends(tracker)):
        from ascend.nudge.channels.webpush import subscribe

        return subscribe(t.db, body)

    @app.delete("/api/push/subscriptions")
    def unsubscribe(body: dict, t=Depends(tracker)):
        from ascend.nudge.channels.webpush import unsubscribe

        return unsubscribe(t.db, body.get("endpoint", ""))

    def public_stats(username):
        db = Database(home)
        try:
            user = db.connection.execute(
                "SELECT * FROM users WHERE username=?", (username,)
            ).fetchone()
            if not user:
                raise HTTPException(404, "Public streak not enabled")
            db.user_id = user["id"]
            if not db.setting("public_streak", False):
                raise HTTPException(404, "Public streak not enabled")
            if auth_mode == "multi":
                db.set_setting("timezone", user["timezone"])
            stats = Tracker(db).stats()
            return {
                "username": username,
                **{
                    key: stats[key]
                    for key in ("current_streak", "best_streak", "today_logged")
                },
            }
        finally:
            db.close()

    @app.get("/api/public/{username}/streak")
    def public_streak(username: str):
        return public_stats(username)

    @app.get("/api/public/{username}/badge.svg")
    def badge(username: str):
        count = public_stats(username)["current_streak"]
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="180" height="28" role="img" aria-label="Ascend streak: {count} days"><rect width="180" height="28" rx="6" fill="#2f6f5e"/><text x="90" y="19" text-anchor="middle" fill="white" font-family="sans-serif" font-size="12">Ascend · {count} days</text></svg>'
        return Response(svg, media_type="image/svg+xml")

    @app.post("/api/telegram/webhook")
    def telegram_webhook(request: Request, body: dict):
        from ascend.nudge.channels import telegram
        from ascend.server.telegram import process_update

        expected = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
        supplied = request.headers.get("x-telegram-bot-api-secret-token", "")
        if not expected or not hmac.compare_digest(expected, supplied):
            raise HTTPException(401, "Invalid webhook secret")
        message = body.get("message") or body.get("callback_query", {}).get(
            "message", {}
        )
        chat = message.get("chat", {})
        if chat.get("type", "private") != "private":
            return {"ignored": True}
        incoming = str(chat.get("id", ""))
        db = Database(home)
        try:
            users = list(db.connection.execute("SELECT * FROM users"))
            user = next(
                (u for u in users if telegram.chat_id(u["id"]) == incoming), None
            )
            if not user:
                return {"ignored": True}
            if auth_mode == "multi" and user["id"] == 1:
                return {"ignored": True}
            if auth_mode == "single" and user["id"] != 1:
                return {"ignored": True}
            db.user_id = user["id"]
            if auth_mode == "multi":
                db.set_setting("timezone", user["timezone"])
            result = process_update(Tracker(db), body)
            if result.get("reply"):
                telegram.send(result["reply"], user_id=db.user_id, actions=False)
            return result
        finally:
            db.close()

    @app.get("/api/me")
    def me(minutes: int | None = None, t=Depends(tracker)):
        if minutes is not None and minutes <= 0:
            raise ValueError("Minutes must be positive")
        return t.overview(minutes)

    @app.get("/api/levels")
    def levels(pack: str | None = None, t=Depends(tracker)):
        if not pack and not (t.active_mission() or {}).get("pack_id"):
            return []
        return t.levels(pack)

    @app.post("/api/entries")
    def entry(body: Entry, t=Depends(tracker)):
        return t.log(**body.model_dump())

    @app.get("/api/entries")
    def entries(t=Depends(tracker)):
        return t.entries()

    @app.post("/api/nodes/{node_id}/mark")
    def mark(node_id: str, body: Mark, t=Depends(tracker)):
        return t.mark(node_id, body.status, body.note)

    @app.post("/api/packs")
    async def upload(file: UploadFile = File(...), t=Depends(tracker)):
        data = await file.read(2_000_001)
        if len(data) > 2_000_000:
            raise HTTPException(413, "Pack exceeds 2 MB")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Pack must be UTF-8") from None
        return t.install_pack(text)

    @app.get("/api/packs")
    def packs(t=Depends(tracker)):
        return [
            {
                k: v
                for k, v in row.items()
                if k not in {"path", "fingerprint", "user_id"}
            }
            for row in t.db.rows("packs")
        ]

    @app.get("/api/packs/{pack_id}")
    def pack(pack_id: str, t=Depends(tracker)):
        if not t.db.rows("packs", "id=?", (pack_id,)):
            raise HTTPException(404, "Pack not found")
        return asdict(t.pack(pack_id))

    @app.get("/api/stats")
    def stats(t=Depends(tracker)):
        return t.stats()

    @app.get("/api/heatmap")
    def heatmap(t=Depends(tracker)):
        return t.heatmap()

    @app.get("/api/search")
    def search(q: str, t=Depends(tracker)):
        return t.search(q)

    @app.post("/api/command")
    def command(body: Command, t=Depends(tracker)):
        try:
            args = parser().parse_args(body.argv)
        except SystemExit:
            raise ValueError("Invalid command arguments") from None
        if args.command in {"login", "install-nudge", "nudge"}:
            raise ValueError("This command is local-only")
        if args.command == "config" and args.key == "server":
            raise ValueError("Server URL is a client setting")
        if args.command == "pack":
            if args.action == "new":
                raise ValueError("Scaffold packs on the client")
            if args.action in {"install", "lint", "diff", "check-links"}:
                if body.pack_text is None and not re.fullmatch(
                    r"[a-z0-9-]+", args.target
                ):
                    raise ValueError(
                        "Upload pack content; server file paths are not accepted"
                    )
                args.target_text = body.pack_text
        return execute(t, args)

    web = Path(__file__).resolve().parents[2] / "web"
    if not web.is_dir():
        web = Path(__file__).resolve().parents[1] / "web"
    if web.is_dir():
        app.mount("/", StaticFiles(directory=web, html=True), name="web")
    return app
