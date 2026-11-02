"""Pure, deliberately limited per-skill readiness and review recommendations."""

from datetime import date, timedelta
from math import ceil


def readiness(evidence):
    result = {}
    for skill in {e["skill"] for e in evidence}:
        rows = [e for e in evidence if e["skill"] == skill]
        solves = {
            e["fixture_key"]
            for e in rows
            if e["outcome"] == "passed" and e["independent"]
        }
        transfer = any(e["transfer"] and e["independent"] for e in rows)
        result[skill] = (
            "demonstrated"
            if len(solves) >= 2 and transfer
            else "developing"
            if solves
            else "introduced"
            if any(e["outcome"] in {"example", "passed"} for e in rows)
            else "developing"
            if any(e["outcome"] == "needs-practice" for e in rows)
            else "unknown"
        )
    return result


def ready(activity, skills):
    if activity["role"] == "example" or activity["kind"] == "free":
        return True
    required = (
        "demonstrated"
        if activity["format"] == "mystery" or activity["difficulty"] != "easy"
        else None
    )
    return all(
        skills.get(skill, "unknown") == required
        if required
        else skills.get(skill, "unknown") != "unknown"
        for skill in activity["skills"]
    )


def review_due(evidence, today):
    due = {}
    for skill in {e["skill"] for e in evidence}:
        rows = sorted(
            (e for e in evidence if e["skill"] == skill), key=lambda e: e["day"]
        )
        assessed = [e for e in rows if e["outcome"] != "example"]
        if not assessed:
            continue
        consecutive, distinct = 0, set()
        for row in assessed:
            if row["outcome"] == "needs-practice" or not row["independent"]:
                consecutive, distinct = 0, set()
            elif row["fixture_key"] not in distinct:
                distinct.add(row["fixture_key"])
                consecutive += 1
        interval = (1, 3, 7, 14)[min(max(consecutive - 1, 0), 3)]
        day = date.fromisoformat(assessed[-1]["day"]) + timedelta(days=interval)
        due[skill] = {"day": day.isoformat(), "due": day <= today}
    return due


def recommend(catalog, evidence, history, today, exclude=(), limit=3, feedback=()):
    skills, due = readiness(evidence), review_due(evidence, today)
    recent = [r["activity_id"] for r in history[:5]]
    latest = {e["skill"]: e for e in evidence if e["outcome"] != "example"}
    feedback_by_activity = {f["activity_id"]: f for f in feedback}

    def rank(a):
        missed = any(
            latest.get(skill, {}).get("outcome") == "needs-practice"
            for skill in a["skills"]
        )
        familiar_only = (
            a["variant_strategy"] == "authored"
            and len({r["fixture_key"] for r in history if r["activity_id"] == a["id"]})
            >= 3
        )
        response = feedback_by_activity.get(a["id"], {})
        unwanted = response.get("repetition") == "unwanted-repeat"
        demanding = response.get("difficulty") == "too-hard" and not response.get(
            "environment_issue"
        )
        return (
            unwanted,
            demanding,
            familiar_only,
            a["id"] in recent[:1],
            not missed,
            not any(due.get(s, {}).get("due") for s in a["skills"]),
            a["role"] == "example"
            and all(skills.get(s, "unknown") != "unknown" for s in a["skills"]),
            a["id"] in recent,
            sum(r["activity_id"] == a["id"] for r in history),
            a["minutes"],
            a["id"],
        )

    return sorted(
        (a for a in catalog if a["id"] not in exclude and ready(a, skills)), key=rank
    )[:limit]


def selection_minutes(activity, feedback):
    """Conservative personal pace from completed, clear, problem-free reports.

    No wall-clock idle time or self-reported difficulty promotes readiness.
    Three distinct runs are required; authored durations remain the floor.
    """
    samples = {
        f["run_id"]: f["working_minutes"] + f["setup_minutes"]
        for f in feedback
        if f["activity_id"] == activity["id"]
        and f["status"] == "passed"
        and f["clarity"] == "clear"
        and not f["environment_issue"]
    }
    if len(samples) < 3:
        return activity["minutes"] + activity["setup_minutes"], len(samples)
    values = sorted(samples.values())
    return max(
        activity["minutes"] + activity["setup_minutes"],
        values[ceil(len(values) * 0.75) - 1],
    ), len(values)
