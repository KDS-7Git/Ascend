"""Observe an owned Relay service; this local report is not a verified track receipt."""

import argparse
import json
import ssl
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener


def observe(
    base, *, expected_release=None, write=False, token=None, ca_file=None, timeout=3
):
    parts = urlsplit(base)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or parts.path not in {"", "/"}
    ):
        raise ValueError(
            "Use an HTTP(S) origin URL without credentials, query or fragment"
        )
    if not 0.2 <= timeout <= 10:
        raise ValueError("timeout must be 0.2..10 seconds")
    context = ssl.create_default_context(cafile=ca_file)
    client = build_opener(ProxyHandler({}), HTTPSHandler(context=context))
    checks = []

    def request(path, *, body=None, extra=None):
        headers = dict(extra or {})
        if body is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = "Bearer " + token
        req = Request(
            base.rstrip("/") + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
        )
        try:
            response = client.open(req, timeout=timeout)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("response exceeds this checker's 2 MB limit")
            try:
                result = json.loads(raw)
            except ValueError:
                result = raw.decode(errors="replace")
            return response.status, result

    for path in ["/health", "/ready", "/version", "/api/updates"]:
        status, result = request(path)
        passed = status == 200
        if path == "/health":
            passed = (
                passed and isinstance(result, dict) and result.get("status") == "alive"
            )
        if path == "/version":
            passed = (
                passed
                and isinstance(result, dict)
                and result.get("schema") == 1
                and isinstance(result.get("release"), str)
                and bool(result.get("release"))
                and type(result.get("read_only")) is bool
            )
        if path == "/version" and expected_release:
            passed = (
                passed
                and isinstance(result, dict)
                and result.get("release") == expected_release
            )
        if path == "/ready":
            passed = passed and isinstance(result, dict) and result.get("ready") is True
        if path == "/api/updates":
            passed = (
                passed
                and isinstance(result, dict)
                and isinstance(result.get("updates"), list)
            )
        checks.append(
            {"path": path, "status": status, "passed": passed, "observed": result}
        )
    status, _ = request("/not-an-endpoint")
    checks.append(
        {"path": "/not-an-endpoint", "status": status, "passed": status == 404}
    )
    if write:
        key = "check-" + uuid.uuid4().hex
        body = {"message": "Synthetic Relay operational check " + key}
        first_status, first = request(
            "/api/updates", body=body, extra={"Idempotency-Key": key}
        )
        again_status, again = request(
            "/api/updates", body=body, extra={"Idempotency-Key": key}
        )
        conflict, _ = request(
            "/api/updates",
            body={"message": "different synthetic input"},
            extra={"Idempotency-Key": key},
        )
        retained_status, retained = request("/api/updates")
        retained_rows = (
            retained.get("updates", []) if isinstance(retained, dict) else []
        )
        passed = (
            first_status == 201
            and again_status == 200
            and isinstance(first, dict)
            and type(first.get("id")) is int
            and isinstance(again, dict)
            and first["id"] == again.get("id")
            and conflict == 409
            and retained_status == 200
            and isinstance(retained_rows, list)
            and any(
                isinstance(row, dict)
                and row.get("id") == first["id"]
                and row.get("message") == body["message"]
                for row in retained_rows
            )
        )
        checks.append(
            {
                "path": "/api/updates",
                "control": "write/replay/conflicting-key",
                "statuses": [first_status, again_status, conflict],
                "passed": passed,
                "retained_synthetic_record_id": first.get("id")
                if isinstance(first, dict)
                else None,
            }
        )
    return {
        "recorded_at": datetime.now(UTC).isoformat(),
        "origin": base,
        "authority": "learner-local observation",
        "satisfies_track_evidence": False,
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
        "scope": "Named endpoint, readiness, release and optional write controls only; no uptime, capacity or public-reachability guarantee.",
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--url", default="http://127.0.0.1:8000")
    cli.add_argument("--expect-release")
    cli.add_argument(
        "--write",
        action="store_true",
        help="Create one synthetic update and check idempotent replay",
    )
    cli.add_argument("--token-file")
    cli.add_argument("--ca-file", help="Trust this CA for this invocation only")
    cli.add_argument("--timeout", type=float, default=3)
    args = cli.parse_args()
    try:
        token = Path(args.token_file).read_text().strip() if args.token_file else None
        report = observe(
            args.url,
            expected_release=args.expect_release,
            write=args.write,
            token=token,
            ca_file=args.ca_file,
            timeout=args.timeout,
        )
    except (OSError, ValueError) as error:
        cli.exit(1, "Check could not complete: " + str(error) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
