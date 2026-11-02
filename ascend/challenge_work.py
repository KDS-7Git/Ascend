"""Persistent notebooks, uploaded artifacts and recovery of ended track tasks.

Drafts and attachment manifests use account-scoped settings. Uploaded bytes live
under an application-controlled directory; a pack never chooses a write path.
Saving a draft is neither a completion nor a learning-day entry.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import secrets

from ascend.engine.validation import guard_secrets, validate_entry
from ascend.engine.verifiers import VerifyResult
from ascend.verifiers import file as file_verifier

MAX_UPLOAD = 8_000_000


class RevisionConflict(ValueError):
    pass


def key(kind, pack, node):
    return f"challenge-{kind}:{pack.id}:{node.id}"


def require_started(t, pack, node):
    if not t.db.rows("task_sessions", "pack_id=? AND node_id=?", (pack.id, node.id)):
        if t.states(pack.id).get(node.id, {}).get("status") != "done":
            raise ValueError("Start this challenge before saving work")


def notebook(t, pack, node):
    saved = t.db.setting(key("notebook", pack, node))
    if saved is not None:
        return saved
    rows = t.db.rows(
        "entries",
        "node_id=? AND source='manual'",
        (f"{pack.id}:{node.id}",),
        order="id DESC",
    )
    entry = rows[0] if rows else {}
    return {
        "learned": entry.get("learned", ""),
        "next_step": entry.get("next_step", f"Continue with {node.title}"),
        "entry_id": entry.get("id"),
        "revision": 0,
        "saved_at": entry.get("logged_at"),
    }


def signature(node):
    return hashlib.sha256(json.dumps(node.verify, sort_keys=True).encode()).hexdigest()


def artifact_path(t, pack, node, token):
    if not re.fullmatch(r"[a-f0-9]{48}", token):
        raise ValueError("Invalid attachment reference")
    root = t.db.home / "uploads" / str(t.db.user_id) / pack.id / node.id
    return root / token


def read_artifact(t, pack, node, manifest):
    path = artifact_path(t, pack, node, manifest["token"])
    # No browser or pack-controlled path, and no symlink at the stored filename.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    import stat

    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("The attachment is not a regular file")
        content = stream.read(MAX_UPLOAD + 1)
    if (
        len(content) > MAX_UPLOAD
        or hashlib.sha256(content).hexdigest() != manifest["sha256"]
    ):
        raise ValueError("The attachment changed; upload it again")
    return content


def uploaded_verification(t, pack, node):
    manifest = t.db.setting(key("attachment", pack, node))
    if not manifest:
        return None
    if manifest["signature"] != signature(node):
        return VerifyResult(
            False, "The evidence requirements changed. Upload your current report."
        )
    try:
        read_artifact(t, pack, node, manifest)
        spec = {
            **node.verify,
            "path": str(artifact_path(t, pack, node, manifest["token"])),
        }
        return file_verifier.verify(spec, {})
    except (OSError, ValueError):
        return VerifyResult(
            False, "The saved attachment is unavailable. Upload it again."
        )


def work(t, pack, node):
    require_started(t, pack, node)
    attachment = t.db.setting(key("attachment", pack, node))
    history = t.db.rows(
        "entries", "node_id=?", (f"{pack.id}:{node.id}",), order="id DESC LIMIT 20"
    )
    return {
        **notebook(t, pack, node),
        "attachment": {k: attachment[k] for k in ("name", "size", "uploaded_at")}
        if attachment
        else None,
        "upload_allowed": node.verify.get("type") == "file",
        "expected_filename": Path(node.verify.get("path", "report")).name,
        "max_upload_bytes": MAX_UPLOAD,
        "history": [
            {k: r[k] for k in ("id", "day", "learned", "next_step", "complete")}
            for r in history
        ],
        "practice": bool(t.db.setting(key("practice", pack, node))),
    }


def _revision(saved, revision):
    if saved["revision"] != revision:
        raise RevisionConflict(
            "Your notes changed in another tab. Your local text is kept; load the latest notes before saving."
        )


def _record_progress(t, pack, node, saved):
    learned, next_step = validate_entry(saved["learned"], saved["next_step"])
    rows = t.db.rows(
        "entries", "id=? AND node_id=?", (saved.get("entry_id"), f"{pack.id}:{node.id}")
    )
    if rows and rows[0]["source"] == "manual":
        t.edit(rows[0]["id"], learned, next_step)
        return rows[0]["id"]
    # Explicit pack ownership is already resolved. Use its mission if it exists,
    # so recovery also works after the learner switches their active track.
    missions = t.db.rows("missions", "pack_id=?", (pack.id,), order="id DESC")
    if missions:
        return t.log(
            learned,
            next_step,
            node_id=f"{pack.id}:{node.id}",
            mission_id=missions[0]["id"],
        )["id"]
    t.db.insert(
        "entries",
        day=t.day().isoformat(),
        logged_at=t.now().isoformat(),
        learned=learned,
        next_step=next_step,
        node_id=f"{pack.id}:{node.id}",
        source="manual",
        complete=0,
    )
    return t.db.rows("entries", order="id DESC")[0]["id"]


def save(t, reference, learned, next_step, revision, log_progress=False):
    pack, node = t.resolve_node(reference)
    require_started(t, pack, node)
    if (
        not isinstance(learned, str)
        or not isinstance(next_step, str)
        or len(learned) > 10000
        or len(next_step) > 4000
    ):
        raise ValueError(
            "Notes are limited to 10,000 characters and next steps to 4,000"
        )
    guard_secrets(learned, next_step)
    with t.db.transaction():
        saved = notebook(t, pack, node)
        _revision(saved, revision)
        saved = {
            **saved,
            "learned": learned,
            "next_step": next_step,
            "revision": revision + 1,
            "saved_at": t.now().isoformat(),
        }
        if log_progress:
            saved["entry_id"] = _record_progress(t, pack, node, saved)
        t.db.set_setting(key("notebook", pack, node), saved)
    return work(t, pack, node)


def complete(t, reference, revision):
    pack, node = t.resolve_node(reference)
    require_started(t, pack, node)
    with t.db.transaction():
        before = t.states(pack.id).get(node.id)
        if before and before["status"] == "done":
            return {
                "completed": True,
                "already_completed": True,
                "work": work(t, pack, node),
            }
        saved = notebook(t, pack, node)
        _revision(saved, revision)
        result = t.verify_node(pack, node)
        if not result.ok:
            raise ValueError(result.summary)
        entry_id = _record_progress(t, pack, node, saved)
        how = (
            "manual"
            if node.verify.get("type", "manual") == "manual"
            else "verifier:" + node.verify["type"]
        )
        t.mark(f"{pack.id}:{node.id}", "done", result.summary, how)
        t.db.update(
            "entries",
            "id=?",
            (entry_id,),
            complete=1,
            completion_before=json.dumps(before),
            completion_revision=t.states(pack.id)[node.id]["revision"],
        )
        t.db.set_setting(
            key("notebook", pack, node),
            {**saved, "entry_id": entry_id, "revision": revision + 1},
        )
    return {
        "completed": True,
        "already_completed": False,
        "verification": result.summary,
        "work": work(t, pack, node),
    }


def upload(t, reference, name, content):
    pack, node = t.resolve_node(reference)
    require_started(t, pack, node)
    if node.verify.get("type") != "file":
        raise ValueError("This challenge is not verified by an uploaded file")
    if not content or len(content) > MAX_UPLOAD:
        raise ValueError("Choose a nonempty evidence file up to 8 MB")
    if Path(node.verify["path"]).suffix.lower() == ".json":
        try:
            json.loads(content)
        except (ValueError, UnicodeError, RecursionError):
            raise ValueError("This task needs a valid JSON report") from None
    token = secrets.token_hex(24)
    path = artifact_path(t, pack, node, token)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        result = file_verifier.verify({**node.verify, "path": str(path)}, {})
        if not result.ok:
            raise ValueError(result.summary)
        name = re.split(r"[/\\]", name or "report")[-1]
        name = "".join(c for c in name if c.isprintable())[:120] or "report"
        manifest = {
            "token": token,
            "name": name,
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "signature": signature(node),
            "uploaded_at": t.now().isoformat(),
        }
        with t.db.transaction():
            previous = t.db.setting(key("attachment", pack, node))
            t.db.set_setting(key("attachment", pack, node), manifest)
        if previous:
            try:
                artifact_path(t, pack, node, previous["token"]).unlink(missing_ok=True)
            except OSError:
                pass  # A superseded file must not invalidate the accepted report.
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return {
        "ok": True,
        "summary": "Evidence accepted. Complete the lab to advance your track.",
        "work": work(t, pack, node),
    }


def retry(t, reference, minutes=None):
    from ascend import timing

    pack, node = t.resolve_node(reference)
    if node.verify.get("type") == "lab":
        raise ValueError(
            "This exercise keeps its original submission rules; use its exercise controls"
        )
    with t.db.transaction():
        rows = t.db.rows("task_sessions", "pack_id=? AND node_id=?", (pack.id, node.id))
        if not rows or rows[0]["status"] != "finished":
            raise ValueError("End the current session before starting another practice")
        # Existing start checks enforce prerequisites, target bounds and one active task.
        timing.start(t, reference, minutes)
        number = int(t.db.setting(key("practice", pack, node), 0)) + 1
        t.db.set_setting(key(f"session-history-{number}", pack, node), rows[0])
        t.db.set_setting(key("practice", pack, node), number)
        t.db.update(
            "task_sessions",
            "id=?",
            (rows[0]["id"],),
            status="running",
            running_since=t.now().isoformat(),
            elapsed_seconds=0,
            budget_seconds=(minutes or node.estimate) * 60,
            finished_at=None,
            notice=0,
        )
        saved = notebook(t, pack, node)
        t.db.set_setting(
            key("notebook", pack, node),
            {**saved, "entry_id": None, "revision": saved["revision"] + 1},
        )
    return timing.summary(t)
