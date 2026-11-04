"""Account-scoped exercises. Only constrained data is evaluated; never learner code."""

import hashlib
import ipaddress
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from ascend import rewards, timing
from ascend.engine.verifiers import VerifyResult

EXERCISES = {"logging", "subnet", "access-policy", "integrity", "timeline", "case"}


def reward_receipt(t, pack_id, node_id, *, fresh=False):
    """Read this user's recorded award; dashboard totals are not a receipt."""
    rows = t.db.rows("xp_awards", "pack_id=? AND node_id=?", (pack_id, node_id))
    award = rows[0] if rows else None
    return {
        "id": f"track:{pack_id}:{node_id}",
        "xp": award["points"] if award else 0,
        "recorded": bool(award),
        "newly_awarded": bool(fresh and award),
        "evidence_kind": award["evidence_kind"] if award else None,
    }


def access_decision(request):
    if not request["enabled"]:
        return (
            False,
            "This identity is disabled. Disabled identities are always denied, even if they own the object or have the admin role.",
        )
    if request["caller"] == request["owner"]:
        return (
            True,
            "This identity is enabled and owns the object, so it may read or write.",
        )
    if request["role"] == "admin" and request["action"] == "read":
        return True, "An enabled admin may read an object owned by someone else."
    if request["role"] == "admin":
        return (
            False,
            "Admins may write only to objects they own. This caller is not the owner.",
        )
    return (
        False,
        "An enabled user may read or write only their own objects. This caller is not the owner.",
    )


def clarify_legacy_case(challenge):
    # Preserve option IDs and the answer key while clarifying this old wording.
    public = challenge["public"]
    if (
        public.get("instructions")
        != "A required training environment is unavailable, but a tool prints its version."
    ):
        return
    case = json.loads((Path(__file__).parent / "cases.json").read_text())[
        "ethical-hacking-foundations:foundations"
    ]
    public.update(
        instructions=case["prompt"], question=case["question"], title=case["title"]
    )
    correct = challenge["expected"]["choice"]
    public["choices"] = {
        key: case["correct"] if key == correct else case["incorrect"]
        for key in public["choices"]
    }
    challenge["explanation"] = case["explanation"]


def generate(exercise, case_id, now):
    rng = secrets.SystemRandom()
    tag = secrets.token_hex(5)
    public = {"exercise": exercise, "questions": {}, "answer_template": {}, "data": {}}
    private = {"public": public, "expected": {}}
    if exercise == "case":
        cases = json.loads((Path(__file__).parent / "cases.json").read_text())
        if case_id not in cases:
            raise ValueError("This reasoning case is not bundled with the server")
        case = cases[case_id]
        options = [case["correct"], case["incorrect"]]
        rng.shuffle(options)
        public.update(
            instructions=case["prompt"],
            question=case.get(
                "question", "Which response is best supported by this scenario?"
            ),
            title=case.get("title", "Make the call"),
            attempt_limit=1,
            choices={"A": options[0], "B": options[1]},
            answer_template={"choice": ""},
        )
        private["expected"] = {"choice": "A" if options[0] == case["correct"] else "B"}
        private["explanation"] = case.get(
            "explanation",
            f"{case['correct']} The scenario does not support this alternative: {case['incorrect']}",
        )
    elif exercise == "logging":
        public.update(
            instructions="Emit one successful and one failed request. Find the FAILED request for your exercise marker in the event data. Count ALL failed requests for this marker; ignore other markers.",
            marker=tag,
            answer_template={"request_id": "", "errors": 0},
        )
        public["data"]["events"] = [
            {
                "request_id": secrets.token_hex(4),
                "marker": "noise-" + secrets.token_hex(3),
                "status": rng.choice([200, 404, 503]),
                "time": now.isoformat(),
            }
            for _ in range(6)
        ]
        private["emitted"] = []
    elif exercise == "subnet":
        prefix = rng.choice([24, 25, 26, 27, 28])
        net = ipaddress.ip_network(
            f"10.{rng.randrange(1, 250)}.{rng.randrange(1, 250)}.0/{prefix}"
        )
        address = net.network_address + rng.randrange(1, net.num_addresses - 1)
        public.update(
            instructions="Compute the IPv4 network (CIDR), broadcast address and usable host count for this ordinary subnet.",
            answer_template={"network": "", "broadcast": "", "usable_hosts": 0},
            data={"interface": f"{address}/{prefix}"},
        )
        private["expected"] = {
            "network": str(net),
            "broadcast": str(net.broadcast_address),
            "usable_hosts": net.num_addresses - 2,
        }
    elif exercise == "access-policy":
        owner = "owner-" + tag
        other = "other-" + tag
        requests = []
        for i in range(6):
            caller = rng.choice([owner, other])
            role = rng.choice(["user", "admin"])
            enabled = rng.choice([True, True, False])
            action = rng.choice(["read", "write"])
            requests.append(
                {
                    "id": f"r{i + 1}",
                    "caller": caller,
                    "owner": owner,
                    "role": role,
                    "enabled": enabled,
                    "action": action,
                }
            )
        # Always include both a legitimate access and an unrelated denied write.
        requests[0].update(caller=owner, enabled=True, action="read")
        requests[1].update(caller=other, enabled=True, role="user", action="write")
        rng.shuffle(requests)
        public.update(
            instructions="Disabled identities are always denied. An owner may read/write. An enabled admin may read any object, but may write only their own. Return a boolean decision for every request.",
            answer_template={r["id"]: False for r in requests},
            data={"requests": requests},
        )
        private["expected"] = {r["id"]: access_decision(r)[0] for r in requests}
    elif exercise == "integrity":
        value = f"Training evidence {tag}\nvalue={rng.randrange(10000, 99999)}\n"
        public.update(
            instructions="Compute SHA-256 over the exact UTF-8 content, including both newline characters. A changed filename would not change this content hash.",
            answer_template={"sha256": ""},
            data={"content": value, "encoding": "UTF-8"},
        )
        private["expected"] = {"sha256": hashlib.sha256(value.encode()).hexdigest()}
    elif exercise == "timeline":
        actor = "learner-" + tag
        base = now.replace(microsecond=0) - timedelta(minutes=3)
        events = [
            {
                "actor": actor,
                "status": "failure",
                "time": (base + timedelta(seconds=i * 8)).isoformat(),
            }
            for i in range(5)
        ]
        events += [
            {
                "actor": actor,
                "status": "success",
                "time": (base + timedelta(seconds=45)).isoformat(),
            },
            {"actor": "maintenance", "status": "failure", "time": base.isoformat()},
            {
                "actor": "maintenance",
                "status": "success",
                "time": (base + timedelta(seconds=2)).isoformat(),
            },
        ]
        rng.shuffle(events)
        public.update(
            instructions="Find the account with at least five failures within sixty seconds followed by success. This pattern is an investigation lead, not proof of compromise. Return the account, failure count and success timestamp.",
            answer_template={"actor": "", "failures": 0, "success_time": ""},
            data={"events": events},
        )
        private["expected"] = {
            "actor": actor,
            "failures": 5,
            "success_time": (base + timedelta(seconds=45)).isoformat(),
        }
    else:
        raise ValueError("Unknown bundled exercise")
    return private


def fingerprint(t, pack):
    # Loading the pack checks content fingerprints and revokes stale trust.
    t.pack(pack.id)
    return t.db.rows("packs", "id=?", (pack.id,))[0]["fingerprint"]


def owned(t, run_id):
    rows = t.db.rows("lab_runs", "id=?", (run_id,))
    if not rows:
        raise ValueError("Exercise instance not found")
    row = rows[0]
    latest = t.db.rows(
        "lab_runs",
        "pack_id=? AND node_id=?",
        (row["pack_id"], row["node_id"]),
        order="rowid DESC",
    )
    if latest[0]["id"] != run_id:
        raise ValueError("This instance was superseded; use the current exercise")
    pack, node = t.resolve_node(f"{row['pack_id']}:{row['node_id']}")
    if fingerprint(t, pack) != row["fingerprint"]:
        raise ValueError("Pack changed; start a fresh exercise")
    if not row["passed_at"] and t.now() - datetime.fromisoformat(
        row["created_at"]
    ) > timedelta(hours=24):
        raise ValueError("Exercise expired; start a fresh instance")
    return row, pack, node


def recorded_result(t, where, params):
    for table, render in [
        ("case_attempts", case_result),
        ("permission_attempts", permission_result),
    ]:
        rows = t.db.rows(table, where, params)
        if rows:
            return render(t, rows[0])
    return None


def view(t, run_id):
    recorded = recorded_result(t, "run_id=?", (run_id,))
    if recorded:
        return recorded
    row, _, _ = owned(t, run_id)
    challenge = json.loads(row["challenge"])
    clarify_legacy_case(challenge)
    public = challenge["public"]
    return {
        **public,
        "id": row["id"],
        "node_id": f"{row['pack_id']}:{row['node_id']}",
        "passed": bool(row["passed_at"]),
        "attempts": row["attempts"],
        "terminal": bool(row["passed_at"]),
        "timer": timing.summary(t),
        "reward": reward_receipt(t, row["pack_id"], row["node_id"]),
        "practice_reward": rewards.receipt(t, event_key=f"assessment:{row['id']}"),
        **({"attempt_limit": 1} if row["exercise"] == "access-policy" else {}),
    }


def permission_result(t, row):
    challenge = json.loads(row["challenge"])
    answers = json.loads(row["answers"])
    feedback = []
    for request in challenge["public"]["data"]["requests"]:
        allowed, explanation = access_decision(request)
        selected = answers.get(request["id"])
        feedback.append(
            {
                "id": request["id"],
                "selected": selected,
                "allowed": allowed,
                "correct": selected == allowed if selected is not None else None,
                "explanation": explanation,
            }
        )
    awards = t.db.rows(
        "xp_awards", "pack_id=? AND node_id=?", (row["pack_id"], row["node_id"])
    )
    return {
        **challenge["public"],
        "id": row["run_id"],
        "node_id": f"{row['pack_id']}:{row['node_id']}",
        "passed": row["correct_count"] == row["total_count"],
        "terminal": True,
        "attempts": 1,
        "attempt_limit": 1,
        "feedback": feedback,
        "score": {
            "correct": row["correct_count"],
            "total": row["total_count"],
            "xp": awards[0]["points"] if awards else 0,
        },
        "reward_eligible": bool(awards),
        "timer": timing.summary(t),
        "reward": reward_receipt(t, row["pack_id"], row["node_id"]),
        "practice_reward": rewards.receipt(t, event_key=f"assessment:{row['run_id']}"),
    }


def case_result(t, row):
    """A permanent, account-scoped decision receipt, readable after reload."""
    challenge = json.loads(row["challenge"])
    clarify_legacy_case(challenge)
    public = challenge["public"]
    selected = json.loads(row["answers"]).get("choice")
    correct = challenge["expected"].get("choice")
    return {
        **public,
        "id": row["run_id"],
        "node_id": f"{row['pack_id']}:{row['node_id']}",
        "passed": bool(row["correct"]),
        "terminal": True,
        "attempts": 1,
        "attempt_limit": 1,
        "feedback": {
            "selected": selected,
            "correct_choice": correct,
            "explanation": challenge.get("explanation")
            or f"The supported decision is: {public['choices'][correct]}",
        },
        "timer": timing.summary(t),
        "reward": reward_receipt(t, row["pack_id"], row["node_id"]),
        "practice_reward": rewards.receipt(t, event_key=f"assessment:{row['run_id']}"),
    }


def current(t, reference):
    """Read the latest exercise without starting or resuming its timer."""
    pack, node = t.resolve_node(reference)
    recorded = recorded_result(t, "pack_id=? AND node_id=?", (pack.id, node.id))
    if recorded:
        return recorded
    rows = t.db.rows(
        "lab_runs", "pack_id=? AND node_id=?", (pack.id, node.id), order="rowid DESC"
    )
    return view(t, rows[0]["id"]) if rows else None


def start(t, reference, fresh=False, minutes=None):
    pack, node = t.resolve_node(reference)
    if node.verify.get("type") != "lab":
        raise ValueError("This task has no bundled exercise")
    with t.db.transaction():
        recorded = recorded_result(t, "pack_id=? AND node_id=?", (pack.id, node.id))
        if recorded:
            if fresh:
                raise ValueError(
                    "This challenge has already been submitted. Review its explanation; another attempt is not available."
                )
            return recorded
        timing.start(t, reference, minutes=minutes)
        digest = fingerprint(t, pack)
        rows = t.db.rows(
            "lab_runs",
            "pack_id=? AND node_id=? AND fingerprint=?",
            (pack.id, node.id, digest),
            order="rowid DESC",
        )
        if rows and not fresh:
            try:
                return view(t, rows[0]["id"])
            except ValueError:
                pass
        t.db.connection.execute(
            "DELETE FROM lab_runs WHERE user_id=? AND pack_id=? AND node_id=? AND passed_at IS NULL",
            (t.db.user_id, pack.id, node.id),
        )
        active = t.db.rows("lab_runs", "passed_at IS NULL")
        if len(active) >= 100:
            raise ValueError(
                "Too many unfinished exercises; reuse an existing instance"
            )
        exercise = node.verify.get("exercise")
        challenge = generate(exercise, node.verify.get("case_id"), t.now())
        run_id = secrets.token_hex(16)
        t.db.insert(
            "lab_runs",
            id=run_id,
            pack_id=pack.id,
            node_id=node.id,
            fingerprint=digest,
            exercise=exercise,
            challenge=json.dumps(challenge),
            created_at=t.now().isoformat(),
        )
    return view(t, run_id)


def emit(t, run_id, kind):
    if kind not in {"ok", "error"}:
        raise ValueError("Event kind must be ok or error")
    with t.db.transaction():
        row, _, _ = owned(t, run_id)
        if row["exercise"] != "logging" or row["passed_at"]:
            raise ValueError("Only an unfinished logging exercise accepts events")
        challenge = json.loads(row["challenge"])
        if kind in challenge["emitted"]:
            return view(t, run_id)
        event = {
            "request_id": secrets.token_hex(4),
            "marker": challenge["public"]["marker"],
            "status": 200 if kind == "ok" else 503,
            "time": t.now().isoformat(),
        }
        challenge["public"]["data"]["events"].append(event)
        secrets.SystemRandom().shuffle(challenge["public"]["data"]["events"])
        challenge["emitted"].append(kind)
        if kind == "error":
            challenge["expected"] = {"request_id": event["request_id"], "errors": 1}
        t.db.update("lab_runs", "id=?", (run_id,), challenge=json.dumps(challenge))
    return view(t, run_id)


def submit(t, run_id, answers):
    if not isinstance(answers, dict) or len(json.dumps(answers)) > 8192:
        raise ValueError("Answers must be a JSON object of at most 8192 characters")
    with t.db.transaction():
        recorded = recorded_result(t, "run_id=?", (run_id,))
        if recorded:
            receipt = recorded
            return {
                "ok": receipt["passed"],
                "completed": receipt["passed"],
                "terminal": True,
                "exercise": receipt,
                "summary": "This challenge has already been submitted. Your first result is final.",
                "timer": timing.summary(t),
                "reward": receipt["reward"],
                "practice_reward": receipt["practice_reward"],
            }
        row, pack, node = owned(t, run_id)
        had_award = reward_receipt(t, pack.id, node.id)["recorded"]
        recorded = recorded_result(t, "pack_id=? AND node_id=?", (pack.id, node.id))
        if recorded:
            raise ValueError(
                "This challenge has already been submitted. Review the recorded result."
            )
        if (
            row["attempts"] >= 10
            and not row["passed_at"]
            and row["exercise"] != "access-policy"
        ):
            raise ValueError(
                "Attempt limit reached; review the lesson and start a fresh instance"
            )
        challenge = json.loads(row["challenge"])
        is_case = row["exercise"] == "case"
        is_policy = row["exercise"] == "access-policy"
        if is_case and (
            set(answers) != {"choice"}
            or type(answers["choice"]) is not str
            or answers["choice"] not in challenge["public"]["choices"]
        ):
            raise ValueError("Choose one of the available answers before submitting.")
        expected = challenge["expected"]
        if is_policy and (
            set(answers) != set(expected)
            or any(type(v) is not bool for v in answers.values())
        ):
            raise ValueError(
                "Choose Allow or Deny for every request before submitting."
            )
        ready = row["exercise"] != "logging" or set(challenge["emitted"]) == {
            "ok",
            "error",
        }
        # Python considers True == 1; types are part of this protocol's answers.
        ok = (
            ready
            and set(answers) == set(expected)
            and all(
                type(answers[k]) is type(v) and answers[k] == v
                for k, v in expected.items()
            )
        )
        if row["passed_at"]:
            return {
                "ok": True,
                "completed": True,
                "summary": "This instance was already verified.",
                "timer": timing.summary(t),
                "reward": reward_receipt(t, pack.id, node.id),
                "practice_reward": rewards.receipt(t, event_key=f"assessment:{run_id}"),
            }
        t.db.update("lab_runs", "id=?", (run_id,), attempts=row["attempts"] + 1)
        if is_policy:
            t.db.insert(
                "permission_attempts",
                pack_id=pack.id,
                node_id=node.id,
                run_id=run_id,
                answers=json.dumps(answers),
                challenge=json.dumps(challenge),
                correct_count=sum(answers[k] == v for k, v in expected.items()),
                total_count=len(expected),
                submitted_at=t.now().isoformat(),
            )
        if is_case:
            t.db.insert(
                "case_attempts",
                pack_id=pack.id,
                node_id=node.id,
                run_id=run_id,
                answers=json.dumps(answers),
                correct=int(ok),
                submitted_at=t.now().isoformat(),
                challenge=json.dumps(challenge),
            )
        practice_reward = None
        if (
            ready
            and set(answers) == set(expected)
            and all(
                type(answers[k]) is type(value)
                and not (isinstance(answers[k], str) and not answers[k].strip())
                for k, value in expected.items()
            )
        ):
            practice_reward = rewards.award(
                t,
                "track",
                f"{pack.id}:{node.id}",
                node.title,
                "assessment-submitted",
                event_key=f"assessment:{run_id}",
            )
        if not ok:
            if is_case:
                timing.finish(t, pack, node, "mcq:incorrect")
            elif is_policy:
                timing.finish(t, pack, node, "verifier:permission-partial")
            return {
                "ok": False,
                "completed": False,
                "terminal": is_case or is_policy,
                "summary": "Answer recorded. No XP earned; review the explanation."
                if is_case
                else "Decisions recorded. Review your partial score and the explanation for each request."
                if is_policy
                else "The expected result has not been demonstrated. Check the instructions and data; no completion or XP was awarded.",
                "exercise": view(t, run_id) if is_case or is_policy else None,
                "timer": timing.summary(t),
                "reward": reward_receipt(t, pack.id, node.id, fresh=not had_award),
                "practice_reward": practice_reward,
            }
        t.db.update("lab_runs", "id=?", (run_id,), passed_at=t.now().isoformat())
        result = t.check(f"{pack.id}:{node.id}", confirm=True)
    return {
        **result,
        "timer": timing.summary(t),
        "receipt": run_id,
        "terminal": True,
        "exercise": view(t, run_id),
        "reward": reward_receipt(t, pack.id, node.id, fresh=not had_award),
        "practice_reward": practice_reward,
    }


def verify(t, pack, node):
    rows = t.db.rows(
        "lab_runs",
        "pack_id=? AND node_id=? AND fingerprint=?",
        (pack.id, node.id, fingerprint(t, pack)),
        order="rowid DESC",
    )
    if not rows or not rows[0]["passed_at"]:
        return VerifyResult(
            False, "Solve this task's current server exercise before completing it."
        )
    return VerifyResult(
        True,
        f"Verified {node.verify['exercise']} exercise for {node.title}.",
        datetime.fromisoformat(rows[0]["passed_at"]),
    )
