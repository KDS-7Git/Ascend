# Ascend: a living workspace for serious practice

**Integrated design and implementation plan, 2026-11-03.** Includes the entire base UI, not only Playground. This extends the [adaptive learning proposal](adaptive-playground-proposal.md) with visual identity, navigation, interaction, motion, rewards, accounts, content operations, and the new [DevOps curriculum](devops-track-design.md).

The design direction is **an expedition workshop**: a calm, readable place to work, with tangible activity objects and an original companion that responds to meaningful moments. Preserve Ascend's warmth and mountain identity while moving away from applying strong neobrutalist borders, offset shadows, and decorative animation to almost every surface.

The work in this change is research, specification, and a functioning **standalone design prototype**. It does not replace the production UI, install the DevOps track, change XP formulas, deploy services, or add organisation accounts. The prototype uses clearly labelled sample data and simulated results.

## Review the proposed experience

Open the [interactive prototype](prototypes/ascend-living-ui.html), or start with its [desktop preview](prototypes/previews/today-desktop.png) and [phone preview](prototypes/previews/today-mobile.png). The [prototype guide](prototypes/README.md) lists the interactions and validation scope.

The prototype covers Today, Playground, the DevOps path, a separate challenge workbench, a three-step worked example, saved work, progress, a hosted-lab waiting flow, a milestone moment, sample-account separation, dark appearance, and reduced motion. Its original SVG companion and miniature deployment scene are authored for this proposal; competitor characters and visual assets are not reused.

Four documents supply the supporting detail:

| Evidence or design | Scope |
| --- | --- |
| [Platform UI/motion audit](platform-ui-motion-audit.md) | Eight platforms, 38 cited first-party sources, 16 public browser visits, 27 captures. Six had directly inspected interfaces; HackerRank/DataCamp browser access was blocked, so their interaction coverage is documentation-based. |
| [Current Ascend audit](ascend-ui-implementation-audit.md) | Disposable-profile browser inspection of current desktop/phone layouts, examples, task results, motion, saves, metrics, and two real test accounts. |
| [Adaptive platform audit](adaptive-playground-platform-audit.md) | Employment versus interest goals, experienced entry, sustained practitioner practice, and what is actually adaptive. |
| [DevOps track design](devops-track-design.md) | Eighteen first-party sources, 13 proposed levels, nine candidate recipes, representative tools, capstone, runtime limits, and integration gates. |

These studies do not establish that a competitor feature causes retention, nor that every signed-in transition was inspected. Historical Duolingo design explanations and current public controls are labelled separately. The prototype's usability checks are not a learner study or a production performance benchmark.

## 1. The base UI decision

The current base has strengths: a recognisable mark, warmth, tactile actions, clear contrast, an existing dark palette, and useful reduced-motion support. The problem is hierarchy. Repeated 2 px outlines and offset shadows make unrelated controls feel equally important; multiple decorative animations compete with the task. In the inspected Playground, header/tabs/recommendation/filters push the first catalog item below a 1,000 px desktop viewport. The right rail repeats navigation and saving instructions.

| Direction considered | Value | Cost or limitation | Decision |
| --- | --- | --- | --- |
| Refine the existing neobrutalism | Lowest visual migration cost; retains the established palette and tactile character. | Still needs substantial hierarchy, density, and motion changes. Keeping every outlined card would preserve the current problem. | A viable conservative option, but not the recommended complete direction. |
| A dark technical console throughout | Strong fit for some security/operations audiences; supports dense technical work. | Can make general learning and 3D/Python subjects feel secondary. Dark appearance should remain a preference rather than a compulsory identity. | Use dark work surfaces where useful, with a complete light theme. |
| Warm, quiet base with expressive learning objects | Accommodates career learners, hobbyists, beginners, and practitioners. Personality comes from authored objects and clear moments. | Requires a small coherent illustration/component system and deliberate migration. | **Recommended; demonstrated in the prototype.** |

Keep substantial outlines/shadows for a few intentional physical cues, such as a primary action or earned artifact. Use spacing, type, alignment, and surface tone to structure ordinary content. Decorative panel borders can be subtle; input boundaries and focus indicators must remain identifiable.

### Initial visual tokens

These are concrete starting tokens, not a claim that colour alone solves usability. Consolidate them into the existing styling system instead of layering another set of global overrides over `style.css`, `effects.css`, and feature CSS.

| Token | Light starting value | Dark starting value | Use |
| --- | --- | --- | --- |
| Canvas | `#F5F6F0` | `#17271F` | Quiet page background. |
| Work surface | `#FFFEFA` | `#1E3027` | Forms, evidence, notes, dialogs. |
| Main text | `#243C33` | `#EBEEE1` | Headings and body. |
| Secondary text | `#637168` | `#B1BDAE` | Supporting copy with sufficient contrast. |
| Primary action | `#214F3C`, white text | `#DEF0AC`, dark text | One principal action in a context. |
| Discovery accent | `#DEF0AC` | `#364D31` | Selected navigation, a small illustrative highlight. |
| Teaching accent | `#EDE8F9`, `#64488E` text | `#383347`, `#D3BCED` text | Worked examples and explanation. |
| Positive result | `#E5F1E6`, `#2F714E` text | `#263F2C`, `#A9D4AC` text | Verified result state, with icon/text. |
| Attention/failure | `#FFF0E7`, `#9D452C` text | `#452F25`, `#F2B28F` text | A failed check or recoverable issue. |
| Form boundary | `#758374` | `#829680` | Stronger than purely decorative separators. |

Calculated text contrast for representative pairs is above 4.5:1: light main text/canvas 10.92:1, secondary text/work surface 5.08:1, primary button 9.34:1, positive result 5.03:1, and failure result 5.68:1. Proposed form-boundary pairs exceed 3:1. These calculations do not replace an audit of composed states, opacity, overlays, focus, or actual rendered text.

Retain the self-hosted Inter variable font initially. Use approximately 16 px task prose, 14–16 px controls/supporting text, and 12–13 px metadata; avoid putting required operational instructions in tiny captions. A 32–44 px page heading and 20–28 px task heading are enough without making every heading extremely heavy. Use a 4/8 px spacing base, 16–24 px component padding, 28–40 px between major sections, 10–12 px action corners, and 16–22 px main surfaces. Validate the resulting density on real phones and at 200% zoom.

## 2. Make each place have a clear purpose

The production shell should offer **Today, Path, Playground, My work, Progress**, with track discovery, documentation, and account/preferences in clearly accessible utility locations. In the prototype the active Path is named DevOps to make the proposed curriculum concrete; production must support all active track domains and keep the track library available.

On a phone, keep the five primary destinations accessible without horizontal page scrolling. Preserve text labels, a visible selected state, keyboard focus, and a minimum 44 px primary touch-target design target. Allow a filter row to scroll inside its own region when necessary. Do not shrink task text to fit a wide desktop layout.

| Place | Main learner question | Proposed composition |
| --- | --- | --- |
| Today | What is worth doing now? | One recommendation with a concrete outcome; time/device fit; a small amount of continuity; optional exploration. Existing progress has context, not a second competing dashboard. |
| Path | Where am I going, and what have I demonstrated? | Chapter groups, current next step, evidence and prerequisites, optional practical starting check, access to other tracks. Show upcoming content truthfully. |
| Playground | What can I practise or investigate? | Immediate activity choices; distinct examples/challenges/workspaces; compact filters; clear independent entry for practitioners; live availability when relevant. |
| Workbench | What do I observe, change, and submit? | Dedicated route, brief, evidence/tools, note area, finish line, original timer contract, meaningful check/result, explicit save state. Remove catalog blocks and continuous decorative motion. |
| My work | Where did my work go? | Account-owned activity groups containing attempts, notes, files, results, and named next actions. Distinguish resume, familiar review, and a new variant. Paginate summaries server-side. |
| Progress | What is becoming stronger? | Skill evidence and uncertainty, scoped activity XP, track coverage, useful habits. Separate these concepts instead of calling all points “verified ability.” |
| Account | Who am I here, and what is shared? | Identity, installation/workspace context, privacy, device/account preferences, session controls, clear access to help. Organisation features appear only with actual membership and permission support. |

Use the same nouns throughout: an **example** teaches, a **challenge** assesses a defined task, a **workspace** supports experimentation, and a **lab environment** supplies execution. A live environment is not automatically a harder task. A challenge can be demanding while using only small artifacts in the browser.

### Different activity presentations

- **Worked example:** illustration/book motif, number of steps, a learning outcome, “Study the example.” Use a narrow teaching surface with an optional anchored walkthrough.
- **Independent challenge:** scenario object, clear finish condition, difficulty/prerequisites, evidence/environment requirements, “Start challenge.” No implied walkthrough or full solution before an assessed attempt.
- **Free workspace:** editable artifact preview, tools/actions available, persistence policy, “Open workspace.” No invented scored completion.
- **Live lab:** target/environment object, setup and runtime states, availability, save/export/release controls. Explain whether the learner is looking at a target, an attack/workstation, or the application control plane.

Recommendations and discovery should reflect intent and skill separately. A job-focused practitioner can go directly to an intermediate independent case. An interest-led expert can explore a hard case or a new subject. Both can request instruction without being treated as globally inexperienced.

## 3. Give the objects meaning and life

Use an original small **trail companion** and a family of learning objects rather than several unrelated mascots. The prototype demonstrates a rounded field device carrying a flag beside a miniature service platform. It retains the mountain/journey theme without copying another platform's character.

| Object/state | Meaning and behaviour |
| --- | --- |
| Companion on Today | A small greeting or acknowledgement in one bounded scene. It does not wander behind text, follow the pointer across the page, or continuously request attention. |
| Evidence folder / case object | Opens into the selected investigation. Its saved/completed state represents the actual activity, not a decorative badge. |
| Deployment/service model | Shows client → edge → application → data. A connection animation follows a learner-triggered example or a real/simulated check, with that source visible. |
| Chapter marker / earned artifact | Changes after the milestone's authoritative evidence is recorded. It persists as a recognisable object and opens the evidence when revisited. |
| Incorrect check | A neutral, attentive state plus specific failed controls. No crying character, shame, XP loss invented by the animation, or fake success. |
| Queue/preparation | An environment object paired with the actual phase and recovery actions. Never show arbitrary progress percentages or fabricated green telemetry. |

Create a small state sheet for each object: default, hover/focus, active, working, success, attention, and reduced-motion equivalent. Reuse the same proportions, stroke style, palette, and direction of movement. Every visual state must still make sense when seen as a static image.

Initial delivery can use inline SVG and CSS transforms/opacity, with existing JavaScript coordinating state. There is no requirement for a 3D engine, image-generation service, animated video background, or model server. If a later hero needs Rive/Lottie or a canvas scene, compare asset size, accessibility fallback, lifecycle control, and measured frame cost before adding the dependency.

A **practice arena** should initially be an asynchronous collection of reviewed cases around a meaningful story—for example, “Release day” with diagnose, repair, and recovery cases. Show personal progress, required skills, estimated live time, and earned artifacts. It need not allocate a machine to every visitor or impose a launch-time race. Optional cohort comparison can come later with clear consent, comparable tasks, assistance policy, and fairness across time zones.

## 4. One event language for every interaction

Use the existing `AscendMotion` and `AscendFeedback` boundaries as the starting point. Consolidate event meaning and cancel obsolete animations; do not run a second independent effect layer over the old one. The inspected current Today page has nine continuous decorative animations plus two temporary glow animations. Preserve the useful tactile/reduced-motion foundations while removing competition for attention.

The durations below are proposed tokens. They are not copied wholesale from a competitor or claimed to be experimentally optimal.

| Event | Visual and motion response | State/accessibility contract |
| --- | --- | --- |
| Hover | Local surface/tone change, optional 1–2 px lift, about 120–160 ms. | Same essential information on keyboard/touch. No layout shift or pointer-only instruction. |
| Press | Small compression or colour acknowledgement, immediate to 100 ms. | Do not wait for animation before accepting the action. Preserve the hit area. |
| Route change | One destination entrance around 180–240 ms when useful. | Update URL/title/selected navigation; focus the destination heading on intentional navigation; preserve editor focus during background updates. Cancel stale transitions. |
| Filter/search | Update the local result region and count. | Keep filter focus, selected state, query, and back navigation understandable. A filter is not a task start. |
| Start assessed task | Replace preflight with the dedicated workspace and original timer. | Before starting, show brief/prerequisites/time policy; release active assessment material through the appropriate server contract. The prototype's client-only fixture is not a production security pattern. |
| Tour | First worked example may auto-open; later guidance is selective and always reopenable. Each step reveals its relevant evidence with visible Next/Skip controls. | Name the next operation, announce step changes, support Escape/keyboard, preserve focus, and avoid revealing an active independent challenge's solution. Finishing a tour does not itself prove learning. |
| Save | Stable “Saving…” → confirmed “Saved” with location/time. | A failed/offline save remains a draft with recovery/download actions. Autosave gets no celebratory animation. |
| Check running | Local busy state; actual phase if available. | Prevent duplicate requests, retain inputs, announce status, permit only supported cancellation. Do not imply CPU progress from elapsed time alone. |
| Check failed | Specific failed control, remaining observations, next test/help. | Distinguish conceptual results from environment/instruction errors. Preserve work and assistance history. |
| Fresh pass | Compact 250–450 ms confirmation on the affected object/result. | Apply the authoritative receipt first. Show evidence, actual reward delta, and a useful next action. No duplicate award or repeat “new achievement” animation after reload. |
| Milestone earned | A rarer scene/artifact transition around 600–1,000 ms, with an immediately usable Continue action. | Milestone evidence must be satisfied; animation is skippable and not a gate. Persistent achievement remains with motion disabled. |
| Streak extended | Small secondary acknowledgement. | Use configured timezone/04:00 logical-day/freeze rules. Avoid guilt or treating login frequency as competence. |
| Runtime waiting/preparing/ready | Real labelled phase, bounded offer, explicit start. | Queuing does not create an assessed attempt. A queue offer cannot end another task or start a VM without the learner's action. |
| Export/release failure | Error beside the environment, with retained-work/runtime state and retry. | Failed export may keep the runtime. Failed cleanup keeps owned inventory and capacity accounted for. Never show “released” before confirmation. |
| New content | Quiet new/revised label and a useful reason to try it. | No celebration or notification on every refresh; no claim that release recency makes content suitable. |
| Account/session change | Clear identity and loading boundary; rehydrate only the selected account. | Abort or ignore obsolete responses and effects. Do not briefly render another account's drafts, totals, or celebrations. |

A proposed event envelope can contain `event_id`, `account_id`, `attempt_id`, `content_version`, `event_type`, `evidence_authority`, `reward_delta`, and confirmed persistence/runtime state. Use a stable receipt identity for events that can be retried. Do not infer a new award by subtracting two unrelated dashboard totals or by adding a CSS class after a click.

Reward rendering should follow **recorded result → evidence summary → newly awarded amount → optional milestone → named next action**. Coalesce simultaneous pass/streak/chapter notifications so they do not compete. Restoring an old result presents a calm receipt. The server remains responsible for atomic/idempotent awards; front-end animation deduplication is an additional presentation concern.

Reduced motion must disable decorative transforms, path travel, counters, particle bursts, and character loops while retaining every status and action. Follow both operating-system and explicit device preferences. Stop offscreen/hidden-tab scenes. The working surface has no continuous background animation. Sound/haptics, if ever introduced, are opt-in and unnecessary to understand a result.

## 5. Rewards that support progress

The competitor audit found different systems: HTB Academy Cubes are access currency, Codewars rank differs from Honor, DataCamp XP represents engagement, and Duolingo's social/league systems have their own rules and privacy choices. These cannot be treated as one universal “XP system.”

Preserve Ascend's existing reward contracts during the redesign:

| Current activity | Presentation rule |
| --- | --- |
| Worked example | Acknowledge learning and offer independent application. Current policy gives no assessment XP. |
| Fresh quick practice | Show the actual award: currently 10 XP per eligible family/day, within a 30 practice-XP daily cap. Continued practice remains available after the cap. |
| Standalone challenge | Show its authored first-solve award, currently 25/50/100 by band, using the stable reward identity. Familiar/revealed repeats cannot create another first-solve award. |
| Track assessment | Preserve its existing timer/correctness scoring and original attempt. A visual redesign does not reset a score or silently turn continuous assessment timing into a pausable session. |
| Hosted/local practice | Show the actual evidence authority and result. Current hosted checks give zero XP and do not automatically verify a track milestone; manual/local observations are weaker evidence. |

The present profile can show “10 Verified XP” and “0 Verified tasks” after a quick solve because those metrics count different things. Replace ambiguous totals with scoped labels and a nearby explanation: track assessment XP, practice/challenge XP, assessed track tasks, independently demonstrated skill evidence, and practice rhythm.

Add meaningful rewards through a completed artifact, a recoverable service, a chapter stamp with its supporting evidence, a portfolio item, and a useful follow-up. Cosmetic companion accessories or arena artifacts can later acknowledge milestones without improving grades, increasing execution permissions, or advancing lab-queue priority. Keep assistance usable; record assisted outcomes accurately instead of shaming users for requesting help.

Do not introduce a spendable currency, loot box, paid retry, or mandatory leaderboard to make the product feel alive. These would add policy/economic complexity without addressing the current problems. Advanced users need fresh, substantial cases and contribution opportunities as much as polished celebration.

## 6. Keep challenges continuous through content operations

The current catalog has 37 activities and only one hard activity. A visual redesign cannot make it an endless expert curriculum. Start with the adaptive proposal's two-family ladder and the DevOps service story; grow a reviewed supply of distinct cases.

Each content item needs an owner, skill/prerequisite map, goal relevance, authored difficulty dimensions, public brief, private rubric, fixture/version identity, assistance policy, variant relationship, time/setup estimate, environment resource envelope, evidence authority, reward key, and retirement policy. A changed port/name alone is not a new transfer challenge.

Use this publishing pipeline:

1. **Draft the learning outcome and finish line.** Include one plausible wrong route and a useful control. Decide whether the task teaches, assesses, or supports open experimentation.
2. **Build/reference-check the fixture.** Test solvability, alternative valid solutions, negative controls, ambiguity, payload bounds, and answer leakage. Keep public metadata from diagnosing a mystery.
3. **Validate the environment.** Pin runnable sources/images, review licensing and allowed actions, measure resources, and verify cleanup before enabling a hosted recipe.
4. **Review language and accessibility.** Test whether a learner can identify the action/output/save location. Include novice and experienced backgrounds where appropriate.
5. **Publish an immutable version.** Existing attempts keep their original fixture, timer, help/reveal state, and reward identity. Publish a concise change note and surface the new item to suitable learners.
6. **Observe and revise.** Separate confusion, technical failure, repeated familiarity, and difficulty mismatch. Retire broken recipes safely while preserving saved work/history and explaining availability.

A proposed initial cadence is a small fortnightly case release only when editorial capacity supports it, monthly link/version checks, and a deeper quarterly curriculum review. Security/upstream breakage can trigger immediate temporary unavailability. These are operating commitments to staff and measure, not an automatic promise to learners before the content exists.

Community contribution begins with data-only variants, tests, explanations, and translations reviewed by a named maintainer. Give contributors attribution and reputation separate from assessed learner competence. A contributor's rank does not grant the ability to publish arbitrary executable code to the runner. Mentor/reviewer flows require real capacity, permissions, moderation, and a response expectation.

## 7. Accounts, organisations, and continuity

Current Ascend supports a local learning account or server-created username/password accounts. The audit's disposable two-account check found no saved-history leakage. Self-service registration/recovery, invitations, organisations, and team administration are not present simply because a profile page exists.

Design personal identity and organisational membership separately. A person can change goals or join/leave a cohort while retaining their own learning history. Membership does not silently disclose private drafts. Shared payment or a classroom must not require shared learner credentials.

| Role/context | Intended scope if implemented |
| --- | --- |
| Learner | Own attempts, notes, evidence, preferences, opt-in portfolio, and own active runtime. |
| Assigned reviewer/mentor | Explicitly submitted work and the relevant rubric; not all private drafts or unrelated activity. |
| Instructor/cohort manager | Assignments and consented cohort progress within membership scope; distinguish engagement metrics from verified outcomes. |
| Organisation administrator | Membership/invitations and organisation settings; additional access to learner work must be explicit and justified by the product's permissions. |
| Content maintainer | Draft/review/publish approved content through the authoring pipeline. This is separate from infrastructure operation. |
| Installation/runner operator | Capacity, enabled recipes, operational health, cleanup/reconciliation. Avoid embedding learner-content access in ordinary operator UI permissions. The machine owner remains technically trusted. |

Start implementation with truthful current identity, installation name, logout/session-expiry recovery, and saved-state boundaries. Account recovery requires an actual identity-verification mechanism. Do not ship a form that appears to recover access but cannot do so safely.

If organisations are added, use stable account and membership IDs, scoped endpoints, ownership checks, invitation states/expiry, audit events, and explicit role changes. Back membership badges and workspace switching with real authorisation. Keep account-level learning history distinct from organisation-specific assignments and reports.

The current workspaces have different recovery stores: hosted drafts are in-memory, Playground drafts use sessionStorage, and track drafts use localStorage. Unify the **language and save state**, then the implementation where appropriate. Show “draft in this tab,” “saved on this device,” and “saved to your account” only when each is true. Before logout, explain pending saves and allow a download/retry. On a shared device, offer deliberate clearing of local recovery data without silently deleting unsynced work. Exclude personal/API data from shared service-worker caches.

Theme/motion can remain device preferences, with a future account default. Operating-system reduced motion wins. Cancel pending save status messages, reward reactions, and stale fetches when account identity changes; an old request completing must never update the new user's view.

## 8. DevOps: deployment as one evolving project

The later [Infrastructure & Internet Operations domain design](infrastructure-internet-domain-design.md) extends this foundation into nine sequential tracks covering VM host administration, Internet publishing, private access/tunnels, mail, capacity, constrained devices and a college-style private cloud. Its device profiles use the user's newer server/PC assumptions, and its capability mapping should reuse the foundation's shared work.

The [full DevOps design](devops-track-design.md) audits KodeKloud, TechWorld with Nana, Killercoda, and official Docker/GitHub/Kubernetes/OpenTofu/Terraform/Ansible/Prometheus/SRE teaching material. It uses **Relay**, a small synthetic-data service, through these 13 levels:

| Phase | Levels and concrete result |
| --- | --- |
| Understand and operate | Follow a request; operate a Linux host; build a versioned release; run a reliable service. The learner can identify the process, artifact, configuration, and state. |
| Make a real release | Deploy behind a secure edge; package with containers; test every change in CI; release and roll back. The learner can trace an artifact into a controlled target and recover a failed version. |
| Reproduce and observe | Recreate infrastructure; observe service health; protect and recover data. The learner can reason about state, drift, useful service signals, secrets, and a tested restore. |
| Integrate | Deploy the stateless service to Kubernetes; operate the capstone. The learner produces a release record, incident/recovery evidence, and a usable handover. |

The proposed core work is **84–111 hours**, subject to learner validation and separate setup/download/account estimates. It provides substantial deployment foundations; it does not claim expertise in every cloud or tool. Teach one representative tool per function, then offer translations and advanced branches such as GitOps, other CI systems, multi-cloud identity, stateful services, and production-scale orchestration.

The capstone ships Relay v2 through CI into a learner-owned disposable target, promotes the tested immutable artifact, detects a supplied regression, restores the required behaviour, proves the required data survives, and hands over a runbook. A passing pipeline, uploaded screenshot, or green `/health` alone cannot satisfy the entire capstone.

Do not describe writable SQLite replicated across containers as a production HA design. Introductory blue/green and Kubernetes exercises use a stateless/read-only mode; a PostgreSQL-backed stateful branch can later teach the additional guarantees and recovery problems.

The prototype's example shows a same-host upstream port mismatch. Its independent case adds a separate private app host and a requirement to preserve blocked public access, so simply copying the example's loopback/port fix fails. These are interaction fixtures, not calibrated evidence that the proposed 20-minute difficulty estimate is correct.

### Concrete workspace integration

The existing pack schema supports proficiency levels, M/L milestones, prerequisites, material links, checkpoints, and existing verifier types. It expects 8–15 main levels, so the proposed 13-level structure fits. A six-level development slice should be tested as a draft and not published as an invalid full proficiency pack.

Three integration gaps require implementation beyond a TOML/catalog entry:

- Material packaging currently assumes the cyber materials root. Add a domain-neutral packaging boundary and an inspectable DevOps material tree for Relay/configs/tests/fixtures.
- Parsed nodes have no general recipe binding or native `devops` verifier. Define a versioned link between an authored requirement and the accepted evidence contract in the shared application/catalog layer or validated schema.
- Current lab detail explicitly says it does not satisfy track evidence. Implement and test any new verifier authority before a lab receipt can complete a verified milestone or earn its assessment award.

The proposed path includes nine candidate recipes; their identifiers in the curriculum are design entries, not runnable capabilities. Review and measure the first restricted edge-route and stateless release-switch adapters before enabling them. Arbitrary Dockerfiles, CI scripts, SSH administration, infrastructure apply, and cluster-admin work belong on learner-owned disposable environments or a separately designed stronger isolation boundary.

## 9. Keep the environment affordable

The owner confirmed **at most two simultaneous hosted labs**, with an 8 GB RAM / four-core / 80 GB disk planning baseline. Keep the main web process separate from the privileged runner boundary. Use browser/artifact work and bounded evaluators for inexpensive practice; allocate a live environment only for the required execution phase. Browser delivery does not automatically mean all work runs on the learner's machine.

Build on the [current runner](server-lab-runner.md) and the [adaptive proposal's resource accounting](adaptive-playground-proposal.md). Current operations serialize behind one worker/global operations lock; a cold image launch can delay another learner's check. A deliberate provisioning lane, ordered per-run mutation handling, resource reservations, and a fair admission queue are prerequisites for a polished multi-user live experience.

The UI should preserve the selected challenge when full, show real availability, and offer a similarly demanding browser/local alternative. Starting, stopped, and cleanup-failed resources still consume their relevant reservations. Preserve the two-hour absolute lifetime and the 10 GiB free-space reserve; queuing does not pause an already started scored attempt.

New DevOps targets are proposed engineering envelopes: an edge-route exercise around 256 MiB / 0.75 CPU and a stateless release-switch exercise around 384 MiB / 1.25 CPU, including bounded checking work. They are not measured allocations. Check the complete recipe pair, transient startup cost, control-plane/host headroom, cache/disk use, and cleanup on the intended host. Two countable slots do not guarantee any arbitrary pair of recipes can run together.

The UI's illustrations, object transitions, and personal arena state should not consume a hosted slot or need a server-side rendering/model service. Keep most motion in the browser and static assets cacheable. Retain small text/config/result artifacts rather than persistent per-learner desktops or full VM disks by default.

## 10. Implement in reviewable increments

Another session is editing this shared workspace. This design creates new artifacts and leaves those implementation changes intact. Before each production milestone, re-read the current contracts, work from an isolated checkout/worktree when necessary, and integrate targeted changes rather than replacing whole files with this prototype.

| Order | Deliverable | Acceptance gate |
| --- | --- | --- |
| **0 — complete** | Audits, integrated visual/interaction direction, DevOps curriculum, standalone prototype. | Sources and limitations recorded; representative prototype interactions verified. |
| **1 — trustworthy state** | Scoped metric labels, explicit save-status model, event/receipt identities, account-switch cancellation, bounded history summaries. | No false saved state, mixed-account result, duplicate award, or ambiguous metric scope in tested success/failure/reload paths. |
| **2 — base UI and navigation** | Shared tokens, light/dark shell, typography, surfaces, touch/focus states, primary navigation, track/docs access. | Representative routes remain readable at 360/390/768/1440 widths and zoom; no route/state regressions; selected context and primary action are clear. |
| **3 — activity and workbench patterns** | Distinct example/challenge/workspace/lab selection; brief-before-start; focused tours; evidence/notes/results; My work. | Correct foreground/timer/reveal rules, real saving locations, one named continuation, keyboard/back-navigation and failure recovery. |
| **4 — purposeful motion and identity** | Original SVG scene/companion system and one event coordinator; remove competing background effects. | Static/reduced-motion equivalents; no celebratory effect before a confirmed event; no infinite decorative workbench motion; no duplicate reward replay. |
| **5 — adaptive practitioner entry** | Goal/background choice, optional practical starting check, direct intermediate entry, too-easy/transfer-aware recommendations and first case ladder. | Beginner and experienced flows fit their evidence; technical/confusion signals do not lower ability; finite novelty is honestly labelled. Reuse the adaptive proposal's gates. |
| **6 — DevOps foundation and local loop** | Relay source/materials, packaging integration, foundational examples, Linux/edge/container deployment tasks. | Actual disposable local execution and recovery; clear rubrics; proper pack validation; no incomplete capability silently marked verified. |
| **7 — reliable hosted practice** | Shared admission/scheduling work and first two reviewed DevOps adapters. | Resource/account limits, responsive existing-run operations during cold starts, fair queue, timeout/expiry/export/cleanup/restart checks. |
| **8 — DevOps integration and capstone** | CI/CD, IaC, observability, secret/data recovery, Kubernetes fundamentals, capstone and advanced branches. | Real learner-owned environment tests and explicit evidence authority; tested artifact promotion and recovery; setup/effort estimates reviewed with learners. |
| **9 — content and optional community/accounts** | Reviewed release cadence, asynchronous arenas, contribution review; self-service/organisation flows as separately scoped capabilities. | Real permissions and reviewer capacity, private-progress preservation, consented sharing, comparable competition rules, no arbitrary execution publishing. |
| **10 — release validation** | Representative learner sessions, accessibility, realistic web/runner load, documentation and rollout controls. | Meet declared usability/state/performance gates and publish remaining limitations before wider promises. |

Keep the current Python/shared application architecture and progressively modularise the vanilla UI. There is no demonstrated need for a framework migration to deliver this design. Separate tokens, primitives, route composition, activity-specific tools, and event presentation. Keep logical state in application APIs, not embedded in animation callbacks. Use versioned static assets and a controlled rollout that cannot serve incompatible schema/script combinations.

### Validation that matters

The prototype's isolated browser review covers tours, saving/export, two sample accounts, incorrect/correct/replayed results, timer continuity, foreground conflicts, lab waiting/offer/expiry/release, search, skip links, dark mode, and reduced motion. Production implementation must additionally test server authority, authentication, concurrent requests, real network failures, and actual runtime evidence. Prototype JavaScript is not a production verifier or account system.

Run task-based sessions with beginners and regular/advanced practitioners across employment and interest motives. Ask them to identify the next action, finish condition, save location, reward meaning, and environment state without coaching. Observe where they hesitate; animation preference alone is not a measure of learning.

Use proposed performance targets such as INP under 200 ms, CLS under 0.1, and LCP under 2.5 seconds on an agreed device/network. Track added asset cost, long tasks, offscreen animation, and physical-phone readability. Test ordinary API use alongside two representative hosted labs; treat client counts and latency limits as measured release gates, not deductions from small recipe memory samples.

Measure fresh transfer, repeated confusion, too-easy/too-hard reports, recommendation overrides, substantive return sessions, and practitioner novelty coverage. For job preparation, review the quality and reproducibility of actual work samples. Keep XP, attendance, and course completion available as context without presenting them as professional competence.

Public research captures currently live under Git-ignored `docs/screenshots/`. The design prototype, source ledgers, and selected prototype previews are separate durable artifacts under `docs/design/`. If this research is later committed/exported with all screenshot links, explicitly include the intended evidence captures; do not change the repository's general screenshot policy as a side effect of a design task.
