"""Fixed, data-only IPv4 policy checker, also runnable with python -I -S.

This is not a sandbox for executable submissions. The only input language is the
bounded schema below; it has no filenames, expressions, plugins or commands.
"""

import ipaddress
import json
import sys
import time

CHECKER_VERSION = "prefix-policy-v1"
MAX_INPUT = 65_536
CHECK_IDS = (
    "customer_aggregate",
    "customer_halves",
    "customer_quarters",
    "overspecific",
    "adjacent",
    "default_route",
    "loopback",
    "unrelated",
    "all_ipv4_prefixes",
)


def assignment(case_key):
    if type(case_key) is not int or not 0 <= case_key <= 65535:
        raise ValueError("Case key must be an integer from 0 to 65535")
    return {
        "version": 1,
        "case_key": case_key,
        "customer_prefix": f"10.{case_key >> 8}.{case_key & 255}.0/24",
        "min_prefix": 24,
        "max_prefix": 26,
    }


def validate_policy(policy):
    if not isinstance(policy, dict) or set(policy) != {"version", "default", "rules"}:
        raise ValueError("policy.json needs only version, default and rules")
    if type(policy["version"]) is not int or policy["version"] != 1:
        raise ValueError("Unsupported policy version")
    if not isinstance(policy["default"], str) or policy["default"] not in {
        "permit",
        "deny",
    }:
        raise ValueError("Default must be permit or deny")
    if not isinstance(policy["rules"], list) or len(policy["rules"]) > 32:
        raise ValueError("Use at most 32 policy rules")
    rules = []
    for rule in policy["rules"]:
        if not isinstance(rule, dict) or set(rule) != {
            "action",
            "prefix",
            "min_prefix",
            "max_prefix",
        }:
            raise ValueError(
                "Each rule needs only action, prefix, min_prefix and max_prefix"
            )
        if not isinstance(rule["action"], str) or rule["action"] not in {
            "permit",
            "deny",
        }:
            raise ValueError("Action must be permit or deny")
        if not isinstance(rule["prefix"], str) or len(rule["prefix"]) > 18:
            raise ValueError("Use a canonical IPv4 prefix")
        try:
            network = ipaddress.IPv4Network(rule["prefix"], strict=True)
        except ValueError:
            raise ValueError("Use a canonical IPv4 prefix") from None
        if str(network) != rule["prefix"]:
            raise ValueError("Use a canonical IPv4 prefix")
        lower, upper = rule["min_prefix"], rule["max_prefix"]
        if (
            type(lower) is not int
            or type(upper) is not int
            or not network.prefixlen <= lower <= upper <= 32
        ):
            raise ValueError(
                "Rule lengths must satisfy prefix length <= min_prefix <= max_prefix <= 32"
            )
        rules.append((rule["action"], network, lower, upper))
    return rules


def decision(route, rules, default):
    for action, network, lower, upper in rules:
        if lower <= route.prefixlen <= upper and route.subnet_of(network):
            return action
    return default


def grade(policy, case_key):
    assigned = assignment(case_key)
    rules = validate_policy(policy)
    customer = ipaddress.IPv4Network(assigned["customer_prefix"])
    base = int(customer.network_address)

    def permits(route):
        return decision(route, rules, policy["default"]) == "permit"

    probes = {
        "customer_aggregate": [customer],
        "customer_halves": list(customer.subnets(new_prefix=25)),
        "customer_quarters": list(customer.subnets(new_prefix=26)),
        "overspecific": [
            ipaddress.IPv4Network((base, 27)),
            ipaddress.IPv4Network((base + 255, 32)),
        ],
        "adjacent": [ipaddress.IPv4Network((base ^ 256, 24))],
        "default_route": [ipaddress.IPv4Network("0.0.0.0/0")],
        "loopback": [
            ipaddress.IPv4Network("127.0.0.0/8"),
            ipaddress.IPv4Network("127.0.0.1/32"),
        ],
        "unrelated": [
            ipaddress.IPv4Network("192.0.2.0/24"),
            ipaddress.IPv4Network("224.0.0.0/4"),
        ],
    }
    positives = {"customer_aggregate", "customer_halves", "customer_quarters"}
    checks = [
        {
            "id": name,
            "status": "pass"
            if all(permits(route) == (name in positives) for route in routes)
            else "fail",
        }
        for name, routes in probes.items()
    ]

    # At fixed route length L, each matching rule covers an interval of canonical
    # route indices. Predicates are constant between their endpoints. Checking
    # one representative per partition proves equivalence for all 2**33-1 IPv4
    # route prefixes, including routes outside the visible example checkset.
    tested, counterexample = 0, None
    for length in range(33):
        shift = 32 - length
        endpoints = {0, 1 << length}
        for _, network, lower, upper in [*rules, ("permit", customer, 24, 26)]:
            if lower <= length <= upper:
                endpoints.update(
                    (
                        int(network.network_address) >> shift,
                        (int(network.broadcast_address) + 1) >> shift,
                    )
                )
        for index in sorted(endpoints)[:-1]:
            route = ipaddress.IPv4Network((index << shift, length))
            expected = 24 <= length <= 26 and route.subnet_of(customer)
            actual = permits(route)
            tested += 1
            if actual != expected and counterexample is None:
                counterexample = {
                    "prefix": str(route),
                    "expected": "permit" if expected else "deny",
                    "actual": "permit" if actual else "deny",
                }
    checks.append(
        {"id": "all_ipv4_prefixes", "status": "fail" if counterexample else "pass"}
    )
    return {
        "checker_version": CHECKER_VERSION,
        "checks": checks,
        "counterexample": counterexample,
        "intervals_checked": tested,
    }


def main():
    import resource

    # Set limits inside the child; preexec_fn is unsafe in a threaded API server.
    for kind, limit in (
        (resource.RLIMIT_CPU, 2),
        (resource.RLIMIT_AS, 134_217_728),
        (resource.RLIMIT_NPROC, 0),
        (resource.RLIMIT_NOFILE, 16),
        (resource.RLIMIT_FSIZE, 32_768),
        (resource.RLIMIT_CORE, 0),
    ):
        resource.setrlimit(kind, (limit, limit))
    started = time.monotonic()
    raw = sys.stdin.buffer.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        raise ValueError("Worker input exceeds 64 KiB")
    data = json.loads(raw)
    if not isinstance(data, dict) or set(data) != {"case_key", "policy"}:
        raise ValueError("Invalid worker input")
    result = grade(data["policy"], data["case_key"])
    usage = resource.getrusage(resource.RUSAGE_SELF)
    with open("/proc/self/status") as stream:
        peak_memory = (
            int(next(line.split()[1] for line in stream if line.startswith("VmHWM:")))
            * 1024
        )
    result["metrics"] = {
        "wall_seconds": time.monotonic() - started,
        "cpu_seconds": usage.ru_utime + usage.ru_stime,
        "peak_memory_bytes": peak_memory,
    }
    encoded = json.dumps(result, allow_nan=False)
    if len(encoded) > 16_384:
        raise ValueError("Worker output exceeds its bound")
    print(encoded)


if __name__ == "__main__":
    main()
