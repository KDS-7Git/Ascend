"""Authored contracts. A local invocation has local authority only."""

import json

MAX_RESULT_BYTES = 1_048_576


def bounded(value, maximum=MAX_RESULT_BYTES):
    if not isinstance(value, dict):
        raise ValueError("Use a JSON object")  # noqa: TRY004 - HTTP validation contract.
    try:
        size = len(json.dumps(value, allow_nan=False).encode())
    except (ValueError, TypeError, RecursionError):
        raise ValueError("Invalid JSON result") from None
    if size > maximum:
        raise ValueError("Result exceeds the allowed size")
    return value


def outcome(checks, *, label="Checked on this PC", authority="local", detail=None):
    status = (
        "unsupported"
        if not checks
        else (
            "error"
            if any(
                c.get("status") not in {"pass", "fail", "unsupported"} for c in checks
            )
            else "unsupported"
            if any(c["status"] == "unsupported" for c in checks)
            else "fail"
            if any(c["status"] == "fail" for c in checks)
            else "pass"
        )
    )
    return {
        "status": status,
        "checks": checks,
        "evidence_label": label,
        "authority": authority,
        "satisfies_track_evidence": False,
        "xp": 0,
        "detail": detail,
    }


def answer_check(answers):
    bounded(answers)
    expected = {
        "discovery_event_id": "92733",
        "executable": "/usr/sbin/arp",
        "arguments": ["arp", "-a"],
        "companion_event_id": "92734",
        "uid": 1000,
        "benign_event_ids": ["control-1"],
        "intent": "insufficient-evidence",
    }
    allowed = set(expected) | {"explanation"}
    if set(answers) - allowed:
        raise ValueError(
            "Unexpected answer fields; submit answers, not a claimed result"
        )
    checks = []
    for key, value in expected.items():
        ok = type(answers.get(key)) is type(value) and answers[key] == value
        checks.append({"id": key, "status": "pass" if ok else "fail"})
    explanation = answers.get("explanation")
    checks.append(
        {
            "id": "explanation_present",
            "status": "pass"
            if isinstance(explanation, str) and 20 <= len(explanation.strip()) <= 4000
            else "fail",
        }
    )
    return outcome(
        checks,
        detail="Matches an authored answer rubric; the explanation is checked for presence only. Command telemetry alone cannot establish intent.",
    )


def local_report(report, recipe):
    """Validate the report shape without promoting it to trusted observations."""
    bounded(report)
    if set(report) != {"checks"} or not isinstance(report["checks"], list):
        raise ValueError("A local report contains only checks")
    required = recipe.get("check_ids", [])
    checks = report["checks"]
    if not required or len(checks) != len(required):
        raise ValueError("Missing or extra local checks")
    if any(
        not isinstance(c, dict)
        or set(c) != {"id", "status"}
        or not isinstance(c["id"], str)
        or not isinstance(c["status"], str)
        or c["status"] not in {"pass", "fail", "error", "unsupported"}
        for c in checks
    ):
        raise ValueError("Invalid local check")
    if sorted(c["id"] for c in checks) != sorted(required):
        raise ValueError("Local check set does not match the recipe")
    return outcome(
        checks,
        detail="Learner-controlled local report; the server did not observe this environment.",
    )
