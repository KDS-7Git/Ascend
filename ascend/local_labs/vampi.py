"""Fixed VAmPI comparison adapter; no generic shell or submitted code execution."""

import hashlib
import json
import secrets
import shutil
import time
from http.client import HTTPConnection, HTTPException

from ascend.local_labs.assets import AssetStore
from ascend.local_labs.catalog import DATA
from ascend.local_labs.checks import outcome
from ascend.local_labs.service import ServiceLab

PROFILES = {"vulnerable": "1", "fixed": "0"}
CHECK_IDS = [f"{profile}.{name}" for profile in PROFILES for name in ("owner_read", "cross_user", "anonymous_denied")]


def request_json(port, path, data=None, token=None):
    connection = HTTPConnection("127.0.0.1", int(port), timeout=3)
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        connection.request("POST" if data is not None else "GET", path, json.dumps(data) if data is not None else None, headers)
        response = connection.getresponse()
        body = response.read(65537)
        if len(body) > 65536:
            raise ValueError("Lab response exceeds 64 KiB")
        return response.status, json.loads(body)
    finally:
        connection.close()


class Vampi(ServiceLab):
    def prepare(self, row):
        d, recipe = self.docker, row["recipe"]
        d.provider()
        launcher = (DATA / "vampi-launcher.txt").read_text()
        proxy_code = (DATA / "loopback-proxy.txt").read_text()
        if hashlib.sha256(launcher.encode()).hexdigest() != recipe["launcher_sha256"]:
            raise ValueError("VAmPI launcher differs from its reviewed hash")
        if hashlib.sha256(proxy_code.encode()).hexdigest() != recipe["proxy_sha256"]:
            raise ValueError("Local proxy differs from its reviewed hash")
        first = not row["resources"]
        if first:
            prefix = f"ascend-ll-{row['owner'][:8]}-{row['id'][:16]}"
            row["resources"] = {"network": prefix + "-net", "front_network": prefix + "-front", "proxy": prefix + "-proxy",
                                "containers": {p: prefix + "-" + p for p in PROFILES},
                                "volumes": {p: prefix + "-" + p + "-data" for p in PROFILES},
                                "initializers": {p: prefix + "-" + p + "-init" for p in PROFILES}}
            self.runtime.save(row)
        image, pulled = d.image(recipe)
        target = self.runtime.runtime_dir(row)
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        downloaded = 0
        for asset in recipe["assets"]:
            path, size = AssetStore(self.runtime.cache).fetch(asset)
            downloaded += size
            shutil.copyfile(path, target / "UPSTREAM-LICENSE.txt")
        resources = row["resources"]
        network = resources["network"]
        if not d.owned("network", network, row):
            if not first:
                raise ValueError("The saved lab network is missing; export and reset")
            d.run("network", "create", "--internal", *d.label_args(row), network)
        front_network = resources["front_network"]
        if not d.owned("network", front_network, row):
            if not first:
                raise ValueError("The saved proxy network is missing; export and reset")
            d.run("network", "create", *d.label_args(row), front_network)
        row["ports"] = {}
        for profile, vulnerable in PROFILES.items():
            volume = resources["volumes"][profile]
            if not d.owned("volume", volume, row):
                if not first:
                    raise ValueError("The saved lab volume is missing; export and reset")
                d.run("volume", "create", *d.label_args(row), volume)
                init = resources["initializers"][profile]
                d.run("create", "--name", init, *d.label_args(row), "--network", "none", "--read-only",
                      "--cap-drop", "ALL", "--cap-add", "CHOWN", "--security-opt", "no-new-privileges",
                      "--pids-limit", "16", "--memory", "64m", "--cpus", "0.5", "--user", "0:0",
                      "--mount", f"type=volume,src={volume},dst=/vampi/database", "--entrypoint", "python",
                      recipe["image"]["reference"], "-c", "import os; os.chown('/vampi/database',10001,10001)")
                d.run("start", "-a", init)
                info = d.owned("container", init, row)
                if info["State"]["ExitCode"]:
                    raise ValueError("Database volume initialization failed")
                d.remove("container", init, row)
            name = resources["containers"][profile]
            item = d.owned("container", name, row)
            if not item:
                if not first:
                    raise ValueError("The saved lab container is missing; export and reset")
                d.run("create", "--name", name, *d.label_args(row), "--network", network,
                      "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                      "--pids-limit", "64", "--memory", "128m", "--memory-swap", "128m", "--cpus", "0.5",
                      "--user", "10001:10001",
                      "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m,uid=10001,gid=10001",
                      "--mount", f"type=volume,src={volume},dst=/vampi/database",
                      "--log-driver", "local", "--log-opt", "max-size=1m", "--log-opt", "max-file=2",
                      "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "vulnerable=" + vulnerable,
                      "--env", "tokentimetolive=3600", "--env", f"ASCEND_LAB_EXPIRES={row['expires_at']}",
                      "--entrypoint", "python", recipe["image"]["reference"], "-c", launcher)
            d.run("start", name)
        proxy = resources["proxy"]
        if not d.owned("container", proxy, row):
            if not first:
                raise ValueError("The saved proxy is missing; export and reset")
            targets = {str(5000 + i): resources["containers"][profile] for i, profile in enumerate(PROFILES)}
            d.run("create", "--name", proxy, *d.label_args(row), "--network", front_network,
                  "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                  "--memory", "64m", "--memory-swap", "64m", "--pids-limit", "32", "--cpus", "0.25", "--user", "10001:10001",
                  "--publish", "127.0.0.1::5000", "--publish", "127.0.0.1::5001",
                  "--log-driver", "local", "--log-opt", "max-size=1m", "--log-opt", "max-file=2",
                  "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", f"ASCEND_LAB_EXPIRES={row['expires_at']}",
                  "--env", "ASCEND_TARGETS=" + json.dumps(targets), "--entrypoint", "python",
                  recipe["image"]["reference"], "-c", proxy_code)
            d.run("network", "connect", network, proxy)
        d.run("start", proxy)
        proxy_info = d.owned("container", proxy, row)
        for index, (profile, vulnerable) in enumerate(PROFILES.items()):
            ports = proxy_info["NetworkSettings"]["Ports"].get(f"{5000 + index}/tcp")
            if not ports or any(p["HostIp"] != "127.0.0.1" for p in ports):
                raise ValueError("Lab proxy must publish only on loopback")
            row["ports"][profile] = int(ports[0]["HostPort"])
            self.runtime.save(row)
            deadline = time.monotonic() + 25
            while True:
                try:
                    status, body = request_json(row["ports"][profile], "/")
                    if status == 200 and body.get("vulnerable") == int(vulnerable):
                        break
                except (OSError, ValueError, HTTPException):
                    pass
                if time.monotonic() >= deadline:
                    logs = d.run("logs", "--tail", "20", resources["containers"][profile])
                    raise ValueError("VAmPI readiness timed out: " + logs[-1500:])
                time.sleep(.2)
            if first and request_json(row["ports"][profile], "/createdb")[0] != 200:
                raise ValueError("VAmPI fixture initialization failed")
        work = self.runtime.work_dir(row)
        work.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not (work / "notes.txt").exists():
            (work / "notes.txt").write_text(recipe["instructions"] + "\n\nMy observations:\n")
        row["endpoints"] = {p: f"http://127.0.0.1:{port}" for p, port in row["ports"].items()}
        return {"download_bytes": downloaded, "image_pulled": pulled, "image_bytes": image["Size"],
                "image_compressed_bytes": recipe["image"]["compressed_bytes"], "build_cache_bytes": 0,
                "memory_limit_per_target": 134217728, "cpus_per_target": .5, "pids_per_target": 64,
                "proxy_memory_limit": 67108864, "proxy_cpus": .25, "proxy_pids": 32}

    def check(self, row):
        checks = []
        try:
            for profile, port in row["ports"].items():
                def login(name, password, port=port):
                    status, result = request_json(port, "/users/v1/login", {"username": name, "password": password})
                    if status != 200 or not result.get("auth_token"):
                        raise ValueError("The known fixture accounts could not log in")
                    return result["auth_token"]
                owner, other = login("name1", "pass1"), login("name2", "pass2")
                title, secret = "ascend-check-" + secrets.token_hex(8), secrets.token_hex(16)
                if request_json(port, "/books/v1", {"book_title": title, "secret": secret}, owner)[0] != 200:
                    raise ValueError("The owner could not create a control book")
                owner_status, own = request_json(port, "/books/v1/" + title, token=owner)
                other_status, cross = request_json(port, "/books/v1/" + title, token=other)
                anonymous_status, anon = request_json(port, "/books/v1/" + title)
                checks.extend([
                    {"id": profile + ".owner_read", "status": "pass" if owner_status == 200 and own.get("secret") == secret else "fail"},
                    {"id": profile + ".cross_user", "status": "pass" if ((other_status == 200 and cross.get("secret") == secret) if profile == "vulnerable" else (other_status == 404 and "secret" not in cross)) else "fail"},
                    {"id": profile + ".anonymous_denied", "status": "pass" if anonymous_status == 401 and "secret" not in anon else "fail"},
                ])
        except (OSError, ValueError, HTTPException) as error:
            present = {c["id"] for c in checks}
            checks.extend({"id": name, "status": "error"} for name in CHECK_IDS if name not in present)
            return outcome(checks, detail=str(error)[:500])
        return outcome(checks, detail="Reference behavior comparison, including owner and anonymous controls. This checks the environments, not independent solving or the security of the entire API.")
