"""Short closed-model HTTP experiment against an explicitly owned target."""

import argparse
import concurrent.futures
import csv
import http.client
import ipaddress
import json
import time
from pathlib import Path
from urllib.parse import urlsplit


def run(url, clients, requests, output, allow_remote=False):
    parts = urlsplit(url)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.fragment
    ):
        raise ValueError("An HTTP(S) target without embedded credentials is required")
    try:
        local = ipaddress.ip_address(parts.hostname).is_loopback
    except ValueError:
        local = parts.hostname.lower() == "localhost"
    if not local and not allow_remote:
        raise ValueError("Non-loopback targets require --allow-owned-remote-target")
    if not 1 <= clients <= 16 or not 1 <= requests <= 200:
        raise ValueError("clients 1..16, requests 1..200")

    def probe(index):
        begin = time.monotonic()
        connection = (
            http.client.HTTPSConnection(parts.hostname, parts.port, timeout=3)
            if parts.scheme == "https"
            else http.client.HTTPConnection(parts.hostname, parts.port, timeout=3)
        )
        try:
            target = (parts.path or "/") + ("?" + parts.query if parts.query else "")
            connection.request("GET", target)
            response = connection.getresponse()
            raw = response.read(1_000_001)
            status = response.status if len(raw) <= 1_000_000 else 0
            size = len(raw)
        except (OSError, http.client.HTTPException):
            status, size = 0, 0
        finally:
            connection.close()
        return {
            "request": index,
            "status": status,
            "elapsed_ms": round((time.monotonic() - begin) * 1000, 3),
            "response_bytes": size,
        }

    # Reserving the output before making requests prevents reruns from silently
    # replacing earlier observations or doing work that cannot be retained.
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["request", "status", "elapsed_ms", "response_bytes"]
        )
        writer.writeheader()
        started = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=clients) as pool:
            for result in pool.map(probe, range(requests)):
                writer.writerow(result)
    return {
        "path": str(output.resolve()),
        "window_seconds": round(time.monotonic() - started, 6),
        "requests": requests,
        "clients": clients,
        "model": "closed: workers start another request only after completion",
        "scope": "Short local experiment. Not fixed arrival-rate, physical hardware, internet capacity or SLO certification.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000/work")
    parser.add_argument("--clients", type=int, default=4)
    parser.add_argument("--requests", type=int, default=16)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-owned-remote-target", action="store_true")
    args = parser.parse_args()
    try:
        result = run(
            args.url,
            args.clients,
            args.requests,
            args.output,
            args.allow_owned_remote_target,
        )
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
