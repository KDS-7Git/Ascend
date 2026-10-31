"""Shared use cases for local CLI and later HTTP clients.

Rules live in engine; persistence and external checks enter through adapters.
"""
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import tempfile

from ascend.engine.levels import next_nodes, open_levels
from ascend.engine.packs import Node, parse_pack, substitute
from ascend.engine.streak import best_streak, logical_date, streak_details
from ascend.engine.validation import guard_secrets, validate_entry
from ascend.engine.verifiers import VerifyResult
from ascend.verifiers import command, file, manual, http, git


class Tracker:
    def __init__(self, db, clock=None):
        self.db = db
        self.clock = clock or (lambda: datetime.now().astimezone())

    def now(self):
        return self.clock()

    def day(self, now=None):
        return logical_date(now or self.now(), self.db.setting("timezone"), self.db.setting("rollover_hour", 4))

    def audit(self, action, detail):
        self.db.insert("audit", created_at=self.now().isoformat(), action=action, detail=json.dumps(detail))

    def parse(self, text, variables=None):
        return parse_pack(text, variables)

    def install_pack(self, text):
        pack = self.parse(text)
        digest = hashlib.sha256(text.encode()).hexdigest()
        root = self.db.home / "packs" / str(self.db.user_id)
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = root / f"{pack.id}.toml"
        old = self.db.rows("packs", "id=?", (pack.id,))
        same = old and old[0]["fingerprint"] == digest
        with tempfile.NamedTemporaryFile(mode="w", dir=root, delete=False) as temp:
            temp.write(text)
            temp_path = Path(temp.name)
        temp_path.replace(target)
        with self.db.transaction():
            self.db.connection.execute("""INSERT INTO packs(user_id,id,path,version,reviewed,trusted,fingerprint)
                VALUES (?,?,?,?,?,?,?) ON CONFLICT(user_id,id) DO UPDATE SET path=excluded.path,
                version=excluded.version,reviewed=excluded.reviewed,trusted=excluded.trusted,fingerprint=excluded.fingerprint""",
                (self.db.user_id, pack.id, str(target), pack.version, old[0]["reviewed"] if same else int(pack.reviewed),
                 old[0]["trusted"] if same else 0, digest))
            self.audit("pack-install", {"pack": pack.id, "version": pack.version})
        return {"id": pack.id, "nodes": len(pack.nodes), "commands": [substitute(n.verify["cmd"], pack.vars) for n in pack.nodes if n.verify.get("type") == "command"],
                "plugins": sorted({n.verify["type"][7:] for n in pack.nodes if n.verify.get("type", "").startswith("plugin:")}), "reviewed": pack.reviewed}

    def pack(self, pack_id=None):
        if pack_id is None:
            mission = self.active_mission()
            pack_id = mission["pack_id"] if mission else None
        rows = self.db.rows("packs", "id=?", (pack_id,))
        if not rows: raise ValueError("No installed pack selected; install a pack and start a mission")
        row = rows[0]
        text = Path(row["path"]).read_text()
        digest = hashlib.sha256(text.encode()).hexdigest()
        if digest != row["fingerprint"]:
            self.db.update("packs", "id=?", (pack_id,), fingerprint=digest, trusted=0, reviewed=0)
        pack = self.parse(text, self.db.setting(f"vars:{pack_id}", {}))
        splits = {r["node_id"]: json.loads(r["steps"]) for r in self.db.rows("node_splits", "pack_id=?", (pack_id,))}
        nodes = []
        for node in pack.nodes:
            if node.id in splits:
                previous = node.needs
                for i, title in enumerate(splits[node.id], 1):
                    child = Node(f"{node.id}-part-{i}", node.level, title, "S", f"I completed this step: {title}", node.resource, previous, minutes=10)
                    nodes.append(child); previous = (child.id,)
                node = replace(node, needs=previous)
            nodes.append(node)
        return replace(pack, nodes=tuple(nodes))

    def trust_pack(self, pack_id):
        pack = self.pack(pack_id)
        self.db.update("packs", "id=?", (pack.id,), trusted=1)
        self.audit("pack-trust", {"pack": pack.id})
        return {"trusted": pack.id}

    def review_pack(self, pack_id):
        pack = self.pack(pack_id)
        self.db.update("packs", "id=?", (pack.id,), reviewed=1)
        self.audit("pack-review", {"pack": pack.id})
        return {"reviewed": pack.id}

    def states(self, pack_id):
        return {s["node_id"]: s for s in self.db.rows("node_state", "pack_id=?", (pack_id,))}

    def overrides(self, pack_id):
        return {r["level_id"] for r in self.db.rows("level_unlocks", "pack_id=?", (pack_id,))}

    def active_mission(self):
        rows = self.db.rows("missions", "status='active'")
        return rows[0] if rows else None

    def new_mission(self, title, pack_id=None, nudge_time=None):
        if not title.strip(): raise ValueError("Mission title is required")
        guard_secrets(title)
        if nudge_time: self.validate_time(nudge_time)
        with self.db.transaction():
            if self.active_mission(): raise ValueError("Another mission is active; finish or pause it first")
            mid = self.db.insert("missions", title=title.strip(), pack_id=pack_id, status="active", created_at=self.now().isoformat(), nudge_time=nudge_time)
        return {"id": mid, "title": title}

    def start_mission(self, pack_id, nudge_time=None):
        pack = self.pack(pack_id)
        return self.new_mission(pack.title, pack.id, nudge_time)

    def finish_mission(self, status="done"):
        if status not in {"done", "paused"}: raise ValueError("Invalid mission status")
        mission = self.active_mission()
        if not mission: raise ValueError("No active mission")
        self.db.update("missions", "id=?", (mission["id"],), status=status, finished_at=self.now().isoformat() if status == "done" else None)
        return {"title": mission["title"], "status": status, "entries": len(self.db.rows("entries", "mission_id=?", (mission["id"],)))}

    def entries(self):
        return self.db.rows("entries", order="id")

    def candidates(self, pack, max_minutes=None):
        return next_nodes(pack, {nid: row["status"] for nid, row in self.states(pack.id).items()}, max_minutes, self.overrides(pack.id))

    def resolve_node(self, reference=None):
        pack_id, node_id = reference.split(":", 1) if reference and ":" in reference else (None, reference)
        pack = self.pack(pack_id)
        if node_id:
            node = next((n for n in pack.nodes if n.id == node_id), None)
        else:
            candidates = self.candidates(pack)
            main = {lv.id for lv in pack.levels if lv.lane == "main"}
            node = next((n for n in candidates if n.level in main), candidates[0] if candidates else None)
        if node is None: raise ValueError("No matching open node; choose a node explicitly")
        return pack, node

    def overview(self, max_minutes=None):
        stats = self.stats()
        mission = self.active_mission()
        result = {"mission": mission, "next": None, "quick_win": None, "level": None, **stats}
        recent = self.entries()
        result["resume"] = recent[-1]["next_step"] if recent else None
        if mission and mission["pack_id"]:
            pack = self.pack(mission["pack_id"])
            row = self.db.rows("packs", "id=?", (pack.id,))[0]
            result["draft"] = pack.source == "ai-draft" and not row["reviewed"]
            lanes = {lv.id: lv.lane for lv in pack.levels}
            for n in self.candidates(pack, max_minutes):
                key = "next" if lanes[n.level] == "main" else "quick_win"
                if result[key] is None: result[key] = {**asdict(n), "estimate": n.estimate, "pack_id": pack.id}
            if max_minutes is not None and result["next"] is None:
                result["next"], result["quick_win"] = result["quick_win"], None
            if result["next"]:
                result["level"] = next(lv for lv in self.levels(pack.id) if lv["id"] == result["next"]["level"])
        return result

    def levels(self, pack_id=None):
        pack = self.pack(pack_id)
        states = self.states(pack.id)
        finished = {nid for nid, row in states.items() if row["status"] in {"done", "skipped"}}
        opened = open_levels(pack, finished, self.overrides(pack.id))
        entries = self.entries()
        eligible = {n.id for n in self.candidates(pack)}
        result = []
        for lv in pack.levels:
            nodes = [n for n in pack.nodes if n.level == lv.id]
            refs = {f"{pack.id}:{n.id}" for n in nodes}
            logs = [e for e in entries if e["node_id"] in refs]
            result.append({**asdict(lv), "open": lv.id in opened, "done": sum(n.id in finished for n in nodes),
                           "total": len(nodes), "active_days": len({e["day"] for e in logs}), "minutes": sum(e["minutes"] or 0 for e in logs),
                           "nodes": [{**asdict(n), "estimate": n.estimate, "pack_id": pack.id,
                                      "status": states.get(n.id, {}).get("status", "todo"), "open": n.id in eligible} for n in nodes]})
        return result

    def unlock(self, level_id):
        pack = self.pack()
        if level_id not in {lv.id for lv in pack.levels}: raise ValueError("Unknown level")
        with self.db.transaction():
            self.db.connection.execute("INSERT OR IGNORE INTO level_unlocks VALUES (?,?,?)", (self.db.user_id, pack.id, level_id))
            self.audit("unlock", {"pack": pack.id, "level": level_id})
        return {"unlocked": level_id}

    def mark(self, reference, status, note=None, how="manual"):
        if status not in {"done", "skipped", "todo"}: raise ValueError("Invalid node status")
        guard_secrets(note)
        pack, node = self.resolve_node(reference)
        with self.db.transaction():
            self.db.connection.execute("""INSERT INTO node_state(user_id,pack_id,node_id,status,done_at,evidence,how)
                VALUES (?,?,?,?,?,?,?) ON CONFLICT(user_id,pack_id,node_id) DO UPDATE SET
                status=excluded.status,done_at=excluded.done_at,evidence=excluded.evidence,how=excluded.how,revision=node_state.revision+1""",
                (self.db.user_id, pack.id, node.id, status, self.now().isoformat() if status != "todo" else None, note, how))
            self.audit("mark", {"pack": pack.id, "node": node.id, "status": status, "how": how})
            if status in {"done", "skipped"}:
                for split in self.db.rows("node_splits", "pack_id=?", (pack.id,)):
                    parent = split["node_id"]
                    children = [f"{parent}-part-{i}" for i in range(1, len(json.loads(split["steps"]))+1)]
                    states = self.states(pack.id)
                    if node.id in children and all(states.get(c, {}).get("status") in {"done", "skipped"} for c in children):
                        self.mark(f"{pack.id}:{parent}", "done", "All user-defined parts completed")
        return {"node": node.id, "status": status, "how": how}

    def backfill(self, references):
        with self.db.transaction():
            return [self.mark(ref, "done", "completed before Ascend") for ref in references]

    def verify_node(self, pack, node):
        vtype = node.verify.get("type", "manual")
        if vtype.startswith("plugin:"):
            if getattr(self, "restricted", False): return VerifyResult(False, "Plugins require administrator permission on a multi-user server")
            from ascend.verifiers.plugin import verify
            return verify(self.db, vtype[7:], node.verify, pack.vars)
        if getattr(self, "restricted", False):
            if vtype in {"command", "git", "http"}:
                return VerifyResult(False, "This verifier requires administrator permission on a multi-user server")
            if vtype == "file":
                target = Path(substitute(node.verify["path"], pack.vars)).expanduser().resolve()
                root = (self.db.home / "artifacts" / str(self.db.user_id)).resolve()
                if not target.is_relative_to(root): return VerifyResult(False, "Evidence must be in your server artifact directory")
        if vtype == "command":
            row = self.db.rows("packs", "id=?", (pack.id,))[0]
            if not row["trusted"]: return VerifyResult(False, f"Run ascend pack trust {pack.id} before executing commands")
        return {"manual": manual, "file": file, "command": command, "http": http, "git": git}[vtype].verify(node.verify, pack.vars)

    def trust_plugin(self, name):
        from ascend.verifiers.plugin import trust
        result = trust(self.db, name)
        self.audit("plugin-trust", {"name": name})
        return result

    def _auto_evidence(self, pack, node, result):
        if not result.ok or not result.evidence_time or not self.db.setting("auto_counts_for_streak", True): return
        stamp = result.evidence_time.isoformat()
        if result.evidence_time > self.now(): return
        guard_secrets(result.summary)
        if self.db.rows("evidence_log", "pack_id=? AND node_id=? AND evidence_time=?", (pack.id, node.id, stamp)): return
        source = "verifier:" + node.verify.get("type", "manual")
        self.db.insert("evidence_log", pack_id=pack.id, node_id=node.id, evidence_time=stamp)
        mission = self.active_mission()
        self.db.insert("entries", day=self.day(result.evidence_time).isoformat(), logged_at=self.now().isoformat(),
                       mission_id=mission["id"] if mission else None, learned=result.summary, next_step=f"Continue after {node.title}",
                       proof=source, node_id=f"{pack.id}:{node.id}", source=source, complete=1)

    def check(self, reference=None, confirm=False):
        pack, node = self.resolve_node(reference)
        result = self.verify_node(pack, node)
        completed = result.ok and (confirm or (node.auto_complete and node.verify.get("type") in {"file", "command"}))
        if completed:
            with self.db.transaction():
                self.mark(f"{pack.id}:{node.id}", "done", result.summary, "verifier:" + node.verify.get("type", "manual"))
                self._auto_evidence(pack, node, result)
        return {"ok": result.ok, "summary": result.summary, "completed": completed, "node": node.id}

    def log(self, learned, next_step, proof=None, minutes=None, node_id=None, complete=False, force=None, mission_id=None):
        if force and not complete: raise ValueError("--force requires --complete")
        if force is not None and not force.strip(): raise ValueError("A force reason is required")
        guard_secrets(force)
        mission = self.active_mission()
        if mission_id:
            rows = self.db.rows("missions", "id=?", (mission_id,))
            if not rows: raise ValueError("Unknown mission")
            mission = rows[0]
        pack = node = None
        if node_id or (mission and mission["pack_id"]):
            reference = node_id or (f"{mission['pack_id']}:" if mission and mission["pack_id"] else None)
            pack, node = self.resolve_node(reference)
            if mission and mission["pack_id"] != pack.id: raise ValueError("Node does not belong to the selected mission")
        if complete and node is None: raise ValueError("Completion requires a pack node")
        previous = self.entries()
        learned, next_step = validate_entry(learned, next_step, proof, previous[-1]["learned"] if previous else None, minutes,
                                            minimum=self.db.setting("min_learned_chars", 20))
        verification = self.verify_node(pack, node) if complete else None
        completed = bool(complete and (verification.ok or force))
        with self.db.transaction():
            # Recheck under the write lock to avoid concurrent duplicate logs.
            last = self.db.rows("entries", order="id DESC")
            validate_entry(learned, next_step, proof, last[0]["learned"] if last else None, minutes)
            entry_id = self.db.insert("entries", day=self.day().isoformat(), logged_at=self.now().isoformat(),
                                      mission_id=mission["id"] if mission else None, learned=learned, next_step=next_step,
                                      proof=proof, minutes=minutes, node_id=f"{pack.id}:{node.id}" if node else None,
                                      source="manual", complete=int(completed))
            if completed:
                before = self.states(pack.id).get(node.id)
                how = "forced" if force else ("manual" if node.verify.get("type", "manual") == "manual" else "verifier:" + node.verify["type"])
                self.mark(f"{pack.id}:{node.id}", "done", force or verification.summary, how)
                self.db.update("entries", "id=?", (entry_id,), completion_before=json.dumps(before), completion_revision=self.states(pack.id)[node.id]["revision"])
        return {"id": entry_id, "day": self.day().isoformat(), "completed": completed,
                "verification": verification.summary if verification else None}

    def stats(self):
        entries = self.entries()
        today = self.day()
        days = {date.fromisoformat(e["day"]) for e in entries if e["day"] <= today.isoformat()}
        allowance = self.db.setting("freezes_per_week", 1)
        streak, used = streak_details(days, today, allowance)
        weeks = []
        monday = today - timedelta(days=today.weekday())
        for i in range(7, -1, -1):
            start = monday - timedelta(weeks=i)
            weeks.append({"week": start.isoformat(), "minutes": sum(e["minutes"] or 0 for e in entries if start.isoformat() <= e["day"] < (start + timedelta(days=7)).isoformat())})
        minutes_by_level = []
        for row in self.db.rows("packs"):
            try: pack = self.pack(row["id"])
            except (ValueError, OSError): continue
            for level in pack.levels:
                ids = {f"{pack.id}:{n.id}" for n in pack.nodes if n.level == level.id}
                minutes_by_level.append({"pack_id": pack.id, "level_id": level.id, "title": level.title,
                                         "minutes": sum(e["minutes"] or 0 for e in entries if e["node_id"] in ids)})
        return {"current_streak": streak, "best_streak": best_streak(days, allowance), "today": today.isoformat(),
                "today_logged": today in days, "days_last_30": sum(today-timedelta(days=29) <= d <= today for d in days),
                "freezes_used": used.get(today.isocalendar()[:2], 0), "freeze_available": max(0, allowance-used.get(today.isocalendar()[:2], 0)),
                "minutes_this_week": weeks[-1]["minutes"], "weeks": weeks, "minutes_by_level": minutes_by_level}

    def heatmap(self):
        counts = {}
        for entry in self.entries(): counts[entry["day"]] = counts.get(entry["day"], 0) + 1
        end = self.day()
        start = end - timedelta(days=end.weekday() + 77)
        return [{"day": (start + timedelta(days=i)).isoformat(), "count": counts.get((start+timedelta(days=i)).isoformat(), 0)} for i in range((end-start).days+1)]

    def park(self, note):
        guard_secrets(note)
        if not note.strip(): raise ValueError("A note is required")
        return {"id": self.db.insert("parked", note=note.strip(), created_at=self.now().isoformat())}

    def export(self):
        def escape(value): return str(value or "").replace("\n", " ").replace("|", "\\|")
        return "# Ascend learning log\n\n" + "\n".join(f"- {e['day']} | {escape(e['learned'])} | Next: {escape(e['next_step'])} | Proof: {escape(e['proof'])}" for e in self.entries()) + "\n"

    @staticmethod
    def validate_time(value):
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value): raise ValueError("Time must be HH:MM")

    def configure(self, key, value):
        if value is None: raise ValueError("A setting value is required")
        key = key.replace("-", "_")
        if key == "nudge_time": self.validate_time(value)
        elif key == "nudge_channel":
            if value not in {"desktop", "ntfy", "telegram", "webpush"}: raise ValueError("Unknown nudge channel")
        elif key == "ntfy_topic":
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value or ""): raise ValueError("Invalid ntfy topic")
        elif key == "timezone":
            from zoneinfo import ZoneInfo
            try: ZoneInfo(value)
            except (KeyError, ValueError): raise ValueError("Unknown IANA timezone") from None
        elif key in {"auto_counts_for_streak", "nudge_enabled", "public_streak"}:
            if value not in {"true", "false"}: raise ValueError("Use true or false")
            value = value == "true"
        else: raise ValueError("Unknown setting")
        self.db.set_setting(key, value)
        if key == "timezone" and getattr(self, "server_mode", False):
            self.db.connection.execute("UPDATE users SET timezone=? WHERE id=?", (value, self.db.user_id))
        return {key: value}

    def edit(self, entry_id, learned=None, next_step=None):
        with self.db.transaction():
            rows = self.db.rows("entries", "id=?", (entry_id,))
            if not rows: raise ValueError("Entry not found")
            entry = rows[0]
            previous = self.db.rows("entries", "id<?", (entry_id,), order="id DESC")
            text, step = validate_entry(learned if learned is not None else entry["learned"], next_step if next_step is not None else entry["next_step"],
                                       entry["proof"], previous[0]["learned"] if previous else None, entry["minutes"], manual=entry["source"] == "manual")
            self.audit("edit", {"before": entry, "after": {"learned": text, "next_step": step}})
            self.db.update("entries", "id=?", (entry_id,), learned=text, next_step=step)
        return {"edited": entry_id}

    def undo(self):
        with self.db.transaction():
            rows = self.db.rows("entries", order="id DESC")
            if not rows: raise ValueError("No entry to undo")
            entry = rows[0]
            age = (self.now() - datetime.fromisoformat(entry["logged_at"])).total_seconds()
            if not 0 <= age <= 600: raise ValueError("Undo is limited to the last 10 minutes")
            if entry["complete"] and entry["node_id"] and entry["completion_revision"] is not None:
                pid, nid = entry["node_id"].split(":", 1)
                state = self.states(pid).get(nid)
                if state and state["revision"] == entry["completion_revision"]:
                    before = json.loads(entry["completion_before"] or "null")
                    self.mark(entry["node_id"], before["status"] if before else "todo", before["evidence"] if before else "Entry undone", before["how"] if before else "manual")
            self.audit("undo", entry)
            self.db.connection.execute("DELETE FROM entries WHERE user_id=? AND id=?", (self.db.user_id, entry["id"]))
        return {"undone": entry["id"]}

    def search(self, query):
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        return self.db.rows("entries", "(learned LIKE ? ESCAPE '\\' OR next_step LIKE ? ESCAPE '\\' OR proof LIKE ? ESCAPE '\\')", (pattern, pattern, pattern), order="id DESC")

    def split(self, reference, steps):
        if len(steps) < 2 or any(len(s.strip()) < 3 for s in steps): raise ValueError("Supply at least two concrete smaller steps")
        guard_secrets(*steps)
        pack, node = self.resolve_node(reference)
        if node.id in self.states(pack.id) and self.states(pack.id)[node.id]["status"] != "todo": raise ValueError("Only unfinished nodes can be split")
        if self.db.rows("node_splits", "pack_id=? AND node_id=?", (pack.id, node.id)): raise ValueError("This node is already split")
        child_ids = {f"{node.id}-part-{i}" for i in range(1, len(steps)+1)}
        if child_ids & {n.id for n in pack.nodes}: raise ValueError("Split IDs would collide with existing nodes")
        with self.db.transaction():
            self.db.insert("node_splits", pack_id=pack.id, node_id=node.id, steps=json.dumps(steps))
            self.audit("split", {"pack": pack.id, "node": node.id, "steps": steps})
        return {"split": node.id, "parts": len(steps)}

    def sync(self):
        pack = self.pack()
        proposals = []
        for node in self.candidates(pack):
            if node.verify.get("type", "manual") == "manual": continue
            result = self.check(f"{pack.id}:{node.id}")
            if result["ok"]: proposals.append(result)
        self.db.set_setting("proposals", [f"{pack.id}:{p['node']}" for p in proposals if not p["completed"]])
        return proposals

    def accept(self):
        results = [self.check(ref, confirm=True) for ref in self.db.setting("proposals", [])]
        self.db.set_setting("proposals", [])
        return results
