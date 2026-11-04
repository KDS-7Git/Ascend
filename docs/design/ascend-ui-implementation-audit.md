# Ascend interface and interaction audit

Reviewed **2026-11-03** as input to the wider visual redesign. The owner explicitly includes the base UI and current neobrutalist styling in scope. This is an audit and implementation design, not a runtime UI change.

The current app has working task flows and substantial animation. Its main weakness is that **navigation, decoration, and repeated control surfaces compete with the learning object**. A redesign should make the activity, its outcome, and its next useful action more tangible. Adding more ambient effects to the existing page structure would not solve that problem.

## Evidence and scope

Inspected the current shared working tree, then ran Chromium against two isolated local instances with disposable databases. The first used a copy of the Ethical Hacking Foundations pack and exercised Today, Path, Playground, a worked example, prediction feedback, an independent challenge, saved work, Stats, Profile, dark mode, and an invalid lab route. The second used two synthetic authenticated accounts to inspect sign-in, sign-out, and history separation. Both server processes were stopped and their temporary profiles removed. No deployed service, real profile, or hosted target was used.

The screenshot set contains **24 captures**, including desktop 1440 × 1000 and phone 390 × 844 layouts. Some teaching/task captures are full-page images. The successful exercise was filled with the fixture's expected answers solely to inspect its result state; this is not evidence of usability, learning, independent solving, or realistic task duration. Hosted execution states below are grounded in code, not a live hosted-lab session.

- [Interaction observations](../screenshots/ascend-ui-redesign-audit/observations.json): 21 captures, no recorded page JavaScript errors, inspected routes, focus, save state, and animation inventory.
- [Account and layout observations](../screenshots/ascend-ui-redesign-audit/account-observations.json): three captures, two synthetic accounts, phone viewport/target geometry, and no recorded page JavaScript errors.
- Existing [Playground usability follow-up](practice-playground-ux.md), [adaptive proposal](adaptive-playground-proposal.md), and [runner design](server-lab-runner.md) establish the intended contracts that a redesign must preserve.

| Surface | Current capture | What it exposes |
| --- | --- | --- |
| Today | [Desktop](../screenshots/ascend-ui-redesign-audit/today-desktop.png), [phone](../screenshots/ascend-ui-redesign-audit/today-phone.png) | Strong primary task, several repeated progress summaries, prominent decorative surfaces. |
| Playground | [Desktop](../screenshots/ascend-ui-redesign-audit/playground-desktop.png), [phone](../screenshots/ascend-ui-redesign-audit/playground-phone.png) | Heading, five navigation tabs, recommendation, filters, surprise action, then catalog. |
| Teaching | [Step one](../screenshots/ascend-ui-redesign-audit/example-tour-desktop.png), [prediction](../screenshots/ascend-ui-redesign-audit/example-prediction-desktop.png) | A real three-step walkthrough with explicit actions and a separate follow-up challenge. |
| Independent work | [Active task](../screenshots/ascend-ui-redesign-audit/challenge-active-desktop.png), [completion](../screenshots/ascend-ui-redesign-audit/challenge-complete-desktop.png) | Dedicated task route, evidence controls, fixed result, +10 practice XP, changed-case continuation. |
| History and progress | [Saved work](../screenshots/ascend-ui-redesign-audit/saved-work-desktop.png), [Stats](../screenshots/ascend-ui-redesign-audit/stats-desktop.png) | Grouped attempts and progress accounting; several result concepts need clearer names. |
| Lab | [Task page](../screenshots/ascend-ui-redesign-audit/lab-desktop.png), [failure page](../screenshots/ascend-ui-redesign-audit/lab-error-desktop.png) | Clear task/setup sections and recoverable invalid-route treatment; live lab execution was not performed. |
| Identity | [Sign-in](../screenshots/ascend-ui-redesign-audit/login-desktop.png), [account A](../screenshots/ascend-ui-redesign-audit/account-1-history-desktop.png), [account B](../screenshots/ascend-ui-redesign-audit/account-2-history-desktop.png) | Basic private-account flow; the second account correctly has no first-account history in this sample. |

## What already works and should survive the redesign

The browser inspection confirmed that starting an example opens `#activity/RUN` and removes the catalog tabs. The three-step tour gives a prediction and feedback, and completion offers a separate challenge. Autosave explicitly reported **“Saved in Playground → Saved work & history.”** The successful challenge displayed its result and +10 XP, then offered a changed case. These are working contracts, not proposals still waiting for implementation.

Result handling already moves focus to the new completion section. Buttons have busy/disabled states, actions are protected against repeated clicks, and error notices remain until dismissed rather than disappearing while being read. Invalid lab IDs produce a contextual error with retry. Screen-reader roles, native controls, a skip link, and focus outlines are present. The reduced-motion phone session recorded **zero active animations**. [Navigation and actions](../../web/app.js), [Playground](../../web/playground.js), [feedback](../../web/feedback.js)

The sampled layouts had no horizontal document overflow. An additional probe verified `innerWidth`, `clientWidth`, and visual viewport width were all 390 px under both desktop and mobile emulation; the six bottom navigation controls fit within that width. This is a useful baseline, not a complete accessibility/device certification.

## Findings and design priorities

| Priority | Finding and concrete evidence | Redesign direction |
| --- | --- | --- |
| High | **The Playground spends its first screen on selection infrastructure.** In the desktop capture the first catalog card begins around the bottom of a 1000 px viewport; on the phone, tabs and the recommendation consume almost the whole first screen before filters and catalog. [Renderer](../../web/playground.js) | Keep one recommendation plus an immediately visible alternate activity. Move advanced filters into a drawer. Make the search/filter row compact and use one vocabulary for activity types. |
| High | **Different mental models share nearly identical containers.** Examples, independent tasks, catalog controls, account settings, and primary actions inherit repeated 2 px outlines, four-pixel radii, and hard shadows. [Base styles](../../web/style.css) | Establish surface and emphasis levels. Use quiet page structure, task-specific illustrated objects, and stronger elevation only for the primary action or selected object. Base UI may change completely; do not treat the existing border/shadow recipe as a fixed requirement. |
| High | **There are too many navigation layers and synonyms.** Today/Path/Tracks/Playground, “mission,” “pack,” “side quest,” and right-rail links overlap. Playground has five tabs and the right rail repeats four destinations. [Shell](../../web/index.html), [context rail](../../web/context-rail.js) | Make user-facing destinations outcome-based: continue learning, explore practice, saved work, and progress. Keep pack/mission implementation terms mainly in author/admin contexts. A sidebar, tabs, and context rail should perform distinct jobs. |
| High | **A lot of movement has no relation to the learner's action.** The Today capture recorded nine infinite animations: seven ambient shapes/particles/orbit elements plus the climber and flag. Two temporary glow effects also ran. [Motion](../../web/effects.js), [motion CSS](../../web/effects.css) | Attach life to meaningful objects and events: a selected activity turns toward the learner, a test run animates its diagram, a successful repair stabilises the model. Keep the reading/work area still. Give one object the attention budget at a time. |
| High | **Three result systems express similar outcomes differently.** Playground uses a shared feedback panel; track notebook completion uses `showChallengeCelebration`; hosted lab operations can display raw JSON followed by a plain result sentence. [Playground](../../web/playground.js), [track notebook](../../web/challenge-work.js), [hosted UI](../../web/local-labs.js) | Define one outcome contract with domain-specific evidence sections. Distinguish result, newly earned reward, progress change, and next action. Render raw technical output behind “Details” unless reading it is itself the task. |
| High | **Saved work has three different durability models.** Track notebook recovery uses localStorage and versioned server saves; Playground fallback uses sessionStorage; hosted editor drafts use in-memory Maps and require explicit Save. [Notebook](../../web/challenge-work.js), [Playground](../../web/playground.js), [hosted UI](../../web/local-labs.js) | Use consistent, truthful states: saving, saved to account, kept on this device, unsaved in this tab, and conflict. Explain the actual scope beside the editor. A hosted draft in a JavaScript Map must not imply survival across refresh. |
| High | **The shared-runner flow lacks a learner admission state.** A full server rejects starts; accepted operations have generic preparing/working messages and all actions are serialized. [Runner](../../ascend/local_labs/hosted.py), [hosted UI](../../web/local-labs.js) | Implement the two-slot waiting/claim/preparation flow from the adaptive proposal. Display actual states, a useful local/browser alternative, and a release action. An animated arena cannot stand in for a real queue or healthy environment. |
| Medium | **Progress terms can disagree in the learner's view.** After the sampled quick solve, Profile reads “10 Verified XP” and “0 Verified tasks.” The task count covers track awards, while the XP total also includes Playground. [Profile renderer](../../web/app.js), [session summary](../../ascend/timing.py) | Label metric scope explicitly: practice XP, assessed track tasks, independent skill evidence, and practice habit. Use a small explanation near the metric. Do not describe a composite points total as mastery. |
| Medium | **General route navigation does not consistently focus the new content.** Several sampled route changes left focus on BODY; `switchTab` updates title/loading/navigation but has no universal destination-heading focus policy. Completion sections do receive focus. [Navigation](../../web/app.js) | Focus the destination heading after user-initiated route changes and announce load failure. Preserve editor focus on background refresh and filter updates. Cancel obsolete transitions so rapid navigation cannot focus stale content. |
| Medium | **The upper hierarchy is heavy while the content is small.** Base text is 15 px; many instructions are 12 px “small” text; headings use weights up to 850 with tight negative letter spacing. Side rails consume space without always adding distinct information. [Styles](../../web/style.css), [rail layout](../../web/context-rail.css) | Use a calmer type scale, readable task prose, and larger operational guidance. Give the evidence/work surface more room. Let typography and spacing organise content before adding container borders. |
| Medium | **The phone nav fits but carries six equally weighted destinations.** The profile probe also found a 28 × 28 home control and a roughly 42 px-high XP control. | Aim for four primary mobile destinations plus an accessible More/account surface. Use at least 44 × 44 px for primary touch targets as a product target; smaller inline text links require appropriate spacing. This audit does not claim all such controls violate WCAG minimums. |
| Medium | **Content continuity is functional but static.** The catalog and pack registry provide activities and installation; repeat/follow-up support exists. There is no complete release-feed/season/team experience in the current UI. [Catalog](../../ascend/playground/catalog.py), [pack browser](../../web/app.js) | Add authored “new this week,” personal next experiments, and a visible finish-to-next bridge only when reviewed content exists. Keep finite-catalog exhaustion honest and historical attempts pinned to their content version. |
| Medium | **Accounts are basic server accounts, not a team product.** Username/password sign-in and CLI user creation exist; a self-service signup/recovery flow, organisation switcher, invitations, and team roles were not found. [Authentication](../../ascend/server/auth.py), [server CLI](../../ascend/server/__main__.py) | Design these as separate account milestones. First make the current account and installation obvious, then add a real organisation/role model if needed. Do not display a workspace switcher that only changes a label. |

## A visual system that gives the learning objects life

Use a **calm working surface with expressive activity objects**. The personality can come from an authored scene, character, artifact, or environment map rather than repeating a thick outline on every control. A strong palette and recognisable mark can survive a complete base-style change.

Suggested surface hierarchy:

1. A quiet page canvas and restrained navigation. Show one current location and one primary continuation.
2. A distinctive activity object: a lab workstation, evidence folder, miniature application, router diagram, or deployment assembly. Its state is understandable even when motion is disabled.
3. An unobstructed work surface with clear instructions, data, controls, and visible saved state. Decoration should not travel behind editable code or the learner's evidence.
4. A focused result scene that explains the outcome and connects to one useful next action. Expand details, rewards, and alternatives on demand.

For example, a DevOps activity can show a small application moving through build, test, release, and health-check stages. Animate a stage only when the corresponding authored simulation or actual job state changes, and label which kind it is. An API investigation can show requests reaching allowed/denied boundaries when the learner submits a test. A character can direct attention to a relevant observation, then leave the work area. These are interface representations of learning and operation states, not claims that a fake animation is a real deployment.

An “arena” can be a navigable collection of cases and earned artifacts. It need not launch a persistent VM per visitor. Keep asynchronous case selection and personal progression available when the two hosted lab slots are occupied. Optional competition must use comparable, explicitly scoped cases and must not grant queue priority through XP.

## Interaction and motion contract

The current primitives already provide useful engineering foundations: transform/opacity animation, bounded result sparks, reduced-motion support, hidden-tab cancellation, native cursors, and non-blocking content. Rework the choreography rather than layering another independent animation system over them.

| Event | Current evidence | Proposed treatment |
| --- | --- | --- |
| Hover/focus | 140–180 ms colour/transform transitions; raised buttons shift −2 px, active press +3 px; nav icons move. | A restrained surface response and a clear focus ring. Match keyboard affordance to hover information; never make essential help hover-only. Preserve the hit area. |
| Click/submit | Shared action wrapper disables the button, sets `aria-busy`, and shows a spinner. | Immediate acknowledgement; retain the input and outcome context. Use the action's own status instead of a second global loading scene. |
| Route change | 100 ms exit; heading entrance 480 ms; sections 440 ms with stagger; some nested detail entrances also run. | Target roughly 180–240 ms for routine transitions, animate only the destination object/region, and never delay input readiness for choreography. Focus the destination heading when appropriate. Durations are proposed tokens, not usability results. |
| Save | Playground debounces 800 ms; notebook has a save state and feedback animation; hosted files need explicit save. | A stable inline save indicator after acknowledgement. No celebratory burst for every autosave. Preserve honest offline/tab/device wording. |
| Incorrect answer | Playground uses “Keep investigating” and retains the working task. | Identify the relevant failed check without shaming the learner or inventing conceptual weakness from a technical failure. Keep inputs and offer a discriminating next test. |
| Example completed | Separate completion panel and fresh-challenge action; no example XP. | Small acknowledgement and an obvious independent next case. A completed tour alone is not a completed learning example. |
| Fresh assessed pass | Result panel, updated XP, and bounded 620–720 ms motion with six local sparks. | One compact result animation after the server receipt. Reveal evidence first, then show newly awarded XP, then the named next case. Replay/re-fetch should not mint rewards or repeat the achievement celebration. |
| Milestone reached | Track completion and milestone labels exist; celebration shares broad “complete” motion. | A rarer, more distinctive 0.8–1.2 second artifact/scene change with persistent evidence. Offer Continue immediately; motion is skippable and never a modal gate. |
| Streak extended | Header feedback animates when a higher streak is observed; result may also mention it. | One supporting acknowledgement, subordinate to the actual learning result. Keep missed-day language neutral and preserve freeze rules. |
| Lab preparing/passing | Hosted UI shows generic operation state, JSON output, and plain result text. | A real state timeline: waiting, preparing, ready, checking, exporting, released. Pair a passed rubric with the exact evidence authority. No verified-track medal for a zero-XP hosted practice receipt. |
| Error, disconnect, failed cleanup | Persistent notices and retry actions exist; runner can retain a slot after failed cleanup. | Keep recovery beside the affected object, explain what is saved and what remains active, and make retry/export/release distinct. Never replace a failure with a happy character. |
| New content | Static catalog/registry and follow-up actions. | Quiet new-content markers and a preview of the required skill/time/environment. Reserve release celebrations for intentional visits, not every app load. |

Keep a single event vocabulary in the application/UI boundary: `work_saved`, `check_failed`, `example_completed`, `practice_passed`, `assessment_passed`, `milestone_earned`, `streak_extended`, and runner lifecycle states. Each event should carry account identity, attempt/content identity, evidence authority, actual reward delta, and an idempotent receipt identity where relevant. Do not derive earned events from a DOM class or from an optimistic click.

Use existing `AscendMotion` and `AscendFeedback` boundaries while separating event semantics from presentation. One motion coordinator should prevent a route entrance, character cue, streak pulse, and reward burst from competing simultaneously. Historical results remain readable without replaying newly-earned animation.

## XP, rewards, and continuous motivation

Current policies are intentionally different:

| Work type | Current policy relevant to the redesign |
| --- | --- |
| Worked example | Saves learning; zero XP and no independent mastery claim. |
| Fresh quick practice | 10 XP at most once per exercise family per logical day, with a 30 practice-XP daily cap. Familiar/revealed repeats do not create new credit. |
| Standalone challenge | Authored first-solve amount (currently 25/50/100 by band), keyed to a stable reward identity; repeats/reveals cannot manufacture another first-solve award. |
| Track assessment | Existing timer-based rule starts at 100 points within budget and decreases after budget to a floor of 25; some permission tasks scale by correctness. This is a separate scoring contract. |
| Free practice and hosted/local labs | No automatic verified assessment XP. Hosted results describe observed controls; manual local reports have a different evidence authority. |

See [Playground award code](../../ascend/playground/__init__.py), [track timing](../../ascend/timing.py), and [streak logic](../../ascend/engine/streak.py). A visual redesign must not silently replace these formulas, convert old receipts, or reward requesting help with less respect. Any scoring-policy revision needs an explicit versioned design.

Add motivation through **visible capability and useful continuation**: an artifact the learner built, a repaired system that now passes controls, a skill evidence card, a personal collection of cases, and the next interesting experiment. Optional cosmetic rewards may reference earned milestones but should have no effect on assessment truth or hosted admission. New currencies, shops, public ladders, and daily scarcity are not required to give this product life.

The immediate retention bottleneck is content as well as presentation. The current catalog has 37 activities and only one hard activity. A recurring challenge surface must have an authored release process: versioned brief/rubric, distinct variants, difficulty review, negative controls, environment acceptance, accessibility review, and a policy for retirement that preserves saved attempts. Community authoring additionally needs moderation and reviewer capacity; it cannot be a public arbitrary-code publishing endpoint.

## Accounts, preferences, and shared environments

The inspected second account did not see the first account's saved group. Server tracker dependencies and `Database` helpers scope data to authenticated user IDs. The runner derives its own account scope. These are useful boundaries to preserve while changing the shell.

The current profile shows username and server origin. In single-user mode logout is hidden and the identity is “Local learning account.” Multi-user mode uses server-created username/password accounts with bearer tokens in sessionStorage. Theme/motion preferences are stored for the browser origin, not synchronised per account. Notebook recovery keys use username and task reference; Playground draft keys use username and run ID. [Profile and login](../../web/app.js), [auth](../../ascend/server/auth.py), [storage](../../ascend/storage/__init__.py)

Priorities for account UX:

- Show the current account and learning installation in the account menu, especially on shared devices. Rehydrate account-owned recommendations, drafts, saved work, and rewards after a switch.
- Before logout/switch, finish or explain pending saves. Provide an explicit shared-device choice for clearing local recovery data; do not silently delete unsynced work.
- Distinguish account preferences from device preferences. “Reduce motion on this device” is useful even before sign-in; a later account default can coexist with the operating-system preference.
- If self-service accounts are introduced, design registration, verification, recovery, session management, and empty-state onboarding together. The current sign-in modal does not supply those capabilities.
- Treat future organisations, instructors, reviewers, and teams as real authorisation roles, separate from personal identity. Invitations, workspace membership, private notes, publishable portfolio evidence, and aggregate team reporting need explicit permissions. A learner joining a team should not expose every private draft by default.
- Keep the two-slot limit and one-active-run-per-account policy visible through the admission flow. Shared workspaces and multiple browser tabs cannot bypass it. Each save/result belongs to an account and attempt even if a public arena or team progress view also references it.

## Engineering integration and acceptance

Implement the redesign through a small token/component system and route-level composition; keep the existing application contracts intact. Avoid another broad append-only CSS override layer: `style.css`, `effects.css`, `feedback.css`, `context-rail.css`, and feature files already share selectors and visual responsibilities. Move toward tokens for typography, spacing, surfaces, semantic colour, focus, and motion, with clear component ownership.

First replace the shell and selection hierarchy, then the activity/workspace/result components, then state-driven objects and account flows. Keep browser/local exercise delivery independent from persistent hosted allocation. Use lightweight SVG/CSS or bounded canvas only where it clarifies the object; do not require a model server, video background, or always-running 3D engine for ordinary navigation.

Specific acceptance gates:

1. A learner can identify the primary action, expected output, save location, and remaining prerequisite without coaching. Test beginner and experienced users; the current automated audit cannot establish comprehension.
2. Starting a task leads to its dedicated page. Returning preserves the same scenario, work, hint/reveal history, and timer contract. Browser back, rapid navigation, and failed saves do not silently abandon work.
3. Hover/focus/click states work with pointer, keyboard, touch, and reduced motion. Provide a visible quiet-mode choice; no continuous motion in evidence-reading and editing surfaces. Text and result meaning remain complete with all animation disabled.
4. Reward motion follows a successful authoritative result; duplicates, refresh, tab restoration, and a different account do not replay or duplicate an earned reward. Assisted, familiar, local-manual, and server-checked results remain labelled.
5. Measure representative phone interactions against proposed targets such as INP under 200 ms, CLS under 0.1, and LCP under 2.5 seconds on the agreed device/network. These are targets, not measurements from this audit. Bound animation work, throttle pointer effects with requestAnimationFrame, and stop hidden/offscreen scenes.
6. As history and content grow, paginate summary data on the server. The current history renderer fetches all runs, groups them client-side, then displays ten groups; that is display pagination rather than a bounded history API. Avoid embedding full work/results in every catalog response.
7. Verify error, empty, partial, offline, login-expired, queue-full, preparing, failed-check, failed-export, and failed-cleanup states alongside happy paths. Account/version conflicts must be recoverable without blending another user's data.

The redesign should be evaluated as a complete experience: calm selection, a tangible learning object, clear action and feedback, trustworthy saved work, and a useful continuation. Motion and characters become part of that experience when they explain or acknowledge real events.
