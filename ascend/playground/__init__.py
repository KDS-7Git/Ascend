"""Shared Playground use cases. No activity ever marks a curriculum node."""

import json
import secrets
from copy import deepcopy
from datetime import datetime

from ascend.engine.practice import (
    readiness,
    ready,
    recommend,
    review_due,
    selection_minutes,
)
from ascend.engine.validation import validate_entry
from ascend.playground import catalog, fixtures, insights


def bounded_object(value):
    if not isinstance(value, dict) or len(json.dumps(value)) > 100_000:
        raise ValueError("Use a JSON object smaller than 100 KB")
    return value


class Playground:
    def __init__(self, tracker):
        self.t = tracker
        self.db = tracker.db

    def owned(self, run_id):
        rows = self.db.rows("activity_runs", "id=?", (run_id,))
        if not rows:
            raise ValueError("Activity run not found")
        return rows[0]

    def history_rows(self):
        return self.db.rows("activity_runs", order="created_at DESC, rowid DESC")

    def evidence(self):
        return self.db.rows("activity_evidence", order="day, rowid")

    def feedback(self, run_id, data):
        return insights.save_feedback(self, run_id, data)

    def insights(self):
        return insights.summary(self)

    def observe_selection(self, filters):
        return insights.observe_selection(self, filters)

    def elapsed(self, row):
        seconds = row["elapsed_seconds"]
        if row["status"] == "active" and row["running_since"]:
            seconds += max(0, (self.t.now() - datetime.fromisoformat(row["running_since"])).total_seconds())
        return seconds


    def pause_clock(self, row):
        self.db.update("activity_runs", "id=?", (row["id"],), elapsed_seconds=self.elapsed(row), running_since=None)

    def event(self, run_id, kind):
        self.owned(run_id)
        self.db.connection.execute(
            "INSERT OR IGNORE INTO activity_events(user_id,run_id,kind,created_at) VALUES (?,?,?,?)",
            (self.db.user_id, run_id, kind, self.t.now().isoformat()),
        )
        return {"recorded": True}

    def detail(self, activity_id):
        item = catalog.get(activity_id)
        skills = readiness(self.evidence())
        minutes, samples = selection_minutes(item, insights.feedback_rows(self))
        history = self.db.rows(
            "activity_runs",
            "activity_id=?",
            (activity_id,),
            order="created_at DESC, rowid DESC",
        )
        return {
            **catalog.public(item),
            "selection_minutes": minutes,
            "timing_samples": samples,
            "readiness": {
                ability: skills.get(skill, "unknown")
                for ability, skill in zip(item["prerequisites"], item["skills"])
            },
            "recommended_ready": ready(item, skills),
            "progress": "solved"
            if any(r["status"] == "passed" for r in history)
            else "started"
            if history
            else "new",
            "bookmarked": bool(
                self.db.rows("activity_bookmarks", "activity_id=?", (activity_id,))
            ),
            "saved_runs": [
                self.summary(r) for r in history if r["status"] in {"active", "saved"}
            ],
            "preparation_options": [
                catalog.public(catalog.get(ref)) for ref in item["preparation"]
            ],
        }

    def list(
        self,
        kind=None,
        minutes=None,
        topic=None,
        difficulty=None,
        environment=None,
        progress=None,
        format=None,
        search="",
        bookmarked=False,
        domain=None,
    ):
        if minutes is not None and (
            type(minutes) is not int or not 1 <= minutes <= 1440
        ):
            raise ValueError("Minutes must be between 1 and 1440")
        items = []
        for a in catalog.CATALOG:
            if any(
                value and a[key] != value
                for key, value in [
                    ("kind", kind),
                    ("topic", topic),
                    ("difficulty", difficulty),
                    ("environment", environment),
                    ("format", format),
                    ("domain", domain),
                ]
            ):
                continue
            if (
                minutes is not None
                and selection_minutes(a, insights.feedback_rows(self))[0] > minutes
            ):
                continue
            if (
                search
                and search.lower()
                not in (" ".join([a["title"], a["brief"], *a["prerequisites"]])).lower()
            ):
                continue
            detail = self.detail(a["id"])
            if (
                progress
                and detail["progress"] != progress
                or bookmarked
                and not detail["bookmarked"]
            ):
                continue
            items.append(detail)
        return {
            "activities": items,
            "empty_reason": None
            if items
            else "No activity fits these filters. Try one of these short worked examples or broaden the filters.",
            "alternatives": self.alternatives(domain) if not items else [],
        }

    def alternatives(self, domain=None):
        examples = [a for a in catalog.CATALOG if a["role"] == "example"]
        selected = [a for a in examples if not domain or a["domain"] == domain]
        return [catalog.public(a) for a in (selected or examples)[:2]]

    def recommendations(self, minutes=10, exclude=(), **filters):
        available = self.list(minutes=minutes, **({"kind": "quick"} | filters))[
            "activities"
        ]
        selected = recommend(
            [catalog.get(a["id"]) for a in available],
            self.evidence(),
            self.history_rows(),
            self.t.day(),
            exclude,
            feedback=insights.feedback_rows(self),
        )
        return {
            "activities": [self.detail(a["id"]) for a in selected],
            "reason": "Matched to the available time and relevant skill evidence. Readiness is a limited estimate."
            if selected
            else "No ready activity fits. Study a separate preparation example or broaden the filters.",
            "alternatives": self.alternatives(filters.get("domain"))
            if not selected
            else [],
            "review": review_due(self.evidence(), self.t.day()),
        }

    def foreground(self, end_scored=False):
        from ascend.local_labs.attempts import Attempts
        Attempts(self.t).expire()
        if self.db.rows("external_lab_attempts", "status IN ('preparing','active')"):
            raise ValueError("Finish the local lab before starting Playground")
        from ascend import timing
        if self.db.rows("task_sessions", "status='running'"):
            if not end_scored:
                raise ValueError("A scored track attempt is running. End scored attempt and switch to stop its clock without completion or XP. Browsing leaves it running.")
            timing.end(self.t)
        for row in self.db.rows("activity_runs", "status='active'"):
            self.pause_clock(row)
            self.event(row["id"], "saved")
        self.db.update("activity_runs", "status='active'", status="saved", updated_at=self.t.now().isoformat())

    def start(self, activity_id, end_scored=False, deliberate=False):
        item = catalog.get(activity_id)
        with self.db.transaction():
            skills = readiness(self.evidence())
            if not ready(item, skills) and not deliberate:
                raise ValueError(
                    "Background is not established for this activity. Study a preparation example, choose an easier challenge, or deliberately try this challenge."
                )
            self.foreground(end_scored)
            previous = self.history_rows()
            seen = {r["fixture_key"] for r in previous}
            variants = list(range(3)) if item["variant_strategy"] == "authored" else [0]
            variants.sort(
                key=lambda v: (
                    f"{item['id']}:v{item['version']}:{v}" in seen,
                    sum(
                        r["fixture_key"] == f"{item['id']}:v{item['version']}:{v}"
                        for r in previous
                    ),
                )
            )
            variant = variants[0]
            for _ in range(30):
                fixture = fixtures.generate(item, self.t.now(), variant)
                key = fixtures.fixture_key(item, fixture, variant)
                if (
                    key not in seen
                    or item["variant_strategy"] == "authored"
                    or item["role"] == "example"
                ):
                    break
            familiar = key in seen
            fixture["definition"] = deepcopy(item)
            fixture["variant"] = variant
            return self.create(item, fixture, key, skills, familiar)

    def create(self, item, fixture, key, skills, familiar=False, work=None):
        run_id = secrets.token_hex(16)
        stamp = self.t.now().isoformat()
        self.db.insert(
            "activity_runs",
            id=run_id,
            activity_id=item["id"],
            version=item["version"],
            kind=item["kind"],
            role=item["role"],
            family=item["family"],
            reward_key=f"track:{item['source_node']}"
            if item.get("source_node") and item["kind"] == "challenge"
            else item["reward_key"],
            fixture_key=key,
            fixture=json.dumps(fixture),
            readiness=json.dumps(skills),
            work=json.dumps(
                work
                if work is not None
                else {"workspace": fixture["public"]["data"]}
                if item["kind"] == "free"
                else work or {}
            ),
            status="active",
            running_since=stamp,
            familiar=int(familiar),
            created_at=stamp,
            updated_at=stamp,
        )
        return self.view(run_id)

    def summary(self, row):
        item = json.loads(row["fixture"])["definition"]
        return {
            k: row[k]
            for k in (
                "id",
                "activity_id",
                "version",
                "kind",
                "role",
                "status",
                "checks",
                "hints",
                "revealed",
                "familiar",
                "created_at",
                "updated_at",
            )
        } | {
            "title": item["title"],
            "difficulty": item["difficulty"],
            "result": json.loads(row["result"]) if row["result"] else None,
            "elapsed_seconds": int(self.elapsed(row)),
        }

    def view(self, run_id):
        row = self.owned(run_id)
        fixture = json.loads(row["fixture"])
        item = fixture["definition"]
        spoiled = self.db.rows(
            "activity_runs",
            "fixture_key=? AND (revealed=1 OR status='passed') AND id<>?",
            (row["fixture_key"], run_id),
        )
        public = {
            **self.summary(row),
            "activity": catalog.public(item),
            **fixture["public"],
            "work": json.loads(row["work"]),
            "feedback": next(
                iter(self.db.rows("activity_feedback", "run_id=?", (run_id,))), None
            ),
            "familiar": bool(row["familiar"] or spoiled),
            "readiness": {
                ability: json.loads(row["readiness"]).get(skill, "unknown")
                for ability, skill in zip(item["prerequisites"], item["skills"])
            },
            "hints_available": len(item["hints"]),
            "hint_text": item["hints"][: row["hints"]],
            "review_available": bool(
                item["review"] and row["status"] in {"passed", "ended"}
            ),
            "hidden_fault": bool(fixture.get("fault") and not fixture.get("repaired")),
            "timer": {
                "elapsed_seconds": int(self.elapsed(row)),
                "target_seconds": item["minutes"] * 60,
                "running": row["status"] == "active",
                "server_time": self.t.now().isoformat(),
            },
        }
        if row["role"] == "example":
            from ascend.playground.guidance import REFLECTIONS, steps

            public["teaching_steps"] = steps(item["family"])
            public["reflection_prompt"] = REFLECTIONS[item["family"]]
            history = {r["skill"] for r in self.db.rows("activity_tour_history")}
            needs_tour = any(
                s not in history
                and json.loads(row["readiness"]).get(s, "unknown") == "unknown"
                for s in item["skills"]
            )
            public["tour"] = public["work"].get(
                "tour",
                {
                    "status": "pending"
                    if needs_tour and row["status"] == "active"
                    else "available",
                    "step": 0,
                },
            )
        if item["role"] == "example" or row["revealed"] or row["status"] == "passed":
            public["debrief"] = fixture["debrief"]
            public["followup"] = fixture.get("followup")
        if row["revealed"] or row["status"] == "passed":
            public["solution"] = fixture["expected"]
            if fixture.get("fault"):
                public["fault_rule"] = fixture["fault"]
        if row["kind"] == "free":
            public["observations"] = self.observations(
                fixture, public["work"]["workspace"]
            )
        return public

    def resume(self, run_id, end_scored=False):
        with self.db.transaction():
            row = self.owned(run_id)
            if row["status"] == "saved":
                self.foreground(end_scored)
                self.event(run_id, "resumed")
                self.db.update(
                    "activity_runs",
                    "id=?",
                    (run_id,),
                    status="active",
                    running_since=self.t.now().isoformat(),
                    updated_at=self.t.now().isoformat(),
                )
            return self.view(run_id)

    def save(self, run_id, work, pause=True):
        bounded_object(work)
        with self.db.transaction():
            row = self.owned(run_id)
            previous = json.loads(row["work"])
            work = {key: value for key, value in work.items() if key != "tour"}
            if "tour" in previous:
                work = {**work, "tour": previous["tour"]}
            if row["kind"] == "free":
                fixtures.experiment(row["family"], work.get("workspace"))
            values = {"work": json.dumps(work), "updated_at": self.t.now().isoformat()}
            if pause and row["status"] == "active":
                self.pause_clock(row)
                self.event(run_id, "saved")
                values["status"] = "saved"
            self.db.update("activity_runs", "id=?", (run_id,), **values)
            return self.view(run_id)

    def tour(self, run_id, step=0, status="active"):
        from ascend.playground.guidance import steps

        with self.db.transaction():
            row = self.owned(run_id)
            item = json.loads(row["fixture"])["definition"]
            if row["role"] != "example":
                raise ValueError(
                    "Walkthroughs are available only for separate worked examples"
                )
            if (
                type(step) is not int
                or not 0 <= step < len(steps(item["family"]))
                or status not in {"active", "finished", "skipped"}
            ):
                raise ValueError("Invalid walkthrough step or status")
            work = json.loads(row["work"]) | {"tour": {"step": step, "status": status}}
            self.db.update("activity_runs", "id=?", (run_id,), work=json.dumps(work))
            if status in {"finished", "skipped"}:
                for skill in item["skills"]:
                    self.db.connection.execute(
                        "INSERT INTO activity_tour_history(user_id,skill,status,updated_at) VALUES (?,?,?,?) ON CONFLICT(user_id,skill) DO UPDATE SET status=excluded.status,updated_at=excluded.updated_at",
                        (self.db.user_id, skill, status, self.t.now().isoformat()),
                    )
            return {"tour": work["tour"]}

    def log(self, run_id, learned, next_step, minutes=None):
        with self.db.transaction():
            self.owned(run_id)
            previous = self.t.entries()
            next_step = next_step or "Choose another activity or return to your track"
            learned, next_step = validate_entry(
                learned,
                next_step,
                previous=previous[-1]["learned"] if previous else None,
                minutes=minutes,
                minimum=self.db.setting("min_learned_chars", 20),
            )
            existing = self.db.rows(
                "entries",
                "activity_run_id=? AND day=?",
                (run_id, self.t.day().isoformat()),
            )
            values = {
                "learned": learned,
                "next_step": next_step,
                "minutes": minutes,
                "source": "manual",
            }
            if existing:
                self.db.update("entries", "id=?", (existing[0]["id"],), **values)
                entry_id = existing[0]["id"]
            else:
                entry_id = self.db.insert(
                    "entries",
                    day=self.t.day().isoformat(),
                    logged_at=self.t.now().isoformat(),
                    mission_id=None,
                    node_id=None,
                    activity_run_id=run_id,
                    **values,
                )
            return {
                "id": entry_id,
                "saved": True,
                "day": self.t.day().isoformat(),
                "activity_run_id": run_id,
            }

    def evidence_write(self, row, fixture, outcome, independent=False):
        for skill in fixture["definition"]["skills"]:
            self.db.connection.execute(
                "INSERT OR REPLACE INTO activity_evidence(user_id,run_id,skill,fixture_key,outcome,independent,transfer,day) VALUES (?,?,?,?,?,?,?,?)",
                (
                    self.db.user_id,
                    row["id"],
                    skill,
                    row["fixture_key"],
                    outcome,
                    int(independent),
                    int(fixture["transfer"] and outcome == "passed"),
                    self.t.day().isoformat(),
                ),
            )

    def award(self, row, fixture):
        if (
            row["familiar"]
            or row["revealed"]
            or self.db.rows(
                "activity_runs",
                "fixture_key=? AND (revealed=1 OR status='passed') AND id<>?",
                (row["fixture_key"], row["id"]),
            )
        ):
            return 0
        day = self.t.day().isoformat()
        if row["kind"] == "quick":
            key, points = f"practice:{row['family']}:{day}", 10
            if (
                sum(
                    r["points"]
                    for r in self.db.rows(
                        "activity_rewards", "kind='quick' AND day=?", (day,)
                    )
                )
                >= 30
            ):
                return 0
        elif row["kind"] == "challenge":
            key, points = row["reward_key"], fixture["definition"]["award"]
            # Once a solution under this achievement identity is revealed, a
            # different authored variant cannot manufacture a first-solve award.
            if self.db.rows("activity_runs", "reward_key=? AND revealed=1", (key,)):
                return 0
            source = fixture["definition"].get("source_node")
            if source and self.db.rows(
                "xp_awards", "pack_id=? AND node_id=?", tuple(source.split(":", 1))
            ):
                return 0
        else:
            return 0
        if self.db.rows("activity_rewards", "reward_key=?", (key,)):
            return 0
        self.db.insert(
            "activity_rewards",
            reward_key=key,
            run_id=row["id"],
            kind=row["kind"],
            day=day,
            points=points,
        )
        return points

    def submit(self, run_id, answers, learned=None, next_step=None):
        bounded_object(answers)
        with self.db.transaction():
            row = self.owned(run_id)
            if row["status"] in {"passed", "ended"}:
                return self.view(run_id)
            if row["status"] != "active":
                raise ValueError("Resume this saved activity before submitting")
            fixture = json.loads(row["fixture"])
            if row["kind"] == "free":
                raise ValueError(
                    "A workspace has no assessment finish line; save work or learning notes"
                )
            if row["role"] == "example":
                self.log(run_id, learned, next_step)
                passed, independent, points, familiar = (
                    True,
                    False,
                    0,
                    bool(row["familiar"]),
                )
            else:
                passed = fixtures.evaluate(fixture, answers)
                familiar = row["familiar"] or bool(
                    self.db.rows(
                        "activity_runs",
                        "fixture_key=? AND (revealed=1 OR status='passed') AND id<>?",
                        (row["fixture_key"], run_id),
                    )
                )
                independent = not (row["hints"] or row["revealed"] or familiar)
                points = self.award(row, fixture) if passed else 0
            work = json.loads(row["work"]) | {"answers": answers}
            if passed:
                self.pause_clock(row)
            outcome = {
                "passed": passed,
                "xp": points,
                "assistance": "independent"
                if independent
                else "practice"
                if familiar
                else "assisted",
                "message": "Worked example saved. Try the separate challenge when ready."
                if row["role"] == "example"
                else "Evidence checks passed."
                if passed
                else "The evidence checks do not all match. Compare your prediction with the fixture, study a separate example, or save for later.",
            }
            self.db.update(
                "activity_runs",
                "id=?",
                (run_id,),
                checks=row["checks"] + 1,
                status="passed" if passed else row["status"],
                result=json.dumps(outcome),
                work=json.dumps(work),
                updated_at=self.t.now().isoformat(),
            )
            self.evidence_write(
                row,
                fixture,
                "example"
                if row["role"] == "example"
                else "passed"
                if passed
                else "needs-practice",
                independent and passed and not row["checks"],
            )
            if (
                passed
                and row["role"] != "example"
                and self.db.setting("auto_counts_for_streak", True)
                and not self.db.rows(
                    "entries",
                    "activity_run_id=? AND day=?",
                    (run_id, self.t.day().isoformat()),
                )
            ):
                self.db.insert(
                    "entries",
                    day=self.t.day().isoformat(),
                    logged_at=self.t.now().isoformat(),
                    mission_id=None,
                    node_id=None,
                    activity_run_id=run_id,
                    learned=f"Completed Playground activity: {fixture['definition']['title']}",
                    next_step="Try a changed case or return to the track",
                    source="activity",
                    complete=0,
                )
            return self.view(run_id)

    def hint(self, run_id):
        with self.db.transaction():
            row = self.owned(run_id)
            item = json.loads(row["fixture"])["definition"]
            if not item["hints"]:
                raise ValueError(
                    "This independent challenge has no hints. Separate preparation examples remain available."
                )
            if row["status"] not in {"active", "saved"}:
                raise ValueError("The attempt has ended; use its review")
            self.db.update(
                "activity_runs",
                "id=?",
                (run_id,),
                hints=min(row["hints"] + 1, len(item["hints"])),
            )
            return self.view(run_id)

    def end(self, run_id):
        with self.db.transaction():
            row = self.owned(run_id)
            if row["status"] != "passed":
                self.pause_clock(row)
                self.db.update(
                    "activity_runs",
                    "id=?",
                    (run_id,),
                    status="ended",
                    updated_at=self.t.now().isoformat(),
                )
            return self.view(run_id)

    def reveal(self, run_id):
        with self.db.transaction():
            row = self.owned(run_id)
            fixture = json.loads(row["fixture"])
            if row["status"] not in {"passed", "ended"}:
                raise ValueError(
                    "Solve or explicitly end the attempt before opening its solution"
                )
            if not fixture["definition"]["review"] and not fixture.get("fault"):
                raise ValueError("This activity has no solution review")
            self.db.update("activity_runs", "id=?", (run_id,), revealed=1)
            return self.view(run_id)

    def bookmark(self, activity_id, enabled=True):
        catalog.get(activity_id)
        if enabled:
            self.db.connection.execute(
                "INSERT OR IGNORE INTO activity_bookmarks(user_id,activity_id) VALUES (?,?)",
                (self.db.user_id, activity_id),
            )
        else:
            self.db.connection.execute(
                "DELETE FROM activity_bookmarks WHERE user_id=? AND activity_id=?",
                (self.db.user_id, activity_id),
            )
        return {"bookmarked": enabled}

    def history(self):
        return [self.summary(r) for r in self.history_rows()]

    def observations(self, fixture, workspace):
        fixtures.experiment(fixture["definition"]["family"], workspace)
        copy = deepcopy(workspace)
        if fixture.get("fault") and not fixture.get("repaired"):
            copy["policy"][fixture["fault"]] = not copy["policy"][fixture["fault"]]
        return fixtures.experiment(fixture["definition"]["family"], copy)

    def experiment(self, run_id, workspace):
        bounded_object(workspace)
        row = self.owned(run_id)
        if row["kind"] != "free":
            raise ValueError("This is not a free-practice workspace")
        if row["status"] != "active":
            raise ValueError(
                "Resume this workspace or make a new copy before experimenting"
            )
        return {
            "observations": self.observations(json.loads(row["fixture"]), workspace)
        }

    def copy(self, run_id, reset=False, fault=False, blank=False, end_scored=False):
        with self.db.transaction():
            row = self.owned(run_id)
            if row["kind"] != "free":
                raise ValueError("Only workspaces can be copied")
            fixture = json.loads(row["fixture"])
            item = fixture["definition"]
            if fault and item["family"] != "access":
                raise ValueError(
                    "Hidden faults are available in the permission workspace"
                )
            if (
                fault
                and readiness(self.evidence()).get("access", "unknown") == "unknown"
            ):
                raise ValueError(
                    "Study the separate request-decisions example before introducing a hidden fault"
                )
            work = json.loads(row["work"])
            if reset or blank:
                work = {"workspace": fixtures.workspace_fixture(item["family"])}
                fixture.pop("fault", None)
                fixture.pop("repaired", None)
            if blank:
                work["workspace"][
                    "requests" if item["family"] == "access" else "events"
                ] = []
            if fault:
                fixture["fault"] = secrets.choice(
                    ["deny_disabled", "admin_write", "owner_access", "admin_read"]
                )
                fixture["debrief"] = (
                    "One implementation rule was inverted relative to the displayed policy. Compare disabled, owner and unrelated-admin controls to isolate it. Repair must restore the owner workflow while still denying disabled and unrelated writes."
                )
                fixture.pop("repaired", None)
            self.foreground(end_scored)
            key = (
                f"workspace-fault:{fixture['fault']}"
                if fixture.get("fault")
                else row["fixture_key"]
            )
            return self.create(
                item,
                fixture,
                key,
                readiness(self.evidence()),
                familiar=bool(
                    self.db.rows(
                        "activity_runs",
                        "fixture_key=? AND (revealed=1 OR status='passed')",
                        (key,),
                    )
                ),
                work=work,
            )

    def repair(self, run_id, rule):
        with self.db.transaction():
            row = self.owned(run_id)
            fixture = json.loads(row["fixture"])
            if not fixture.get("fault") or row["kind"] != "free":
                raise ValueError("This workspace has no hidden fault")
            if row["status"] != "active":
                raise ValueError(
                    "Resume this workspace or make a new copy before repairing"
                )
            if rule != fixture["fault"]:
                return {
                    "repaired": False,
                    "message": "That rule does not explain the captured behavior. Keep testing the controls.",
                }
            fixture["repaired"] = True
            controls = fixtures.experiment(
                "access", json.loads(row["work"])["workspace"]
            )
            self.db.update(
                "activity_runs", "id=?", (run_id,), fixture=json.dumps(fixture)
            )
            return {
                "repaired": True,
                "controls": controls,
                "message": "Implementation restored to your displayed policy. The saved requests now match that policy's control results.",
            }
