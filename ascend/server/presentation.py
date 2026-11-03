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


def workspace(node):
    """Adapt legacy file-task delivery text for browser uploads, not its verifier."""
    if node.get("verify", {}).get("type") != "file":
        return node
    from pathlib import Path

    result = dict(node)
    target = node["verify"].get("path", "")
    filename = Path(target).name
    replacements = {
        "Ascend checks files on the SERVER computer: for a hosted/container deployment, place your report at the server’s configured lab path. A file saved only on your laptop is not visible to that checker.": "Save this report on your own computer, then upload it through Notes & evidence. You do not need access to the server filesystem.",
        "This exercise checks the file on the computer running Ascend. For a hosted/container server, the report must be placed at that server’s configured lab path; a file saved only on your laptop will not be visible to the checker.": "Save this report on your own computer, then upload it through Notes & evidence. You do not need access to the server filesystem.",
        "Use Challenge options → Check evidence, then Log progress → Mark as done only after reviewing the finish line.": "Use Check evidence in your notebook, then Complete lab after reviewing the finish line.",
        "Back in Ascend, open Challenge options → Check evidence to check that the report file is present. Then use Log progress, briefly describe what you learned, and select Mark as done when your report contains the observations and explanations above.": "Back in Ascend, upload your report under Notes & evidence and record your observations in the notebook. Choose Complete lab when the finish line is met.",
    }

    def adapt(text):
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text.replace(target, filename) if target else text

    for field in ("brief", "setup", "done_when"):
        if result.get(field):
            result[field] = adapt(result[field])
    for field in ("steps", "hints"):
        result[field] = [adapt(text) for text in result.get(field, [])]
    return result


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
