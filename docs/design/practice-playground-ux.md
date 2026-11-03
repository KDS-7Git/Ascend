# Playground usability follow-up — 2026-11-02

The owner reported approximately 2–3 minutes for the shown worked-example experience, unclear instructions, uncertainty about where work was saved, and confusion about the required “Next action”. The screenshots also showed catalog navigation remaining above a running activity and visually identical text hiding a trailing newline. Prior topic familiarity, independent-challenge timing, and task difficulty were not supplied. This is actionable usability feedback, not a calibrated timing study.

Public first-party flows were inspected again on 2026-11-02:

| Source | Observed pattern | Ascend implementation |
| --- | --- | --- |
| [PortSwigger getting started](https://portswigger.net/web-security/getting-started) | Read learning materials, practice in labs, track progress. | Separate lesson and challenge presentation; the catalog leads into a dedicated activity. |
| [TryHackMe rooms](https://help.tryhackme.com/en/articles/6611837-rooms) | Rooms contain tasks with descriptions/questions; walkthrough and challenge rooms have different purposes. | Worked examples have guided steps and low-stakes predictions; independent challenges retain their evidence questions. |
| [HTB Starting Point](https://help.hackthebox.com/en/articles/6007919-introduction-to-starting-point) | Beginner tasks use explained concepts, walkthroughs, clear task answers and progressive complexity. | Explicit objective, explained prediction feedback, then a separate fresh challenge. No automatic challenge walkthrough. |
| [Duolingo Practice tab](https://blog.duolingo.com/guide-to-duolingo-practice-hub/) | Learners choose clear skills and lesson types for on-demand practice. | Distinct Learn with guidance, Test yourself, and Experiment freely sections; Subject and Time are primary filters. |

This was a public documentation/product-flow review, not a signed-in audit of competitor interfaces. The visual design uses Ascend's existing type, color, icon and component system.

Implemented behavior:

- `#activity/RUN` is a dedicated page; legacy `#playground/RUN` links redirect. The catalog tabs and completed track-session strip are absent.
- Worked examples and free workspaces have pausable practice clocks. Assessed challenges use continuous time anchored to their original start: saving, leaving, browser closure and server restarts cannot pause or reset it. Completion or explicit end stops the clock. Switching to another activity requires an explicit end. Existing fixed activity rewards apply. Pre-upgrade practice time is not reconstructed.
- Every worked-example family has three authored steps with Back, Next step, Skip tour, and prediction feedback. The first unfamiliar skill opens automatically; step position survives refresh; finish/skip preferences are remembered per skill. Open walkthrough remains available. Escape within the walkthrough skips it. Tour interactions alone never complete an example or establish readiness.
- The final prompt asks for a specific takeaway in the learner's own words. The next-action text box is now an optional return reminder, with an explanation. Learning logs retain a system next-action default when it is omitted.
- Work saves in the user's Ascend profile and is accessible through Playground → Saved work & history. No downloaded file is implied. Autosave status and Save & leave explain this destination. History shows one group per activity, across versions; #attempts/ACTIVITY opens all attempts for individual review or return.
- The integrity example displays escaped text and byte counts to expose the final newline. It explicitly distinguishes matching bytes from authenticating an author.
- Optional session feedback captures work/setup minutes, clarity, difficulty and unwanted repetition. A conservative personal estimate needs three distinct completed, clear, problem-free reports and cannot fall below the authored estimate. Local 14-day usage counts support subsequent review; they do not establish learning outcomes.

The software tests cover dedicated routing, desktop/phone layouts, keyboard navigation, persisted steps, paused clocks, independent challenge isolation, feedback and checkpoint semantics. Actual beginner transfer sessions and roughly two weeks of observation remain empirical follow-up work.
