"""Authenticated control-plane client; the web app has no provider privileges."""

import hashlib
import hmac
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener

from fastapi import HTTPException

from ascend.local_labs.runner_protocol import NoRedirect


class RunnerClient:
    def __init__(self, url=None, key=None, site=None):
        self.url = (
            url if url is not None else os.environ.get("ASCEND_RUNNER_URL", "")
        ).rstrip("/")
        self.key = key if key is not None else os.environ.get("ASCEND_RUNNER_KEY", "")
        self.site = (
            site if site is not None else os.environ.get("ASCEND_RUNNER_SITE_ID", "")
        )
        self.configured = bool(self.url)
        if self.configured:
            parsed = urlsplit(self.url)
            if (
                parsed.scheme not in {"https", "http"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
                or (
                    parsed.scheme == "http"
                    and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                )
            ):
                raise ValueError("Runner URL needs HTTPS, or HTTP on loopback")
            if len(self.key) < 32 or not self.site or len(self.site) > 100:
                raise ValueError(
                    "Set a runner key of at least 32 characters and a stable ASCEND_RUNNER_SITE_ID"
                )

    def scope(self, tracker):
        return hmac.new(
            self.key.encode(),
            f"{self.site}/{tracker.db.user_id}".encode(),
            hashlib.sha256,
        ).hexdigest()

    def request(self, path, data=None):
        if not self.configured:
            raise HTTPException(503, "The server lab runner is not connected")
        req = Request(
            self.url + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={
                "Authorization": "Bearer " + self.key,
                "Content-Type": "application/json",
            },
        )
        try:
            with build_opener(NoRedirect()).open(req, timeout=12) as response:
                body = response.read(1048577)
                if len(body) > 1048576:
                    raise ValueError("Runner response exceeds its bound")
                return json.loads(body)
        except HTTPError as error:
            if error.code == 400:
                try:
                    detail = json.loads(error.read(8192)).get(
                        "detail", "Invalid runner request"
                    )
                except (ValueError, UnicodeError):
                    detail = "Invalid runner request"
                raise HTTPException(400, detail) from None
            raise HTTPException(
                503,
                "The lab runner could not accept this request; check its connection and configuration",
            ) from None
        except (URLError, OSError, ValueError):
            raise HTTPException(
                503, "The server lab runner is not responding; retry when it reconnects"
            ) from None

    def capabilities(self):
        return (
            self.request("/v1/capabilities")
            if self.configured
            else {"configured": False, "recipes": []}
        )

    def runs(self, tracker):
        return self.request(f"/v1/accounts/{self.scope(tracker)}/runs")

    def action(self, tracker, action, run_id=None, data=None):
        path = f"/v1/accounts/{self.scope(tracker)}/runs"
        if action != "start":
            if not re.fullmatch(r"[a-f0-9]{32}", run_id or ""):
                raise ValueError("Invalid run ID")
            path += f"/{run_id}/{action}"
        return self.request(path, data or {})

    def file(self, tracker, run_id, name):
        if not re.fullmatch(r"[a-f0-9]{32}", run_id or ""):
            raise ValueError("Invalid run ID")
        return self.request(
            f"/v1/accounts/{self.scope(tracker)}/runs/{run_id}/files?"
            + urlencode({"name": name})
        )
