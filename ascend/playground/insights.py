"""Local, user-scoped practice feedback. Observations never award learning credit."""

from datetime import timedelta
import json


def feedback_rows(p):
    runs = {r["id"]: r for r in p.history_rows()}
    return [
        {
            **r,
            "activity_id": runs[r["run_id"]]["activity_id"],
            "status": runs[r["run_id"]]["status"],
        }
        for r in p.db.rows("activity_feedback", order="created_at, rowid")
    ]


def save_feedback(p, run_id, data):
    p.owned(run_id)
    allowed = {
        "working_minutes",
        "setup_minutes",
        "difficulty",
        "clarity",
        "repetition",
        "environment_issue",
        "note",
    }
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError("Unknown feedback fields")
    data = {"setup_minutes": 0, "environment_issue": False, "note": "", **data}
    for key, low in (("working_minutes", 1), ("setup_minutes", 0)):
        if type(data.get(key)) is not int or not low <= data[key] <= 1440:
            raise ValueError(f"{key} must be between {low} and 1440")
    for key, options in {
        "difficulty": {"too-easy", "about-right", "too-hard"},
        "clarity": {"clear", "unclear"},
        "repetition": {"fresh", "welcome-review", "unwanted-repeat"},
    }.items():
        if not isinstance(data.get(key), str) or data[key] not in options:
            raise ValueError(f"Choose a valid {key}")
    if (
        type(data["environment_issue"]) is not bool
        or not isinstance(data["note"], str)
        or len(data["note"]) > 2000
    ):
        raise ValueError(
            "Use a boolean environment issue and a note of at most 2000 characters"
        )
    values = {**data, "created_at": p.t.now().isoformat()}
    with p.db.transaction():
        if p.db.rows("activity_feedback", "run_id=?", (run_id,)):
            p.db.update("activity_feedback", "run_id=?", (run_id,), **values)
        else:
            p.db.insert("activity_feedback", run_id=run_id, **values)
    return {"saved": True, "feedback": data}


def observe_selection(p, filters):
    # Only known filter keys can enter the deduplicated local observation.
    allowed = {
        "minutes",
        "kind",
        "topic",
        "domain",
        "difficulty",
        "environment",
        "progress",
        "format",
        "search",
        "bookmarked",
    }
    if (
        not isinstance(filters, dict)
        or set(filters) - allowed
        or len(json.dumps(filters)) > 2000
    ):
        raise ValueError("Invalid selection filters")
    for key, value in filters.items():
        if key not in {"minutes", "bookmarked"} and not isinstance(value, str):
            raise ValueError("Selection filters must be strings")
        if key == "bookmarked" and type(value) is not bool:
            raise ValueError("bookmarked must be a boolean")
    available = p.list(**filters)["activities"]
    recommendation = p.recommendations(**filters)["activities"]
    key = json.dumps(filters, sort_keys=True)
    p.db.connection.execute(
        "INSERT OR IGNORE INTO activity_selections(user_id,day,filters,available,recommended,created_at) VALUES (?,?,?,?,?,?)",
        (
            p.db.user_id,
            p.t.day().isoformat(),
            key,
            len(available),
            len(recommendation),
            p.t.now().isoformat(),
        ),
    )
    return {"recorded": True}


def summary(p):
    since = (p.t.now() - timedelta(days=14)).isoformat()
    feedback = [r for r in feedback_rows(p) if r["created_at"] >= since]
    events = p.db.rows("activity_events", "created_at>=?", (since,))
    selections = p.db.rows("activity_selections", "created_at>=?", (since,))
    runs = [r for r in p.history_rows() if r["created_at"] >= since]
    timings = []
    for activity_id in sorted({r["activity_id"] for r in feedback}):
        reports = [r for r in feedback if r["activity_id"] == activity_id]
        timings.append(
            {
                "activity_id": activity_id,
                "reports": len(reports),
                "working_minutes": [r["working_minutes"] for r in reports],
                "setup_minutes": [r["setup_minutes"] for r in reports],
            }
        )
    return {
        "window_days": 14,
        "selection_queries": len(selections),
        "queries_with_choices": sum(r["available"] > 0 for r in selections),
        "queries_with_ready_choices": sum(r["recommended"] > 0 for r in selections),
        **{
            kind: sum(r["kind"] == kind for r in events)
            for kind in ("saved", "resumed", "returned")
        },
        "runs_with_hints": sum(r["hints"] > 0 for r in runs),
        "revealed_runs": sum(r["revealed"] > 0 for r in runs),
        "feedback_reports": len(feedback),
        "unclear_reports": sum(r["clarity"] == "unclear" for r in feedback),
        "unwanted_repeats": sum(r["repetition"] == "unwanted-repeat" for r in feedback),
        "environment_issues": sum(r["environment_issue"] for r in feedback),
        "timing_reports": timings,
    }
