"""Portable infrastructure artifact workshop. It never provisions infrastructure.

Native commands and operational acceptance controls live in lessons/*.md.
An artifact pass is local feedback, not an Ascend skill-verification receipt.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import ipaddress
import json
import math
from pathlib import Path
import shutil
import statistics
import sys
import xml.etree.ElementTree as ET
from email import policy
from email.parser import BytesParser

ROOT = Path(__file__).resolve().parent
MAX_INPUT = 1024 * 1024


def read_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_INPUT:
        raise ValueError("Input exceeds this workshop's 1 MiB bound")
    return json.loads(path.read_text())


def field(data, dotted):
    value = data
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"Missing field: {dotted}")
        value = value[part]
    return value


def evaluate(candidate, rules):
    """Interpret a data-only rubric; never eval strings or execute commands."""
    findings = []
    for rule in rules:
        try:
            actual = field(candidate, rule["field"])
            op = rule["op"]
            expected = rule.get("value")
            numeric = (
                isinstance(actual, (int, float))
                and not isinstance(actual, bool)
                and math.isfinite(actual)
            )
            if op == "eq":
                valid = type(actual) is type(expected) and actual == expected
            elif op == "in":
                valid = actual in expected
            elif op == "min":
                valid = numeric and actual >= expected
            elif op == "max":
                valid = numeric and actual <= expected
            elif op == "same":
                valid = actual == field(candidate, expected)
            elif op == "different":
                valid = actual != field(candidate, expected)
            elif op == "subset":
                valid = isinstance(actual, list) and set(actual) <= set(expected)
            elif op == "contains":
                valid = isinstance(actual, list) and all(
                    value in actual for value in expected
                )
            elif op == "unique":
                valid = isinstance(actual, list) and len(actual) == len(set(actual))
            elif op == "cidr_contains":
                network = ipaddress.ip_network(actual, strict=False)
                valid = ipaddress.ip_address(expected) in network
            elif op == "cidr_excludes":
                network = ipaddress.ip_network(actual, strict=False)
                valid = ipaddress.ip_address(expected) not in network
            elif op == "sum_max":
                values = [field(candidate, name) for name in rule["fields"]]
                valid = all(
                    isinstance(v, (int, float))
                    and not isinstance(v, bool)
                    and math.isfinite(v)
                    and v >= 0
                    for v in values
                )
                valid = valid and sum(values) <= expected
            elif op == "near":
                valid = numeric and abs(actual - expected) <= rule.get(
                    "tolerance", 0.001
                )
            else:
                raise ValueError(f"Unsupported rule operator: {op}")
            findings.append(
                {"control": rule["why"], "passed": bool(valid), "field": rule["field"]}
            )
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            findings.append(
                {"control": rule["why"], "passed": False, "error": str(error)}
            )
    return {
        "scope": "Local configuration/artifact reasoning only; native operational checks remain separate.",
        "passed": bool(findings) and all(item["passed"] for item in findings),
        "controls": findings,
    }


def case_for(level, variant):
    if not isinstance(level, str) or not level.isdigit() or not 1 <= int(level) <= 8:
        raise ValueError("Choose a level 01..08")
    if variant not in {"guided", "transfer"}:
        raise ValueError("Choose the guided or transfer case")
    return read_json(ROOT / "cases" / f"{int(level):02d}-{variant}.json")


def prepare(args, reference=False):
    case = case_for(args.level, args.variant)
    destination = Path(args.out).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    try:
        (destination / "assignment.json").write_text(
            json.dumps(
                {
                    "level": f"{int(args.level):02d}",
                    "variant": args.variant,
                    "scope": case["scope"],
                    "brief": case["brief"],
                    "contract": case["rules"],
                    "starting_point": "reference (help used)"
                    if reference
                    else "broken practice case",
                },
                indent=2,
            )
            + "\n"
        )
        value = case["reference"] if reference else case["starting"]
        (destination / "candidate.json").write_text(json.dumps(value, indent=2) + "\n")
        inputs = ROOT / "inputs" / f"{int(args.level):02d}"
        if inputs.exists():
            shutil.copytree(inputs, destination / "inputs")
    except Exception:
        # This newly created directory is owned by this operation only.
        shutil.rmtree(destination)
        raise
    print(f"{'REFERENCE (help used)' if reference else 'WORKSPACE'}: {destination}")
    print(case["brief"])
    print(
        "Edit candidate.json, then check this directory. Native work is in the corresponding lesson."
    )


def check(args):
    destination = Path(args.workspace).resolve()
    assignment = read_json(destination / "assignment.json")
    case = case_for(assignment["level"], assignment["variant"])
    result = evaluate(read_json(destination / "candidate.json"), case["rules"])
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


def analyze(path):
    path = Path(path)
    if path.stat().st_size > MAX_INPUT:
        raise ValueError("CSV exceeds the 1 MiB workshop bound")
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or len(rows) > 10000:
        raise ValueError("Expected 1..10,000 request records")
    durations = [float(row["duration_ms"]) for row in rows]
    arrivals = [float(row["arrival_ms"]) for row in rows]
    if any(not math.isfinite(value) or value < 0 for value in durations + arrivals):
        raise ValueError("Durations and arrivals must be finite and nonnegative")
    statuses = [int(row["status"]) for row in rows]
    if any(value != 0 and not 100 <= value <= 599 for value in statuses):
        raise ValueError(
            "Status must be 0 for no response or an HTTP status from 100..599"
        )
    successes = [
        value for value, status in zip(durations, statuses) if 200 <= status < 300
    ]
    window = max(a + d for a, d in zip(arrivals, durations)) - min(arrivals)
    if window <= 0:
        raise ValueError("Observation window must be positive")
    ordered = sorted(durations)
    result = {
        "requests": len(rows),
        "successes": len(successes),
        "errors": len(rows) - len(successes),
        "all_request_mean_ms": statistics.mean(durations),
        "all_request_p95_ms": ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)],
        "observation_window_ms": window,
        "successful_rps": len(successes) / (window / 1000),
        "scope": "CSV observations, not a benchmark of this machine; errors remain in latency accounting.",
    }
    print(json.dumps(result, indent=2))


def inspect_vm(path):
    path = Path(path)
    if path.stat().st_size > MAX_INPUT:
        raise ValueError("XML exceeds workshop bound")
    raw = path.read_text(encoding="utf-8")
    if "<!DOCTYPE" in raw.upper() or "<!ENTITY" in raw.upper():
        raise ValueError("External/entity-bearing XML is not accepted")
    root = ET.fromstring(raw)
    if root.tag != "domain":
        raise ValueError("Expected a libvirt domain definition")
    print(
        json.dumps(
            {
                "name": root.findtext("name"),
                "hypervisor": root.get("type"),
                "vcpus": root.findtext("vcpu"),
                "memory": root.findtext("memory"),
                "configured_current_vcpus": root.find("vcpu").get("current")
                if root.find("vcpu") is not None
                else None,
                "memory_unit": root.find("memory").get("unit", "KiB")
                if root.find("memory") is not None
                else None,
                "disk_sources": [
                    item.attrib for item in root.findall("./devices/disk/source")
                ],
                "interfaces": [
                    item.attrib for item in root.findall("./devices/interface/source")
                ],
                "scope": "Definition inspection only; this does not create or inspect a running guest.",
            },
            indent=2,
        )
    )


def inspect_mail(path):
    path = Path(path)
    if path.stat().st_size > MAX_INPUT:
        raise ValueError("Message exceeds workshop bound")
    raw = path.read_bytes()
    mail = BytesParser(policy=policy.default).parsebytes(raw)
    print(
        json.dumps(
            {
                key: str(mail.get(key, ""))
                for key in [
                    "From",
                    "To",
                    "Subject",
                    "Message-ID",
                    "Authentication-Results",
                ]
            }
            | {
                "scope": "Header parsing only; displayed authentication claims are not independently verified."
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["prepare", "reference"]:
        command = commands.add_parser(name)
        command.add_argument("level")
        command.add_argument(
            "--variant", choices=["guided", "transfer"], default="guided"
        )
        command.add_argument("--out", required=True)
    command = commands.add_parser("check")
    command.add_argument("workspace")
    for name in ["analyze", "inspect-vm", "inspect-mail", "fingerprint"]:
        command = commands.add_parser(name)
        command.add_argument("path")
    args = parser.parse_args()
    try:
        if args.command in {"prepare", "reference"}:
            prepare(args, args.command == "reference")
        elif args.command == "check":
            return check(args)
        elif args.command == "analyze":
            analyze(args.path)
        elif args.command == "inspect-vm":
            inspect_vm(args.path)
        elif args.command == "inspect-mail":
            inspect_mail(args.path)
        elif args.command == "fingerprint":
            path = Path(args.path)
            if path.stat().st_size > MAX_INPUT:
                raise ValueError("File exceeds workshop bound")
            print(
                json.dumps(
                    {
                        "file": str(path),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
            )
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        OverflowError,
        RecursionError,
        ET.ParseError,
    ) as error:
        print(f"Workshop error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
