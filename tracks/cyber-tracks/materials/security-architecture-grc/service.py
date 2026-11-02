"""Deliberately incomplete, local-only teaching API. All data are synthetic.
X-Lab-User simulates an identity; it is NOT real authentication.
Inspect and repair the permission/property boundary as assigned in the lesson.
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

NOTES = {"1": {"owner": "alice", "text": "Synthetic project note", "internal": "Demo only"},
         "2": {"owner": "bob", "text": "Synthetic shopping note", "internal": "Demo only"}}

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self.send_json(200, {"status": "ok", "fixture": "ascend-notes-v1"})
        key = self.path.removeprefix("/notes/") if self.path.startswith("/notes/") else ""
        note = NOTES.get(key)
        if not note:
            return self.send_json(404, {"error": "not found"})
        user = self.headers.get("X-Lab-User", "")
        if user not in {"alice", "bob"}:
            return self.send_json(401, {"error": "use a synthetic lab identity"})
        # Exercise: being a known user does not establish ownership of this note.
        self.send_json(200, note)

    def do_PATCH(self):
        key = self.path.removeprefix("/notes/") if self.path.startswith("/notes/") else ""
        note = NOTES.get(key)
        if not note:
            return self.send_json(404, {"error": "not found"})
        if self.headers.get("X-Lab-User") != note["owner"]:
            return self.send_json(403, {"error": "not owner"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.send_json(400, {"error": "invalid length"})
        if not 0 < size <= 2048:
            return self.send_json(413, {"error": "body must be 1 to 2048 bytes"})
        try:
            changes = json.loads(self.rfile.read(size))
        except (ValueError, UnicodeError):
            return self.send_json(400, {"error": "invalid JSON"})
        if not isinstance(changes, dict):
            return self.send_json(400, {"error": "expected an object"})
        # Exercise: decide which properties a note owner is allowed to change.
        note.update(changes)
        self.send_json(200, note)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print("Local fixture: http://127.0.0.1:" + str(args.port), flush=True)
    try:
        HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("Stopped. In-memory changes are discarded.")
