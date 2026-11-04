"""Reproduce real loopback API, persistence, release and recovery controls."""

import concurrent.futures
import csv
import http.client
import json
import socket
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path

import analyze
import backup
import check_service
import edge
import probe_load
import relay
import release


@contextmanager
def service(folder, **options):
    server = relay.RelayServer(
        ("127.0.0.1", 0), data=folder / "relay.sqlite", quiet=True, **options
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    try:
        thread.start()
    except Exception:
        server.server_close()
        raise
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        if thread.is_alive():
            raise RuntimeError("Owned server did not stop")


def request(server, path, body=None, headers=None):
    client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        client.request(
            "POST" if body is not None else "GET",
            path,
            body=json.dumps(body) if body is not None else None,
            headers=headers or {},
        )
        response = client.getresponse()
        raw = response.read()
        return response.status, json.loads(raw)
    finally:
        client.close()


@contextmanager
def edge_service(config):
    server = ThreadingHTTPServer(("127.0.0.1", 0), edge.EdgeHandler)
    server.config = config
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    try:
        thread.start()
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        if thread.is_alive():
            raise RuntimeError("Owned edge did not stop")


class RelayControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ascend-relay-check-")
        self.folder = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_http_release_write_and_idempotency(self):
        with service(self.folder, release="v1") as server:
            base = f"http://127.0.0.1:{server.server_port}"
            result = check_service.observe(base, expected_release="v1", write=True)
            self.assertTrue(result["passed"], result)
            self.assertFalse(
                check_service.observe(base, expected_release="wrong")["passed"]
            )
            self.assertEqual(1, len(request(server, "/api/updates")[1]["updates"]))
            self.assertEqual(400, request(server, "/api/updates", {"message": ""})[0])
            self.assertEqual(
                400, request(server, "/api/updates", {"message": "a", "admin": True})[0]
            )

    def test_readiness_and_rotated_write_identity(self):
        gate, token = self.folder / "ready.txt", self.folder / "token.txt"
        gate.write_text("ready")
        token.write_text("first-synthetic-key")
        with service(self.folder, ready_file=gate, token_file=token) as server:
            self.assertEqual(
                401, request(server, "/api/updates", {"message": "unauthenticated"})[0]
            )
            first = {"Authorization": "Bearer first-synthetic-key"}
            self.assertEqual(
                201, request(server, "/api/updates", {"message": "first"}, first)[0]
            )
            token.write_text("second-synthetic-key")
            self.assertEqual(
                401, request(server, "/api/updates", {"message": "old"}, first)[0]
            )
            second = {"Authorization": "Bearer second-synthetic-key"}
            self.assertEqual(
                201, request(server, "/api/updates", {"message": "new"}, second)[0]
            )
            gate.write_text("drain")
            self.assertEqual(200, request(server, "/health")[0])
            self.assertEqual(503, request(server, "/ready")[0])
            self.assertEqual(
                503, request(server, "/api/updates", {"message": "blocked"}, second)[0]
            )
            gate.write_text("ready")
            self.assertEqual(200, request(server, "/ready")[0])

    def test_read_only_and_restart_persistence(self):
        with service(self.folder) as server:
            self.assertEqual(
                201,
                request(server, "/api/updates", {"message": "kept across restart"})[0],
            )
        with service(self.folder, read_only=True, release="v2") as server:
            self.assertEqual(
                "kept across restart",
                request(server, "/api/updates")[1]["updates"][0]["message"],
            )
            self.assertEqual(
                405, request(server, "/api/updates", {"message": "must not write"})[0]
            )
            self.assertEqual("v2", request(server, "/version")[1]["release"])

    def test_consistent_snapshot_and_independent_restore(self):
        with service(self.folder) as server:
            request(server, "/api/updates", {"message": "included"})
            snapshot = backup.copy_database(
                self.folder / "relay.sqlite", self.folder / "backup.sqlite"
            )
            request(server, "/api/updates", {"message": "after backup"})
        restored = backup.copy_database(
            self.folder / "backup.sqlite", self.folder / "restored.sqlite"
        )
        self.assertEqual(snapshot["records_sha256"], restored["records_sha256"])
        self.assertEqual(1, restored["records"])
        self.assertEqual(2, backup.inspect(self.folder / "relay.sqlite")["records"])
        with self.assertRaises(FileExistsError):
            backup.copy_database(
                self.folder / "backup.sqlite", self.folder / "relay.sqlite"
            )

    def test_immutable_artifact_and_selected_release(self):
        source = Path(relay.__file__)
        artifact = self.folder / "v1"
        twin = self.folder / "v1-twin"
        release.build(source, artifact, "v1", "local-study")
        release.build(source, twin, "v1", "local-study")
        self.assertEqual(
            (artifact / "manifest.json").read_bytes(),
            (twin / "manifest.json").read_bytes(),
        )
        state = self.folder / "deployment/current.json"
        release.select(artifact, state)
        self.assertEqual("v1", release.resolve(state)["release"])
        before = state.read_bytes()
        (artifact / "relay.py").write_text("print('unreviewed change')\n")
        with self.assertRaises(ValueError):
            release.select(artifact, state)
        self.assertEqual(before, state.read_bytes())
        with self.assertRaises(ValueError):
            release.resolve(state)

    def test_edge_diagnosis_preserves_the_direct_control(self):
        config = self.folder / "route.json"
        with service(self.folder, release="edge-origin-v1") as origin:
            good = {"host": "127.0.0.1", "port": origin.server_port}
            config.write_text(json.dumps(good))
            with edge_service(config) as proxy:
                self.assertEqual(
                    "edge-origin-v1", request(proxy, "/version")[1]["release"]
                )
                with socket.socket() as unavailable:
                    unavailable.bind(("127.0.0.1", 0))
                    config.write_text(
                        json.dumps(
                            {"host": "127.0.0.1", "port": unavailable.getsockname()[1]}
                        )
                    )
                    self.assertEqual(502, request(proxy, "/version")[0])
                    self.assertEqual(200, request(origin, "/version")[0])
                config.write_text("[]")
                self.assertEqual(502, request(proxy, "/version")[0])
                config.write_text(json.dumps({"host": "192.0.2.1", "port": 8000}))
                self.assertEqual(502, request(proxy, "/version")[0])
                config.write_text(json.dumps(good))
                result = check_service.observe(
                    f"http://127.0.0.1:{proxy.server_port}",
                    expected_release="edge-origin-v1",
                )
                self.assertTrue(result["passed"], result)

    def test_bounded_admission_and_recovery_count_failed_work(self):
        with service(self.folder, workers=1, delay_ms=500) as server:
            base = f"http://127.0.0.1:{server.server_port}/work"
            overloaded = self.folder / "overloaded.csv"
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                held = pool.submit(request, server, "/work")
                deadline = time.monotonic() + 2
                while not server.active and time.monotonic() < deadline:
                    time.sleep(0.001)
                self.assertEqual(
                    1, server.active, "The owned slow request must occupy the worker"
                )
                sample = probe_load.run(base, 2, 4, overloaded)
                self.assertEqual(200, held.result(timeout=3)[0])
            report = analyze.analyze(overloaded, sample["window_seconds"])
            self.assertEqual(4, report["attempts"])
            self.assertEqual(4, report["failed"])
            self.assertEqual(1, report["error_rate"])
            self.assertEqual(4, server.rejected)
            self.assertEqual(1, server.peak)
            normal = self.folder / "normal.csv"
            sample = probe_load.run(base, 1, 2, normal)
            report = analyze.analyze(normal, sample["window_seconds"])
            self.assertEqual(2, report["successful"])
            self.assertEqual(0, report["failed"])
            self.assertEqual(200, request(server, "/ready")[0])
            before = server.requests
            with self.assertRaises(FileExistsError):
                probe_load.run(base, 1, 2, normal)
            self.assertEqual(
                before,
                server.requests,
                "An existing report must stop a rerun before any HTTP work",
            )

    def test_load_target_limits_and_analysis_denominator(self):
        output = self.folder / "attempts.csv"
        with self.assertRaises(ValueError):
            probe_load.run("http://192.0.2.1/work", 1, 1, output)
        with self.assertRaises(ValueError):
            probe_load.run("http://127.0.0.1:8000/work", 17, 1, output)
        self.assertFalse(output.exists())
        with output.open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=["status", "elapsed_ms", "response_bytes"]
            )
            writer.writeheader()
            writer.writerow({"status": 200, "elapsed_ms": 100, "response_bytes": 10})
            writer.writerow({"status": 503, "elapsed_ms": 1, "response_bytes": 8})
        report = analyze.analyze(output, 2)
        self.assertEqual(0.5, report["error_rate"])
        self.assertEqual(50.5, report["mean_ms_all"])
        self.assertEqual(100, report["p95_ms_all"])
        self.assertEqual(0.5, report["successful_requests_per_second"])
        self.assertEqual(9, report["observed_response_bytes_per_second"])
        with self.assertRaises(ValueError):
            analyze.analyze(output, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
