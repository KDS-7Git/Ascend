"""Authored stopping points save partial logs, never assessment completion."""

import json


def list_for(t, reference):
    pack, node = t.resolve_node(reference)
    saved = {
        r["checkpoint_id"]: r
        for r in t.db.rows(
            "node_checkpoints", "pack_id=? AND node_id=?", (pack.id, node.id)
        )
    }
    return {
        "reference": f"{pack.id}:{node.id}",
        "title": node.title,
        "full_minutes": node.estimate,
        "checkpoints": [
            {
                **c,
                "saved": c["id"] in saved,
                "entry_id": saved.get(c["id"], {}).get("entry_id"),
            }
            for c in node.checkpoints
        ],
    }


def record(t, reference, checkpoint_id, learned, minutes=None):
    pack, node = t.resolve_node(reference)
    checkpoint = next((c for c in node.checkpoints if c["id"] == checkpoint_id), None)
    if checkpoint is None:
        raise ValueError("No such authored checkpoint")
    with t.db.transaction():
        existing = t.db.rows(
            "node_checkpoints",
            "pack_id=? AND node_id=? AND checkpoint_id=?",
            (pack.id, node.id, checkpoint_id),
        )
        if existing:
            entry = t.db.rows("entries", "id=?", (existing[0]["entry_id"],))[0]
            if learned != entry["learned"]:
                raise ValueError(
                    "Checkpoint already saved; edit its learning entry to change the note"
                )
            return {"saved": True, "entry_id": entry["id"], "parent_completed": False}
        if node.id not in {n.id for n in t.candidates(pack)}:
            raise ValueError("Checkpoint requires an open, unfinished parent task")
        result = t.log(
            learned,
            checkpoint["next_step"],
            minutes=minutes,
            node_id=f"{pack.id}:{node.id}",
        )
        t.db.insert(
            "node_checkpoints",
            pack_id=pack.id,
            node_id=node.id,
            checkpoint_id=checkpoint_id,
            definition=json.dumps(checkpoint),
            entry_id=result["id"],
            created_at=t.now().isoformat(),
        )
        return {"saved": True, "entry_id": result["id"], "parent_completed": False}


def recommend(t, reference, minutes):
    detail = list_for(t, reference)
    pending = next((c for c in detail["checkpoints"] if not c["saved"]), None)
    if pending and (minutes is None or pending["minutes"] <= minutes):
        return {**detail, "checkpoint": pending}
    return None
