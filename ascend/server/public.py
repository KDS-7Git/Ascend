"""Public discovery and opt-in account registration/recovery.

Only bundled teaching metadata is published; private packs and learner state
are never consulted by the public catalog.
"""

import re
from functools import lru_cache
from zoneinfo import available_timezones

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from ascend.engine.packs import parse_pack
from ascend.registry import bundled_pack_path, registry_entries
from ascend.server import auth
from ascend.server.accounts import LoginThrottle
from ascend.storage import Database


class Registration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=12, max_length=1024)
    timezone: str = Field(default="UTC", min_length=1, max_length=100)
    label: str = Field(default="Browser", min_length=1, max_length=80)


class Recovery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=40)
    recovery_code: str = Field(min_length=1, max_length=120)
    new_password: str = Field(min_length=12, max_length=1024)


@lru_cache(maxsize=1)
def catalog():
    result = []
    for entry in registry_entries():
        pack = parse_pack(bundled_pack_path(entry["id"]).read_text())
        first = next(
            (node for node in pack.nodes if node.level == pack.levels[0].id), None
        )
        result.append(
            {
                "id": entry["id"],
                "title": entry["title"],
                "category": entry.get("category", "Projects"),
                "description": entry.get("description")
                or (first.preview or first.brief if first else ""),
                "aliases": entry.get("aliases", []),
                "entry": entry.get("entry") or entry.get("prerequisite_summary", ""),
                "limits": entry.get("limits", ""),
                "main_levels": sum(level.lane == "main" for level in pack.levels),
                "nodes": len(pack.nodes),
                "track_order": entry.get("track_order"),
                "reviewed": pack.reviewed,
                "version": pack.version,
            }
        )
    return result


def track_detail(track_id):
    summary = next((item for item in catalog() if item["id"] == track_id), None)
    if summary is None:
        raise HTTPException(404, "Track not found")
    pack = parse_pack(bundled_pack_path(track_id).read_text())
    return {
        **summary,
        "levels": [
            {
                "id": level.id,
                "title": level.title,
                "lane": level.lane,
                "challenges": [
                    {"title": node.title, "preview": node.preview or node.brief}
                    for node in pack.nodes
                    if node.level == level.id
                ],
            }
            for level in pack.levels
        ],
    }


def mount(app, home, auth_mode, registration, account_management):
    recovery = auth_mode == "multi" and (registration or account_management)

    @app.get("/api/site")
    def site():
        return {
            "auth_mode": auth_mode,
            "registration": registration,
            "recovery": recovery,
            "account_management": account_management,
            "password_min_length": 12,
            "session_lifetime_days": auth.SESSION_LIFETIME.days,
            "timezones": sorted(available_timezones()),
        }

    @app.get("/api/catalog")
    def public_catalog():
        tracks = catalog()
        return {
            "tracks": tracks,
            "categories": sorted({item["category"] for item in tracks}),
        }

    @app.get("/api/catalog/{track_id}")
    def public_track(track_id: str):
        return track_detail(track_id)

    if registration:
        registration_throttle = LoginThrottle()

        @app.post("/api/register", status_code=201)
        def register(body: Registration, request: Request):
            registration_throttle.check(
                request.client.host if request.client else "unknown", "registration"
            )
            db = Database(home)
            try:
                try:
                    return auth.register(
                        db, body.username, body.password, body.timezone, body.label
                    )
                except ValueError as error:
                    if str(error) == "That username is already in use":
                        raise HTTPException(409, str(error)) from None
                    raise
            finally:
                db.close()

    if recovery:
        recovery_throttle = LoginThrottle()

        @app.post("/api/recover")
        def recover(body: Recovery, request: Request):
            identity = recovery_throttle.check(
                request.client.host if request.client else "unknown", body.username
            )
            db = Database(home)
            try:
                code = auth.recover_password(
                    db, body.username, body.recovery_code, body.new_password
                )
                recovery_throttle.succeeded(identity)
                return {"recovered": True, "recovery_code": code}
            finally:
                db.close()


def mount_pages(app, web):
    def landing():
        return FileResponse(web / "landing.html")

    def authentication():
        return FileResponse(web / "auth.html")

    def workspace():
        return FileResponse(web / "index.html")

    for path in ("/", "/welcome", "/tracks", "/how-it-works", "/privacy"):
        app.add_api_route(
            path, landing, methods=["GET", "HEAD"], include_in_schema=False
        )
    for path in ("/auth", "/login", "/signup"):
        app.add_api_route(
            path, authentication, methods=["GET", "HEAD"], include_in_schema=False
        )
    for path in ("/app", "/app/"):
        app.add_api_route(
            path, workspace, methods=["GET", "HEAD"], include_in_schema=False
        )

    @app.get("/tracks/{track_id}", include_in_schema=False)
    def track_page(track_id: str):
        known = re.fullmatch(r"[a-z0-9-]+", track_id) and any(
            item["id"] == track_id for item in catalog()
        )
        return FileResponse(web / "landing.html", status_code=200 if known else 404)
