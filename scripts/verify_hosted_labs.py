"""Real browser/control-plane acceptance using disposable web and runner profiles."""

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ascend.application import Tracker
from ascend.local_labs.hosted import RECIPES
from ascend.local_labs.runtime import Runtime
from ascend.server.lab_runner import RunnerClient
from ascend.storage import Database

AUDIT = {
    "discovery_event_id": "92733",
    "executable": "/usr/sbin/arp",
    "arguments": ["arp", "-a"],
    "companion_event_id": "92734",
    "uid": 1000,
    "benign_event_ids": ["control-1"],
    "intent": "insufficient-evidence",
    "explanation": "The audit log records discovery but cannot establish malicious intent on its own.",
}


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--record", type=Path)
    parser.add_argument("--screenshots", type=Path)
    parser.add_argument("--cache-source", type=Path, action="append", default=[])
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="ascend-hosted-validation-"))
    key = os.urandom(32).hex()
    web_port, runner_port = port(), port()
    runner_url, web_url = (
        f"http://127.0.0.1:{runner_port}",
        f"http://127.0.0.1:{web_port}",
    )
    env = {
        **os.environ,
        "ASCEND_RUNNER_KEY": key,
        "ASCEND_RUNNER_URL": runner_url,
        "ASCEND_RUNNER_SITE_ID": "disposable-validation",
        "AUTH_MODE": "single",
    }
    processes, logs, records = [], [], []
    successful = False
    scope = RunnerClient(runner_url, key, "disposable-validation").scope(
        SimpleNamespace(db=SimpleNamespace(user_id=1))
    )
    cache = root / "runner/accounts" / scope / "labs/cache"
    cache.mkdir(parents=True, mode=0o700)
    for source in args.cache_source:
        for path in source.rglob("*"):
            if (
                path.is_file()
                and not path.is_symlink()
                and re.fullmatch(r"[a-f0-9]{64}", path.name)
            ):
                shutil.copyfile(path, cache / path.name)

    def api(path, body=None):
        req = Request(
            web_url + "/api/" + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(req, timeout=15) as response:
                return json.load(response)
        except HTTPError as error:
            raise AssertionError(error.read(8192).decode()) from None

    def wait_job(job):
        deadline = time.monotonic() + 700
        while time.monotonic() < deadline:
            state = api("hosted-labs/runs")
            current = state["job"]
            if (
                current
                and current["id"] == job["id"]
                and current["status"] not in {"queued", "running"}
            ):
                assert current["status"] == "complete", current
                return current, next(
                    (r for r in state["runs"] if r["id"] == current["run_id"]), None
                )
            time.sleep(0.2)
        raise AssertionError("Runner operation timed out")

    def action(run, name, data=None):
        return wait_job(api(f"hosted-labs/runs/{run['id']}/{name}", data or {}))

    def read(run, name):
        from urllib.parse import urlencode

        return api(f"hosted-labs/runs/{run['id']}/files?" + urlencode({"name": name}))[
            "content"
        ]

    def save(run, name, value):
        action(run, "save", {"name": name, "content": json.dumps(value)})

    try:
        for name, command in [
            (
                "runner",
                [
                    sys.executable,
                    "-m",
                    "ascend.local_labs.runner",
                    "--home",
                    str(root / "runner"),
                    "--port",
                    str(runner_port),
                    "--reserve-gib",
                    "0",
                    "--max-active",
                    "1",
                ],
            ),
            (
                "web",
                [
                    sys.executable,
                    "-m",
                    "ascend.server",
                    "--home",
                    str(root / "web"),
                    "--port",
                    str(web_port),
                ],
            ),
        ]:
            log = (root / (name + ".log")).open("wb")
            logs.append(log)
            processes.append(subprocess.Popen(command, env=env, stdout=log, stderr=log))
        for _ in range(100):
            try:
                assert api("hosted-labs/capabilities")["configured"]
                break
            except (URLError, OSError, AssertionError):
                assert all(p.poll() is None for p in processes), (
                    "Validation service exited; inspect " + str(root)
                )
                time.sleep(0.1)
        else:
            raise AssertionError("Validation services did not become ready")
        chosen = (
            sorted(RECIPES)
            if args.all
            else ["linux-audit-discovery", "bgp-export-policy"]
        )
        for recipe in chosen:
            print("Starting real hosted lifecycle: " + recipe, flush=True)
            started = time.monotonic()
            for retry in range(3):
                try:
                    _, run = wait_job(api("hosted-labs/runs", {"recipe_id": recipe}))
                    break
                except AssertionError as error:
                    if retry == 2 or not any(
                        word in str(error).lower()
                        for word in (
                            "urlopen error",
                            "network is unreachable",
                            "temporary failure",
                            "timed out",
                        )
                    ):
                        raise
                    print(
                        "Transient download failure; retrying pinned acquisition for "
                        + recipe,
                        flush=True,
                    )
            start_seconds = time.monotonic() - started
            job, _ = action(run, "check")
            initial = job["result"]["status"]
            if recipe == "linux-audit-discovery":
                assert initial == "fail"
                assert "type=" in read(run, "input/evidence.log")
                save(run, "work/answers.json", AUDIT)
            elif recipe == "bgp-export-policy":
                assignment = json.loads(read(run, "input/assignment.json"))
                policy = {
                    "version": 1,
                    "default": "deny",
                    "rules": [
                        {
                            "action": "permit",
                            "prefix": assignment["customer_prefix"],
                            "min_prefix": 24,
                            "max_prefix": 26,
                        }
                    ],
                }
                save(run, "work/policy.json", policy)
            elif recipe == "wrongsecrets-basics":
                assert initial == "fail"
                values = {
                    "challenge_1": re.search(
                        r'password\s*=\s*"([^"]+)"',
                        read(run, "input/WrongSecretsConstants.java"),
                    ).group(1),
                    "challenge_2": re.search(
                        r"^password=(.+)$",
                        read(run, "input/application.properties"),
                        re.MULTILINE,
                    ).group(1),
                    "challenge_3": re.search(
                        r'ENV DOCKER_ENV_PASSWORD="([^"]+)"',
                        read(run, "input/Dockerfile"),
                    ).group(1),
                    "explanation": "Source, configuration and image variables expose secrets to readers; use a scoped secret store and rotate exposed values.",
                }
                save(run, "work/answers.json", values)
                response, _ = action(
                    run,
                    "http",
                    {"target": "challenges", "path": "/challenge/challenge-1"},
                )
                assert response["result"]["status"] == 200
            elif recipe == "vampi-ownership":
                response, _ = action(
                    run,
                    "http",
                    {
                        "target": "fixed",
                        "path": "/users/v1/login",
                        "method": "POST",
                        "body": json.dumps({"username": "name1", "password": "pass1"}),
                    },
                )
                assert response["result"]["status"] == 200, response
            else:
                commands = ["configure terminal", "router bgp 65000"]
                if recipe == "bgp-single-session":
                    commands += [f"neighbor {run['addresses']['x1']} remote-as 65100"]
                elif recipe == "bgp-session-protection":
                    commands += [
                        f"neighbor {run['addresses']['x1']} ttl-security hops 1",
                        f"neighbor {run['addresses']['x2']} password GuessWhat",
                    ]
                else:
                    commands = [
                        "configure terminal",
                        "ip prefix-list CUSTOMER seq 5 permit 192.168.42.0/24",
                        "router bgp 65000",
                        "address-family ipv4 unicast",
                    ] + [
                        f"neighbor {run['addresses'][peer]} prefix-list CUSTOMER out"
                        for peer in ("x1", "x2")
                    ]
                action(run, "router", {"commands": commands + ["end", "write memory"]})
            job, run = action(run, "check")
            assert job["result"]["status"] == "pass", job
            assert job["result"]["authority"] == "server-runner"
            assert (
                job["result"]["xp"] == 0
                and not job["result"]["satisfies_track_evidence"]
            )
            if recipe == "linux-audit-discovery":
                from playwright.sync_api import expect, sync_playwright

                errors = []
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    for width in (390, 1440):
                        page = browser.new_page(
                            viewport={"width": width, "height": 900}
                        )
                        page.on(
                            "pageerror",
                            lambda error, errors=errors: errors.append(str(error)),
                        )
                        page.goto(web_url + "/#lab/linux-audit-discovery")
                        expect(
                            page.get_by_role("button", name="Check work", exact=True)
                        ).to_be_visible()
                        page.get_by_label("Lab file", exact=True).select_option(
                            "work/answers.json"
                        )
                        expect(page.get_by_label("File contents")).to_have_value(
                            re.compile("92733")
                        )
                        assert page.evaluate(
                            "document.documentElement.scrollWidth <= innerWidth"
                        )
                        if args.screenshots:
                            args.screenshots.mkdir(parents=True, exist_ok=True)
                            page.screenshot(
                                path=str(
                                    args.screenshots / f"hosted-audit-{width}.png"
                                ),
                                full_page=True,
                            )
                        page.close()
                    browser.close()
                assert not errors, errors
            expiry = run["expires_at"]
            action(run, "stop")
            _, run = action(run, "resume")
            assert run["expires_at"] == expiry
            job, run = action(run, "check")
            assert job["result"]["status"] == "pass"
            _, run = action(run, "finish")
            assert run["status"] == "destroyed"
            assert read(run, "work/submission.json")
            record = {
                "recipe_id": recipe,
                "startup_seconds": round(start_seconds, 3),
                "initial_status": initial,
                "final_status": job["result"]["status"],
                "stop_resume_deadline_preserved": True,
                "export_retained": True,
                "runtime_destroyed": True,
            }
            records.append(record)
            # Administrator-only eviction for this disposable account after destruction.
            scope = RunnerClient(runner_url, key, "disposable-validation").scope(
                SimpleNamespace(db=SimpleNamespace(user_id=1))
            )
            home = root / "runner/accounts" / scope
            db = Database(home / "tracker")
            try:
                Runtime(Tracker(db), root=home / "labs").prune(32, images=True)
            finally:
                db.close()
            print(json.dumps(record), flush=True)
        successful = True
        result = {
            "reviewed_on": time.strftime("%Y-%m-%d"),
            "recipes": records,
            "real_control_plane": True,
            "browser_widths": [390, 1440] if "linux-audit-discovery" in chosen else [],
            "production_reserve_gib": 10,
            "verification_reserve_gib": 0,
        }
        if args.record:
            args.record.parent.mkdir(parents=True, exist_ok=True)
            args.record.write_text(json.dumps(result, indent=2) + "\n")
        print("Hosted acceptance passed.", flush=True)
    finally:
        try:
            for run in api("hosted-labs/runs")["runs"]:
                if run["status"] != "destroyed":
                    action(run, "destroy")
        except (OSError, AssertionError):
            print("Cleanup needs inspection at " + str(root), flush=True)
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for log in logs:
            log.close()
        if successful:
            shutil.rmtree(root)
        else:
            print("Validation evidence retained at " + str(root), flush=True)


if __name__ == "__main__":
    main()
