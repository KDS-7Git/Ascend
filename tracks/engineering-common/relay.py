"""Relay: a small synthetic-data service for Ascend's local engineering labs.

Python 3.11+, standard library only. This teaching HTTP server is not a general
production web server. Bind it deliberately and put an appropriate edge in front.
"""

import argparse
import hmac
import json
import re
import signal
import sqlite3
import threading
import time
import uuid
from contextlib import closing
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

MAX_BODY = 4096
MAX_MESSAGE = 280
SCHEMA = """
CREATE TABLE IF NOT EXISTS updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    idempotency_key TEXT UNIQUE
);
PRAGMA user_version=1;
"""


def initialize_database(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=2)) as db, db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript(SCHEMA)


class RelayServer(ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True
    allow_reuse_address = True

    def __init__(
        self,
        address,
        *,
        data,
        release="v1",
        read_only=False,
        ready_file=None,
        token_file=None,
        workers=8,
        delay_ms=0,
        quiet=False,
    ):
        self.data = Path(data)
        self.release = release
        self.read_only = read_only
        self.ready_file = Path(ready_file) if ready_file else None
        self.token_file = Path(token_file) if token_file else None
        self.delay_ms = delay_ms
        self.quiet = quiet
        self.started_at = time.monotonic()
        self.slots = threading.BoundedSemaphore(workers)
        self.lock = threading.Lock()
        self.active = self.peak = self.requests = self.rejected = 0
        initialize_database(self.data)
        super().__init__(address, RelayHandler)

    def process_request(self, request, client_address):
        request.settimeout(4)
        if not self.slots.acquire(blocking=False):
            with self.lock:
                self.rejected += 1
            body = b'{"error":"capacity","retryable":true}'
            response = (
                b"HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\n"
                b"Content-Type: application/json\r\nRetry-After: 1\r\n"
                + f"Content-Length: {len(body)}\r\n\r\n".encode()
                + body
            )
            try:
                request.sendall(response)
            except OSError:
                pass
            self.shutdown_request(request)
            return
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            super().process_request(request, client_address)
        except Exception:
            with self.lock:
                self.active -= 1
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self.lock:
                self.active -= 1
            self.slots.release()

    def readiness(self):
        if self.ready_file:
            try:
                if self.ready_file.read_text().strip() != "ready":
                    return False, "readiness gate is closed"
            except (OSError, UnicodeError):
                return False, "readiness gate is missing or unreadable"
        try:
            with closing(sqlite3.connect(self.data, timeout=0.3)) as db:
                db.execute("SELECT id FROM updates LIMIT 1").fetchone()
        except sqlite3.Error:
            return False, "state store unavailable"
        return True, "ready"


class RelayHandler(BaseHTTPRequestHandler):
    server_version = "RelayLab/1"
    protocol_version = "HTTP/1.0"

    def log_message(self, *_args):
        pass

    def reply(self, status, data, *, content_type="application/json"):
        request_id = self.headers.get("X-Request-ID", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", request_id):
            request_id = uuid.uuid4().hex
        raw = data.encode() if isinstance(data, str) else json.dumps(data).encode()
        with self.server.lock:
            self.server.requests += 1
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Request-ID", request_id)
            self.send_header("X-Relay-Release", self.server.release)
            self.end_headers()
            self.wfile.write(raw)
        except (TimeoutError, BrokenPipeError, ConnectionResetError):
            pass
        if not self.server.quiet:
            print(
                json.dumps(
                    {
                        "at": datetime.now(UTC).isoformat(),
                        "request_id": request_id,
                        "method": self.command,
                        "path": urlsplit(self.path).path,
                        "status": status,
                        "release": self.server.release,
                    }
                ),
                flush=True,
            )

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            self.reply(
                200,
                "<!doctype html><meta charset=utf-8><title>Relay lab</title>"
                "<main><h1>Relay</h1><p>A synthetic-data deployment lab.</p>"
                "<p>Inspect <a href='/version'>release identity</a>, "
                "<a href='/health'>liveness</a>, <a href='/ready'>readiness</a>, "
                "<a href='/api/updates'>saved updates</a> and <a href='/metrics'>metrics</a>.</p>"
                "<p>Use the supplied curl/client examples to post synthetic updates.</p></main>",
                content_type="text/html; charset=utf-8",
            )
        elif path == "/health":
            self.reply(200, {"status": "alive", "release": self.server.release})
        elif path == "/ready":
            ready, reason = self.server.readiness()
            self.reply(
                200 if ready else 503,
                {"ready": ready, "reason": reason, "release": self.server.release},
            )
        elif path == "/version":
            self.reply(
                200,
                {
                    "release": self.server.release,
                    "schema": 1,
                    "read_only": self.server.read_only,
                },
            )
        elif path == "/work":
            time.sleep(self.server.delay_ms / 1000)
            self.reply(
                200,
                {
                    "completed": True,
                    "release": self.server.release,
                    "delay_ms": self.server.delay_ms,
                },
            )
        elif path == "/api/updates":
            try:
                with closing(sqlite3.connect(self.server.data, timeout=0.3)) as db:
                    rows = db.execute(
                        "SELECT id,message,created_at FROM updates ORDER BY id DESC LIMIT 50"
                    ).fetchall()
                self.reply(
                    200,
                    {
                        "updates": [
                            {"id": r[0], "message": r[1], "created_at": r[2]}
                            for r in rows
                        ]
                    },
                )
            except sqlite3.Error:
                self.reply(503, {"error": "state store unavailable"})
        elif path == "/metrics":
            with self.server.lock:
                values = {
                    "relay_http_responses_total": self.server.requests,
                    "relay_connections_active": self.server.active,
                    "relay_connections_peak": self.server.peak,
                    "relay_admission_rejected_total": self.server.rejected,
                }
            values["relay_uptime_seconds"] = round(
                time.monotonic() - self.server.started_at, 3
            )
            self.reply(
                200,
                "".join(f"{name} {value}\n" for name, value in values.items()),
                content_type="text/plain; version=0.0.4; charset=utf-8",
            )
        else:
            self.reply(404, {"error": "unknown endpoint"})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/updates":
            self.reply(404, {"error": "unknown endpoint"})
            return
        if self.server.read_only:
            self.reply(405, {"error": "read-only replica"})
            return
        if self.server.token_file:
            try:
                expected = self.server.token_file.read_text().strip()
            except (OSError, UnicodeError):
                self.reply(503, {"error": "write credential unavailable"})
                return
            received = self.headers.get("Authorization", "")
            if not expected or not hmac.compare_digest(
                received.encode(), ("Bearer " + expected).encode()
            ):
                self.reply(401, {"error": "write credential rejected"})
                return
        lengths = self.headers.get_all("Content-Length", [])
        if (
            self.headers.get("Transfer-Encoding")
            or len(lengths) != 1
            or not lengths[0].isdigit()
        ):
            self.reply(411, {"error": "one Content-Length required"})
            return
        if len(lengths[0]) > 8:
            self.reply(413, {"error": "body must be 1..4096 bytes"})
            return
        length = int(lengths[0])
        if not 0 < length <= MAX_BODY:
            self.reply(413, {"error": "body must be 1..4096 bytes"})
            return
        try:
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("incomplete body")
            value = json.loads(body)
            if not isinstance(value, dict) or set(value) != {"message"}:
                raise ValueError("expected only message")
            message = value["message"]
            if (
                not isinstance(message, str)
                or not 1 <= len(message.strip()) <= MAX_MESSAGE
            ):
                raise ValueError("message must contain 1..280 characters")
            key = self.headers.get("Idempotency-Key")
            if key is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", key):
                raise ValueError("invalid idempotency key")
        except (TimeoutError, ValueError, UnicodeError) as error:
            self.reply(400, {"error": str(error)})
            return
        if not self.server.readiness()[0]:
            self.reply(503, {"error": "not ready for writes"})
            return
        try:
            with closing(sqlite3.connect(self.server.data, timeout=2)) as db, db:
                db.execute("BEGIN IMMEDIATE")
                prior = (
                    db.execute(
                        "SELECT id,message FROM updates WHERE idempotency_key=?", (key,)
                    ).fetchone()
                    if key
                    else None
                )
                if prior:
                    if prior[1] != message:
                        self.reply(
                            409,
                            {
                                "error": "idempotency key already used for another message"
                            },
                        )
                    else:
                        self.reply(200, {"id": prior[0], "duplicate": True})
                    return
                row = db.execute(
                    "INSERT INTO updates(message,created_at,idempotency_key) VALUES(?,?,?)",
                    (message, datetime.now(UTC).isoformat(), key),
                )
                new_id = row.lastrowid
            self.reply(201, {"id": new_id, "duplicate": False})
        except sqlite3.Error:
            self.reply(503, {"error": "state store busy or unavailable"})


def parser():
    args = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    args.add_argument("--host", default="127.0.0.1")
    args.add_argument("--port", type=int, default=8000)
    args.add_argument("--data", default="data/relay.sqlite")
    args.add_argument("--release", default="v1")
    args.add_argument("--read-only", action="store_true")
    args.add_argument("--ready-file")
    args.add_argument("--token-file")
    args.add_argument("--workers", type=int, default=8)
    args.add_argument("--delay-ms", type=int, default=0)
    args.add_argument("--quiet", action="store_true")
    return args


def main():
    cli = parser()
    args = cli.parse_args()
    if (
        not 0 <= args.port <= 65535
        or not 1 <= args.workers <= 64
        or not 0 <= args.delay_ms <= 1000
    ):
        cli.error("port must be 0..65535, workers 1..64, and delay-ms 0..1000")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", args.release):
        cli.error("release must be a short identifier")
    server = RelayServer(
        (args.host, args.port),
        data=args.data,
        release=args.release,
        read_only=args.read_only,
        ready_file=args.ready_file,
        token_file=args.token_file,
        workers=args.workers,
        delay_ms=args.delay_ms,
        quiet=args.quiet,
    )

    def stop(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(
        json.dumps(
            {
                "event": "listening",
                "host": args.host,
                "port": server.server_port,
                "release": args.release,
                "data": str(Path(args.data).resolve()),
                "read_only": args.read_only,
            }
        ),
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
