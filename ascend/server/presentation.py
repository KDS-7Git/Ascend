"""Separate learner previews from the instructions for a started attempt.

Pack exports remain authoring data. This is staged disclosure in the learning
flow, not an anti-cheat secrecy boundary for a public curriculum.
"""

DETAIL_FIELDS = {
    "brief",
    "setup",
    "steps",
    "hints",
    "materials",
    "done_when",
    "auto_complete",
}


def attempts(tracker):
    return {
        (row["pack_id"], row["node_id"]) for row in tracker.db.rows("task_sessions")
    }


def preview(node, started=()):
    result = {key: value for key, value in node.items() if key not in DETAIL_FIELDS}
    result["verify"] = {
        key: value
        for key, value in node.get("verify", {}).items()
        if key in {"type", "exercise"}
    }
    result["has_attempt"] = (node.get("pack_id"), node["id"]) in started or node.get(
        "status"
    ) == "done"
    result["details_available"] = False
    return result


def overview(tracker, result):
    started = attempts(tracker)
    for key in ("next", "quick_win"):
        if result.get(key):
            result[key] = preview(result[key], started)
    if result.get("level"):
        result["level"]["nodes"] = [
            preview(node, started) for node in result["level"]["nodes"]
        ]
    return result


def levels(tracker, result):
    started = attempts(tracker)
    for level in result:
        level["nodes"] = [preview(node, started) for node in level["nodes"]]
    return result
