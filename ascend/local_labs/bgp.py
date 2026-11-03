"""Bounded FRR execution of three pinned BGP Labs control-plane exercises.

Only bgpd runs: there is no kernel router, privileged container, host network,
published port, or writable host mount. The learner configures the owned router
with vtysh. Named volumes preserve its configuration across stop/resume.
"""

import hashlib
import ipaddress
import json
import shutil
import time

from ascend.local_labs.assets import AssetStore, atomic_json
from ascend.local_labs.catalog import DATA
from ascend.local_labs.checks import outcome
from ascend.local_labs.docker import Docker

RECIPES = {"bgp-single-session", "bgp-session-protection", "bgp-prefix-filter"}


def initial_config(recipe_id, node, addresses):
    """FRR translation of the selected upstream AS numbers and route fixtures."""
    if recipe_id not in RECIPES or node not in addresses:
        raise ValueError("Unknown BGP fixture")
    asns = {"rtr": 65000, "x1": 65100, "x2": 65101}
    router_ids = {"rtr": "10.0.0.1", "x1": "10.0.0.10", "x2": "10.0.0.11"}
    lines = [
        "frr defaults traditional",
        f"hostname {node}",
        "log stdout",
        "!",
        f"router bgp {asns[node]}",
        f" bgp router-id {router_ids[node]}",
        " no bgp ebgp-requires-policy",
        " no bgp network import-check",
        " bgp log-neighbor-changes",
    ]
    if node == "rtr":
        if recipe_id != "bgp-single-session":
            for peer in ("x1", "x2"):
                lines.append(f" neighbor {addresses[peer]} remote-as {asns[peer]}")
                lines.append(f" neighbor {addresses[peer]} timers connect 1")
        lines += [" address-family ipv4 unicast", "  network 192.168.42.0/24"]
        if recipe_id == "bgp-prefix-filter":
            lines.append("  network 10.0.0.1/32")
        lines.append(" exit-address-family")
    else:
        peers = ["rtr"]
        if recipe_id == "bgp-prefix-filter":
            peers.append("x2" if node == "x1" else "x1")
        for peer in peers:
            lines.append(f" neighbor {addresses[peer]} remote-as {asns[peer]}")
            lines.append(f" neighbor {addresses[peer]} timers connect 1")
        if recipe_id == "bgp-session-protection":
            lines.append(
                f" neighbor {addresses['rtr']} "
                + ("ttl-security hops 1" if node == "x1" else "password GuessWhat")
            )
        lines += [
            " address-family ipv4 unicast",
            f"  neighbor {addresses['rtr']} default-originate",
        ]
        if recipe_id != "bgp-single-session":
            lines.append(
                "  network "
                + ("192.168.100.0/24" if node == "x1" else "192.168.101.0/24")
            )
        lines.append(" exit-address-family")
    return "\n".join(lines + ["!", "line vty", "!"]) + "\n"


class BgpLab:
    def __init__(self, runtime):
        self.runtime, self.docker = runtime, Docker(runtime)

    def command(self, row, node, *commands):
        name = row["resources"]["containers"][node]
        info = self.docker.owned("container", name, row)
        if not info or not info["State"]["Running"]:
            raise ValueError("A BGP router is missing or stopped")
        return self.docker.run(
            "exec",
            name,
            "vtysh",
            "-d",
            "bgpd",
            *(arg for command in commands for arg in ("-c", command)),
        )

    def configure_peer(self, row, node, *commands):
        router_peer = row["addresses"][node]
        control_peer = row["addresses"]["rtr"]
        self.command(
            row,
            "rtr",
            "configure terminal",
            "router bgp 65000",
            f"neighbor {router_peer} shutdown",
            "end",
        )
        try:
            self.command(
                row,
                node,
                "configure terminal",
                f"router bgp {65100 if node == 'x1' else 65101}",
                f"neighbor {control_peer} shutdown",
                *commands,
                "end",
            )
            if not self.wait_session(row, node, expected=False, timeout=3):
                raise ValueError("The external control session did not close")
            self.command(
                row,
                node,
                "configure terminal",
                f"router bgp {65100 if node == 'x1' else 65101}",
                f"no neighbor {control_peer} shutdown",
                "end",
            )
            self.reload_router(row, node)
        finally:
            self.command(
                row,
                "rtr",
                "configure terminal",
                "router bgp 65000",
                f"no neighbor {router_peer} shutdown",
                "end",
            )
            self.command(
                row,
                node,
                "configure terminal",
                f"router bgp {65100 if node == 'x1' else 65101}",
                f"no neighbor {control_peer} shutdown",
                "end",
            )

    def summary(self, row, node):
        data = json.loads(self.command(row, node, "show bgp ipv4 unicast summary json"))
        peers = data.get("ipv4Unicast", data).get("peers")
        if not isinstance(peers, dict):
            # No peers is the intended initial single-session task state.
            if data == {}:
                return {}
            raise ValueError("FRR did not return its expected BGP summary")
        return peers

    def established(self, row, node, peer="rtr"):
        return (
            self.summary(row, node).get(row["addresses"][peer], {}).get("state")
            == "Established"
        )

    def wait_session(self, row, node, expected=True, timeout=12):
        deadline = time.monotonic() + timeout
        while True:
            if self.established(row, node) == expected:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.2)

    def observe_routes(self, row, node, *, filtered=False, timeout=8):
        """Wait for updates after establishment and require a stable control pair."""
        deadline = time.monotonic() + timeout
        stable_since = None
        while True:
            table = json.loads(self.command(row, node, "show bgp ipv4 unicast json"))
            routes = table.get("routes")
            if not isinstance(routes, dict):
                raise ValueError("FRR did not return its route table")
            expected = (
                self.established(row, node)
                and "192.168.42.0/24" in routes
                and (not filtered or "10.0.0.1/32" not in routes)
            )
            now = time.monotonic()
            if expected:
                if stable_since is None:
                    stable_since = now
                if now - stable_since >= 1:
                    return table, True
            else:
                stable_since = None
            if now >= deadline:
                return table, False
            time.sleep(0.2)

    def reload_router(self, row, node="rtr"):
        """Reapply TTL settings to fresh sockets after interactive changes."""
        self.command(row, node, "write memory")
        self.docker.run("restart", "--time", "3", row["resources"]["containers"][node])
        deadline = time.monotonic() + 8
        while True:
            try:
                if "FRRouting 8.4.1" in self.command(row, node, "show version"):
                    return
            except (ValueError, OSError):
                pass
            if time.monotonic() >= deadline:
                raise ValueError("The router could not reload its saved configuration")
            time.sleep(0.2)

    def recover_probe(self, row):
        peer = row.get("active_probe")
        if peer is None:
            return
        if peer not in {"x1", "x2"}:
            raise ValueError("Unknown interrupted BGP control")
        address = row["addresses"]["rtr"]
        commands = (
            [
                f"no neighbor {address} ebgp-multihop 2",
                f"neighbor {address} ttl-security hops 1",
            ]
            if peer == "x1"
            else [f"neighbor {address} password GuessWhat"]
        )
        self.configure_peer(row, peer, *commands)
        row.pop("active_probe")
        self.runtime.save(row)

    def prepare(self, row):
        recipe, d = row["recipe"], self.docker
        d.provider()
        launcher = (DATA / "bgp-launcher.txt").read_text()
        if hashlib.sha256(launcher.encode()).hexdigest() != recipe["launcher_sha256"]:
            raise ValueError("BGP launcher differs from its reviewed hash")
        if hashlib.sha256(_adapter_bytes()).hexdigest() != recipe["adapter_sha256"]:
            raise ValueError("BGP adapter differs from its reviewed hash")
        first = not row["resources"]
        if first:
            prefix = f"ascend-bgp-{row['owner'][:8]}-{row['id'][:16]}"
            nodes = ["rtr", "x1"] + (
                [] if recipe["id"] == "bgp-single-session" else ["x2"]
            )
            row["resources"] = {
                "network": prefix + "-net",
                "containers": {n: prefix + "-" + n for n in nodes},
                "volumes": {n: prefix + "-" + n + "-config" for n in nodes},
            }
            self.runtime.save(row)
        image, pulled = d.image(recipe)
        target = self.runtime.runtime_dir(row)
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        downloaded = 0
        for asset in recipe["assets"]:
            path, size = AssetStore(self.runtime.cache).fetch(asset)
            downloaded += size
            shutil.copyfile(path, target / asset["path"].replace("/", "-"))
        resources = row["resources"]
        if not d.owned("network", resources["network"], row):
            if not first:
                raise ValueError("The saved BGP network is missing; export and reset")
            d.run(
                "network",
                "create",
                "--internal",
                *d.label_args(row),
                resources["network"],
            )
        net = d.owned("network", resources["network"], row)
        if not net["Internal"]:
            raise ValueError("BGP requires its private internal network")
        subnet = ipaddress.ip_network(
            next(c["Subnet"] for c in net["IPAM"]["Config"] if ":" not in c["Subnet"])
        )
        if first:
            row["addresses"] = {
                n: str(subnet.network_address + i)
                for n, i in (("rtr", 2), ("x1", 10), ("x2", 11))
                if n in resources["containers"]
            }
            self.runtime.save(row)
        for node, name in resources["containers"].items():
            volume = resources["volumes"][node]
            if not d.owned("volume", volume, row):
                if not first:
                    raise ValueError("The saved BGP configuration volume is missing")
                d.run("volume", "create", *d.label_args(row), volume)
            if not d.owned("container", name, row):
                if not first:
                    raise ValueError(
                        "The saved BGP container is missing; export and reset"
                    )
                d.run(
                    "create",
                    "--name",
                    name,
                    *d.label_args(row),
                    "--network",
                    resources["network"],
                    "--ip",
                    row["addresses"][node],
                    "--read-only",
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges",
                    "--user",
                    "100:101",
                    "--sysctl",
                    "net.ipv4.ip_unprivileged_port_start=0",
                    "--memory",
                    "128m",
                    "--memory-swap",
                    "128m",
                    "--cpus",
                    "0.5",
                    "--pids-limit",
                    "32",
                    "--tmpfs",
                    "/run/frr:rw,nosuid,noexec,size=8m,uid=100,gid=101",
                    "--tmpfs",
                    "/tmp:rw,nosuid,noexec,size=8m,uid=100,gid=101",
                    "--tmpfs",
                    "/var/tmp/frr:rw,nosuid,noexec,size=8m,uid=100,gid=101",
                    "--mount",
                    f"type=volume,src={volume},dst=/etc/frr",
                    "--log-driver",
                    "local",
                    "--log-opt",
                    "max-size=1m",
                    "--log-opt",
                    "max-file=2",
                    "--env",
                    f"ASCEND_LAB_EXPIRES_AT={int(row['expires_at'])}",
                    "--entrypoint",
                    "/bin/sh",
                    recipe["image"]["reference"],
                    "-c",
                    launcher,
                )
                config = target / (node + ".conf")
                config.write_text(initial_config(recipe["id"], node, row["addresses"]))
                # Docker cp preserves mode. The non-root router must be able to
                # read these authored configs even when the runner uses umask 077.
                config.chmod(0o644)
                d.run("cp", str(config), name + ":/etc/frr/frr.conf")
                vty = target / "vtysh.conf"
                vty.write_text("service integrated-vtysh-config\n")
                vty.chmod(0o644)
                d.run("cp", str(vty), name + ":/etc/frr/vtysh.conf")
            d.run("start", name)
        deadline = time.monotonic() + 12
        for node in resources["containers"]:
            while True:
                try:
                    if "FRRouting 8.4.1" in self.command(row, node, "show version"):
                        break
                except (ValueError, OSError):
                    pass
                if time.monotonic() > deadline:
                    raise ValueError(
                        "BGP readiness failed: "
                        + d.run("logs", "--tail", "10", resources["containers"][node])
                    )
                time.sleep(0.2)
        work = self.runtime.work_dir(row)
        work.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not (work / "notes.txt").exists():
            (work / "notes.txt").write_text(
                recipe["instructions"] + "\n\nMy observations:\n"
            )
        row["connect_commands"] = {
            n: f"docker exec -it {name} vtysh -d bgpd"
            for n, name in resources["containers"].items()
        }
        row["fixture"] = {
            "customer_prefix": "192.168.42.0/24",
            "router_loopback": "10.0.0.1/32",
            "router_as": 65000,
            "peer_as": {
                n: 65100 if n == "x1" else 65101
                for n in resources["containers"]
                if n != "rtr"
            },
        }
        return {
            "download_bytes": downloaded,
            "image_pulled": pulled,
            "image_bytes": image["Size"],
            "image_compressed_bytes": recipe["image"]["compressed_bytes"],
            "build_cache_bytes": 0,
            "memory_limit_per_router": 134217728,
            "cpus_per_router": 0.5,
            "pids_per_router": 32,
        }

    def alive(self, row):
        return bool(row["resources"].get("containers")) and all(
            (item := self.docker.owned("container", name, row))
            and item["State"]["Running"]
            for name in row["resources"]["containers"].values()
        )

    def check(self, row):
        checks, traces = [], {}

        def add(name, passed):
            checks.append({"id": name, "status": "pass" if passed else "fail"})

        try:
            if not self.alive(row):
                raise ValueError("The BGP environment is missing or stopped")
            if row["recipe"]["id"] == "bgp-session-protection":
                # FRR 8.4.1 can retain an earlier accepted socket's TTL behavior
                # after GTSM is removed and restored interactively. Reload the
                # saved learner configuration before performing fresh probes.
                self.recover_probe(row)
                self.reload_router(row)
                traces["router_reloaded"] = True
            for peer in [n for n in row["resources"]["containers"] if n != "rtr"]:
                up = self.wait_session(row, peer, timeout=8)
                add("session." + peer, up)
                if row["recipe"]["id"] != "bgp-single-session":
                    table, settled = self.observe_routes(
                        row,
                        peer,
                        filtered=row["recipe"]["id"] == "bgp-prefix-filter",
                        timeout=8 if up else 0,
                    )
                    up = up and self.established(row, peer)
                    checks[-1]["status"] = "pass" if up else "fail"
                    routes = table["routes"]
                    traces[peer] = table
                    add(
                        (
                            "adv_pfx."
                            if row["recipe"]["id"] == "bgp-prefix-filter"
                            else "prefix."
                        )
                        + peer,
                        up and settled and "192.168.42.0/24" in routes,
                    )
                    if row["recipe"]["id"] == "bgp-prefix-filter":
                        add(
                            "drop_pfx." + peer,
                            up and settled and "10.0.0.1/32" not in routes,
                        )
            if row["recipe"]["id"] == "bgp-session-protection":
                # Change only the authored external controls, then restore them.
                # A configuration string alone is not a negative runtime probe.
                for peer, bad, restore, name in (
                    (
                        "x1",
                        [
                            f"no neighbor {row['addresses']['rtr']} ttl-security hops 1",
                            f"neighbor {row['addresses']['rtr']} ebgp-multihop 2",
                        ],
                        [
                            f"no neighbor {row['addresses']['rtr']} ebgp-multihop 2",
                            f"neighbor {row['addresses']['rtr']} ttl-security hops 1",
                        ],
                        "gtsm.rejected",
                    ),
                    (
                        "x2",
                        [
                            f"neighbor {row['addresses']['rtr']} password DeliberatelyWrong"
                        ],
                        [f"neighbor {row['addresses']['rtr']} password GuessWhat"],
                        "md5.rejected",
                    ),
                ):
                    baseline = self.established(row, peer)
                    if not baseline:
                        add(name, False)
                        continue
                    row["active_probe"] = peer
                    self.runtime.save(row)
                    try:
                        self.configure_peer(row, peer, *bad)
                        denied = not self.wait_session(row, peer, timeout=5)
                    finally:
                        self.configure_peer(row, peer, *restore)
                        row.pop("active_probe", None)
                        self.runtime.save(row)
                    recovered = self.wait_session(row, peer, timeout=30)
                    traces[name] = {
                        "baseline": baseline,
                        "denied": denied,
                        "recovered": recovered,
                    }
                    add(name, baseline and denied and recovered)
            atomic_json(self.runtime.work_dir(row) / "bgp-observations.json", traces)
            return outcome(checks, detail=row["recipe"]["check_meaning"])
        except (ValueError, OSError, json.JSONDecodeError) as error:
            return outcome(
                [{"id": "bgp_runtime", "status": "error"}], detail=str(error)
            )

    def stop(self, row):
        for node in row["resources"]["containers"]:
            self.command(row, node, "write memory")
        for name in row["resources"]["containers"].values():
            self.docker.run("stop", "--time", "3", name)

    def submission(self, row):
        if not row.get("last_check"):
            raise ValueError("Run local-lab check before exporting BGP observations")
        for node in row["resources"]["containers"]:
            if self.alive(row):
                content = self.command(row, node, "show running-config")
                (self.runtime.work_dir(row) / (node + "-config.txt")).write_text(
                    content + "\n"
                )
        atomic_json(self.runtime.work_dir(row) / "checks.json", row["last_check"])
        return {"report": {"checks": row["last_check"]["checks"]}}

    def destroy(self, row):
        errors = []
        resources = row.get("resources", {})
        for kind, names in (
            ("container", resources.get("containers", {}).values()),
            ("volume", resources.get("volumes", {}).values()),
            ("network", [resources["network"]] if resources.get("network") else []),
        ):
            for name in names:
                try:
                    self.docker.remove(kind, name, row)
                except (ValueError, OSError) as error:
                    errors.append(str(error))
        if errors:
            raise ValueError("; ".join(errors))
        target = self.runtime.runtime_dir(row)
        if target.is_symlink():
            raise ValueError("BGP runtime directory is a symlink")
        if target.exists():
            shutil.rmtree(target)


def _adapter_bytes():
    from pathlib import Path

    return Path(__file__).read_bytes()
