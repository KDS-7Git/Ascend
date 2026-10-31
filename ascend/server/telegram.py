"""Telegram conversations reuse the same validation and logging use case."""
from datetime import datetime, timedelta

from ascend.engine.validation import validate_entry


def process_update(tracker, update):
    update_id = update.get("update_id")
    if type(update_id) is not int: return {"ignored": True}
    with tracker.db.transaction():
        if tracker.db.rows("telegram_updates", "update_id=?", (update_id,)): return {"duplicate": True}
        tracker.db.insert("telegram_updates", update_id=update_id)
        callback = update.get("callback_query", {})
        message = update.get("message", {})
        text = message.get("text", "").strip()
        if callback.get("data") in {"ascend-log", "ascend-quick"}:
            overview = tracker.overview()
            node = overview.get("quick_win") if callback["data"] == "ascend-quick" else overview.get("next")
            if callback["data"] == "ascend-quick" and not node: return {"reply": "No quick win is open. Tap Log a step to record your own work."}
            tracker.db.set_setting("telegram_flow", {"step": "learned", "expires": (tracker.now()+timedelta(minutes=20)).isoformat(),
                "node_id": f"{node['pack_id']}:{node['id']}" if node else None, "mission_id": (overview.get("mission") or {}).get("id")})
            return {"reply": "What did you learn? Reply with at least 20 characters, without passwords or flags."}
        flow = tracker.db.setting("telegram_flow")
        if text == "/cancel":
            tracker.db.set_setting("telegram_flow", None)
            return {"reply": "Cancelled. Your progress is unchanged."}
        if not flow or datetime.fromisoformat(flow["expires"]) < tracker.now():
            tracker.db.set_setting("telegram_flow", None)
            return {"reply": "Tap Log a step on a reminder to start, or open Ascend."}
        if len(text) > 4096: return {"reply": "Keep the note under 4096 characters."}
        if flow["step"] == "learned":
            try: learned, _ = validate_entry(text, "Continue learning")
            except ValueError as error: return {"reply": str(error)}
            tracker.db.set_setting("telegram_flow", {**flow, "step": "next", "learned": learned})
            return {"reply": "What's your next step? Reply with one concrete action."}
        try:
            result = tracker.log(flow["learned"], text, node_id=flow["node_id"], mission_id=flow["mission_id"])
        except ValueError as error: return {"reply": str(error)}
        tracker.db.set_setting("telegram_flow", None)
        return {"reply": f"Saved your step for {result['day']}. Thank you for showing up.", "logged": True}
