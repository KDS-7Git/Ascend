from datetime import datetime, time, timedelta
import json
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

from ascend.nudge.channels.desktop import send


class NudgeRunner:
    def __init__(self, tracker, sender=None):
        self.tracker = tracker
        if sender is None and tracker.db.setting("nudge_channel", "desktop") == "ntfy":
            from ascend.nudge.channels.ntfy import send as ntfy_send
            sender = lambda message: ntfy_send(message, topic=tracker.db.setting("ntfy_topic"))
        self.sender = sender or send

    def message(self):
        overview = self.tracker.overview()
        next_node = overview.get("next") or overview.get("quick_win")
        step = next_node["title"] if next_node else (overview.get("resume") or "Take one small step")
        return f"Streak {overview['current_streak']} (at risk). Next: {step}. A small step is enough."

    def run(self, test=False):
        if test:
            self.sender("Ascend test: " + self.message())
            return {"sent": True, "test": True}
        tracker = self.tracker
        with tracker.db.transaction():
            if tracker.stats()["today_logged"]: return {"sent": False, "reason": "Today is logged"}
            now = tracker.now()
            timezone = tracker.db.setting("timezone")
            if timezone: now = now.astimezone(ZoneInfo(timezone))
            mission = tracker.active_mission()
            reminder = (mission or {}).get("nudge_time") or tracker.db.setting("nudge_time", "21:30")
            hour, minute = map(int, reminder.split(":"))
            today = tracker.day()
            first = datetime.combine(today, time(hour, minute), tzinfo=now.tzinfo)
            if hour < tracker.db.setting("rollover_hour", 4): first += timedelta(days=1)
            due = [i for i in range(2) if first + timedelta(hours=2*i) <= now]
            # One notification per invocation, including after a machine resumes.
            slot = max(due) if due else None
            key = "nudge_sent:" + today.isoformat()
            sent = tracker.db.setting(key, [])
            if slot is None or slot in sent or len(sent) >= 2:
                return {"sent": False, "reason": "No reminder due"}
            self.sender(self.message())
            tracker.db.set_setting(key, [*sent, slot])
            return {"sent": True, "slot": slot}


def systemd_units(home, executable=None):
    def quote(value):
        return json.dumps(str(value)).replace("%", "%%")
    return {
        "ascend-nudge.service": "[Unit]\nDescription=Ascend daily reminder\n\n[Service]\nType=oneshot\n"
            + f"Environment={quote('ASCEND_HOME=' + str(Path(home).resolve()))}\n"
            + f"ExecStart={quote(executable or sys.executable)} -m ascend nudge\n",
        "ascend-nudge.timer": "[Unit]\nDescription=Check Ascend reminder schedule\n\n[Timer]\nOnCalendar=*-*-* *:*:00\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n",
    }


def install_timer(home, directory=None, enable=True, dry_run=False):
    units = systemd_units(home)
    if dry_run: return units
    directory = Path(directory or "~/.config/systemd/user").expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in units.items(): (directory / name).write_text(text)
    if enable:
        try:
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, timeout=10, capture_output=True)
            subprocess.run(["systemctl", "--user", "enable", "--now", "ascend-nudge.timer"], check=True, timeout=10, capture_output=True)
        except (subprocess.SubprocessError, OSError):
            raise ValueError("Timer files written; enable with systemctl --user enable --now ascend-nudge.timer in your desktop session") from None
    return {"installed": str(directory), "enabled": enable}
