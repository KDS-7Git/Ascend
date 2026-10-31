# What to paste into Antigravity to start

## First, the thing to understand before you paste anything

`hackstreak-spec.md`, `hackstreak-spec-v2.md`, and `spec-v3-public-release.md` are not three products. They're one
design, revised three times — each file says explicitly what it keeps and what it overrides from the one before it.
Do not have the agent build v1 completely, then rebuild as v2, then rebuild as v3. That throws away work for no
reason, since the end architecture was already decided before the first line of code gets written.

What's actually sequenced is the **build phases** described inside v2 §11 and v3 §10 (Phase 1 → 1b → 2 → 3 → 4), not
the spec file numbers. Give the agent the full picture now, so it never makes a Phase 1 choice that conflicts with
where this is headed (a bad schema shortcut that breaks the migration story later, say) — but scope the actual
work it does tonight to Phase 1 + 1b only, and go no further until that's living in your daily routine for real.

## Step 1 — tonight: Phase 1 + 1b only

Open Antigravity in a fresh project folder with these five files present (or pasted into context):
`hackstreak-spec.md`, `hackstreak-spec-v2.md`, `spec-v3-public-release.md`, `ui-ux-spec.md`,
`packs/home-hack-lab.toml`. Then paste this:

---

> Read `hackstreak-spec.md`, `hackstreak-spec-v2.md`, and `spec-v3-public-release.md` in that order. Together they
> describe one evolving design, not three separate products — each later file supersedes the one before it wherever
> they conflict, exactly as each file states at its top. Build according to the PHASES defined inside
> `spec-v3-public-release.md` section 10, not according to which spec file a detail came from.
>
> Right now, build **only Phase 1 and Phase 1b**: the standalone engine, CLI, pack system, levels/milestones, and
> local desktop nudging — nothing from Phase 2 onward (no server, no web client; `ui-ux-spec.md` is for later and you
> can ignore it for this step). Structure the code as a clean `engine/` + `storage/` + `cli/` package, separated so a
> server can wrap the same engine later without a rewrite, per `spec-v3-public-release.md` §2. Python 3.11+,
> standard library only (Phase 1b's notification call may use `urllib`, still no third-party dependency). Name the
> CLI binary `ascend`.
>
> Write the tests from `hackstreak-spec.md` section 11 and `hackstreak-spec-v2.md` section 12 FIRST, then implement
> until they pass. Install `packs/home-hack-lab.toml` as the sample pack at `packs/community/home-hack-lab.toml`
> with its placeholder `[vars]` left as placeholders, not my real Pi IP or folder paths.
>
> When finished, show me: the file tree, full `pytest` output, and a demo of `ascend pack install`,
> `ascend mission start`, `ascend backfill`, `ascend levels`, `ascend`, `ascend 20`, `ascend done ... --complete`,
> `ascend stats`, and the nudge config/test command (or a clear note on what's stubbed if desktop notifications
> aren't testable in this environment). Ask me before building anything beyond Phase 1b.

---

## Implementation clarifications from final review

These fix real inconsistencies found by re-reading all three specs together. They override anything in
`hackstreak-spec.md` or `hackstreak-spec-v2.md` that conflicts, exactly as the files' own precedence rules say —
these are just spelled out explicitly because they were easy to miss otherwise.

1. **Naming, everywhere.** v1 and v2 say `hack`, `~/.hackstreak/`, `HACKSTREAK_HOME`, and `hackstreak/verifiers/`
   throughout — including inside their own embedded "prompt for the agent" sections (v1 §12, v2 §13). All of that is
   superseded. The binary is `ascend`. Data lives at `~/.config/ascend/` (an `ASCEND_HOME` environment variable
   overrides this, matching what the Dockerfile already uses for server mode). The database file is
   `$ASCEND_HOME/ascend.db` — in standalone mode that's `~/.config/ascend/ascend.db`; in the Docker image,
   `ASCEND_HOME=/data`, so it's `/data/ascend.db`. The verifier plugin folder is `~/.config/ascend/verifiers/`.
2. **Phase 1b is desktop notification ONLY, tonight.** v2 §11b describes a full Telegram-from-the-Pi system (a
   `sync-to-pi` command, a `nudge_telegram.py` file, systemd timers on the Pi) and calls it "Phase 1b." That is
   superseded by `spec-v3-public-release.md` §7, which correctly narrows Phase 1b to the local desktop notification
   only and moves Telegram to Phase 2, sent by the server once one exists. Build only the desktop notification path
   tonight — do not implement `sync-to-pi`, Telegram, or anything cross-machine yet, even though v2 §11b describes it
   in more detail than the thing that actually supersedes it.
3. **Verifier paths must resolve `~`.** The starter pack's `[vars]` includes `hack_dir = "~/hack"`, substituted
   directly into `file` and `command` verifier paths (e.g. `{hack_dir}/report.md`). A plain string substitution does
   NOT expand `~` to the home directory — `Path("~/hack/report.md").exists()` checks a literal folder named `~`, not
   the home directory. The `file` and `command` verifiers must call `expanduser()` (or equivalent) on any path before
   using it, or the sample pack's own verifiers will fail on night one. Add this as an explicit test case.
4. **`lint` must check `pack.kind`.** `hackstreak-spec-v2.md` §8b says every pack needs `kind = "project"` or
   `kind = "proficiency"`, but §3's lint checklist never actually lists this as something `lint` validates. Add it:
   `lint` rejects a pack missing `kind` or with any other value.
5. **`GET /api/health`** (used by the Docker healthcheck in `docker/Dockerfile`) should be added to the route list in
   `spec-v3-public-release.md` §6 when Phase 2 is built — a trivial 200-OK endpoint, not used tonight, just noted so
   it isn't forgotten when the server is written.

## Step 2 — actually verify it, don't just accept the demo

Before trusting any of this:
1. Skim the code it produces. You don't need to review every line, but check the streak logic against the test
   table in `hackstreak-spec.md` §11 yourself — run `pytest -v` and read what passed.
2. Run `ascend pack lint` and `ascend pack check-links` on `home-hack-lab.toml` yourself, read every `done_when`,
   then `ascend review` it before trusting it as your real roadmap.
3. **Use it for real, daily, for at least a week or two** — chess lesson, then `ascend`, then one step, then
   `ascend done`. This is the actual test. A demo that runs once in a chat is not the same as a tool that survives
   a deadline week.

## Step 3 — only once Phase 1 is genuinely part of your routine

Come back and hand the agent `spec-v3-public-release.md` (architecture, already given) plus `ui-ux-spec.md` (the web
client design) together, and tell it to build Phase 2: the server, the HTTP API, and the web PWA, per
`spec-v3-public-release.md` §10's Phase 2 scope. Not before. A server and a phone app for a habit you haven't
actually kept yet is building the sequel before the first movie was any good.

## Step 4 and beyond

Phase 3 (plugin verifiers, community pack CI, docs, publish) and Phase 4 (Telegram, real Web Push, public extras)
follow the same rule: don't start the next one until the current one is proven, not just built.
