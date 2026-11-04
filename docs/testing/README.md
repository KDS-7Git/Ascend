# Verification record

The current Playground, engineering-track, reward and workspace implementation
passed 658 regression tests, including phone/desktop challenge timing, grouped
history, saved-work recovery, reward feedback and accessibility checks. See the
[workspace completion record](workspace-completion.md) for scope and reproduction.
All seven reviewed server-runner recipes passed real lifecycle validation.
Reproduce environment checks with [the hosted acceptance script](../../scripts/verify_hosted_labs.py)
and [the runner setup guide](../design/server-lab-runner.md). Source/image reviews
and measured resource requirements are retained below; development captures, raw
logs and machine-specific deployment inventories stay local.

All implementation milestones were tested before moving to the next phase.
Initial failing test runs are retained as `phase-*-red.txt`; these are historical
test-first evidence, not unresolved failures.

| Milestone | Cumulative result | Full output |
|---|---:|---|
| Phase 1 | 53 passed | [phase-1.txt](phase-1.txt) |
| Phase 1b | 59 passed | [phase-1b.txt](phase-1b.txt) |
| Phase 2 | 75 passed | [phase-2.txt](phase-2.txt) |
| Phase 3 | 82 passed | [phase-3.txt](phase-3.txt) |
| Phase 4 + final regression checks | 101 passed | [phase-4.txt](phase-4.txt) |

The suite ran here on Python 3.12.3. CI is configured for Python 3.11, 3.12, and
3.13; those additional versions were not executed locally. Early server-phase
runs include one test-client deprecation warning; the final environment uses
the supported test transport and finishes without that warning.

- [CLI demo](cli-demo.md): every originally requested command, with synthetic
  records in a disposable profile and a stub desktop notifier.
- [File tree](file-tree.txt): project files, excluding ignored caches and data.
- [Standalone wheel](standalone-wheel.txt): a fresh environment containing only
  Ascend and pip; no server, notification, or testing dependencies.
- [Distribution build](distribution-build.txt): built wheel and source archive.
- [Complete container smoke test](phase-4-container.txt): health, PWA, bundled
  pack installation, and non-root runtime; [build output](phase-4-docker.txt).
- [Resource checks](community-links.txt): all accessible resources returned 200;
  Raspberry Pi documentation returned 403 from this environment. The original
  URL is retained and requires a human browser check.
- [Browser screenshots](../screenshots/): actual Chromium rendering. Automated
  flows cover 390px, 768px, and 1440px layouts, completion, search, theme persistence,
  and parked ideas.

Desktop, ntfy, Telegram and Web Push transport boundaries are mocked in tests.
Web Push encryption and VAPID header generation run for real before the mocked
HTTP call. Live Android delivery, actual Telegram bot setup, and arm64 execution
need the intended deployment and devices. No external publication or production
deployment was performed.
