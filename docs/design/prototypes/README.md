# Ascend experience prototype

Open the [interactive preview](ascend-living-ui.html) to explore the proposed base UI and learning flows. The [integrated design plan](../ascend-experience-redesign.md) explains the research, production contracts, and implementation sequence.

This is a standalone design artifact with labelled sample data. Accounts, checks, rewards, timers, and lab availability are simulated in the browser. It does not connect to Ascend, authenticate anyone, provision a runtime, or change real progress.

## Open locally

Open `docs/design/prototypes/ascend-living-ui.html` in a modern browser. Keep its neighbouring CSS/JavaScript files and the repository's `web/` assets in place. The preview uses the existing self-hosted Inter font and Ascend favicon.

If your browser restricts local-file storage or assets, run this from the repository root:

```bash
.venv/bin/python -m http.server 8765 --bind 127.0.0.1
```

Visit <http://127.0.0.1:8765/docs/design/prototypes/ascend-living-ui.html>. Stop that preview server with Ctrl+C when finished. No build or application server is required.

## Try the experience

| Place | What to try |
| --- | --- |
| [Today](ascend-living-ui.html#today) | Inspect the recommendation, deployment scene, and original trail companion. Change your goal through the account control. |
| [Playground](ascend-living-ui.html#playground) | Compare example, challenge, and lab presentations. Filter/search the sample catalog or use the experienced-practitioner entry. |
| [DevOps path](ascend-living-ui.html#devops) | Explore the proposed 13-level service journey. This demonstrates one active track; the production navigation must support the other domains too. |
| [Worked example](ascend-living-ui.html#example) | The first visit for each sample learner opens a three-step walkthrough. Use the named next actions, Skip tour, or reopen it. Save a learning note and mark the example studied. |
| [Independent challenge](ascend-living-ui.html#challenge) | Read the brief, then press **Start challenge** to enter the workbench and begin the continuous clock. Compare the evidence, try an incorrect repair, and check a successful one. |
| [Hosted lab](ascend-living-ui.html#queue) | Join the queue, then explicitly simulate a slot becoming free. Claim the 90-second offer, check the sample environment, and finish/release it. |
| [My work](ascend-living-ui.html#work) | Return to notes and results, reload to check recovery, or download a plain-text copy. |
| [Progress](ascend-living-ui.html#progress) | Compare sample XP, practice rhythm, and skill evidence. Preview the milestone moment. |

The example uses a same-host port mismatch. The independent case adds a separate private application host and an access-policy constraint. Copying the example's loopback repair does not solve it. The case demonstrates interaction design; its difficulty and duration have not been calibrated with learners.

Starting the challenge is explicit. Its original clock continues when navigating away and freezes when the attempt passes or is explicitly ended. Opening an example during an active challenge requires ending that attempt; starting a new task while a hosted lab is active requires finishing/releasing the lab. A queue offer does not end another task automatically.

A first successful sample challenge records **50 challenge XP once**. Studying the example and checking the hosted lab award no XP. This illustrates the existing reward distinctions rather than introducing a new production scoring system.

Use **Explore the interactions** in the top banner for shortcuts, a milestone preview, and **Reset all sample progress**. A milestone preview is explicitly a demonstration and does not assert that its underlying curriculum was completed.

## Accounts, saving, and accessibility

The account control switches between **Mira** and **Arun**, with separate sample goals, notes, tour history, and results. It also controls dark appearance and expressive motion. Operating-system reduced motion takes precedence over the motion switch.

Sample state is saved under the browser-storage key `ascend-design-preview-v1`. It belongs to this preview and browser origin. If a write fails, the UI describes the work as held only in the open tab and offers a download. A download is a separate device copy. These behaviours do not implement server persistence, real authentication, cross-device sync, or secure account isolation.

Use the keyboard skip link to reach the main content. Search is available from the header or Ctrl/Cmd+K. Dialogs support Escape. Status, reward, and tour meaning remain available with motion disabled.

## Selected views

| View | Capture |
| --- | --- |
| Base UI | [Desktop](previews/today-desktop.png), [phone](previews/today-mobile.png), [dark appearance](previews/today-dark-desktop.png) |
| Playground | [Desktop](previews/playground-desktop.png), [phone](previews/playground-mobile.png) |
| Challenge workbench | [Active investigation](previews/challenge-desktop.png), [recorded result](previews/challenge-passed-desktop.png) |
| Teaching | [First walkthrough step on a phone](previews/example-mobile.png) |
| DevOps path | [Desktop](previews/devops-desktop.png) |
| Hosted practice | [Slot offer](previews/queue-desktop.png) |
| Milestone | [Celebration preview](previews/milestone-desktop.png) |

## Validation and implementation boundary

The [validation record](validation.json) preserves the source hashes and results of eight isolated Chromium flow checks, followed by final layout/capture checks after the control-boundary and touch-target adjustments. The flow review covered tours, sample-account separation, save/export/reload, storage failure, wrong/correct/repeated results, timer continuity, foreground conflicts, queue lifecycle/expiry, search, keyboard skip, dark appearance, and reduced motion.

Final layout checks cover the eight routes at 360, 390, 768, and 1440 CSS pixels. Sampled contrast calculations are included in the record. These are browser checks, not a complete accessibility certification, physical-device study, calibrated learner assessment, or production load test.

Production implementation needs server-authoritative results and rewards, authenticated ownership, durable saves, real environment admission/cleanup, and reviewed content. Client-only answer checking and hiding fixture markup are appropriate to this labelled preview only. Follow the [master plan's staged delivery gates](../ascend-experience-redesign.md#10-implement-in-reviewable-increments) when integrating the design.
