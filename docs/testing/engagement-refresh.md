# Engagement refresh verification — 2026-11-01

- Full suite: **109 passed in 16.79s**, including the built-wheel asset/server smoke
  test and browser flows at phone, tablet, and desktop sizes.
- Repository CI style checks: 53 files formatted; unused-import/variable checks pass.
- JavaScript syntax checks and `git diff --check` pass.
- All five version-2 cyber packs pass `ascend pack lint`. A traversal through the
  actual level/prerequisite engine reaches every node. All original expanded IDs
  are retained, and each track offers 10–20 minute optional discoveries.
- Browser regressions cover task guidance, hidden hints, partial sessions,
  successful completion and unlock feedback, failed evidence, locked tasks, and
  excluding skipped milestones from earned badges and completion percentages.
- Live local server checks passed at 390px/light, 1440px/light, and 390px/dark:
  challenge steps, hint disclosure, time filters, all four tabs, no horizontal
  overflow, and no uncaught JavaScript errors. No learner progress was written by
  these browser checks.
- The five installed packs were backed up and updated. Existing entries, node
  states, and the active mission were compared before/after and preserved. The
  running server was restarted with its original command, working directory, and
  environment, and returns the new challenge metadata.
- Resource check: 119 distinct final URLs; 103 reachable, 16 access restricted or
  unreachable. Fifteen obsolete/restricted URLs were replaced with checked
  references. See [the detailed results](cyber-track-links.json); a timeout or
  access restriction is not reported as a verified working page.

The full suite exposed an existing Git verifier bug: a default `1970-01-01`
cutoff can parse before the epoch in local time, causing Git to return no commits.
The verifier now omits the cutoff unless one is requested. The real-repository
test verifies both normal matching and an explicit future cutoff.

Screenshots in `docs/screenshots/` use a disposable database with clearly synthetic
progress. They do not contain or change the learner's real records. Tests establish
software behavior; sustained motivation still requires actual use.
