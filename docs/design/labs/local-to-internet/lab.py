"""Reproduce a small HTTP operations lab with real Caddy and loopback services.

Requires Python 3.10+, Caddy, and OpenSSL. No root, account, public tunnel, or
machine-wide trust changes. The sample HTTP applications are teaching fixtures.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Application:
    def __init__(self, name, workers, work_ms):
        self.name = name
        self.ready = True
        self.workers = threading.BoundedSemaphore(workers)
        self.lock = threading.Lock()
        self.active = self.peak = self.admitted = self.rejected = 0
        self.peer_disconnects = 0
        self.work_ms = work_ms
        self.started = threading.Event()
        self.release = threading.Event()
        self.release.set()

    def handler(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def reply(self, status, **extra):
                body = json.dumps({"node": app.name, "version": "relay-proof-v1", **extra}).encode()
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    if status == 503:
                        self.send_header("Retry-After", "1")
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    # A health checker may stop reading after receiving status.
                    # Count the disconnect; client-side assertions still decide
                    # whether each tested response actually arrived.
                    with app.lock:
                        app.peer_disconnects += 1

            def do_GET(self):
                if self.path == "/ready":
                    self.reply(200 if app.ready else 503, ready=app.ready)
                    return
                if self.path in {"/limited", "/slow-b"}:
                    if not app.workers.acquire(blocking=False):
                        with app.lock:
                            app.rejected += 1
                        self.reply(503, result="admission-full")
                        return
                    try:
                        with app.lock:
                            app.active += 1
                            app.admitted += 1
                            app.peak = max(app.peak, app.active)
                        app.started.set()
                        # A bounded stand-in for a slow dependency, not CPU work.
                        app.release.wait(timeout=3)
                        time.sleep(app.work_ms / 1000)
                        self.reply(200, result="work-complete")
                    finally:
                        with app.lock:
                            app.active -= 1
                        app.workers.release()
                    return
                self.reply(200, result="reachable")

        return Handler


def request(port, path="/", *, tls=None, hostname="127.0.0.1"):
    connection = (http.client.HTTPSConnection(hostname, port, context=tls, timeout=4)
                  if tls else http.client.HTTPConnection(hostname, port, timeout=4))
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        raw = response.read()
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            body = {"raw": raw.decode(errors="replace")[:200]}
        return response.status, body
    finally:
        connection.close()


def wait_until(predicate, *, seconds=6, description="condition"):
    deadline = time.monotonic() + seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except (OSError, http.client.HTTPException) as error:
            last_error = error
        time.sleep(0.08)
    raise AssertionError(f"Timed out waiting for {description}; last error: {last_error}")


def reserve_port():
    reservation = socket.socket()
    reservation.bind(("127.0.0.1", 0))
    return reservation, reservation.getsockname()[1]


def linux_owned_listeners(pid):
    """Inspect only this child process's listening TCP socket inodes."""
    process = Path(f"/proc/{pid}")
    if not (process / "fd").is_dir():
        return None
    inodes = set()
    for fd in (process / "fd").iterdir():
        try:
            target = os.readlink(fd)
        except OSError:
            continue
        if target.startswith("socket:["):
            inodes.add(target[8:-1])
    listeners = []
    for name in ["tcp", "tcp6"]:
        table = process / "net" / name
        if not table.exists():
            continue
        for line in table.read_text().splitlines()[1:]:
            columns = line.split()
            if columns[3] != "0A" or columns[9] not in inodes:
                continue
            address, port = columns[1].split(":")
            if name == "tcp":
                address = socket.inet_ntop(socket.AF_INET, bytes.fromhex(address)[::-1])
            else:
                raw = bytes.fromhex(address)
                address = socket.inet_ntop(socket.AF_INET6, b"".join(raw[i:i+4][::-1] for i in range(0, 16, 4)))
            listeners.append(f"{address}:{int(port, 16)}")
    return sorted(listeners)


def bounded_integer(low, high):
    def parse(value):
        result = int(value)
        if not low <= result <= high:
            raise argparse.ArgumentTypeError(f"expected {low}..{high}")
        return result
    return parse


def run(args):
    executable = shutil.which(args.caddy) or str(Path(args.caddy).resolve())
    if not Path(executable).is_file():
        raise SystemExit("Caddy is missing. Pass --caddy /path/to/caddy; see README.md.")
    openssl = shutil.which("openssl")
    if not openssl:
        raise SystemExit("OpenSSL is required to generate this lab's temporary certificate.")
    if args.burst <= args.workers:
        raise SystemExit("Use --burst greater than --workers to exercise overload rejection.")

    report = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Local HTTP/TLS/routing/readiness/application-admission proof only.",
        "environment": {"os": platform.system(), "architecture": platform.machine(),
                        "python": platform.python_version(), "visible_logical_cpus": os.cpu_count()},
        "caddy_version": subprocess.check_output([executable, "version"], text=True).strip(),
        "caddy_binary_sha256": hashlib.sha256(Path(executable).read_bytes()).hexdigest(),
        "parameters": {"workers_per_sample_app": args.workers, "burst_clients": args.burst,
                       "simulated_dependency_ms": args.work_ms},
        "checks": [],
        "limitations": [
            "These sample services share one host, storage, power and uplink; this does not establish host high availability.",
            "The semaphore bounds application work only; this is not a global bound on accepted TCP connections or HTTP server threads.",
            "The burst uses bounded client threads and an imposed I/O wait; it is not an arrival-rate capacity benchmark or a learner study.",
            "TLS uses a temporary certificate trusted by this client only; public DNS, ACME issuance, WAN access, VPN, SSH, mail and VM administration are not exercised.",
            "Observed process memory is for this run on the recorded host, not a recommended Raspberry Pi or shared-runner capacity.",
        ],
    }
    def passed(name, evidence):
        report["checks"].append({"name": name, "passed": True, "evidence": evidence})
        print(f"PASS {name}", flush=True)

    apps = [Application("app-a", args.workers, args.work_ms),
            Application("app-b", args.workers, args.work_ms)]
    servers, threads, reservations, child = [], [], [], None
    ports = []
    with tempfile.TemporaryDirectory(prefix="ascend-http-proof-") as tmp:
        folder = Path(tmp)
        log_path = folder / "caddy.log"
        try:
            for app in apps:
                server = ThreadingHTTPServer(("127.0.0.1", 0), app.handler())
                server.daemon_threads = True
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                try:
                    thread.start()
                except Exception:
                    server.server_close()
                    raise
                servers.append(server)
                threads.append(thread)
                ports.append(server.server_port)
            held_http, http_port = reserve_port()
            reservations.append(held_http)
            held_tls, tls_port = reserve_port()
            reservations.append(held_tls)
            broken_target, broken_port = reserve_port()
            reservations.append(broken_target)
            ports.extend([http_port, tls_port])
            # Keep the broken target bound but non-listening: no other process
            # can take it, and a connect must fail without leaving loopback.
            cert, key = folder / "cert.pem", folder / "key.pem"
            subprocess.run([
                openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-days", "1", "-keyout", str(key), "-out", str(cert),
                "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost",
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            config = """{
    admin off
    auto_https off
    persist_config off
    default_sni localhost
    servers {
        protocols h1
    }
}
(routes) {
    handle /broken {
        reverse_proxy 127.0.0.1:BROKEN
    }
    handle /limited {
        reverse_proxy 127.0.0.1:APP_A
    }
    handle /slow-b {
        reverse_proxy 127.0.0.1:APP_B
    }
    handle {
        reverse_proxy 127.0.0.1:APP_A 127.0.0.1:APP_B {
            lb_policy round_robin
            health_uri /ready
            health_interval 100ms
            health_timeout 500ms
        }
    }
}
http://127.0.0.1:HTTP_PORT {
    bind 127.0.0.1
    import routes
}
https://localhost:TLS_PORT {
    bind 127.0.0.1
    tls CERT KEY
    import routes
}
"""
            for token, value in {"BROKEN": broken_port, "APP_A": servers[0].server_port,
                                 "APP_B": servers[1].server_port, "HTTP_PORT": http_port,
                                 "TLS_PORT": tls_port, "CERT": json.dumps(str(cert)),
                                 "KEY": json.dumps(str(key))}.items():
                config = config.replace(token, str(value))
            config_path = folder / "Caddyfile"
            config_path.write_text(config)
            child_env = dict(os.environ, XDG_CONFIG_HOME=str(folder / "config"),
                             XDG_DATA_HOME=str(folder / "data"), GOMAXPROCS="2")
            adapted = subprocess.run([executable, "adapt", "--config", str(config_path),
                                      "--adapter", "caddyfile"], env=child_env, check=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            adapted_config = json.loads(adapted.stdout)
            expected_listeners = sorted([f"127.0.0.1:{http_port}", f"127.0.0.1:{tls_port}"])
            configured_listeners = sorted(address for server in adapted_config["apps"]["http"]["servers"].values()
                                          for address in server["listen"])
            assert configured_listeners == expected_listeners, configured_listeners
            subprocess.run([executable, "validate", "--config", str(config_path),
                            "--adapter", "caddyfile"], env=child_env, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            held_http.close()
            held_tls.close()
            with log_path.open("wb") as log:
                child = subprocess.Popen([executable, "run", "--config", str(config_path),
                                          "--adapter", "caddyfile"], env=child_env,
                                         stdout=log, stderr=subprocess.STDOUT)
            wait_until(lambda: request(http_port)[0] == 200, description="owned Caddy listener")
            assert child.poll() is None
            live_listeners = linux_owned_listeners(child.pid)
            if live_listeners is not None:
                assert live_listeners == expected_listeners, live_listeners
            passed("explicit-listener-bindings", {"adapted_listeners": configured_listeners,
                                                   "linux_owned_live_listeners": live_listeners})
            for server, app in zip(servers, apps):
                status, body = request(server.server_port)
                assert status == 200 and body["node"] == app.name
            passed("direct-service-and-reverse-proxy", {"status": 200, "bind": "loopback only"})

            nodes = [request(http_port)[1]["node"] for _ in range(8)]
            assert collections.Counter(nodes) == {"app-a": 4, "app-b": 4}, nodes
            passed("explicit-round-robin", {"requests": 8, "node_counts": dict(collections.Counter(nodes))})
            status, _ = request(http_port, "/broken")
            assert status == 502, status
            passed("incorrect-upstream-negative-control", {"status": status, "repair_control": request(http_port)[0]})

            trusted = ssl.create_default_context(cafile=str(cert))
            assert request(tls_port, tls=trusted, hostname="localhost")[0] == 200
            rejected = []
            for name, context, host in [("untrusted-ca", ssl.create_default_context(), "localhost"),
                                        ("wrong-name", trusted, "127.0.0.1")]:
                try:
                    request(tls_port, tls=context, hostname=host)
                except ssl.SSLCertVerificationError:
                    rejected.append(name)
                else:
                    raise AssertionError(f"TLS negative control did not reject {name}")
            passed("tls-trust-and-name-controls", {"trusted_status": 200, "rejected": rejected,
                                                  "machine_trust_store_changed": False})

            apps[1].release.clear()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                in_flight = pool.submit(request, http_port, "/slow-b")
                try:
                    assert apps[1].started.wait(timeout=3)
                    apps[1].ready = False
                    def only_a():
                        return all(request(http_port)[1].get("node") == "app-a" for _ in range(8))
                    wait_until(only_a, seconds=2, description="readiness removes app-b from new balanced traffic")
                    assert not in_flight.done(), "Existing request finished before traffic exclusion was observed"
                    assert apps[1].active == 1, "The existing app-b operation must still be active"
                finally:
                    apps[1].release.set()
                existing_status, existing_body = in_flight.result(timeout=4)
                assert existing_status == 200 and existing_body["node"] == "app-b"
            passed("readiness-and-inflight-completion", {"new_balanced_requests": "app-a",
                   "existing_request": "app-b still active when exclusion was observed, then completed 200",
                   "scope": "The explicit /slow-b test route bypasses balancing; only new balanced traffic is excluded."})
            apps[1].ready = True
            wait_until(lambda: set(request(http_port)[1]["node"] for _ in range(8)) == {"app-a", "app-b"},
                       description="healthy app-b returns to the pool")
            passed("readiness-recovery", {"healthy_backends": 2})

            app = apps[0]
            app.release.clear()
            barrier = threading.Barrier(args.burst)
            def work_request():
                barrier.wait(timeout=4)
                return request(http_port, "/limited")[0]
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.burst) as pool:
                futures = [pool.submit(work_request) for _ in range(args.burst)]
                try:
                    wait_until(lambda: app.admitted + app.rejected >= args.burst,
                               seconds=2.5, description="bounded burst reaches admission point")
                finally:
                    app.release.set()
                statuses = [future.result(timeout=4) for future in futures]
            counts = dict(collections.Counter(statuses))
            assert set(statuses) == {200, 503}, counts
            assert 0 < app.peak <= args.workers and app.active == 0
            passed("bounded-work-and-overload-rejection", {"status_counts": counts,
                   "peak_application_work": app.peak, "configured_slots": args.workers})
            assert request(http_port, "/limited")[0] == 200
            passed("post-overload-recovery", {"status": 200, "active_work_after": app.active})
            status_path = Path(f"/proc/{child.pid}/status")
            if status_path.exists():
                report["observed_caddy_memory"] = {
                    line.split(":", 1)[0]: line.split(":", 1)[1].strip()
                    for line in status_path.read_text().splitlines()
                    if line.startswith(("VmRSS:", "VmHWM:"))
                }
        except Exception:
            if log_path.exists():
                print("Owned Caddy log tail:\n" + "\n".join(log_path.read_text().splitlines()[-8:]))
            raise
        finally:
            for app in apps:
                app.release.set()
            if child is not None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            for server in servers:
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join(timeout=2)
            for reservation in reservations:
                reservation.close()
        assert child is not None and child.poll() is not None
        assert not any(thread.is_alive() for thread in threads)
        for port in ports:
            with socket.socket() as probe:
                probe.settimeout(0.3)
                assert probe.connect_ex(("127.0.0.1", port)) != 0, port
        report["sample_app_peer_disconnects"] = {app.name: app.peer_disconnects for app in apps}
    assert not folder.exists()
    passed("owned-process-and-file-cleanup", {"child_stopped": True, "listeners_closed": len(ports),
                                             "temporary_certificate_and_config_removed": True})
    report["all_passed"] = True
    if args.output:
        target = Path(args.output).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Evidence saved to {target}")
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--caddy", default="caddy", help="Path to a Caddy binary; none is downloaded automatically")
    parser.add_argument("--workers", type=bounded_integer(1, 8), default=2)
    parser.add_argument("--burst", type=bounded_integer(2, 16), default=12)
    parser.add_argument("--work-ms", type=bounded_integer(20, 500), default=120)
    parser.add_argument("--output", help="Exact path for the JSON evidence; omitted means print only")
    run(parser.parse_args())
