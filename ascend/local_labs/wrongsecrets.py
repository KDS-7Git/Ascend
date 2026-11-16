"""Three fixed local WrongSecrets challenges, with local upstream answer checks."""

import hashlib
import secrets
import shutil
import time
from html.parser import HTMLParser
from http.client import HTTPConnection, HTTPException
from http.cookies import SimpleCookie
from urllib.parse import urlencode

from ascend.local_labs.assets import AssetStore, atomic_json
from ascend.local_labs.catalog import DATA
from ascend.local_labs.checks import outcome
from ascend.local_labs.service import ServiceLab

CHALLENGES = (1, 2, 3)
CHECK_IDS = [
    f"challenge_{i}.{name}"
    for i in CHALLENGES
    for name in ("answer_accepted", "wrong_answer_rejected")
] + ["exposure_explanation_present"]


class ChallengePage(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.csrf, self.feedback = None, set()
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") == "_csrf":
            self.csrf = attrs.get("value")
        if attrs.get("data-cy") in {"success-alert", "incorrect-alert"}:
            self.feedback.add(attrs["data-cy"])


def request(port, path, *, data=None, cookie=None, headers=None):
    connection = HTTPConnection("127.0.0.1", port, timeout=6)
    sent = {"Content-Type": "application/x-www-form-urlencoded", **(headers or {})}
    if cookie:
        sent["Cookie"] = cookie
    try:
        connection.request(
            "POST" if data is not None else "GET",
            path,
            urlencode(data) if isinstance(data, dict) else data,
            sent,
        )
        response = connection.getresponse()
        content = response.read(262145)
        if len(content) > 262144:
            raise ValueError("WrongSecrets response exceeds 256 KiB")
        cookies = SimpleCookie()
        for key, value in response.getheaders():
            if key.lower() == "set-cookie":
                cookies.load(value)
        session = cookies.get("JSESSIONID")
        return (
            response.status,
            content.decode("utf-8"),
            ("JSESSIONID=" + session.value) if session else cookie,
        )
    finally:
        connection.close()


def answer(port, number, value):
    path = f"/challenge/challenge-{number}"
    status, page, cookie = request(port, path)
    csrf = ChallengePage(page).csrf
    if status != 200 or not csrf or not cookie:
        raise ValueError(
            "WrongSecrets did not provide a challenge session and CSRF token"
        )
    status, page, _ = request(
        port,
        path,
        data={"action": "submit", "solution": value, "_csrf": csrf},
        cookie=cookie,
    )
    feedback = ChallengePage(page).feedback
    if status != 200 or len(feedback) != 1:
        raise ValueError("WrongSecrets returned no unambiguous answer result")
    return feedback == {"success-alert"}


class WrongSecrets(ServiceLab):
    def prepare(self, row):
        recipe, d = row["recipe"], self.docker
        d.provider()
        launcher = (DATA / "wrongsecrets-launcher.txt").read_text()
        proxy = (DATA / "wrongsecrets-proxy.txt").read_text()
        if (
            hashlib.sha256(launcher.encode()).hexdigest() != recipe["launcher_sha256"]
            or hashlib.sha256(proxy.encode()).hexdigest() != recipe["proxy_sha256"]
        ):
            raise ValueError(
                "WrongSecrets launcher or proxy differs from its reviewed hash"
            )
        first = not row["resources"]
        if first:
            prefix = f"ascend-ll-{row['owner'][:8]}-{row['id'][:16]}"
            row["resources"] = {
                "network": prefix + "-net",
                "front_network": prefix + "-front",
                "proxy": prefix + "-proxy",
                "containers": {"app": prefix + "-app"},
                "volumes": {},
                "initializers": {},
            }
            self.runtime.save(row)
        image, pulled = d.image(recipe)
        helper, helper_pulled = d.image({"image": recipe["helper_image"]})
        target, work = self.runtime.runtime_dir(row), self.runtime.work_dir(row)
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        work.mkdir(parents=True, exist_ok=True, mode=0o700)
        downloaded = 0
        for asset in recipe["assets"]:
            source, size = AssetStore(self.runtime.cache).fetch(asset)
            downloaded += size
            name = asset["filename"]
            if name not in {
                "LICENSE",
                "Challenge1.java",
                "Challenge2.java",
                "Challenge3.java",
                "WrongSecretsConstants.java",
                "application.properties",
                "Dockerfile",
            }:
                raise ValueError("Unexpected WrongSecrets source file")
            shutil.copyfile(source, target / name)
        resources = row["resources"]
        for key in ("network", "front_network"):
            if not d.owned("network", resources[key], row):
                if not first:
                    raise ValueError(
                        "Saved WrongSecrets network is missing; export and reset"
                    )
                d.run(
                    "network",
                    "create",
                    *(["--internal"] if key == "network" else []),
                    *d.label_args(row),
                    resources[key],
                )
        app = resources["containers"]["app"]
        if not d.owned("container", app, row):
            if not first:
                raise ValueError(
                    "Saved WrongSecrets container is missing; export and reset"
                )
            d.run(
                "create",
                "--name",
                app,
                *d.label_args(row),
                "--network",
                resources["network"],
                "--dns",
                "127.0.0.1",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--user",
                "2000:2000",
                "--memory",
                "768m",
                "--memory-swap",
                "768m",
                "--cpus",
                "1",
                "--pids-limit",
                "128",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=64m,uid=2000,gid=2000",
                "--log-driver",
                "local",
                "--log-opt",
                "max-size=1m",
                "--log-opt",
                "max-file=2",
                "--env",
                f"ASCEND_LAB_EXPIRES={int(row['expires_at'])}",
                "--env",
                "CHALLENGE59_SLACK_WEBHOOK_URL=",
                "--env",
                "GOOGLE_SERVICE_ACCOUNT_KEY=",
                "--env",
                "GOOGLE_DRIVE_DOCUMENT_ID=",
                "--env",
                "AWS_EC2_METADATA_DISABLED=true",
                "--entrypoint",
                "/bin/sh",
                recipe["image"]["reference"],
                "-c",
                launcher,
            )
        d.run("start", app)
        proxy_name = resources["proxy"]
        if not d.owned("container", proxy_name, row):
            if not first:
                raise ValueError(
                    "Saved WrongSecrets proxy is missing; export and reset"
                )
            d.run(
                "create",
                "--name",
                proxy_name,
                *d.label_args(row),
                "--network",
                resources["front_network"],
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--user",
                "10001:10001",
                "--memory",
                "64m",
                "--memory-swap",
                "64m",
                "--cpus",
                "0.25",
                "--pids-limit",
                "16",
                "--log-driver",
                "local",
                "--log-opt",
                "max-size=1m",
                "--log-opt",
                "max-file=2",
                "--publish",
                "127.0.0.1::8080",
                "--env",
                "PYTHONDONTWRITEBYTECODE=1",
                "--env",
                f"ASCEND_LAB_EXPIRES={row['expires_at']}",
                "--env",
                "ASCEND_TARGET=" + app,
                "--entrypoint",
                "python",
                recipe["helper_image"]["reference"],
                "-I",
                "-S",
                "-c",
                proxy,
            )
            d.run("network", "connect", resources["network"], proxy_name)
        d.run("start", proxy_name)
        info = d.owned("container", proxy_name, row)
        ports = info["NetworkSettings"]["Ports"].get("8080/tcp")
        if not ports or any(p["HostIp"] != "127.0.0.1" for p in ports):
            raise ValueError("WrongSecrets proxy must publish only on loopback")
        row["port"] = int(ports[0]["HostPort"])
        self.runtime.save(row)
        deadline = time.monotonic() + 75
        while True:
            try:
                status, page, _ = request(row["port"], "/challenge/challenge-1")
                if status == 200 and ChallengePage(page).csrf:
                    break
            except (OSError, ValueError, HTTPException):
                pass
            if time.monotonic() >= deadline or not self.alive(row):
                raise ValueError(
                    "WrongSecrets readiness failed: "
                    + d.run("logs", "--tail", "15", app)[-1800:]
                )
            time.sleep(0.4)
        if not (work / "answers.json").exists():
            atomic_json(
                work / "answers.json",
                {**{f"challenge_{i}": "" for i in CHALLENGES}, "explanation": ""},
            )
            (work / "notes.txt").write_text(
                recipe["instructions"] + "\n\nMy observations:\n"
            )
        row["files"] = {
            "source_directory": str(target),
            "answers": str(work / "answers.json"),
            "notes": str(work / "notes.txt"),
        }
        row["endpoints"] = {"challenges": f"http://127.0.0.1:{row['port']}"}
        return {
            "download_bytes": downloaded,
            "image_pulled": pulled,
            "helper_image_pulled": helper_pulled,
            "image_bytes": image["Size"] + helper["Size"],
            "build_cache_bytes": 0,
            "runtime_bytes": sum(p.stat().st_size for p in target.iterdir()),
            "target_memory_limit": 805306368,
            "target_cpus": 1,
            "target_pids": 128,
            "proxy_memory_limit": 67108864,
            "proxy_cpus": 0.25,
            "proxy_pids": 16,
        }

    def check(self, row):
        values = self.runtime.read_work(row, "answers.json", maximum=16384)
        if set(values) != {
            "challenge_1",
            "challenge_2",
            "challenge_3",
            "explanation",
        } or any(not isinstance(v, str) or len(v) > 4000 for v in values.values()):
            raise ValueError(
                "Use three text answers and an explanation of at most 4000 characters"
            )
        checks = []
        try:
            for number in CHALLENGES:
                wrong = answer(
                    row["port"], number, "ascend-invalid-" + secrets.token_hex(16)
                )
                accepted = answer(row["port"], number, values[f"challenge_{number}"])
                checks.extend(
                    [
                        {
                            "id": f"challenge_{number}.answer_accepted",
                            "status": "pass" if accepted else "fail",
                        },
                        {
                            "id": f"challenge_{number}.wrong_answer_rejected",
                            "status": "fail" if wrong else "pass",
                        },
                    ]
                )
            checks.append(
                {
                    "id": "exposure_explanation_present",
                    "status": "pass"
                    if len(values["explanation"].strip()) >= 20
                    else "fail",
                }
            )
        except (OSError, ValueError, HTTPException) as error:
            present = {c["id"] for c in checks}
            checks.extend(
                {"id": name, "status": "error"}
                for name in CHECK_IDS
                if name not in present
            )
            return outcome(checks, detail=str(error)[:500])
        return outcome(
            checks,
            detail="Saved answers were checked by the local WrongSecrets application, with a wrong-answer control for each challenge. Explanation presence only is checked. This does not establish independent discovery; upstream answers and spoilers are public. Only these check statuses synchronize, not the secret answers.",
        )
