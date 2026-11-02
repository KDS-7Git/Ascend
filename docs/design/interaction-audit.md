# Interaction and page-context audit

Updated 2026-11-03. This is a review of implemented behavior and public reference
pages, not a designer rating or an authenticated competitor-account study.
It follows the reported dead-end walkthrough, plain success messages, time-filter
mismatch, and unused page margins. The earlier engagement audit is historical.

## Eight reference products

All eight URLs below returned 200 and were rendered in Chromium. Screenshots and
page text were inspected; product claims below are limited to these public pages.
No competitor imagery, course content or component code is shipped in Ascend.

| Reference | Useful pattern | Application here |
| --- | --- | --- |
| [Duolingo](https://blog.duolingo.com/new-duolingo-home-screen-design/) | Guided sequence with a clear current step and completed steps; the article explains its 2022 path redesign. | Walkthrough → takeaway → fresh challenge. The next action is visible when a step finishes. |
| [TryHackMe](https://help.tryhackme.com/en/articles/6611837-rooms) | Walkthrough and challenge rooms have distinct purposes; rooms consist of tasks with descriptions and questions. | Prediction feedback teaches the reason. Independent assessment remains separate from example completion. |
| [Hack The Box](https://help.hackthebox.com/en/articles/6007919-introduction-to-starting-point) | Starting Point describes linear tiers, tasks, machine state and accessible walkthroughs; the article has a separate section index. | Visible session state, secondary replay and contextual navigation alongside the working column. |
| [PortSwigger Academy](https://portswigger.net/web-security/getting-started) | Read materials, practice skills, track progress; short distinct actions for each stage. | Completion leads to a fresh challenge; reference material stays secondary. |
| [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) | Finishing a level gives information needed for the next level; persistent level navigation. | Path sidebar links to real levels. Finishing a walkthrough no longer promotes reopening the walkthrough. |
| [The Odin Project](https://www.theodinproject.com/paths/foundations/courses/foundations) | Scannable grouped course sections and an ordered lesson list. | Open section navigation and consistent reading width, with no new grid of decorative cards. |
| [Codecademy](https://www.codecademy.com/learn/learn-python-3) | Primary Start action, adjacent useful course context, distinct lessons/projects/quizzes and qualified time estimates. | Page-specific supporting columns; selected available time controls the promoted activity, while authored estimates remain honest. |
| [Exercism](https://exercism.org/) | Practice, automatic analysis and human mentoring are distinct; feedback includes improvement guidance. | Evidence checks explain the next action. Green feedback does not imply that an uploaded artifact proves reasoning or mastery. |

[Carbon's notification guidance](https://carbondesignsystem.com/components/notification/usage/)
also informed status colors, icon/title/body structure, and actionable error text.
The previous React Bits, Aceternity, Magic UI and Motion review remains recorded in
`ui-workspace-sources.json`. Native SVG, CSS and Web Animations suit this plain
JavaScript application; this pass adds no animation framework or third-party runtime.
Exercism documentation guesses and a freeCodeCamp article returned 404; the
freeCodeCamp learning page returned an empty HTTP body. They were not used as evidence.

## Implemented decisions

- **Feedback:** mint success, amber guidance/partial outcome, lavender information,
  red error. Every treatment has a label and distinct glyph, so color is supplemental.
  The check draws once; completion has a short local geometric burst. There is no
  repeating celebration, fake XP, audio, or reward replay on reload. Errors remain
  visible until dismissed. Dialog feedback remains inside the native top layer.
- **Walkthrough:** the takeaway appears directly after finishing or skipping. Focus
  moves to its heading without opening a phone keyboard. Replay is a text action;
  the existing textarea is retained so replay does not erase a draft. Completing
  the example puts the fresh-challenge action near the title and folds saved work
  into review. Tour completion alone awards nothing.
- **Available time:** the track's canonical next node remains unchanged in the
  service. When it exceeds the chosen time, Today promotes an eligible checkpoint,
  a fitting side task, or a fitting Playground activity, in that order. The chosen
  activity's real estimate must fit; no estimate is reduced to match the filter.
  The longer track task is explained in one short line. With no fitting option,
  the page says so and offers a duration change. Any time restores the full task.
- **Card containment:** the time-fit card now uses the same positioned flex layout
  as the main challenge. This fixes the reported escaped staircase and full-width
  yellow label. Browser checks assert illustration containment and label width,
  beyond checking document overflow alone.
- **Wide pages:** at 1440 px and above, the shared frame grows to 1440 px and reserves
  a 224–248 px supporting column. Today/Stats show real momentum and continuation;
  Path links to levels; Tracks keeps the active mission nearby; Docs has an article
  section index; Profile has settings navigation; Playground and activities expose
  their sections and saved-work destination. The existing primary navigation uses
  the left side. Challenge retains its dedicated notebook layout. Narrow screens
  keep these same actions in the primary flow and do not squeeze in a side column.
- **Cursor:** `?cursor=circuit` is an opt-in preview pending owner feedback. It adds
  short neutral right-angle traces to the grid, fades on idle, keeps the native
  cursor, and never intercepts clicks. The default remains the existing grid.

## Coverage and limits

`tests/test_ui_feedback.py` covers the primary handoff, draft preservation during
replay and reload, honest duration choices and the empty state, icon/label status,
reduced motion, illustration containment, and page/column geometry at 320, 390,
768, 1440 and 1920 px. It visits Today, Path, Stats, Tracks, Docs, Profile and all
four Playground catalog sections. Dedicated activity and notebook browser tests
cover the remaining workspaces, evidence upload, completion, recovery and practice.
Screenshots use disposable profiles in `docs/screenshots/feedback/`.

This verifies the shared screens and selected complete journeys. It does not certify
every authored challenge, external lab environment, device/browser, learning outcome
or future UX score. A senior review should include a real new learner finishing a
lab, recovering notes, understanding partial credit, and selecting the next task.
