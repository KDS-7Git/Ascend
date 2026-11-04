"""Small account-bound records and server-owned grading; no runtime or local paths."""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta

from ascend import rewards
from ascend.local_labs.catalog import detail, executable
from ascend.local_labs.checks import answer_check, bounded, local_report


class Attempts:
    def __init__(self, tracker):
        self.t, self.db = tracker, tracker.db

    def owned(self, attempt_id):
        rows = self.db.rows("external_lab_attempts", "id=?", (attempt_id,))
        if not rows:
            raise ValueError("Lab attempt not found")
        return rows[0]

    def view(self, attempt_id):
        self.expire()
        row = self.owned(attempt_id)
        result = {k: v for k, v in row.items() if k not in {"nonce_hash", "user_id"}}
        result["result"] = json.loads(row["result"]) if row["result"] else None
        if result["result"] and result["result"].get("practice_reward"):
            result["result"]["practice_reward"]["newly_awarded"] = False
        result["assignment"] = (
            json.loads(row["assignment"]) if row["assignment"] else None
        )
        result["satisfies_track_evidence"] = False
        return result

    def history(self):
        return [
            self.view(r["id"])
            for r in self.db.rows(
                "external_lab_attempts", order="created_at DESC, rowid DESC"
            )
        ]

    def recipe(self, recipe_id, offline=False):
        candidate = detail(recipe_id)
        if offline and candidate.get("evidence_reviewed"):
            from ascend.local_labs.upstream import report_recipe

            return report_recipe(recipe_id)
        return executable(recipe_id)

    def expire(self):
        self.db.connection.execute(
            "UPDATE external_lab_attempts SET status='abandoned',ended_at=? WHERE user_id=? AND status IN ('preparing','active') AND expires_at<=?",
            (self.t.now().isoformat(), self.db.user_id, self.t.now().isoformat()),
        )

    def create(self, recipe_id, *, offline=False, case_key=None):
        recipe = self.recipe(recipe_id, offline)
        case, fixture = None, recipe["fixture_id"]
        if case_key is not None and (
            not offline or recipe["grading"] != "prefix-policy-v1"
        ):
            raise ValueError(
                "A case key is allowed only for an offline policy submission"
            )
        if recipe["grading"] == "prefix-policy-v1":
            from ascend.local_labs.prefix import assigned_case, fixture_id

            case = assigned_case(case_key)
            fixture = fixture_id(recipe, case)
        nonce, attempt_id = secrets.token_hex(32), secrets.token_hex(16)
        now = self.t.now().isoformat()
        with self.db.transaction():
            self.expire()
            if not offline and (
                self.db.rows(
                    "activity_runs",
                    "status='active' OR (status='saved' AND role<>'example' AND kind<>'free')",
                )
                or self.db.rows("task_sessions", "status='running'")
                or self.db.rows(
                    "external_lab_attempts", "status IN ('preparing','active')"
                )
            ):
                raise ValueError(
                    "Finish the active session before starting a local lab"
                )
            self.db.insert(
                "external_lab_attempts",
                id=attempt_id,
                recipe_id=recipe_id,
                recipe_version=recipe["version"],
                checker_version=recipe["checker_version"],
                fixture_id=fixture,
                assignment=json.dumps(case) if case else None,
                nonce_hash=hashlib.sha256(nonce.encode()).hexdigest(),
                origin="offline"
                if offline
                else "online"
                if getattr(self.t, "server_mode", False)
                else "local",
                status="imported" if offline else "preparing",
                created_at=now,
                expires_at=(self.t.now() + timedelta(hours=24)).isoformat(),
            )
        return {**self.view(attempt_id), "nonce": nonce}

    def adopt_local_assignment(self, attempt_id, nonce, remote):
        """Adopt the server case on the PC before preparing files; no API route."""
        if getattr(self.t, "server_mode", False):
            raise ValueError("A server assignment cannot be replaced")
        from ascend.local_labs.prefix import fixture_id

        with self.db.transaction():
            row = self.authorize(attempt_id, nonce)
            recipe = self.recipe(row["recipe_id"])
            if (
                row["origin"] != "local"
                or row["status"] != "preparing"
                or recipe["grading"] != "prefix-policy-v1"
            ):
                raise ValueError(
                    "Only a new local policy workspace can adopt an assignment"
                )
            if any(
                remote.get(k) != row[k]
                for k in ("recipe_id", "recipe_version", "checker_version")
            ):
                raise ValueError("Remote recipe or checker version mismatch")
            fixture = fixture_id(recipe, remote.get("assignment"))
            if remote.get("fixture_id") != fixture:
                raise ValueError("Remote fixture does not match its assigned case")
            self.db.update(
                "external_lab_attempts",
                "id=?",
                (attempt_id,),
                assignment=json.dumps(remote["assignment"]),
                fixture_id=fixture,
            )
        return {**self.view(attempt_id), "nonce": nonce}

    def authorize(self, attempt_id, nonce):
        row = self.owned(attempt_id)
        if not isinstance(nonce, str) or not hmac.compare_digest(
            row["nonce_hash"], hashlib.sha256(nonce.encode()).hexdigest()
        ):
            raise ValueError("Invalid attempt nonce")
        return row

    def ready(self, attempt_id, nonce):
        with self.db.transaction():
            self.expire()
            row = self.authorize(attempt_id, nonce)
            if row["status"] == "active":
                return self.view(attempt_id)
            if (
                row["status"] != "preparing"
                or datetime.fromisoformat(row["expires_at"]) <= self.t.now()
            ):
                raise ValueError("Attempt is not available to start")
            self.db.update(
                "external_lab_attempts",
                "id=?",
                (attempt_id,),
                status="active",
                started_at=self.t.now().isoformat(),
            )
        return self.view(attempt_id)

    def abandon(self, attempt_id, nonce):
        with self.db.transaction():
            row = self.authorize(attempt_id, nonce)
            if row["status"] in {"preparing", "active", "imported"}:
                self.db.update(
                    "external_lab_attempts",
                    "id=?",
                    (attempt_id,),
                    status="abandoned",
                    ended_at=self.t.now().isoformat(),
                )
        return self.view(attempt_id)

    def submit(self, attempt_id, data):
        bounded(data)
        allowed = {
            "nonce",
            "recipe_version",
            "checker_version",
            "fixture_id",
            "answers",
            "report",
            "submission",
        }
        if set(data) - allowed:
            raise ValueError("Unexpected submission fields")
        with self.db.transaction():
            row = self.authorize(attempt_id, data.get("nonce"))
            if row["status"] not in {"active", "imported"}:
                raise ValueError("Attempt already submitted, abandoned, or not ready")
            if datetime.fromisoformat(row["expires_at"]) <= self.t.now():
                raise ValueError("Attempt has expired")
            recipe = self.recipe(row["recipe_id"], row["origin"] == "offline")
            current_fixture = recipe["fixture_id"]
            case = json.loads(row["assignment"]) if row["assignment"] else None
            if recipe["grading"] == "prefix-policy-v1":
                from ascend.local_labs.prefix import fixture_id

                current_fixture = fixture_id(recipe, case)
            for key in ("recipe_version", "checker_version", "fixture_id"):
                current = (
                    recipe["version"]
                    if key == "recipe_version"
                    else current_fixture
                    if key == "fixture_id"
                    else recipe[key]
                )
                if data.get(key) != row[key] or current != row[key]:
                    raise ValueError(
                        "Submission recipe, checker or fixture version mismatch"
                    )
            if recipe["grading"] == "audit-answers-v1":
                if set(data) & {"report", "submission"}:
                    raise ValueError("This task accepts answers only")
                result = answer_check(data.get("answers"))
                if getattr(self.t, "server_mode", False):
                    result.update(
                        authority="server-answer", evidence_label="Answer checked"
                    )
            elif recipe["grading"] == "local-report-v1":
                if set(data) & {"answers", "submission"}:
                    raise ValueError("This task accepts a local report only")
                report = data.get("report")
                if isinstance(report, dict) and (
                    "evidence" in report
                    or (recipe.get("adapter") == "frr-bgp-v1" and "exercise" in report)
                ):
                    from ascend.local_labs.upstream import validate_report

                    result = validate_report(recipe, report)
                else:
                    result = local_report(report, recipe)
            elif recipe["grading"] == "upstream-report-v1":
                from ascend.local_labs.upstream import validate_report

                if set(data) & {"answers", "submission"}:
                    raise ValueError("This task accepts an upstream local report only")
                result = validate_report(recipe, data.get("report"))
            elif recipe["grading"] == "prefix-policy-v1":
                from ascend.local_labs.prefix import check_submission

                if set(data) & {"answers", "report"}:
                    raise ValueError(
                        "This task accepts only the policy.json submission"
                    )
                result = check_submission(
                    recipe,
                    case,
                    data.get("submission"),
                    trusted=getattr(self.t, "server_mode", False),
                )
                if result["status"] == "error":
                    raise ValueError(
                        "Policy tests unavailable; retry this attempt: "
                        + result["detail"]
                    )
            else:
                raise ValueError("No supported grader for this recipe")
            result.update(
                recipe_id=row["recipe_id"],
                recipe_version=row["recipe_version"],
                checker_version=row["checker_version"],
                fixture_id=row["fixture_id"],
                origin=row["origin"],
            )
            participation = True
            if recipe["grading"] == "audit-answers-v1":
                answers = data.get("answers", {})
                strings = (
                    "discovery_event_id",
                    "executable",
                    "companion_event_id",
                    "intent",
                    "explanation",
                )
                participation = (
                    all(
                        isinstance(answers.get(key), str) and answers[key].strip()
                        for key in strings
                    )
                    and len(answers["explanation"].strip()) >= 20
                    and type(answers.get("uid")) is int
                    and all(
                        isinstance(answers.get(key), list)
                        and answers[key]
                        and all(
                            isinstance(value, str) and value.strip()
                            for value in answers[key]
                        )
                        for key in ("arguments", "benign_event_ids")
                    )
                )
            if participation and result["status"] in {"pass", "fail"}:
                result["practice_reward"] = rewards.award(
                    self.t,
                    "local-lab",
                    row["recipe_id"],
                    recipe["title"],
                    "lab-result-recorded",
                    event_key=f"local-lab:{attempt_id}",
                )
            self.db.update(
                "external_lab_attempts",
                "id=?",
                (attempt_id,),
                status="finished",
                ended_at=self.t.now().isoformat(),
                result=json.dumps(result),
            )
        response = self.view(attempt_id)
        if result.get("practice_reward"):
            response["result"]["practice_reward"] = result["practice_reward"]
        return response
