"""Small loopback-only teaching proxy; use Caddy/NGINX for the full edge lab."""

import argparse
import http.client
import json
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class EdgeHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path not in {
            "/",
            "/health",
            "/ready",
            "/version",
            "/api/updates",
            "/work",
        }:
            self.send_error(404)
            return
        upstream = None
        try:
            config = json.loads(self.server.config.read_text())
            if (
                not isinstance(config, dict)
                or set(config) != {"host", "port"}
                or config["host"] != "127.0.0.1"
                or type(config["port"]) is not int
                or not 1024 <= config["port"] <= 65535
            ):
                raise ValueError("Expected a loopback host and port 1024..65535")
            upstream = http.client.HTTPConnection(
                "127.0.0.1", config["port"], timeout=2
            )
            upstream.request("GET", self.path)
            response = upstream.getresponse()
            body = response.read(1_000_001)
            if len(body) > 1_000_000:
                raise ValueError("Response exceeds lab bound")
            status = response.status
            mime = response.getheader("Content-Type", "application/octet-stream")
        except (OSError, ValueError, KeyError, http.client.HTTPException):
            status, mime = 502, "application/json"
            body = b'{"error":"upstream unavailable or invalid; inspect the origin and route"}'
        finally:
            if upstream:
                upstream.close()
        try:
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be 0..65535")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), EdgeHandler)
    server.config = Path(args.config)

    def stop(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(
        json.dumps(
            {
                "edge": "127.0.0.1",
                "port": server.server_port,
                "route_file": str(server.config.resolve()),
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
