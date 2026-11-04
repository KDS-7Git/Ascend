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
from ascend import challenge_work
from ascend.cli import execute, parser
from ascend.nudge import NudgeRunner
from ascend.registry import registry_entries
from ascend.server.auth import authenticate, login
from ascend.server import presentation
from ascend.storage import Database, default_home


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Model):
    username: str = Field(max_length=100)
    password: str = Field(max_length=1024)
    label: str = Field(default="CLI or browser", min_length=1, max_length=80)


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


class ChallengeNotes(Model):
    learned: str = Field(max_length=10000)
    next_step: str = Field(max_length=4000)
    revision: int = Field(ge=0, strict=True)
    log_progress: bool = False


class CompleteChallenge(Model):
    revision: int = Field(ge=0, strict=True)


class PracticeAgain(Model):
    minutes: int | None = Field(default=None, ge=1, le=1440, strict=True)


class ActivityStart(Model):
    end_scored: bool = False
    deliberate: bool = False


class ActivityAction(Model):
    data: dict = Field(default_factory=dict)
    learned: str | None = Field(default=None, max_length=10000)
    next_step: str | None = Field(default=None, max_length=10000)
    minutes: int | None = Field(default=None, strict=True)
    end_scored: bool = False
    reset: bool = False
    fault: bool = False
    blank: bool = False
    rule: str | None = None
    pause: bool = True
    step: int = Field(default=0, strict=True)
    status: str = "active"


class LabAttemptStart(Model):
    recipe_id: str = Field(max_length=100, pattern=r"^[a-z0-9-]+$")
    offline: bool = Field(default=False, strict=True)
    case_key: int | None = Field(default=None, strict=True, ge=0, le=65535)


class LabAttemptToken(Model):
    nonce: str = Field(min_length=64, max_length=64)


class LabSubmission(LabAttemptToken):
    recipe_version: str = Field(max_length=100)
    checker_version: str = Field(max_length=100)
    fixture_id: str = Field(max_length=100)
    answers: dict | None = None
    report: dict | None = None
    submission: dict | None = None


def create_app(home=None, auth_mode=None, scheduler=True, account_management=None):
    home = Path(home or default_home())
    auth_mode = auth_mode or os.environ.get("AUTH_MODE", "single")
    if auth_mode not in {"single", "multi"}:
        raise ValueError("AUTH_MODE must be single or multi")
    from ascend.server import accounts

    if account_management is None:
        account_management = os.environ.get("ASCEND_ACCOUNT_MANAGEMENT") == "1"
    account_management = bool(account_management and auth_mode == "multi")
    login_throttle = accounts.LoginThrottle()
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
    from ascend.server.lab_runner import RunnerClient

    app.state.lab_runner = RunnerClient()

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
        if (
            request.url.path.startswith(("/api/lab-attempts", "/api/hosted-labs"))
            and request.method == "POST"
        ):
            # Bound the wire body too, including chunked requests without Content-Length.
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > 1_048_576:
                    return JSONResponse(
                        {"detail": "Lab submission exceeds 1 MiB"}, status_code=413
                    )
                body.extend(chunk)
            request._body = bytes(body)
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

    @app.exception_handler(challenge_work.RevisionConflict)
    async def note_conflict(request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

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
        return {
            "status": "ok",
            "auth_mode": auth_mode,
            "account_management": account_management,
        }

    @app.post("/api/login")
    def sign_in(body: Login, request: Request):
        if auth_mode != "multi":
            raise HTTPException(404, "Sign-in is not enabled for this local workspace")
        identity = login_throttle.check(
            request.client.host if request.client else "unknown", body.username
        )
        db = Database(home)
        try:
            try:
                token = login(db, body.username, body.password, body.label)
            except ValueError:
                raise HTTPException(401, "Invalid username or password") from None
            login_throttle.succeeded(identity)
            return {"token": token}
        finally:
            db.close()

    @app.get("/api/account")
    def account(t=Depends(tracker)):
        row = t.db.connection.execute(
            "SELECT id,username,timezone FROM users WHERE id=?", (t.db.user_id,)
        ).fetchone()
        return {
            **dict(row),
            "auth_mode": auth_mode,
            "account_management": account_management,
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

    accounts.mount(app, tracker, account_management)

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
        return presentation.overview(t, t.overview(minutes))

    @app.get("/api/lab-catalog")
    def lab_catalog(
        track: str | None = None,
        level: str | None = None,
        location: str | None = None,
        search: str | None = None,
        t=Depends(tracker),
    ):
        from ascend.local_labs.catalog import catalog

        return catalog(track=track, level=level, location=location, search=search)

    @app.get("/api/lab-attempts")
    def lab_attempts(t=Depends(tracker)):
        from ascend.local_labs.attempts import Attempts

        return Attempts(t).history()

    @app.post("/api/lab-attempts")
    def lab_attempt_start(body: LabAttemptStart, t=Depends(tracker)):
        from ascend.local_labs.attempts import Attempts

        return Attempts(t).create(
            body.recipe_id, offline=body.offline, case_key=body.case_key
        )

    @app.get("/api/lab-attempts/{attempt_id}")
    def lab_attempt(attempt_id: str, t=Depends(tracker)):
        from ascend.local_labs.attempts import Attempts

        return Attempts(t).view(attempt_id)

    @app.post("/api/lab-attempts/{attempt_id}/ready")
    def lab_attempt_ready(attempt_id: str, body: LabAttemptToken, t=Depends(tracker)):
        from ascend.local_labs.attempts import Attempts

        return Attempts(t).ready(attempt_id, body.nonce)

    @app.post("/api/lab-attempts/{attempt_id}/abandon")
    def lab_attempt_abandon(attempt_id: str, body: LabAttemptToken, t=Depends(tracker)):
        from ascend.local_labs.attempts import Attempts

        return Attempts(t).abandon(attempt_id, body.nonce)

    @app.post("/api/lab-attempts/{attempt_id}/submit")
    def lab_attempt_submit(attempt_id: str, body: LabSubmission, t=Depends(tracker)):
        from ascend.local_labs.attempts import Attempts

        return Attempts(t).submit(attempt_id, body.model_dump(exclude_none=True))

    @app.get("/api/lab-catalog/{lab_id}")
    def lab_catalog_detail(lab_id: str, t=Depends(tracker)):
        from ascend.local_labs.catalog import detail

        return detail(lab_id)

    @app.get("/api/hosted-labs/capabilities")
    def hosted_capabilities(t=Depends(tracker)):
        return app.state.lab_runner.capabilities()

    @app.get("/api/hosted-labs/runs")
    def hosted_runs(t=Depends(tracker)):
        return app.state.lab_runner.runs(t)

    @app.post("/api/hosted-labs/runs")
    def hosted_start(body: LabAttemptStart, t=Depends(tracker)):
        return app.state.lab_runner.action(
            t, "start", data={"recipe_id": body.recipe_id}
        )

    from ascend.local_labs.runner_protocol import Action as HostedAction

    @app.post("/api/hosted-labs/runs/{run_id}/{action}")
    def hosted_action(run_id: str, action: str, body: HostedAction, t=Depends(tracker)):
        from ascend.local_labs.runner_protocol import ACTIONS

        if action not in ACTIONS - {"start"}:
            raise HTTPException(404, "Unknown server lab action")
        return app.state.lab_runner.action(
            t, action, run_id, body.model_dump(exclude_none=True)
        )

    @app.get("/api/hosted-labs/runs/{run_id}/files")
    def hosted_file(run_id: str, name: str, t=Depends(tracker)):
        return app.state.lab_runner.file(t, run_id, name)

    @app.get("/api/playground")
    def activities(
        kind: str | None = None,
        minutes: int | None = None,
        topic: str | None = None,
        difficulty: str | None = None,
        environment: str | None = None,
        progress: str | None = None,
        format: str | None = None,
        search: str = "",
        bookmarked: bool = False,
        domain: str | None = None,
        t=Depends(tracker),
    ):
        return t.playground.list(
            kind,
            minutes,
            topic,
            difficulty,
            environment,
            progress,
            format,
            search,
            bookmarked,
            domain,
        )

    @app.get("/api/playground/recommendations")
    def practice(
        minutes: int = 10,
        exclude: str = "",
        kind: str = "quick",
        topic: str | None = None,
        difficulty: str | None = None,
        environment: str | None = None,
        progress: str | None = None,
        format: str | None = None,
        search: str = "",
        bookmarked: bool = False,
        domain: str | None = None,
        t=Depends(tracker),
    ):
        return t.playground.recommendations(
            minutes,
            exclude.split(","),
            kind=kind,
            topic=topic,
            difficulty=difficulty,
            environment=environment,
            progress=progress,
            format=format,
            search=search,
            bookmarked=bookmarked,
            domain=domain,
        )

    @app.get("/api/playground/history")
    def activity_history(t=Depends(tracker)):
        return t.playground.history()

    @app.get("/api/playground/insights")
    def activity_insights(t=Depends(tracker)):
        return t.playground.insights()

    @app.post("/api/playground/selection")
    def activity_selection(body: ActivityAction, t=Depends(tracker)):
        return t.playground.observe_selection(body.data)

    @app.get("/api/playground/activities/{activity_id}")
    def activity_detail(activity_id: str, t=Depends(tracker)):
        return t.playground.detail(activity_id)

    @app.post("/api/playground/activities/{activity_id}/start")
    def activity_start(activity_id: str, body: ActivityStart, t=Depends(tracker)):
        return t.playground.start(activity_id, body.end_scored, body.deliberate)

    @app.post("/api/playground/activities/{activity_id}/bookmark")
    def activity_bookmark(activity_id: str, enabled: bool = True, t=Depends(tracker)):
        return t.playground.bookmark(activity_id, enabled)

    @app.get("/api/playground/runs/{run_id}")
    def activity_run(run_id: str, t=Depends(tracker)):
        return t.playground.view(run_id)

    @app.post("/api/playground/runs/{run_id}/{action}")
    def activity_action(
        run_id: str, action: str, body: ActivityAction, t=Depends(tracker)
    ):
        p = t.playground
        if action == "feedback":
            return p.feedback(run_id, body.data)
        if action == "returned":
            return p.event(run_id, "returned")
        if action == "tour":
            return p.tour(run_id, body.step, body.status)
        if action == "resume":
            return p.resume(run_id, body.end_scored)
        if action == "save":
            return p.save(run_id, body.data, body.pause)
        if action == "submit":
            return p.submit(run_id, body.data, body.learned, body.next_step)
        if action == "log":
            return p.log(run_id, body.learned, body.next_step, body.minutes)
        if action == "experiment":
            return p.experiment(run_id, body.data)
        if action == "copy":
            return p.copy(run_id, body.reset, body.fault, body.blank, body.end_scored)
        if action == "repair":
            return p.repair(run_id, body.rule)
        if action in {"hint", "end", "reveal"}:
            return getattr(p, action)(run_id)
        raise ValueError("Unknown activity action")

    @app.get("/api/levels")
    def levels(pack: str | None = None, t=Depends(tracker)):
        if not pack and not (t.active_mission() or {}).get("pack_id"):
            return []
        return presentation.levels(t, t.levels(pack))

    @app.post("/api/entries")
    def entry(body: Entry, t=Depends(tracker)):
        return t.log(**body.model_dump())

    @app.get("/api/challenges/{reference}")
    def challenge(reference: str, t=Depends(tracker)):
        from ascend import labs, timing

        pack, node = t.resolve_node(reference)
        level = next(lv for lv in t.levels(pack.id) if lv["id"] == node.level)
        public_node = next(n for n in level["nodes"] if n["id"] == node.id)
        sessions = t.db.rows(
            "task_sessions", "pack_id=? AND node_id=?", (pack.id, node.id)
        )
        public_node = (
            {
                **presentation.workspace(public_node),
                "details_available": True,
                "has_attempt": True,
            }
            if sessions or public_node.get("status") == "done"
            else presentation.preview(public_node)
        )
        exercise, exercise_error = None, None
        if node.verify.get("type") == "lab":
            try:
                exercise = labs.current(t, reference)
            except ValueError as error:
                exercise_error = str(error)
        return {
            "node": public_node,
            "level": {
                "id": level["id"],
                "title": level["title"],
                "open": level["open"],
            },
            "session": timing.describe(t, sessions[0]) if sessions else None,
            "exercise": exercise,
            "exercise_error": exercise_error,
            "work": challenge_work.work(t, pack, node)
            if public_node["details_available"]
            else None,
        }

    @app.post("/api/challenges/{reference}/notes")
    def save_challenge_notes(reference: str, body: ChallengeNotes, t=Depends(tracker)):
        return challenge_work.save(t, reference, **body.model_dump())

    @app.post("/api/challenges/{reference}/complete")
    def complete_challenge(reference: str, body: CompleteChallenge, t=Depends(tracker)):
        return challenge_work.complete(t, reference, body.revision)

    @app.post("/api/challenges/{reference}/practice")
    def practice_again(reference: str, body: PracticeAgain, t=Depends(tracker)):
        return challenge_work.retry(t, reference, body.minutes)

    @app.post("/api/challenges/{reference}/check")
    def check_challenge(reference: str, t=Depends(tracker)):
        pack, node = t.resolve_node(reference)
        challenge_work.require_started(t, pack, node)
        result = t.verify_node(pack, node)
        return {"ok": result.ok, "summary": result.summary}

    @app.post("/api/challenges/{reference}/evidence")
    async def upload_evidence(
        reference: str, file: UploadFile = File(...), t=Depends(tracker)
    ):
        content = await file.read(challenge_work.MAX_UPLOAD + 1)
        if len(content) > challenge_work.MAX_UPLOAD:
            raise HTTPException(413, "Choose an evidence file up to 8 MB")
        return challenge_work.upload(t, reference, file.filename, content)

    @app.get("/api/challenges/{reference}/evidence")
    def download_evidence(reference: str, t=Depends(tracker)):
        from urllib.parse import quote

        pack, node = t.resolve_node(reference)
        manifest = t.db.setting(challenge_work.key("attachment", pack, node))
        if not manifest:
            raise HTTPException(404, "No saved attachment")
        content = challenge_work.read_artifact(t, pack, node, manifest)
        return Response(
            content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename*=UTF-8''"
                + quote(manifest["name"]),
            },
        )

    @app.get("/api/entries")
    def entries(t=Depends(tracker)):
        return t.entries()

    @app.get("/api/nodes/{reference}/checkpoints")
    def checkpoint_list(reference: str, t=Depends(tracker)):
        from ascend import checkpoints

        return checkpoints.list_for(t, reference)

    @app.post("/api/nodes/{reference}/checkpoints/{checkpoint_id}")
    def checkpoint_log(
        reference: str, checkpoint_id: str, body: ActivityAction, t=Depends(tracker)
    ):
        from ascend import checkpoints

        return checkpoints.record(
            t, reference, checkpoint_id, body.learned, body.minutes
        )

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
        catalog = {entry["id"]: entry for entry in registry_entries()}
        result = []
        for row in t.db.rows("packs"):
            try:
                loaded = t.pack(row["id"])
                metadata = {
                    "title": loaded.title,
                    "kind": loaded.kind,
                    "levels": sum(level.lane == "main" for level in loaded.levels),
                    "nodes": len(loaded.nodes),
                    "valid": True,
                }
                # Loading edited content may revoke its old review/trust state.
                row = t.db.rows("packs", "id=?", (row["id"],))[0]
            except (ValueError, OSError):
                metadata = {
                    "title": row["id"].replace("-", " ").title(),
                    "valid": False,
                }
            result.append(
                {
                    k: v
                    for k, v in row.items()
                    if k not in {"path", "fingerprint", "user_id"}
                }
                | metadata
                | {
                    key: catalog.get(row["id"], {}).get(key, default)
                    for key, default in (
                        ("category", "Projects" if row["id"] in catalog else "Custom"),
                        ("domain", None),
                        ("track_order", None),
                        ("recommended_after", []),
                        ("description", ""),
                        ("entry", ""),
                        ("prerequisite_summary", ""),
                    )
                }
            )
        return result

    @app.get("/api/packs/{pack_id}")
    def pack(pack_id: str, t=Depends(tracker)):
        if not t.db.rows("packs", "id=?", (pack_id,)):
            raise HTTPException(404, "Pack not found")
        result = asdict(t.pack(pack_id))
        from ascend.local_labs.catalog import catalog

        result["lab_references"] = catalog(track=pack_id)
        started = presentation.attempts(t)
        result["nodes"] = [
            presentation.preview({**node, "pack_id": pack_id}, started)
            for node in result["nodes"]
        ]
        return result

    @app.get("/api/stats")
    def stats(t=Depends(tracker)):
        from ascend.rewards import practice_summary

        return {**t.stats(), "practice_points": practice_summary(t)}

    @app.get("/api/rewards")
    def reward_summary(t=Depends(tracker)):
        from ascend.rewards import summary

        return summary(t)

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
        if args.command in {"login", "install-nudge", "nudge", "local-lab"}:
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
        result = execute(t, args)
        if args.command in {None, "today"}:
            return presentation.overview(t, result)
        if args.command == "levels":
            return presentation.levels(t, result)
        return result

    web = Path(__file__).resolve().parents[2] / "web"
    if not web.is_dir():
        web = Path(__file__).resolve().parents[1] / "web"
    if web.is_dir():
        app.mount("/", StaticFiles(directory=web, html=True), name="web")
    return app
