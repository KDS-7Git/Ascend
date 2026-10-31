"""Argument parsing and presentation only; use cases are shared with the server."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from ascend.application import Tracker
from ascend.engine.packs import dump_toml, parse_pack
from ascend.storage import Database


def parser():
    p = argparse.ArgumentParser(prog="ascend", description="One small, proof-backed step at a time")
    p.add_argument("--json", action="store_true")
    p.add_argument("--server")
    sub = p.add_subparsers(dest="command")
    today = sub.add_parser("today"); today.add_argument("minutes", type=int, nargs="?")
    done = sub.add_parser("done")
    done.add_argument("learned"); done.add_argument("next_step")
    done.add_argument("--complete", action="store_true"); done.add_argument("--force")
    done.add_argument("--proof"); done.add_argument("--minutes", "--min", type=int)
    done.add_argument("--node", dest="node_id"); done.add_argument("--mission", dest="mission_id", type=int)
    mission = sub.add_parser("mission").add_subparsers(dest="action", required=True)
    new = mission.add_parser("new"); new.add_argument("title")
    start = mission.add_parser("start"); start.add_argument("pack"); start.add_argument("--nudge-time")
    mission_time = mission.add_parser("nudge-time"); mission_time.add_argument("time")
    for name in ("finish", "pause", "list"): mission.add_parser(name)
    pack = sub.add_parser("pack").add_subparsers(dest="action", required=True)
    for name in ("install", "lint", "trust", "review", "diff"):
        action = pack.add_parser(name); action.add_argument("target")
    pack.add_parser("list")
    new = pack.add_parser("new"); new.add_argument("title"); new.add_argument("--path")
    review = sub.add_parser("review"); review.add_argument("target")
    mark = sub.add_parser("mark"); mark.add_argument("node"); mark.add_argument("status", choices=["done", "skipped", "todo"]); mark.add_argument("--note")
    skip = sub.add_parser("skip"); skip.add_argument("node"); skip.add_argument("--note")
    backfill = sub.add_parser("backfill"); backfill.add_argument("nodes", nargs="+")
    unlock = sub.add_parser("unlock"); unlock.add_argument("level")
    check = sub.add_parser("check"); check.add_argument("node", nargs="?"); check.add_argument("--complete", action="store_true")
    levels = sub.add_parser("levels"); levels.add_argument("--pack")
    for name in ("stats", "heatmap", "more", "parked", "remind-check"): sub.add_parser(name)
    park = sub.add_parser("park"); park.add_argument("note")
    resolve = sub.add_parser("resolve"); resolve.add_argument("idea_id", type=int)
    export = sub.add_parser("export"); export.add_argument("path", nargs="?", default="log.md")
    config = sub.add_parser("config"); config.add_argument("key"); config.add_argument("value", nargs="?")
    login = sub.add_parser("login"); login.add_argument("url", nargs="?")
    edit = sub.add_parser("edit"); edit.add_argument("entry_id", type=int); edit.add_argument("--learned"); edit.add_argument("--next-step")
    sub.add_parser("undo")
    search = sub.add_parser("search"); search.add_argument("query")
    split = sub.add_parser("split"); split.add_argument("node"); split.add_argument("steps", nargs="+")
    sub.add_parser("sync"); sub.add_parser("accept")
    sub.add_parser("nudge")
    install = sub.add_parser("install-nudge")
    install.add_argument("--dry-run", action="store_true"); install.add_argument("--directory")
    install.add_argument("--no-enable", action="store_true")
    return p


def pack_text(target):
    path = Path(target).expanduser()
    if path.is_file(): return path.read_text()
    for root in (Path(__file__).resolve().parents[2] / "packs/community", Path(__file__).resolve().parents[1] / "community"):
        path = root / f"{target}.toml"
        if path.is_file(): return path.read_text()
    raise ValueError("Pack not found; use a local TOML path or bundled pack ID")


def execute(tracker, args):
    command = args.command
    if command in {None, "today"}: return tracker.overview(getattr(args, "minutes", None))
    if command == "done": return tracker.log(**{k: getattr(args, k) for k in ("learned", "next_step", "proof", "minutes", "node_id", "complete", "force", "mission_id")})
    if command == "mission":
        if args.action == "new": return tracker.new_mission(args.title)
        if args.action == "start": return tracker.start_mission(args.pack, args.nudge_time)
        if args.action == "list": return tracker.db.rows("missions")
        if args.action == "nudge-time":
            mission = tracker.active_mission()
            if not mission: raise ValueError("No active mission")
            if args.time != "off": tracker.validate_time(args.time)
            tracker.db.update("missions", "id=?", (mission["id"],), nudge_time=None if args.time == "off" else args.time)
            return {"nudge_time": args.time}
        return tracker.finish_mission("paused" if args.action == "pause" else "done")
    if command in {"pack", "review"}:
        action = "review" if command == "review" else args.action
        if action == "list": return tracker.db.rows("packs")
        if action == "trust": return tracker.trust_pack(args.target)
        if action == "review": return tracker.review_pack(args.target)
        if action == "new":
            import re
            pid = re.sub(r"[^a-z0-9]+", "-", args.title.lower()).strip("-")
            text = dump_toml({"pack": {"id": pid, "title": args.title, "kind": "project", "version": 1, "source": "human", "reviewed": False},
                "level": [{"id": "start", "title": "First steps"}], "node": [{"id": "first", "level": "start", "title": "Make one example", "size": "S",
                    "done_when": "A small working example saved with an explanation", "resource": "https://docs.python.org/3/"}]})
            target = Path(args.path or f"{pid}.toml"); target.write_text(text)
            return {"created": str(target)}
        text = getattr(args, "target_text", None) or pack_text(args.target)
        if action == "install": return tracker.install_pack(text)
        pack = tracker.parse(text)
        if action == "lint": return {"valid": pack.id, "nodes": len(pack.nodes)}
        if action == "diff":
            old = tracker.pack(pack.id)
            before, after = {n.id for n in old.nodes}, {n.id for n in pack.nodes}
            return {"added": sorted(after-before), "removed": sorted(before-after), "retained": len(before & after)}
    if command == "mark": return tracker.mark(args.node, args.status, args.note)
    if command == "skip": return tracker.mark(args.node, "skipped", args.note)
    if command == "backfill": return tracker.backfill(args.nodes)
    if command == "unlock": return tracker.unlock(args.level)
    if command == "check": return tracker.check(args.node, args.complete)
    if command == "levels": return tracker.levels(args.pack)
    if command == "stats": return tracker.stats()
    if command == "heatmap": return tracker.heatmap()
    if command == "more":
        pack = tracker.pack()
        return [asdict(n) for n in tracker.candidates(pack)[1:3]]
    if command == "park": return tracker.park(args.note)
    if command == "parked": return tracker.db.rows("parked", "resolved=0")
    if command == "resolve":
        tracker.db.update("parked", "id=?", (args.idea_id,), resolved=1)
        return {"resolved": args.idea_id}
    if command == "export": return tracker.export()
    if command == "remind-check": return tracker.stats()["today_logged"]
    if command == "nudge" or (command == "config" and args.key == "nudge-test"):
        from ascend.nudge import NudgeRunner
        return NudgeRunner(tracker).run(test=command == "config")
    if command == "install-nudge":
        from ascend.nudge import install_timer
        return install_timer(tracker.db.home, args.directory, not args.no_enable, args.dry_run)
    if command == "config": return tracker.configure(args.key, args.value)
    if command == "edit": return tracker.edit(args.entry_id, args.learned, args.next_step)
    if command == "undo": return tracker.undo()
    if command == "search": return tracker.search(args.query)
    if command == "split": return tracker.split(args.node, args.steps)
    if command == "sync": return tracker.sync()
    if command == "accept": return tracker.accept()
    raise ValueError("Unknown command")


def bar(done, total):
    filled = round(10*done/total) if total else 0
    return "[" + "#"*filled + "-"*(10-filled) + "]"


def render(args, result):
    if args.json: return json.dumps(result, indent=2, default=str)
    if args.command in {None, "today"}:
        mission = result["mission"]
        draft = " [draft]" if result.get("draft") else ""
        lines = [f"Mission : {mission['title'] if mission else 'Start with ascend pack install home-hack-lab'}"]
        lv = result.get("level")
        if lv: lines.append(f"Level   : {lv['title']} {bar(lv['done'], lv['total'])} {lv['done']}/{lv['total']} steps · {lv['active_days']} active days")
        node = result.get("next")
        if node:
            text = f"{node['id']} — {node['title']}{draft} (~{node['estimate']} min); {node['done_when']}"
            if result.get("resume"): text += f" | Resume: {result['resume']}"
        else: text = result.get("resume") if not mission or not mission.get("pack_id") else None
        lines.append(f"Next    : {text or 'No step fits or remains open; try ascend split or ascend levels'}")
        quick = result.get("quick_win")
        if quick: lines.append(f"Quick win: {quick['id']} — {quick['title']}{draft} (~{quick['estimate']} min)")
        lines.append(f"Streak  : {result['current_streak']} days (best {result['best_streak']}) · freeze available: {result['freeze_available']}")
        lines.append("Today   : " + ("Logged" if result["today_logged"] else "Pending — log before your 04:00 rollover"))
        return "\n".join(lines)
    if args.command == "levels":
        return "\n".join(f"{lv['title']} ({lv['lane']}, {'open' if lv['open'] else 'locked'}) {bar(lv['done'], lv['total'])} {lv['done']}/{lv['total']} steps · {lv['active_days']} active days · {lv['minutes']} min" for lv in result)
    if args.command == "stats":
        return f"Streak: {result['current_streak']} days · best: {result['best_streak']}\nDays logged in last 30: {result['days_last_30']}\nFreezes used this week: {result['freezes_used']}\nMinutes this week: {result['minutes_this_week']}"
    if args.command == "heatmap":
        rows = [result[i:i+7] for i in range(0, len(result), 7)]
        return "Mon Tue Wed Thu Fri Sat Sun\n" + "\n".join(" ".join(" # " if day["count"] else " . " for day in week) for week in rows)
    if args.command == "done": return f"Logged entry {result['id']} for {result['day']}. " + ("Node complete." if result["completed"] else "Partial progress saved.") + (f" {result['verification']}" if result.get("verification") else "")
    if args.command == "check": return f"{result['summary']}. " + ("Node complete." if result["completed"] else "Use ascend check --complete to confirm a passing result.")
    return json.dumps(result, indent=2, default=str)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0].isdigit(): argv.insert(0, "today")
    args = parser().parse_args(argv)
    db = None
    try:
        from ascend.cli.remote import configure_server, login, request, server_url
        server = server_url(args.server)
        if args.command == "config" and args.key == "server":
            result = configure_server(args.value)
        elif args.command == "login":
            url = args.url or server
            if not url: raise ValueError("Supply a server URL")
            result = login(url)
        elif server:
            data = {"argv": argv}
            if args.command == "pack" and args.action in {"install", "lint", "diff"}:
                data["pack_text"] = pack_text(args.target)
            result = request(server, "/api/command", data)
        else:
            db = Database()
            result = execute(Tracker(db), args)
        if args.command == "remind-check": return 0 if result else 1
        if args.command == "export":
            Path(args.path).expanduser().write_text(result)
            print(f"Exported {args.path}")
        else: print(render(args, result))
        return 0
    except (ValueError, OSError) as error:
        print(f"ascend: {error}", file=sys.stderr)
        return 2
    finally:
        if db: db.close()
