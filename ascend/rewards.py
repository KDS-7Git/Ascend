"""Participation credit, kept separate from scored XP and milestone evidence.

Only meaningful, successfully recorded operations call award(). Browser drafts,
clicks, timers, queue events and failed saves do not pass through this boundary.
The per-activity/day identity and cap are enforced inside the SQLite write lock.
"""

import hashlib
import json

POINTS = 5
DAILY_CAP = 30
SOURCES = {"track", "playground", "local-lab", "hosted-lab", "learning-note"}


def _public(row, *, fresh=False):
    return {
        "id": f"practice:{row['id']}",
        "points": row["points"],
        "newly_awarded": bool(fresh and row["points"]),
        "day": row["day"],
        "reason": row["reason"],
        "source": row["source"],
        "reference": row["reference"],
        "title": row["title"],
    }


def award(t, source, reference, title, reason, *, event_key=None):
    if source not in SOURCES or not reference or not title:
        raise ValueError("A practice reward needs a known activity")
    activity_key = f"{source}:{reference}"
    event_key = event_key or activity_key
    day = t.day().isoformat()
    with t.db.transaction():
        existing = t.db.rows("practice_rewards", "event_key=?", (event_key,))
        if existing:
            return _public(existing[0])
        previous = t.db.rows(
            "practice_rewards",
            "activity_key=? AND day=? AND points>0",
            (activity_key, day),
        )
        used = t.db.connection.execute(
            "SELECT COALESCE(SUM(points),0) FROM practice_rewards WHERE user_id=? AND day=?",
            (t.db.user_id, day),
        ).fetchone()[0]
        points = 0 if previous else min(POINTS, max(0, DAILY_CAP - used))
        if not points:
            reason = "already-counted-today" if previous else "daily-cap"
        identity = t.db.insert(
            "practice_rewards",
            activity_key=activity_key,
            event_key=event_key,
            source=source,
            reference=reference,
            title=title,
            reason=reason,
            day=day,
            earned_at=t.now().isoformat(),
            points=points,
        )
        return _public(
            t.db.rows("practice_rewards", "id=?", (identity,))[0], fresh=True
        )


def note_event(source, reference, learned, next_step):
    """An unchanged saved reflection is the same event, even on another day."""
    digest = hashlib.sha256(
        json.dumps([learned.strip(), next_step.strip()]).encode()
    ).hexdigest()
    return f"note:{source}:{reference}:{digest}"


def receipt(t, *, event_key=None, activity_key=None):
    """Restore the last recorded receipt without granting participation credit."""
    if event_key is not None:
        where, value = "event_key=?", event_key
    elif activity_key is not None:
        where, value = "activity_key=?", activity_key
    else:
        return None
    row = t.db.connection.execute(
        f"SELECT * FROM practice_rewards WHERE user_id=? AND {where} ORDER BY id DESC LIMIT 1",
        (t.db.user_id, value),
    ).fetchone()
    return _public(dict(row)) if row else None


def practice_summary(t):
    day = t.day().isoformat()
    row = t.db.connection.execute(
        "SELECT COALESCE(SUM(points),0) AS total, COALESCE(SUM(CASE WHEN day=? THEN points ELSE 0 END),0) AS today FROM practice_rewards WHERE user_id=?",
        (day, t.db.user_id),
    ).fetchone()
    return {
        **dict(row),
        "day": day,
        "per_activity": POINTS,
        "daily_cap": DAILY_CAP,
        "remaining_today": max(0, DAILY_CAP - row["today"]),
        "purpose": "Practice points acknowledge participation; they do not verify skill or buy access.",
    }


def milestones(t):
    completed = t.db.rows("node_state", "status='done'", order="done_at DESC")
    packs, result = {}, []
    for state in completed:
        pack_id = state["pack_id"]
        if pack_id not in packs:
            try:
                packs[pack_id] = t.pack(pack_id)
            except (ValueError, OSError):
                packs[pack_id] = None
        pack = packs[pack_id]
        node = (
            next((n for n in pack.nodes if n.id == state["node_id"]), None)
            if pack
            else None
        )
        if not node or not node.milestone:
            continue
        how = state["how"]
        label = (
            "Assessed milestone"
            if how in {"verifier:lab", "verifier:ctf"}
            else "Artifact checked · completion recorded"
            if how == "verifier:file"
            else "Completion recorded by you"
        )
        result.append(
            {
                "id": f"milestone:{pack.id}:{node.id}",
                "reference": f"{pack.id}:{node.id}",
                "title": node.title,
                "pack_title": pack.title,
                "completed_at": state["done_at"],
                "evidence_kind": how,
                "evidence_label": label,
            }
        )
    return result


def summary(t):
    recent = t.db.connection.execute(
        "SELECT * FROM practice_rewards WHERE user_id=? ORDER BY id DESC LIMIT 20",
        (t.db.user_id,),
    ).fetchall()
    achievements = milestones(t)
    return {
        "practice": practice_summary(t),
        "xp": t.xp_totals(),
        "milestones": {"total": len(achievements), "items": achievements},
        "recent": [_public(dict(row)) for row in recent],
    }
