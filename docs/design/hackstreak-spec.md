# hackstreak: a Duolingo-style streak tracker for learning cyber (and anything else)

A local-first tool that makes "one small real step per day" automatic, visible and hard to quietly skip.
Written to be handed to a coding agent (Antigravity) and built in phases. **Build Phase 1 only first.**

---

## 1. Why this exists (the problem, in the owner's words)

- Overwhelmed by choice -> reads a few words, learns nothing.
- Cannot tell whether something was "done" -> cannot tick anything.
- Interruptions (calls, deadlines) destroy the thread -> restarts from zero on a new topic.
- Duolingo chess streak works daily. OverTheWire Bandit stalled. The difference:

| Duolingo has | hackstreak must provide |
|---|---|
| Tiny fixed minimum | A "valid day" = ONE small, proof-backed step |
| Zero decisions | `hack` prints the single next step. No menu. |
| Cost of skipping | Visible streak + loss warning |
| A nudge | Telegram message at a chosen time |
| Low friction | One command to resume, one command to log |

## 2. Non-goals

- Not a course platform, not a planner, not a monthly roadmap. Only the NEXT step.
- No AI content generation. Learning material comes from real sources (OverTheWire, TryHackMe, picoCTF, books).
- Never store passwords, flags or secrets.

## 3. Design principles

1. **Derived, not stored.** Streak numbers are always computed from the raw log. No counters to corrupt.
2. **Proof over ticks.** A day only counts with a one-line "what I learned" (min 20 characters) plus a "next step".
3. **Forgiving but honest.** 1 freeze per ISO week, never miss twice in a row.
4. **Late-night aware.** The owner often works past midnight. The day rolls over at **04:00 local time**, not 00:00.
5. **Local-first, plain files.** SQLite + exportable markdown. Works offline on Ubuntu, Windows and a Raspberry Pi 5.
6. **Small surface.** Phase 1 is about 200 lines of Python and ZERO dependencies.

## 4. Tech choices

- Python 3.11+, standard library only for Phase 1 (`sqlite3`, `argparse`, `datetime`).
- Data in `~/.hackstreak/hackstreak.db` (override with `HACKSTREAK_HOME`).
- Phase 2: `urllib` for Telegram (no extra dependency). Phase 3: FastAPI + one static HTML page.

## 5. Data model (SQLite)

```sql
CREATE TABLE IF NOT EXISTS missions (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',   -- active | done | paused
  created_at TEXT NOT NULL,
  finished_at TEXT
);
-- Rule: at most ONE mission with status='active' at a time (enforced in code).

CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY,
  day TEXT NOT NULL,            -- logical date YYYY-MM-DD (after 04:00 rollover)
  logged_at TEXT NOT NULL,      -- real timestamp, ISO 8601
  mission_id INTEGER,           -- nullable
  learned TEXT NOT NULL,        -- >= 20 chars
  next_step TEXT NOT NULL,      -- what to do next time
  proof TEXT,                   -- optional: URL, commit hash, level name, file path
  minutes INTEGER               -- optional
);
CREATE INDEX IF NOT EXISTS idx_entries_day ON entries(day);

CREATE TABLE IF NOT EXISTS parked (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL,
  note TEXT NOT NULL,
  resolved INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY, value TEXT NOT NULL
);
-- defaults: rollover_hour=4, freezes_per_week=1, min_learned_chars=20
```

## 6. Rules

- **Logical day:** `logical_date(now) = (now - rollover_hour hours).date()`.
  Logging at 01:00 on 1 Nov counts for 31 Oct.
- **Valid day:** at least one entry whose logical day is that date.
- **One entry is enough.** More entries the same day are allowed (they feed stats, not the streak).
- **Freeze:** a missing day is bridged if (a) the day before AND the day after are both logged, and
  (b) fewer than `freezes_per_week` freezes were already used in that ISO week. A bridged day adds 0 to the count
  but does not break the chain. Freezes are computed, not stored.
- **Never miss twice:** two missing days in a row always break the streak.
- **Today pending:** if today is not logged yet, the streak is not broken. It is shown as "at risk".
- **Anti-gaming:** reject `learned` shorter than 20 characters, or identical to the previous entry's `learned`.
- **Secrets guard:** warn and refuse if `learned`/`proof` looks like a 32-character alphanumeric string
  (that is a Bandit password) or contains `flag{` / `picoCTF{` / `THM{`.

## 7. CLI

```
hack                       # prints: active mission, LAST next_step, streak, at-risk warning. Nothing else.
hack done "learned..." "next step..." [--proof X] [--min N] [--mission ID]
hack mission new "Title"   # fails if another mission is active (finish or pause it first)
hack mission finish        # marks done, prints a short summary
hack mission list
hack park "one-line idea"  # the rabbit-hole parking lot
hack parked                # list unresolved parked ideas
hack stats                 # current streak, best streak, days logged in last 30, freezes used this week
hack heatmap               # 12-week text heatmap (GitHub style)
hack export [path]         # writes log.md (one line per entry) for git
hack remind-check          # exit 0 if today logged, exit 1 if not (used by the nudge script)
```

Output style: short and plain. `hack` must fit in 6 lines. Example:

```
Mission : Hack and harden my Pi
Next    : Bandit level 13 - ssh with a private key
Streak  : 9 days   (best 9)   freeze available: yes
Today   : NOT logged yet - log before 04:00
```

## 8. Streak algorithm (reference implementation, must pass the tests in section 11)

```python
from datetime import date, timedelta

def compute_streak(logged: set[date], today: date, freezes_per_week: int = 1) -> int:
    count, used = 0, {}
    d = today if today in logged else today - timedelta(days=1)
    while True:
        if d in logged:
            count += 1
        else:
            wk = d.isocalendar()[:2]
            isolated = (d - timedelta(days=1)) in logged and (d + timedelta(days=1)) in logged
            if isolated and used.get(wk, 0) < freezes_per_week:
                used[wk] = used.get(wk, 0) + 1     # bridge the gap, add 0
            else:
                break
        d -= timedelta(days=1)
    return count
```

`best_streak` = run the same logic from every logged day and take the max (fine for personal-scale data).

## 9. Phases

**Phase 1: CLI core (build this first, one sitting).**
`hack`, `hack done`, `mission`, `park/parked`, `stats`, `export`, `remind-check`, tests. Install as a single file
`hack` on PATH (Linux) or `hack.bat`/`pipx` shim (Windows).

**Phase 2: Nudges.**
- `nudge.py`: if `hack remind-check` fails, send a Telegram message through the Bot API using
  `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from environment variables. The message includes the streak and the
  next step: "Streak 9. Chess done? Next: Bandit 13 - ssh key login."
- Run it from cron (Linux) or a systemd timer on the Raspberry Pi at e.g. 21:30 and again at 23:30 (second one only if still unlogged).
- Optional: auto `git add/commit/push` of `log.md` on every `hack done` (green squares on GitHub).

**Phase 3: Dashboard (optional, only after a 14-day streak).**
- FastAPI on the Pi: `GET /api/streak`, `GET /api/entries`, `POST /api/entries`. One static HTML page with a heatmap and the next step.
- `hack` can talk to the Pi instead of local SQLite when `HACKSTREAK_SERVER` is set (so laptop and phone share one log).
- Read-only `GET /api/streak` so the Praxis dashboard can show "hack streak" next to the other platforms.

**Phase 4: Ideas, deliberately NOT now.**
Per-mission streaks, weekly review prompt, TryHackMe API import (their streak API is unofficial, so check the terms of use first), an Android widget.

## 10. Security and safety

- Local files only in Phase 1. No network code at all.
- Telegram token only from environment variables, never written to the DB or the repo. Add `.env` to `.gitignore`.
- Phase 3 server: bind to LAN only, require a bearer token from env, never expose to the internet.
- Never log credentials. The secrets guard in section 6 is mandatory, not optional.

## 11. Acceptance tests (write these first)

`compute_streak(logged, today)` with `freezes_per_week=1`, `today = 2026-11-05` (Thursday):

| Case | Logged days | Expected |
|---|---|---|
| empty | none | 0 |
| only today | 11-05 | 1 |
| 3 consecutive ending yesterday, today pending | 11-02, 11-03, 11-04 | 3 |
| gap of 1 inside one week | 11-02, 11-04, 11-05 | 3 (11-03 frozen) |
| two gaps in the same ISO week | 11-02, 11-04, 11-06 with today 11-06 | breaks at the second gap |
| gap of 2 | 11-01, 11-04, 11-05 | 2 |
| yesterday missed, today pending | 11-03 | 0 (breaks until today is logged) |
| yesterday missed, then today logged | 11-03, 11-05 | 3 (yesterday frozen) |
| gap crossing a week boundary | one freeze per week each | each week's freeze is counted separately |

Other tests:
- `logical_date` at 2026-11-01 01:00 -> 2026-10-31; at 2026-11-01 04:00 -> 2026-11-01.
- `hack done` rejects `learned` shorter than 20 characters and rejects a repeat of the previous `learned`.
- `hack done` rejects a 32-character alphanumeric string and `flag{...}`-style content.
- `hack mission new` fails while another mission is active.
- DB file is created on first run with the schema above and survives repeated runs (idempotent).

## 12. Prompt to paste into the Antigravity agent

> Build **Phase 1 only** of the project described in `hackstreak-spec.md`. Python 3.11, standard library only, a single
> installable CLI called `hack`. Write the tests from section 11 FIRST (pytest), then implement until they pass.
> Do not add features that are not in Phase 1. Do not add a web UI, network code or any dependency.
> When done, show me: the file tree, the output of `pytest`, and a demo of `hack mission new`, `hack done`, `hack`, `hack stats`.
> Ask me before deviating from the spec.

## 13. Owner's usage rules (the human part)

1. Sequence: chess lesson -> one cyber step -> `hack done`.
2. Finish each session by writing the NEXT step. That is the whole re-entry system.
3. New idea or link? `hack park "..."` and go back. Review the parked list only when a mission finishes.
4. A deadline day counts. Ten minutes and one Bandit level is a valid day.
5. Missed a day? Fine. Never miss two.
