"""Server-clock task sessions and once-per-node verification rewards."""

import math
from datetime import datetime


def elapsed(t, row):
    value = row["elapsed_seconds"]
    if row["status"] == "running":
        value += max(
            0, (t.now() - datetime.fromisoformat(row["running_since"])).total_seconds()
        )
    return value


def points(seconds, budget):
    return max(25, 100 - math.floor(50 * max(0, seconds - budget) / budget))


def scored_points(t, row, seconds):
    base = points(seconds, row["budget_seconds"])
    decisions = t.db.rows(
        "permission_attempts",
        "pack_id=? AND node_id=?",
        (row["pack_id"], row["node_id"]),
    )
    if decisions:
        return base * decisions[0]["correct_count"] // decisions[0]["total_count"]
    return base


def describe(t, row):
    value = elapsed(t, row)
    practice = bool(
        t.db.setting(f"challenge-practice:{row['pack_id']}:{row['node_id']}")
    )
    return {
        **row,
        "elapsed_seconds": int(value),
        "remaining_seconds": max(0, math.ceil(row["budget_seconds"] - value)),
        "potential_xp": 0 if practice else scored_points(t, row, value),
        "practice": practice,
        "server_time": t.now().isoformat(),
    }


def summary(t):
    from ascend.local_labs.attempts import Attempts

    Attempts(t).expire()
    local_runs = t.db.rows("external_lab_attempts", "status IN ('preparing','active')")
    rows = t.db.rows("task_sessions", "status='running'")
    awards = t.db.rows("xp_awards")
    finished = t.db.rows(
        "task_sessions", "status='finished'", order="finished_at DESC, id DESC"
    )
    recent = describe(t, finished[0]) if finished else None
    if recent:
        reference = (recent["pack_id"], recent["node_id"])
        state = t.db.rows("node_state", "pack_id=? AND node_id=?", reference)
        decision = t.db.rows("case_attempts", "pack_id=? AND node_id=?", reference)
        policy = t.db.rows("permission_attempts", "pack_id=? AND node_id=?", reference)
        recent["outcome"] = (
            "completed"
            if state and state[0]["status"] == "done"
            else "partial"
            if policy and policy[0]["correct_count"] < policy[0]["total_count"]
            else "incorrect"
            if decision and not decision[0]["correct"]
            else "ended"
        )
        recent["xp_earned"] = sum(
            r["points"] for r in awards if (r["pack_id"], r["node_id"]) == reference
        )
    return {
        "active": describe(t, rows[0]) if rows else None,
        "recent": recent,
        "paused": [
            describe(t, r) for r in t.db.rows("task_sessions", "status='paused'")
        ],
        "xp": t.xp_totals()["total"],
        "xp_by_source": t.xp_totals(),
        "playground_active": next(
            (
                r
                for r in t.playground.history()
                if r["status"] == "active"
                or (r["strict_timer"] and r["status"] == "saved")
            ),
            None,
        ),
        "local_lab_active": Attempts(t).view(local_runs[0]["id"])
        if local_runs
        else None,
        "verified_awards": sum(
            r["evidence_kind"] != "verifier:permission-partial" for r in awards
        ),
    }


def start(t, reference, minutes=None):
    pack, node = t.resolve_node(reference)
    if node.id not in {n.id for n in t.candidates(pack)} and t.states(pack.id).get(
        node.id, {}
    ).get("status") not in {"done", "skipped"}:
        raise ValueError("Complete the prerequisites before starting this task")
    budget = node.estimate if minutes is None else minutes
    if type(budget) is not int or not 1 <= budget <= 1440:
        raise ValueError("Session target must be 1 to 1440 minutes")
    with t.db.transaction():
        from ascend.local_labs.attempts import Attempts

        Attempts(t).expire()
        if t.db.rows("external_lab_attempts", "status IN ('preparing','active')"):
            raise ValueError("Finish the local lab before starting a track session")
        activities = t.db.rows("activity_runs", "status IN ('active','saved')")
        if any(t.playground.strict_timer(row) for row in activities):
            raise ValueError(
                "End the timed Playground challenge before starting a track session"
            )
        if any(row["status"] == "active" for row in activities):
            raise ValueError(
                "Save the active Playground activity before starting a track session"
            )
        active = t.db.rows("task_sessions", "status='running'")
        if active and (active[0]["pack_id"], active[0]["node_id"]) != (
            pack.id,
            node.id,
        ):
            raise ValueError("End the current task session before starting another")
        previous = t.db.rows(
            "task_sessions", "pack_id=? AND node_id=?", (pack.id, node.id)
        )
        if previous:
            row = previous[0]
            if row["status"] == "paused":
                raise ValueError(
                    "This legacy session is paused. End it before continuing unscored practice."
                )
            # Reopening never resets the target, clock or once-per-node attempt.
        else:
            t.db.insert(
                "task_sessions",
                pack_id=pack.id,
                node_id=node.id,
                title=node.title,
                budget_seconds=budget * 60,
                running_since=t.now().isoformat(),
                status="running",
            )
        row = t.db.rows("task_sessions", "pack_id=? AND node_id=?", (pack.id, node.id))[
            0
        ]
    return describe(t, row)


def end(t):
    with t.db.transaction():
        rows = t.db.rows("task_sessions", "status='running'")
        if not rows:
            rows = t.db.rows("task_sessions", "status='paused'")
        if not rows:
            raise ValueError("No task session to end")
        row = rows[-1]
        t.db.update(
            "task_sessions",
            "id=?",
            (row["id"],),
            elapsed_seconds=elapsed(t, row),
            running_since=None,
            status="finished",
            finished_at=t.now().isoformat(),
        )
    return summary(t)


def finish(t, pack, node, how):
    rows = t.db.rows("task_sessions", "pack_id=? AND node_id=?", (pack.id, node.id))
    if not rows or rows[0]["status"] == "finished":
        return
    row = rows[0]
    seconds = elapsed(t, row)
    t.db.update(
        "task_sessions",
        "id=?",
        (row["id"],),
        elapsed_seconds=seconds,
        running_since=None,
        status="finished",
        finished_at=t.now().isoformat(),
    )
    # Presence-only file checks and self-marking are not skill rewards.
    practice = t.db.setting(f"challenge-practice:{pack.id}:{node.id}")
    if (
        not practice
        and row["status"] == "running"
        and how
        in {
            "verifier:lab",
            "verifier:ctf",
            "verifier:permission-partial",
        }
    ):
        if t.db.rows(
            "activity_rewards", "reward_key=?", (f"track:{pack.id}:{node.id}",)
        ):
            return
        t.db.connection.execute(
            "INSERT OR IGNORE INTO xp_awards VALUES (?,?,?,?,?,?)",
            (
                t.db.user_id,
                pack.id,
                node.id,
                scored_points(t, row, seconds),
                t.now().isoformat(),
                how,
            ),
        )


def reminders(t, sender):
    with t.db.transaction():
        rows = t.db.rows("task_sessions", "status='running'")
        if not rows:
            return {"sent": False}
        row = rows[0]
        seconds = elapsed(t, row)
        budget = row["budget_seconds"]
        due = 2 if seconds >= budget else 1 if seconds >= budget * 0.75 else 0
        if due <= row["notice"]:
            return {"sent": False}
        message = f"Ascend: {row['title']}. " + (
            "Your target time has elapsed; verified completion still earns XP."
            if due == 2
            else "Three quarters of your planned session has elapsed."
        )
        delivery = sender(message)
        if isinstance(delivery, dict) and delivery.get("sent") == 0:
            return {"sent": False}
        t.db.update("task_sessions", "id=?", (row["id"],), notice=due)
        return {"sent": True, "notice": due}
