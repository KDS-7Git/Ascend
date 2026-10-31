# v3: from personal tool to public, self-hostable, server-capable project

Supersedes v1/v2 wherever they conflict. Keeps: streak algorithm (v1 §8), pack format and levels/milestones (v2 §3, §8b),
verifier interface shape (v2 §7), day-wise/level logic. Changes: the project is no longer about one person or one subject.

## 0. Naming (your call — pick one or suggest your own, update throughout before publishing)

Working name used below: **Ascend**. Binary: `ascend`. Alternatives: **Pathforge**, **Wayrune**. Rationale: generic,
not tied to hacking, describes climbing levels toward mastery. Rename is a find-and-replace; nothing below depends on the word.

## 1. What changes, and why

| | Before (hackstreak, personal) | Now (Ascend, public) |
|---|---|---|
| Who it's for | You | Anyone learning anything, you included |
| Subject | Baked toward cyber | Domain-agnostic; cyber is one example pack among many |
| Where it runs | Your laptop only | Standalone on one machine, OR a server (e.g. your Pi) with many clients |
| Your data | In the same repo as the code | In your own private packs/profile, outside the installable package |
| Users | Implicitly one | Zero or more, with isolated data, if you run it as a server |
| Nudge source | A sync hack to the Pi | The server (if you run one) — no sync needed, it's just the server |

Compare to the projects you named: **Trilium** and **CherryTree** both work great as a single local app, and
**separately** offer (Trilium) or could offer (CherryTree via file sync) a server/sync mode for multiple devices.
Ascend follows the same shape: the core engine and CLI work with zero setup and zero dependencies on one machine;
running a server is an opt-in upgrade, not a requirement.

## 2. Two modes, one engine

```
engine/           <- pure logic: streak math, level/gate logic, pack parsing, verifier interface. No I/O assumptions.
storage/          <- SQLite access. Same schema whether local or server.
cli/              <- `ascend` command. Talks to storage/ DIRECTLY in standalone mode,
                      or to a remote server over HTTP in client mode (one `--server URL` / config line switches it).
server/           <- optional. A thin HTTP API in front of engine/ + storage/. Adds multi-user + nudging + a web view.
```

- **Standalone mode** (default, what v1/v2 described): `pip install ascend-tracker`, stdlib only, one local SQLite file.
  Nothing to deploy. This stays the easiest path and the one the README leads with.
- **Server mode** (new, opt-in): run `ascend-server` (adds `fastapi`+`uvicorn`, server-side only — the CLI client
  stays dependency-free) somewhere always-on — your Pi, a VPS, a spare machine. Point any number of CLI installs or
  a browser at it. One source of truth, so a dual-boot laptop, a phone (via Termux), and a desktop all see the same
  streak, because there is only one streak, held by the server.

The CLI's own commands (`ascend`, `ascend done ...`, `ascend levels`, ...) are **identical in both modes**. Only
`ascend config server <url>` + `ascend login` differ. This matters for onboarding: a new user never needs to think
about servers to get a working streak tracker tonight; they opt into the server later, with no relearning.

## 3. Multi-user & auth (server mode only)

```sql
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,         -- PBKDF2/scrypt, stdlib hashlib, never plaintext, never logged
  timezone TEXT NOT NULL DEFAULT 'UTC',-- IANA name, e.g. 'Asia/Calcutta'. REQUIRED once >1 user exists.
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS api_tokens (
  token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL, label TEXT
);
```

- Every existing table (`entries`, `node_state`, `missions`, `packs`, `parked`, `settings`) gains `user_id`, and every
  query is scoped to the caller's user. One SQLite file, many isolated users — same approach Praxis already uses.
- **Fixed gap:** v1 §6's `logical_date()` (the 4 AM rollover) assumed one person's local time, which breaks the moment a
  server has users in different timezones — "local" becomes meaningless on a server process. Every call to
  `logical_date(now)` in server mode becomes `logical_date(now, user.timezone)`, reading `users.timezone` above. In
  standalone mode there is exactly one implicit user, so this has no effect on you today; it only matters once someone
  else's account exists. `AUTH_MODE=single` can default this to the system's local timezone without asking.
- `ascend login <server-url>` prompts for username/password, stores a long-lived token in `~/.config/ascend/token`
  (0600 permissions), not the password.
- `AUTH_MODE=single` (default for a private deployment, e.g. just you on your own Pi) skips login entirely — one
  implicit user, same as v1/v2. `AUTH_MODE=multi` turns on real accounts, for anyone who wants to run this for a
  family, a study group, or the public internet. This single switch is what makes the same codebase fit "just me"
  and "a public instance" without two code paths.
- Server binds to the LAN by default (`--host 0.0.0.0` is opt-in, documented with a warning: put it behind a
  reverse proxy with TLS, e.g. Caddy, if exposing it past your LAN).

## 4. Packs: personal data vs. the public library

This is the piece that makes the repo genuinely reusable rather than "my project with your name filed off":

```
ascend/                     <- the installable package (engine, storage, cli, server). No personal data. This is what you publish.
packs/community/            <- curated example packs anyone can use, reviewed, in the repo, e.g.:
  home-hack-lab.toml           networking-101.toml
  dsa-fundamentals.toml        webdev-fullstack.toml
  gamedev-godot.toml           os-internals.toml
~/.config/ascend/packs/     <- a USER's own private packs. Never committed, never shipped. gitignored by default
                                if the user clones the repo to hack on it; irrelevant for a pip-installed user.
```

- `ascend pack install <id>` can install from `packs/community/` (bundled or fetched from the repo's raw URL) or from
  a local file path. Either way it copies into the user's own data dir; editing your copy never touches the shared one.
- Your current cyber pack and personal `[vars]` (your Pi's IP, your folder paths) move to `packs/community/home-hack-lab.toml`
  as a *generic example* (placeholder IP, `{hack_dir}` already parameterised — it already is, good) — genuinely useful
  to a stranger, not wired to you specifically. Anything truly yours (your actual IP, your actual Telegram token) lives
  only in your local `[vars]` override or `.env`, never in a file you'd commit.
- `CONTRIBUTING.md` explains how someone submits a new community pack via PR: run `ascend pack lint` and
  `ascend pack check-links`, fill in the "done_when produces a real artifact" requirement, no AI-hallucinated URLs
  (same discipline you asked for, now a contribution rule, not just a personal one).

## 5. Verifiers as a real plugin system (this is your "customizability," the Trilium/CherryTree equivalent of plugins/scripts)

- Built-in verifiers (`manual`, `file`, `command`, later `http`/`git`) ship in `ascend/verifiers/`.
- **Third-party verifiers**: any Python file exposing `verify(spec, vars) -> VerifyResult` (v2 §7's interface) dropped
  into `~/.config/ascend/verifiers/` is loadable via `verify = { type = "plugin:my_checker", ... }`. This is how someone
  adds a Codeforces checker, a Duolingo-API checker, a smart-home sensor checker — whatever their own "proficiency" needs
  — without forking the core engine. Exactly the extension point Trilium's scripting API and CherryTree's plugins play,
  sized for this project.
- **Trust is explicit and unchanged in spirit from v2 §7**: a plugin is code, so `ascend pack install` lists any
  `plugin:` verifiers a pack references, and nothing executes until `ascend plugin trust <name>` — same reasoning as
  the `command` verifier trust step, extended to Python plugins, since they run with the same permissions you have.
- Document the interface in `docs/writing-a-verifier.md` with the two built-in examples (`file`, `command`) as the
  template, so a contributor can write one without reading the whole engine.

## 6. HTTP API (server mode)

```
GET  /api/health                              -> 200 OK, no auth (used by docker/Dockerfile's HEALTHCHECK)
POST /api/login                               -> token
GET  /api/me                                  -> streak, active mission, today status  (mirrors `ascend`)
GET  /api/levels?pack=<id>
POST /api/entries        {learned, next_step, node_id?, proof?}   -> mirrors `ascend done`
POST /api/nodes/{id}/mark {status}
POST /api/packs           (multipart TOML upload) -> lint result
GET  /api/packs, GET /api/packs/{id}
GET  /api/stats, GET /api/heatmap
```

- Same validation rules as the CLI (20-char minimum, secrets guard, one active mission) — the CLI's local mode and
  the server must enforce identical rules, so behaviour never depends on which mode a user picked. In practice this
  means `engine/` functions take plain data in and out and neither `cli/` nor `server/` duplicates logic; they are
  both thin wrappers around the same calls.
- A minimal read-only `GET /api/public/<username>/streak` (opt-in per user, off by default) is the hook for a future
  "show my streak on my GitHub profile" badge — a nice public-repo touch, not required for v1.

## 7. Nudging, simplified by server mode (supersedes v2 §11b's sync workaround)

- **If you run a server:** the server itself is the always-on machine (your Pi). It owns the single `nudge_time`
  per user and sends the Telegram (or, later, ntfy.sh / Pushover / email) message directly — there is no "sync the
  DB to the Pi" step anymore, because the Pi already holds the only copy. This directly fixes the dual-boot problem:
  neither OS needs to be awake at nudge time, since the server isn't on the laptop at all.
- **If you don't run a server (standalone mode):** the local desktop-notification timer from v2 §11b still applies,
  as the lightweight fallback for a single machine.
- Nudge channels are pluggable with the same shape as verifiers (`nudge/channels/telegram.py`, `ntfy.py`, `desktop.py`),
  so someone self-hosting for a study group could add Discord or Matrix without touching the core.

## 7b. Schema migrations across phases (fixed gap)

The schema genuinely changes shape across v1 -> v2 -> v3 (new columns, new tables). Prose saying "add this column" is
not a safe upgrade path for someone's real database. Adopt the same pattern Praxis already uses successfully:

```
storage/migrations/
  0001_init.sql          -- v1: entries, missions, parked, settings
  0002_packs.sql          -- v2: packs, node_state, entries.node_id/source/complete
  0003_multiuser.sql      -- v3: users, api_tokens, user_id columns, users.timezone
```

```sql
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
```

On every startup (`ascend`, `ascend-server`): read the current version (0 if the table is empty), apply every
migration file numbered above it, in order, inside one transaction per file, and record the new version. Idempotent,
so running it twice is harmless, and it is what lets you upgrade from "just the Phase 1 CLI I'm using today" to the
server later without losing or corrupting your existing streak.

## 7c. SQLite concurrency (fixed gap)

Once a server has more than one writer at a time — your CLI and the web PWA both logging around the same moment —
SQLite's default mode can block or, in rarer cases, surprise you. Two concrete, cheap mitigations, not a rewrite:
- `PRAGMA journal_mode=WAL;` on every connection at startup — readers no longer block writers.
- The server process is the only thing that opens the DB in server mode (the CLI talks to it over HTTP, never opens
  the file directly once a server is configured) — a single-writer-per-process design, which is sufficient at the
  scale this project is designed for (one person, a study group, not internet-scale traffic). If that ever stops
  being true, that is the point to move off SQLite, not before.

## 8. Deployment

**On your Pi (recommended for you — always-on, matches your hardware):**
```yaml
# docker-compose.yml
services:
  ascend:
    build: .
    ports: ["8420:8420"]
    volumes: ["./data:/data"]       # SQLite file lives here, back this up
    environment:
      - AUTH_MODE=single            # set to "multi" if others will use this instance
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}   # from a local .env, gitignored
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
```
`docker compose up -d` on the Pi (arm64 base image, same pattern Praxis already documents for itself). CLI clients
on any machine set `ascend config server http://<pi-ip>:8420`.

**For anyone else cloning the repo:** same Dockerfile/compose runs on an x86 VPS, a Raspberry Pi, or just `localhost`
for testing — nothing Pi-specific is hardcoded. Document all three in the README's "Deploy" section. A plain
`pip install` with no server is still the zero-friction path for someone who just wants the CLI on one machine.

## 9. Open-source polish checklist

Before making the repo public:
- `LICENSE` — MIT is the simplest permissive default and matches most CLI tools; CherryTree is GPLv3 and Trilium is
  AGPLv3, which are fine alternatives if you specifically want modifications/hosted forks to stay open. Pick one
  deliberately rather than leaving it unset (an unlicensed public repo legally defaults to "no rights granted").
- `README.md` — what it is (one paragraph), a GIF/screenshot of `ascend` and `ascend levels`, quickstart (`pip install`,
  `ascend pack install home-hack-lab`, `ascend`), then "Server mode" and "Writing your own pack" as later sections.
  Lead with standalone mode; server mode is "when you're ready," not a prerequisite.
- `CONTRIBUTING.md` — how to submit a community pack (section 4) and a verifier (section 5), code style, how to run tests.
- `docs/` — pack format reference (v2 §3 content, cleaned up), verifier-writing guide, API reference (section 6), deployment guide (section 8).
- `examples/` — 2-3 finished example packs across different domains (cyber, DSA, a language, a creative skill) so a
  visitor immediately sees this isn't a cyber-only or CS-only tool.
- Tests + CI (GitHub Actions running `pytest` + `ascend pack lint` on every community pack) — keeps community
  contributions honest without you manually reviewing every TOML line by line.
- A clear "Status" note if you publish before Phase 2 (server) is built, so early users know standalone mode is solid
  and server mode is in progress — honest scoping beats an overpromised README.

## 10. Build order (unchanged principle: don't let building this become its own overwhelm spiral)

1. **Phase 1 (v2):** standalone engine + CLI + packs + levels/milestones. Ship this alone first — it is already a complete,
   useful, installable tool with zero dependencies.
2. **Phase 1b (v2):** local nudging (desktop notification).
3. **Phase 2 (this file, REVISED): server + a real web client together, not server-alone.** A headless API with no UI
   is not useful day to day, and checking progress from a phone matters as much as the server itself. Build:
   - `server/` (FastAPI) behind the identical CLI commands, auth, the HTTP API (§6), Docker Compose (§8).
   - `web/`: a small PWA (one static page + a manifest + a service worker) hitting the same API: shows the next step,
     the quick win, levels/streak/heatmap, and a form to log `ascend done` equivalents — a FULL client, not read-only,
     so the phone alone is enough on a day you never open a terminal. Add to Android home screen via the browser's
     "Install app" prompt (standard PWA behaviour, no app-store listing needed).
   - Notification channel (§12 below), default **ntfy**, since it is the least infrastructure for a real Android push.
4. **Phase 3:** plugin verifiers + trust step, community pack registry + lint CI, docs/CONTRIBUTING polish, then publish.
5. **Phase 4:** Telegram channel + inline-button quick actions, true Web Push from the PWA (no separate app at all),
   public-facing extras (streak badge, etc.).

## 12. Interacting beyond the CLI, and real Android notifications

**Two clients, one source of truth, pick per moment, not permanently.** CLI is fastest when you're already at a
terminal mid-step (SSH'd into the Pi, running nmap, then straight to `ascend done`). The web PWA is the one you open
from your phone to check the streak, see which level you're on, or log a step on a day with no terminal in sight.
Neither is "the real one"; both call the identical API from §6, so progress never forks between them.

**Why ntfy is the default notification channel, not Telegram and not Web Push, to start:**

| Option | Android push? | Setup effort | Notes |
|---|---|---|---|
| CLI alone | No | — | Cannot push anything; only reacts when run |
| **ntfy** | Yes, real push | Lowest: install the app, subscribe to one topic, server does a plain HTTP POST | Free hosted `ntfy.sh` or self-host later; no account/bot needed |
| Telegram | Yes, real push | Low-medium: create a bot, get a chat id | Bonus: inline buttons can log a step directly from the notification |
| Web Push (PWA) | Yes, on Android Chrome | Highest: needs HTTPS + VAPID keys + a reachable server | No separate app installed at all — the most "one unified app" feel, worth it once the project is mature |

Ship ntfy first (§7's pluggable channel design already anticipated this: `nudge/channels/ntfy.py`), add Telegram as an
alternative users can switch to (`ascend config nudge-channel ntfy|telegram|desktop`), and leave Web Push as a Phase 4
upgrade once the server has a real domain and TLS anyway.

Do not start Phase 2 until Phase 1 genuinely works for you day to day. A public repo with an unused server is worse
than a private tool with a real streak — the whole point of this project is proof that something got finished.

## 11. Prompt for the coding agent (replaces v2 §13 going forward)

> Read `hackstreak-spec-v2.md` for the engine/pack/level/milestone/streak rules, and `spec-v3-public-release.md` for
> scope and architecture (v3 supersedes v2 on anything about naming, personal data, or deployment).
> Build **Phase 1 + Phase 1b only, in standalone mode**, as a clean `engine/` + `storage/` + `cli/` package (already
> separated so Phase 2's server can wrap the same engine later without a rewrite). Do not build `server/` yet. Rename
> the CLI binary to `ascend` (or ask me if I've chosen a different name by then). Keep the sample community pack at
> `packs/community/home-hack-lab.toml` with placeholder `[vars]`, not my real IP or paths. Write tests first. No
> dependencies beyond the standard library. Ask me before starting anything in section 10's Phase 2 or later.

## 13. What "verified" means here, honestly

This spec is a reasoned design, produced by thinking through the problem and reviewing it for gaps (§7b's migration
runner, §7c's SQLite concurrency note, and §3's per-user timezone fix all came from that review pass — not from
building something and discovering the bug the hard way). It is **not verified** in the sense that matters most:
no line of it has run yet, and a design review on paper cannot find everything a real implementation will surface.
That is normal for software, not a flaw unique to this plan — treat every "ask me before deviating" instruction to
the coding agent as the mechanism for surfacing the next real gap, not as a formality.

Two gaps are left deliberately open rather than papered over:
- **Exact API request/response contracts** (§6) — only a route list exists, not pinned JSON schemas or error codes.
- **Plugin sandboxing detail** (§5) — a trust step is specified, but the actual sandboxing mechanics are not designed.

Both are real LLD work, and writing it now, before Phase 1 (which needs neither) even exists, would be specifying
against a moving target. Do that work when Phase 2/3 actually starts, informed by how Phase 1 behaved in practice.

**The actual risk reduction isn't a longer spec, it's this order:** ship the small Phase 1 CLI, write its tests
first and make them pass for real (not just plan to), use it daily until it earns trust, THEN build the server on a
foundation that has already proven itself. A design that looks complete on paper and a system that has survived a
week of real use are not the same kind of confidence, and only the second one actually answers "will I fail after
building this."

## 14. Feature audit: what it has, what it should have, what it deliberately doesn't

**"Customizable" was always meant on one specific axis: the roadmap, not the UI.** That axis is genuinely strong:

| Already specified | Where |
|---|---|
| Roadmap is editable data (TOML), not code | v2 §3 |
| Levels, gated main path + always-open side lane | v2 §3, §5 |
| Milestone-gated proficiency, not just checkbox completion | v2 §8b |
| Pluggable verifiers (built-in + third-party Python plugins) | v2 §7, v3 §5 |
| Two pack kinds (project vs. proficiency), both AI-draftable or hand-written | v2 §8b, §9 |
| Numbered-series generator (`{from, to}`) for any wargame/course with levels | v2 §3 |
| User `[vars]` substitution, so one pack works across different setups | v2 §3 |
| Multi-user, each isolated, one codebase for solo and shared use | v3 §3 |
| Pluggable nudge channels (ntfy/Telegram/desktop, Discord/Matrix addable) | v3 §7 |
| Same API for CLI and web, so neither is a second-class client | v3 §6, §12 |

Measured honestly against Trilium/CherryTree, this spec is strong on **content/roadmap** extensibility and weak on
**interface** extensibility and a few **data-hygiene** basics those tools treat as table stakes. Below is the honest
gap list, split into what's worth fixing now (cheap, in the spec, no new phase) versus what's correctly deferred.

### 14a. Adding now (cheap to spec, real gaps, no phase change)

- **Entries are append-only with no fix-up path.** If the owner logs the wrong node or mistypes `learned`, there was no
  way to correct it. Added: `ascend edit <entry-id> [--learned ...] [--next-step ...]` and `ascend undo` (removes the
  most recent entry made in the last 10 minutes only, to stop it being an easy way to quietly rewrite history). Both
  write an audit row rather than silently overwriting, so the streak computation stays honest and inspectable.
- **`minutes` was captured but never surfaced.** v1's schema has a `minutes` column on `entries`; nothing in the CLI
  ever lets the owner set it or see it back. Added: `ascend done ... --minutes N` and `minutes` totals per level/week
  in `ascend stats`, so "proficiency" has a real time-investment number behind it, not just a day count.
- **No search over months of accumulated notes.** Every `learned` line is a small, real note; after a few months
  that's a genuine knowledge log, and there was no way to find anything in it. Added: `ascend search "<text>"`
  (substring over `learned`/`next_step`/`proof`, SQLite `LIKE` is sufficient at this scale — no search engine needed)
  and the same as `GET /api/search?q=` on the server.
- **No visual skill map, despite the whole design being modeled on one.** `hack levels` was specified as a text
  progress bar; the actual Duolingo signature feature — a path of nodes you can see, not just a number — was never
  designed. Added to the web PWA (§10's Phase 2 scope, not a new phase): a simple level-path view, one row per level,
  nodes as circles (locked/open/done/milestone), reusing data already returned by `GET /api/levels`. No separate
  visual-design pass is scheduled for this now — ship the functional version in Phase 2; polishing it is Phase 4.
- **No theming, despite customization being the explicit goal.** Trilium and CherryTree both ship themes; this spec's
  web PWA had none specified. Added: CSS custom properties for color tokens, a light/dark toggle defaulting to
  `prefers-color-scheme`, stored in `localStorage` (view preference only, never synced — losing it on a new device
  is an acceptable trade-off for the amount of code it saves). This is near-zero marginal cost once the PWA exists,
  so it's folded into Phase 2, not deferred.
- **One global nudge time couldn't fit a varied schedule.** The owner's week already has lab-night vs. free-half-day
  rhythm (see the original hack-lab planning); one fixed `nudge_time` doesn't reflect that. Added: an optional
  `nudge_time` override per mission (`ascend mission start <pack> --nudge-time 21:30`), falling back to the global
  setting when unset.

### 14b. Real gaps, deliberately NOT added (with the actual reason, not just "later")

- **Full theming/branding system, i18n, accessibility audit.** These matter a lot for a public tool with many users,
  and genuinely little for the first real user (you, in English, on your own devices). Building them now would be
  designing for an audience that doesn't exist yet. Revisit once outside contributors actually show up — their
  needs should shape this, not a guess made in advance.
- **Public-signup hardening (rate limiting, invite-only mode, email verification).** `AUTH_MODE=multi` as specified
  is adequate for a study group you personally invite; it is NOT specified to be safe as an open-signup public
  service. Don't flip a server to open multi-user on the public internet without a real security pass first — this
  is a correctness gap I'm flagging, not one I'm fixing by writing more spec prose at this stage, because the right
  fix depends on who's actually using it.
- **Offline-first PWA (background sync queue, conflict resolution for offline edits).** Real engineering, real value
  eventually, but the server is reachable from your phone over the same network as the Pi almost all the time; building
  a sync-conflict system for an offline scenario that rarely occurs yet would be solving a problem you don't have.
- **Social/leaderboard features (compare streaks with friends, encouragement, comments).** Explicitly against the
  original design goal: the whole point was escaping overwhelm and open-ended systems, not adding a second source of
  social pressure. If you want this later for a study group, it's a small addition on top of the public-streak hook
  already in §6 — but it's opt-in territory, not a default.
- **Account export/deletion (GDPR-style "give me all my data" / "delete everything").** Only matters once real
  strangers' data is on a server you run. Required before genuinely public multi-user hosting, irrelevant before
  that. Flagged here so it isn't forgotten, not built now.

**Where this leaves you:** the roadmap/content side — the part you specifically asked not to be hardcoded — is the
best-covered part of the design. The interface side had real, fixable gaps (no edit/undo, no search, no visual map,
no theming), now folded into the existing Phase 2 scope at no cost to the build order. The remaining gaps are real
but correctly out of scope until there's an actual audience whose needs would shape them better than a guess would.
