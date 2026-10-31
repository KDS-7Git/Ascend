# Start here — what every file in this folder is for

This folder is meant to be opened as the project folder in Antigravity (or any coding agent). Below is exactly
what each file is, in the order that matters, and what to actually do.

## The one thing to understand first

`hackstreak-spec.md`, `hackstreak-spec-v2.md`, and `spec-v3-public-release.md` are **one design, revised three
times** — not three products to build one after another. Each later file states what it keeps and what it
overrides from the one before it. You will hand the agent all three at once; it reads them in order and treats the
later ones as corrections to the earlier ones.

What *is* sequenced is build **phases** (Phase 1 → 1b → 2 → 3 → 4), described inside the spec files themselves —
not the spec file numbers. `kickoff-prompt.md` is written around this.

**This folder has been through an actual review pass** (reading every file fresh and cross-checking them against
each other, not just re-reading what I remembered writing). It found and fixed five real issues: a naming drift
between `hack` (v1/v2) and `ascend` (v3) that was stated once but repeated dozens of times the other way; `hack
done`/`hack mission ...` wording left over from the old name in `new-unit-request-template.md`; a scope leak where
v2's Phase 1b description includes a full Telegram system that v3 actually narrows to desktop-only; a missing
`expanduser()` requirement that would have made the starter pack's own verifiers fail on night one, since its
`hack_dir = "~/hack"` variable is substituted as a literal string; and a lint rule (`pack.kind`) that was described
in prose but never added to the actual lint checklist. All five are patched — see "Implementation clarifications
from final review" near the top of `kickoff-prompt.md` for the authoritative, consolidated fix list.

**One open item, left open on purpose:** the project's name. `spec-v3-public-release.md` proposed "Ascend" as a
placeholder and explicitly left the final choice to you. Nothing has been built yet, so renaming later is a
find-and-replace, not a migration — "Ascend" is used throughout as the working name unless you say otherwise.

## File-by-file

| File | What it is | When it matters |
|---|---|---|
| **`kickoff-prompt.md`** | The exact text to paste into Antigravity to start. | Open this first. Copy its "Step 1" prompt block and paste it as your first message to the agent, with this whole folder open as the project. |
| `hackstreak-spec.md` | Original design: why this exists, the streak math, the core CLI rules. Mostly superseded by the next file, but still holds the streak algorithm and its test table, which stay valid. | Read by the agent, not by you, unless you want the reasoning behind the streak rules. |
| `hackstreak-spec-v2.md` | Adds: packs (the editable TOML roadmap format), levels, milestones, verifiers (auto-checks). This is the core engine design. Supersedes v1 wherever they disagree. | Read by the agent. |
| `spec-v3-public-release.md` | Adds: making it public/self-hostable, multi-user, the server + Docker architecture, and an honest audit of what's missing and what's deliberately deferred. Supersedes v2 on naming, personal data, and deployment. | Read by the agent now (for context), but its *server* content (Phase 2+) isn't built until Step 3 below. |
| `ui-ux-spec.md` | The precise design brief for the web client: screen layout, the level-path visual, colors, responsive behavior. | Not used in Step 1 at all. Only matters once you reach Phase 2 (the web client). Keep it in the folder anyway so the agent has full context. |
| `new-unit-request-template.md` | A template *you* fill in and paste into a **new chat with me (Claude)** whenever you want a new learning pack (networking, DSA, a language, etc.) drafted. Not for the coding agent. | Use later, whenever you want a new subject pack. Not part of tonight's build. |
| `packs/home-hack-lab.toml` | The one starter roadmap: build a home hack lab on your Pi, attack it, harden it. A draft — review it yourself before trusting it (see its own header comments). | The agent installs this as the sample pack during Step 1. |
| `docker/Dockerfile`, `docker/docker-compose.yml`, `docker/.dockerignore` | How to run the server on your Pi (or anywhere) once Phase 2 exists. | Not used until Step 3. Don't let the agent build `server/` before then. |

## What to actually do, in order

**Step 1 — tonight.** Open `kickoff-prompt.md`, copy the prompt under "Step 1," paste it to the agent with this
folder as the project. This builds *only* the standalone CLI (Phase 1) and local nudging (Phase 1b) — no server, no
web app yet.

**Step 2 — before trusting it.** Run the tests yourself (`pytest -v`), read `packs/home-hack-lab.toml`'s
`done_when` lines, run `ascend pack lint` and `ascend pack check-links` on it, and actually use the CLI daily for
at least a week or two. This step is not optional — a demo that runs once in a chat is not the same as a habit tool
that survives a deadline week.

**Step 3 — only once Step 2 has genuinely stuck.** Go back to the agent with `spec-v3-public-release.md` and
`ui-ux-spec.md` and tell it to build Phase 2: the server (using the `docker/` files) and the web client. Full
instructions for this step are at the end of `kickoff-prompt.md`.

**Later, whenever you want a new subject.** Fill in `new-unit-request-template.md` and paste it into a *new* chat
with me — not the coding agent — to get a new pack drafted, then lint/review/install it the same way.

Don't skip ahead. The whole point of staging this is that a server and a phone app for a habit you haven't actually
kept yet is building the sequel before the first movie was any good.
