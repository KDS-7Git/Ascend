# hackstreak v2: streaks + editable roadmaps ("packs") + optional auto-verification

**Precedence:** this file supersedes `hackstreak-spec.md` (v1) wherever they conflict.
Keep v1 sections 6 (rules), 8 (streak algorithm), 10 (security) and the streak tests in 11 exactly as written.
Replaced by this file: v1 sections 4, 5, 7, 9 and 12.

---

## 1. The design in one paragraph

The app has three layers. The **engine** (code) knows streaks, logging and "what is my next step", and knows nothing about any
subject. **Packs** (plain TOML text files the owner can edit) hold the roadmap: nodes with prerequisites, size, a real
resource link and a mandatory "done when" sentence. **Verifiers** (small plugins) can check a node automatically
(a file exists, a command succeeds, Codeforces shows a new accepted problem). The map is therefore DATA the owner controls,
not behaviour hardcoded in the program, and auto-fetch is an optional bonus on top of honest manual marking.

## 2. Principles added in v2

1. **Map = data.** Nothing about Bandit, Juice Shop or any platform appears in engine code. Ever.
2. **Packs are read-only inputs; progress is separate.** Pack files are never modified by the app. Progress lives in SQLite.
   Updating a pack never loses progress (nodes are matched by `id`).
3. **Every node has a `done_when`.** An ambiguous "did I do it?" is a pack-authoring defect and `lint` rejects it.
4. **Streak day and node completion are different things.** Any real work counts for the streak (partial progress is fine).
   A node completes only when its `done_when` is met. This removes the "I did something but can't tick anything" feeling.
5. **Verifiers propose, humans confirm,** except hard local checks, which may auto-complete if the node allows it.
6. **Generated maps are drafts.** A pack drafted by an AI is labelled `source = "ai-draft"` and `reviewed = false` and every node it
   shows is marked `[draft]` until the owner runs `hack review`. AI may order and link; it must not invent lessons or URLs.

## 3. Pack format (TOML, readable with Python's standard `tomllib`)

```toml
[pack]
id = "home-hack-lab"          # unique, kebab-case
title = "Home hack lab"
version = 1
source = "ai-draft"           # human | ai-draft | imported
reviewed = false

[vars]                        # user-editable values, substituted as {name} inside strings
pi_user = "pi"
pi_ip = "192.168.1.50"

# Levels group nodes (like Duolingo units). Order in the file = order of the main path.
[[level]]
id = "setup"
title = "Build the lab"
lane = "main"                 # main = gated path (default) | side = always-open quick wins
gate = true                   # main lanes only: level opens when the previous main level is fully done/skipped

[[level]]
id = "warmup"
title = "Daily warm-up"
lane = "side"                 # side lanes never block and never wait; they supply the "quick win" for busy days

[[node]]
level = "setup"
id = "pi-reachable"           # unique within the pack, stable forever (progress is keyed on it)
title = "Pi is reachable from the laptop"
size = "M"                    # S <= 30 min, M = 1-2 h, L = 3 h+
needs = []                    # prerequisite node ids (must form a DAG)
done_when = "ping to the Pi works from the laptop in both directions"
resource = "https://www.raspberrypi.com/documentation/computers/remote-access.html"
verify = { type = "command", cmd = "ping -c 1 -W 2 {pi_ip}" }   # optional; default is manual
auto_complete = false         # true = a passing verifier completes the node without asking

# Series: one definition that expands into many chained nodes (generic, works for any numbered material).
[[node]]
id = "bandit"
title = "OverTheWire Bandit, level {n}"
series = { from = 13, to = 33 }
size = "S"
needs = []
done_when = "I logged in to level {next} and can explain the command that got me there"
resource = "https://overthewire.org/wargames/bandit/"
```

Rules enforced by `hack pack lint <file>`:
- `id`s unique; `needs` reference existing ids; graph is acyclic.
- every node has a `level` that exists; levels have `id`, `title`, `lane` (`main` default, or `side`); at least one `main` level exists.
- a `series` node lives in exactly one level (use two series nodes if the material spans levels).
- every node has `title`, `size` (S/M/L), `done_when` (min 15 characters) and `resource` (an http(s) URL).
- series expand to ids `bandit-13` ... `bandit-33`; each depends on the previous one; the first inherits the series' `needs`.
  `{n}` = current number, `{next}` = n + 1.
- unknown `verify.type` is an error. A pack containing `command` verifiers prints the commands and requires `hack pack trust <id>` first (see section 7).
- `hack pack check-links <file>` sends a HEAD/GET to every `resource` and reports dead links. Run it on every AI-drafted pack.

## 4. Storage additions (SQLite)

```sql
CREATE TABLE IF NOT EXISTS packs (
  id TEXT PRIMARY KEY, path TEXT NOT NULL, version INTEGER, reviewed INTEGER DEFAULT 0, trusted INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS node_state (
  pack_id TEXT NOT NULL, node_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'todo',      -- todo | done | skipped
  done_at TEXT, evidence TEXT, how TEXT,    -- how: manual | verifier:<type> | forced
  PRIMARY KEY (pack_id, node_id)
);
-- entries (from v1) gain three columns:
ALTER TABLE entries ADD COLUMN node_id TEXT;       -- "pack:node", nullable
ALTER TABLE entries ADD COLUMN source TEXT DEFAULT 'manual';   -- manual | verifier:<type>
ALTER TABLE entries ADD COLUMN complete INTEGER DEFAULT 0;
-- missions (from v1) gain: pack_id TEXT  (a mission = "work through this pack"); still only ONE active mission.
```

## 5. Choosing the next step (the "zero decisions" rule)

```python
SIZE_MIN = {"S": 30, "M": 120, "L": 240}

def open_levels(levels, nodes, finished):
    opened, prev_complete = set(), True
    for lv in levels:                                  # pack order
        if lv.lane == "side":
            opened.add(lv.id)                          # side lanes are always open
            continue
        if prev_complete or not lv.gate:
            opened.add(lv.id)
        prev_complete = all(n.id in finished for n in nodes if n.level == lv.id)
    return opened

def next_nodes(nodes, levels, state, max_minutes=None):
    finished = {nid for nid, st in state.items() if st in ("done", "skipped")}
    opened = open_levels(levels, nodes, finished)
    out = []
    for n in nodes:                                    # pack order = tie-breaker
        if n.id in finished:
            continue
        if n.level not in opened:                      # level gate
            continue
        if not all(r in finished for r in n.needs):    # locked by prerequisites
            continue
        # NOTE: prev_complete in open_levels() checks only the milestone node(s) of a level when any exist,
        # not every node in it -- gate = "passed the level's real test", not "touched every item".
        if max_minutes is not None and SIZE_MIN[n.size] > max_minutes:
            continue
        out.append(n)
    return out
```

- `hack` shows the first candidate from a `main` lane as **Next**, and the first candidate from a `side` lane as **Quick win**
  (so a busy day always has a 10-minute option). No full list by default; `hack more` shows two alternatives.
- Level display: `Level 2/3  Recon & attack  [####------] 3/8 steps  5 active days`. "Active days" = distinct logical days with an
  entry whose node belongs to that level. This is the per-level, day-wise view; the global daily streak is unchanged.
- `hack levels` lists every level with progress and active days. `hack unlock <level>` opens a gated level early (logged), so a
  gate can never trap the owner. `hack skip <node>` is `mark ... skipped`.
- With `hack <minutes>`: show the main-lane step if it fits, otherwise the side-lane quick win, otherwise suggest `hack split`.
- `hack 20` = "I have 20 minutes": only nodes that fit. If none fit it says so and suggests `hack split`.
- On an academic/deadline day the owner types `hack 10` and gets the smallest valid step. The streak survives.

## 6. Entry semantics (partial vs complete)

- `hack done "learned..." "next step..."` logs an entry (counts for the streak) against the current node. The node stays open.
- `hack done ... --complete` also tries to mark the node done: it runs the node's verifier first.
  - verifier passes (or node is manual): node becomes `done`, `how` = manual or verifier name.
  - verifier fails: print its reason, do NOT complete. `--force "reason"` overrides and records `how = forced`.
- `hack check` runs the current node's verifier on its own and, if it passes, offers to complete it.
- `hack mark <node> done|skipped|todo [--note ...]` is the honest manual route. It is always allowed.
- `hack backfill <node> [<node>...]` marks nodes done with `how = manual`, `evidence = "completed before hackstreak"`, without creating streak entries.
  (The owner uses this for Bandit 0-12.)

## 7. Verifiers (plugins)

Interface, one small file per verifier in `hackstreak/verifiers/`:

```python
class VerifyResult(NamedTuple):
    ok: bool
    summary: str            # shown to the user and stored as evidence, e.g. "nmap output 1.2 KB, modified today"
    evidence_time: datetime | None   # when the real-world thing happened (None = unknown)

def verify(spec: dict, vars: dict) -> VerifyResult: ...
```

Built-ins by phase:

| Type | Checks | Phase |
|---|---|---|
| `manual` | nothing; human confirms | 1 |
| `file` | path exists, optional `min_bytes`, optional `contains` regex | 1 |
| `command` | runs a shell command, exit code 0 = pass, 10 s timeout, output truncated | 1 |
| `http` | GET url, expected status | 2 |
| `git` | repo has a commit matching a regex since a date | 2 |
| `codeforces` | public API: accepted problems since node start >= N | 3 |
| `praxis` | reads the local Praxis API (`/api/overview`, `/api/submissions`) for solved-count deltas | 3 |
| `github` | public API: commits/pushes since a date | 3 |

**Trust model.** `command` verifiers execute shell commands from a pack file. A pack from someone else (or from an AI) is
code. Therefore: `hack pack install` prints every command, nothing runs until `hack pack trust <id>` is typed, and editing a
pack resets trust. Commands run with the owner's permissions, with no `sudo`, never through a shell string built from user input
(use `shlex.split`, `shell=False`).

**Auto evidence counts.** When a verifier passes with a known `evidence_time`, the app writes an entry for that day with
`source = "verifier:<type>"` and an auto-generated `learned` line (the verifier summary). Proof is the verifier, so the 20-character
rule applies only to manual entries. Setting `auto_counts_for_streak` (default true) can turn this off.

`hack sync` runs the verifiers of all UNLOCKED nodes, lists what looks done, and either completes (`auto_complete = true`) or asks
`hack accept`.

## 8. What can honestly be auto-fetched (verify these before building, APIs change)

| Source | Auto-detect? | How | My confidence |
|---|---|---|---|
| Anything on the owner's machines (files, scans, containers, ssh works, git commits) | Yes | `file` / `command` / `git` / `http` | High, fully under the owner's control |
| Codeforces | Yes | public API | High |
| GitHub | Yes | public API | High |
| Praxis (own app) | Yes | already syncs CF/LC/AtCoder/GfG, reuse its API | High |
| LeetCode, GfG | Partly | unofficial endpoints, may break | Medium |
| TryHackMe, HackTheBox | Unclear | no stable official progress API that I am sure of; check docs first | Low |
| OverTheWire (Bandit etc.), picoCTF, books, videos | No | no account-progress API | Use manual + a concrete `done_when` |

**Artifact trick for things that cannot be fetched:** make the proof something that exists on the owner's disk (a short
writeup file, a scan, a script) and verify THAT with the `file` verifier. It also builds the habit of explaining things.
**Never store or log wargame passwords or flags** (v1 secrets guard stays).

## 8b. Pack scale: "project" packs vs "proficiency" packs

A pack that finishes in a week solves nothing; the owner is back to "what now" within days. Two kinds of pack, named
explicitly so neither gets mistaken for the other:

- **Project pack** (`pack.kind = "project"`): a concrete build with a finish line, 3-6 levels, finishes in days-to-weeks.
  Example: the home hack lab itself.
- **Proficiency pack** (`pack.kind = "proficiency"`): meant to make the owner genuinely good at a subject (networking,
  OS internals, a language, DSA topic, web/mobile dev). **8-15 main levels**, each a real sub-skill, spanning weeks to a
  few months at the owner's real pace. This is the default for "I want to learn X" requests.

Every level in a proficiency pack ends with one **milestone node** (`milestone = true`, size `M` or `L`): a harder,
integrative task that cannot be passed by rote repetition of the level's small nodes, e.g. "build a tiny TCP chat
client+server from scratch, no copied code, and explain every socket call" rather than "read about sockets." A level's
gate (section 5) checks on the milestone node specifically, not merely on every node being done, so "proficient in this
level" has a real test behind it, the same way a Duolingo unit ends with a harder review lesson.
`lint` requires at least one `milestone = true` node per main level.

## 9. Pack authoring (how maps get made without losing control)

Three sources, all ending in the same lint -> review -> install pipeline:
1. **By hand:** `hack pack new "Topic"` scaffolds a TOML file with one example node.
2. **AI draft:** the owner (or Claude, or a local model) produces TOML from the prompt below, then:
   `hack pack lint` -> `hack pack check-links` -> read it -> `hack review <pack>` (flips `reviewed`) -> `hack pack install`.
3. **Imported:** converted from a public roadmap by hand. Check that source's licence before copying its content.

Prompt for generating a pack draft (paste into any LLM):

> Output ONLY a TOML file in the hackstreak pack format (sections `[pack]`, `[vars]`, `[[node]]`).
> Topic: <topic>. My level: <level>. Hardware: <hardware>. Weekly time: <time>.
> Rules: every node needs id, title, size (S<=30min, M=1-2h, L=3h+), needs, done_when (one concrete checkable sentence,
> ideally an artifact on my disk), and resource (a real, well-known URL; if you are not sure a URL exists, write
> `resource = "TODO"` instead of guessing). Do not write lesson content. Prefer free official or community resources.
> Use `series` for numbered material. If this is a PROFICIENCY request (learn a subject, not build one project), use
> `pack.kind = "proficiency"` and write 8-15 `[[level]]` blocks on the `main` lane (like Duolingo units), each 4-8 nodes
> covering one real sub-skill, and end each level with one `milestone = true` node that is a harder integrative task
> (build/explain something from scratch), not a repeat of the level's small steps. If this is a PROJECT request (one
> concrete build with a finish line), use `pack.kind = "project"` and keep it to 3-6 levels total.
> Either way add at most one `side` lane level of S-sized quick wins for busy days. Every node needs a `level`.
> Order so that the first node can be started tonight. Prefer done_when sentences that produce an artifact on my disk.
> Set `source = "ai-draft"` and `reviewed = false`.

### 9b. Workflow: "ask Claude for each new unit"

The engine ships with one starter pack. Every later unit is a new pack drafted on request:
1. Fill in `new-unit-request-template.md` (topic, current level, time, hardware, what is already done) and paste it into a chat.
2. The model replies with ONLY a TOML pack. Save it to `packs/<id>.toml`.
3. `hack pack lint` -> `hack pack check-links` -> read every `done_when` -> `hack review <id>` -> `hack pack install <id>`.
4. `hack backfill ...` for anything already done, then `hack mission start <id>` (only one active mission at a time).
The model has no memory between chats, so the template carries everything it needs; do not rely on it remembering the format.

## 10. CLI summary (v1 commands plus)

```
hack                         next node, mission, streak, today status (max 6 lines)
hack 20                      next node that fits in 20 minutes
hack more                    two alternatives to the current next node
hack done "..." "..." [--complete] [--force "why"] [--proof X]
hack check                   run current node's verifier
hack sync                    run verifiers on all unlocked nodes, propose completions
hack accept                  confirm proposed completions
hack mark <node> done|skipped|todo [--note ...]
hack backfill <node>...      mark old progress without creating streak entries
hack pack new|lint|check-links|install|trust|list|diff|review
hack mission start <pack>    make a pack the active mission (one active at a time)
hack levels                  every level: progress bar, steps done/total, active days
hack unlock <level>          open a gated level early (always allowed, always logged)
hack skip <node>             shorthand for: mark <node> skipped
hack split <node> "a" "b"    (Phase 2) replace a node with owner-defined smaller steps, stored in the DB, pack untouched
hack park / parked / stats / heatmap / export / remind-check     (unchanged from v1)
hack config nudge-time HH:MM | nudge-channel telegram|desktop|both | nudge-test
hack install-nudge            set up the local (Ubuntu) desktop-notification timer
```

## 11. Phases (revised)

- **Phase 1 (one sitting, stdlib only):** v1 Phase 1 + packs (`tomllib`), `lint`, `install`, `trust`, `mission start`, next-step picking
  with `hack <minutes>`, `mark`, `backfill`, `done --complete`, verifiers `manual` / `file` / `command`, milestone-gated levels.
- **Phase 1b (nudging -- build right after Phase 1, same week):** see section 11b. This exists now, not later, because a
  system that never pings the owner relies on willpower, which is the exact thing that has not worked so far.
- **Phase 2:** `http` and `git` verifiers, `sync`/`accept`, `split`, `check-links`.
- **Phase 3:** Codeforces / Praxis / GitHub verifiers, dashboard, shared log across devices.
- **Phase 4 (deliberately later):** pack sharing, optional LeetCode/TryHackMe verifiers if their APIs prove stable.

## 11b. Nudging (Phase 1b)

**Problem specific to this owner:** the laptop dual-boots Windows 11 and Ubuntu 24.04. A cron job on Ubuntu goes silent
on every day spent in Windows. The Raspberry Pi 5 is the one machine that is always on regardless of what the laptop is
doing, so the Pi is the primary nudge source. The laptop's own notifications are a secondary, bonus channel.

**Primary: Telegram from the Pi (reliable across both OSes).**
- `hack sync-to-pi` (or a `cron`/`rsync` one-liner) mirrors `~/.hackstreak/hackstreak.db` (or just the `entries`/`node_state`
  tables) to the Pi once a day, OR, simpler for Phase 1b: the owner runs `hack` ad-hoc on the Pi itself over SSH, OR the DB
  lives on the Pi from the start and the laptop points `HACKSTREAK_HOME` at it over the already-working SSH/LAN link from
  the hack-lab mission. Pick whichever is already true by the time this is built; do not add a new sync mechanism just for
  this.
- On the Pi, a systemd timer (or cron) runs at a configurable time (`settings.nudge_time`, default `21:30`), executing
  `hack remind-check`. Exit 1 (not logged today) triggers `hackstreak/nudge_telegram.py`, which POSTs to
  `https://api.telegram.org/bot<token>/sendMessage` using `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` from environment
  variables (never stored in the DB or committed to git; `.env` stays in `.gitignore`).
- Message includes the streak, "at risk" framing, and the actual next step text, e.g.
  `"Streak 9 (at risk). Chess done? Next: bandit-14 or recon-scan (20 min)."`
- A second, later check (e.g. 23:30) fires only if still unlogged, mirroring Duolingo's second reminder. No third nudge
  in one day: more than two starts to feel naggy rather than helpful, and the owner already named notification fatigue
  as a risk ("sometimes im not able to do this" referred to overload, not forgetting).

**Secondary: local desktop notification on Ubuntu (bonus, same trigger).**
- `hack install-nudge` installs a user-level systemd timer calling `hack remind-check`; on failure it shells out to
  `notify-send "hackstreak" "<message>"` (available by default on Ubuntu/GNOME). This only fires on days the owner is
  booted into Ubuntu at that hour, which is why it is secondary, not the thing relied on.
- No equivalent is built for Windows in Phase 1b. If needed later, Windows Toast via `win10toast` or a scheduled task
  is a Phase 2+ add-on, not required while the Pi/Telegram path exists.

**Config:** `hack config nudge-time 21:30`, `hack config nudge-channel telegram|desktop|both`, `hack config nudge-test`
(sends a test message immediately, so the owner can confirm it works before trusting it).

**Tests:** `remind-check` exit code matches whether today is logged; the nudge script does not fire a second message
on the same day after the owner logs between the two check times; a missing Telegram token degrades to "desktop only,
warn once" rather than crashing silently.

## 12. Added acceptance tests

- `lint` rejects: duplicate id, missing `done_when`, `needs` pointing nowhere, a cycle, size outside S/M/L, non-URL resource.
- Series `{from=13,to=15}` expands to `bandit-13..15`, chained in order, with `{n}`/`{next}` substituted.
- `next_nodes` skips locked nodes, skips done/skipped nodes, respects `max_minutes`, and returns `[]` when nothing fits.
- Updating a pack file (adding a node, reordering) keeps existing `node_state` rows intact.
- `done --complete` with a failing `file` verifier leaves the node `todo`; with `--force` it records `how = forced`.
- `command` verifier: times out after 10 s, never uses `shell=True`, and a pack with command verifiers cannot run before `trust`.
- `backfill` creates `node_state` rows but zero entries (streak unchanged).
- Verifier-sourced entries count for the streak on the day of `evidence_time`, not the day of `sync`.
- Levels: nodes in main level 2 are hidden until every node of main level 1 is done/skipped; `unlock` opens it early; `gate = false` opens it at once.
- Side-lane nodes are always eligible and never block or unlock anything on the main path.
- `hack` with one main and one side candidate prints both (Next + Quick win); `hack 10` prefers whichever fits.
- Active days per level counts distinct logical days, not entries (two entries on one day = 1).
- `lint` rejects a node whose `level` does not exist and a pack with no main level.
- No engine source file contains the strings "bandit", "juice", "overthewire" (grep test).

## 13. Prompt for the coding agent

> Read `hackstreak-spec-v2.md` (it supersedes v1 where they conflict; also read v1 for the streak rules and algorithm).
> Build **Phase 1 AND Phase 1b of v2**: Python 3.11, standard library only for Phase 1 (Phase 1b's Telegram call may use
> `urllib`, still no third-party dependency), one installable CLI `hack`. Write the tests from v1 section 11 and v2
> section 12 FIRST (pytest), then implement until they pass. Install `packs/home-hack-lab.toml` as the sample pack and run
> `hack pack lint` on it. Ask me before deviating from the spec. When finished show: file tree, `pytest` output, and a demo of
> `hack pack install`, `hack mission start`, `hack backfill`, `hack levels`, `hack`, `hack 20`, `hack done ... --complete`,
> `hack stats`, `hack config nudge-test` (or an explanation of what is stubbed if Telegram credentials are not available
> in this environment).
