# Platform UI, interaction, rewards, and continuity audit

Reviewed **2026-11-03** as an extension of the [eight-platform learning audit](adaptive-playground-platform-audit.md). This review informs Ascend's whole product shell, visual identity, practice experience, and future DevOps learning surfaces. It does not implement a redesign or change rewards.

The strongest direction is **a calm, legible work surface with a small number of expressive, stateful objects**. Distinctive illustration, tactile controls, clear navigation, and meaningful completion feedback can make the product feel alive. Animating every card or turning every result into a celebration would undermine the focused work that practitioners need.

## Evidence and scope

- **Observed:** public pages inspected using Chromium at **1440 × 1000** and **390 × 844**, selected hover/press interactions, catalog/tab navigation, DOM styles, and screenshots. Direct product-page visual coverage succeeded for PortSwigger, TryHackMe, HTB Academy, Codewars, Exercism, and Duolingo.
- **Documented:** first-party help pages describing rewards, lesson completion, accounts, progression, content, and interactions that require a signed-in account. This is not the same as personally triggering those events.
- **Historical:** dated design/engineering articles, particularly Duolingo's character, streak, family-plan, and league descriptions. They explain design decisions; older subscription benefits and event rules must not be assumed current.
- **Proposed:** the Ascend adaptations and motion timings in this document. These are design hypotheses and implementation requirements to test, not copied competitor measurements.

HackerRank and DataCamp's training pages returned **403** in the browser used for this review, although ordinary HTTP retrieval had provided readable product/help content. Their live hover, transition, and completion effects were **not verified**. Codewars initially timed out waiting for page load, then rendered on a normal retry. No access controls were bypassed, accounts created, target labs started, purchases made, or messages sent. Authenticated dashboards, success animations, and organisation administration were not comprehensively exercised on any competitor.

The [evidence ledger](platform-ui-motion-sources.json) records source URLs, dates, access limits, browser observations, and screenshot hashes. Captures in [the screenshot directory](../screenshots/platform-ui-audit/) are research evidence; competitor characters and artwork are not proposed Ascend assets. Programmatic focus samples are not a complete keyboard-accessibility audit. CSS animation samples do not capture every canvas/video/JavaScript animation.

## Visual and navigation comparison

| Platform | What was observed or documented | Useful lesson for the whole Ascend UI |
| --- | --- | --- |
| **PortSwigger** | **Observed:** white canvas, orange accent, plain readable typography, separate global and Academy navigation, topic-based content, strong title/brief hierarchy, restrained borders. A public lab brief has a breadcrumb, level, explicit solve condition, access action, and collapsed solution panels. The Academy page visibly promotes new material. [Desktop](../screenshots/platform-ui-audit/portswigger-1440.png), [mobile](../screenshots/platform-ui-audit/portswigger-390.png), [lab brief](../screenshots/platform-ui-audit/portswigger-lab-brief.png). | Make the learning hierarchy and task brief understandable without decorative assistance. Large site menus should not be repeated inside a running exercise. Its denser global navigation is not a template for a small app. |
| **TryHackMe** | **Observed:** dark navy hero, lime primary action, expressive floating character, a contrasting light content area, icons plus text navigation, and background-based filters: “Starting from scratch,” “Already know the basics,” “Upskilling for experts.” Mobile stacks actions and illustration. A cookie overlay occupies substantial mobile space. [Desktop](../screenshots/platform-ui-audit/tryhackme-1440.png), [mobile](../screenshots/platform-ui-audit/tryhackme-390.png), [filter selection](../screenshots/platform-ui-audit/tryhackme-interaction.png). | Give characters one deliberate region and place real choices near them. Make experienced entry explicit. Keep transient banners from covering core work or consuming most of a small viewport. |
| **HTB Academy** | **Observed:** dark layered surfaces, large white headings, lime action emphasis, illustrations overlapping otherwise quiet cards, clear job/skill choices. Selecting “Master new skills” scrolls to and selects the Skill Paths section. At narrow width the header becomes a menu and content stacks. [Desktop](../screenshots/platform-ui-audit/htb-1440.png), [mobile](../screenshots/platform-ui-audit/htb-390.png), [skill selection](../screenshots/platform-ui-audit/htb-interaction.png). | Illustration can supply identity without heavy borders on every container. Make a card's destination predictable and preserve the selected context. A large atmospheric marketing hero is unsuitable above every daily workbench. |
| **HackerRank** | **Documented/public HTML:** Prepare, Certify, Compete navigation; time-based preparation kits; topic/status/difficulty filters; problem test results and scoring. Live training-page layout and transitions were blocked in this browser. [HR-PREP], [HR-PRACTICE], [HR-SCORE] | Separate finding a problem from solving it. A clear evidence/test panel is more useful during execution than a game-themed catalog. Do not infer animation or current spacing from the text-only evidence. |
| **Codewars** | **Observed:** dark textured marketing canvas, coral/red emphasis, floating language tiles, restrained corner radii, large typographic hierarchy and one prominent Get Started action. **Documented:** the trainer/library and solving UI serve different purposes. [Desktop](../screenshots/platform-ui-audit/codewars-interaction.png), [mobile](../screenshots/platform-ui-audit/codewars-390.png), [CW-TRAIN], [CW-SOLVED]. | A recognisable motif and accent can provide character without adding a mascot to every screen. Keep the editor, tests, and result explanation visually quiet. The moving language-tile hero is inspiration for discovery surfaces only. |
| **Exercism** | **Observed:** pale neutral surfaces, purple action/navigation accents, strong dark type, a persistent language header, About/Learn/Practice tabs, language/exercise illustrations, and status filters above a two-column exercise catalog. Practice is a separate URL and selected tab, not an overlay on the welcome section. [Track](../screenshots/platform-ui-audit/exercism-1440.png), [practice catalog](../screenshots/platform-ui-audit/exercism-interaction.png), [mobile](../screenshots/platform-ui-audit/exercism-390.png). | Especially useful for Ascend: stable context, distinct page roles, compact illustrated identity, and different exercise states. Teaching examples and independent challenges need recognisable purpose, not just identical cards with different labels. |
| **DataCamp** | **Documented/public HTML:** role-oriented career tracks, narrower skill tracks, browser exercises, progress displays, and targeted assessment recommendations. Current help explains profile/course/team XP views. Live training-page layout and transitions were blocked. [DC-TRACKS], [DC-XP] | Make role progress, course progress, and activity points separate views with named scope. Avoid displaying a number without explaining whether it is lifetime, course, or recent team activity. No claim about live animation is made here. |
| **Duolingo** | **Observed:** sparse white background, expressive animated character composition, large friendly type, a single primary action and secondary existing-account action; raised rounded buttons. Mobile places illustration, promise, then full-width actions. Get Started opens a separate “I want to learn…” subject-selection page. **Historical design evidence:** characters communicate personality and milestone transformations. [Desktop](../screenshots/platform-ui-audit/duolingo-1440.png), [mobile](../screenshots/platform-ui-audit/duolingo-390.png), [onboarding](../screenshots/platform-ui-audit/duolingo-onboarding.png), [DU-MOTION], [DU-CHARACTER]. | Use a recognisable original companion and a small visual vocabulary. Preserve generous hierarchy and responsive action placement. A professional practice platform can be warm without making the editor or failure feedback theatrical. |

These observations support evolving Ascend's current neobrutalist treatment: retain tactile emphasis on important controls, but reduce repeated heavy borders, hard shadows, equal-weight panels, and decorative motion across the base UI. The useful distinction is between an expressive discovery surface and a precise work surface. The evidence does not prove one palette or illustration style is universally best.

## Sampled interactions and transitions

The values here are **observed samples of named public controls**, not global platform design tokens:

| Interaction | Direct observation | Ascend implication |
| --- | --- | --- |
| Duolingo Get Started press | The anchor's computed transform changed from zero vertical translation to **4 px downward** while pressed. The raised visual treatment gives a physical response. | A small press response can make primary controls tactile. It must not move adjacent layout or delay navigation. |
| PortSwigger Login hover | The sampled outline control changed to a dark fill; computed hover transition declared **200 ms** for background/color. | Hover can confirm interactivity with a modest surface change. Equivalent clarity must exist for keyboard and touch users. |
| TryHackMe Join for FREE hover | The sampled button changed colour/fill over a declared **200 ms** transition. | Prefer local colour/elevation changes over page-wide effects on pointer movement. |
| TryHackMe experience tab | Clicking “Already know the basics” changed the selected tab in place and retained the page route. | Filters should acknowledge selection, explain the resulting set, and preserve context. Do not confuse them with starting an activity. |
| HTB skill-route card | Clicking the skill card changed the URL fragment, scrolled to the catalog area, and selected “SKILL PATHS.” | Large cards need a coherent destination. Avoid a card click that changes an unrelated region without locating the user there. |
| Exercism Practice tab | Opens `/tracks/python/exercises`, retains the language header, and visibly marks Practice selected. | A dedicated task/catalog route can preserve orientation while replacing the page content. This directly informs the owner's request that Start open a distinct working page. |
| PortSwigger View all labs | Opens the all-labs catalog as a separate page. | Navigation remains navigation; the work page should not keep the launcher's full category blocks above the actual task. |
| Codewars Get Started hover | The sampled CTA declares a **200 ms opacity transition**. This sample does not establish all other hover effects. | Keep simple transitions predictable and cheap to render. |

HTB's public page also exposed finite entrance animation and long decorative loops in a sampled animation inventory; TryHackMe exposed a looping illustration animation. Those observations demonstrate that richer landing-page motion can coexist with ordinary cards. They do not justify permanent decorative animation during terminal/editor work.

## How completion, XP, rewards, and motivation differ

| Platform | What the sources establish | Important distinction or pressure pattern |
| --- | --- | --- |
| **PortSwigger** | Academy progress, lab completion, topic progression, mysteries, and certification preparation are documented. [PS-PREP] | No spendable XP economy or exact completion animation was established in this audit. A visible completed state can be motivating without points on every interaction. |
| **TryHackMe** | Correct answers and room difficulty feed points/levels. Current points documentation distinguishes walkthrough/challenge credit and monthly/all-time boards. Leagues add promotion/demotion, ranked rewards, and incentives for new content. [TH-POINTS], [TH-LEVELS], [TH-LEAGUES] | Monthly standing and permanent history are different measures. First-completion races and inactivity demotion create pressure; they are a poor default for a two-slot service or someone practising around work. |
| **HTB** | Academy **Cubes are access currency**, separate from Labs' challenge/season points. Modules above Tier 0 use Cubes; some are earned progressively while answering questions. Academy documentation explicitly says they are not all granted instantly at module completion. Active/retired Labs challenges and Seasons have their own rules. [HT-ACADEMY], [HT-MODULES], [HT-CHALLENGES], [HT-SEASONS] | Do not turn Ascend's existing XP into paid lesson currency, or animate a module-end award that the server has not actually granted. Scarce lab access must not depend on XP rank. |
| **HackerRank** | Practice badges/points, test-case scores, and rated-contest standing are separately documented. Unlocking an editorial can affect practice progress credit. [HR-SCORE] | A test pass, a practice badge, and a competition rating establish different things. No live “accepted” animation was personally exercised. |
| **Codewars** | The documented loop is green test output → submit solution → rank/Honor progress → satisfaction feedback/discussion/solution review. Rank concerns completed kata difficulty; Honor also recognises contribution and community activity. [CW-SOLVED], [CW-RANK], [CW-HONOR] | Completion can open a useful next learning action, not just a reward modal. Contribution reputation should not be reported as practical skill mastery. |
| **Exercism** | Reputation recognises mentoring, publishing solutions, writing/updating exercises, and code/documentation contribution. It cannot be spent; thresholds can permit more contribution. [EX-REPUTATION] | Mature participation offers experienced users work beyond repeated exercises. Privilege systems still require review and account authorisation; a point total alone is not a reason to grant arbitrary execution permissions. |
| **DataCamp** | XP measures learning engagement. Current help says completed exercises do not give repeat XP, hints/solutions can reduce/remove task XP, lifetime XP persists, and there is no special whole-course XP bonus. A course statement of accomplishment is separate. XP cannot buy content/subscriptions. [DC-XP], [DC-FINISH], [DC-CURRENCY] | Distinguish a completion celebration from an extra award. Ascend's existing assistance policy need not copy DataCamp's hint penalty; help should remain usable without misleading mastery claims. |
| **Duolingo** | Historical articles describe weekly leagues, Friends Quests, shareable streak milestones, and character transformations; the league article includes an opt-out through profile privacy. [DU-LEAGUES], [DU-QUESTS], [DU-MOTION] | XP competition, streak continuity, and language competence are different. Do not hard-code old XP amounts, premium benefits, or league rules from historical articles. Make optional social play separable from privacy and study access. |

The most useful reward is often **evidence of an ability the learner now has**: a corrected deployment, a passing regression, a recovered service, or a useful explanation. XP can acknowledge activity; a badge can mark a milestone; a companion can celebrate. None should replace the result explanation.

### Completion sequence to adapt for Ascend

1. Submission enters a visible checking state; the workspace and saved draft remain intact. A clicked button is not a pass.
2. The authoritative result arrives. Show exactly which conditions passed, what remains wrong, and the evidence scope.
3. If a new reward was actually recorded, show the exact award and its reason once. A replay, retry, restored tab, or duplicate event must not imply another first-solve award.
4. Use a small local success response for a normal task. Reserve the larger companion/environment response for a real milestone or first achievement.
5. Offer a named next step: changed-condition case, next deployment stage, targeted example, or saved-work review. The user can also stop with a clear saved state.

For a failed test, identify the failing condition and a useful next experiment. Avoid mockery, angry characters, screen shake, or a celebration that covers the error. Queue delays, network errors, and service outages must not look like a skill failure or cause reward pressure. Duolingo's separate [outage/streak engineering article][DU-OUTAGE] is relevant precedent for treating infrastructure failure differently from learner inactivity.

## Making the product feel alive without distracting from work

Duolingo's streak-design account describes exploration, readable transformations, animation timing, and a shareable artifact. Its character article describes designing performance around a short story and consistent personality, even when the production pipeline uses 3D. [DU-MOTION], [DU-CHARACTER] The implication is **state, intent, and continuity**, rather than simply adding a looped animation.

Proposed Ascend character and environment rules:

- Create an **original** companion tied to Ascend's identity. Define a small set of understandable states: welcoming, explaining, thinking/checking, celebrating, and pointing to recovery. Make it optional and quieter for experienced users.
- Give it one bounded home on Today, track introductions, an empty state, or a milestone summary. Avoid a floating overlay that follows the pointer or obscures a terminal.
- Let an arena or landscape reflect **real learning state**. For DevOps, a small app/service/deployment scene can visibly connect build, release, health, and recovery milestones. A failed health check should change the relevant service node, not turn the entire page red.
- Separate illustration from live telemetry. A decorative pipeline must not imply that a server is running, a deployment succeeded, or a lab is available unless the application state supports it.
- Preserve identity across sessions through saved progress and the learner's work. A character appearing in a new random pose is less meaningful than a completed system stage remaining visibly completed.
- Treat arenas as optional visual ways to browse the same track/catalog. Supply a straightforward list/table view and a clear next action. Avoid mandatory spatial puzzles merely to locate a lesson.

### Proposed event and motion specification

These are initial Ascend implementation targets, **not competitor timings**:

| Event | Visual response | Accessibility and state rule |
| --- | --- | --- |
| Hover | Brief accent/surface change, optionally a subtle local lift; roughly 120–180 ms. | No essential information appears only on hover. Maintain visible keyboard focus. |
| Press | Small tactile compression, roughly 80–120 ms or immediate feedback. | Never shift surrounding layout; do not delay the action until animation ends. |
| Route or tab change | Content replacement with a short 160–240 ms transition if useful. | Announce title/selection, move focus deliberately, preserve back navigation and scroll where appropriate. |
| Saving | “Saving…” then timestamped “Saved” or actionable failure. | Only acknowledge persistence after confirmation. Reduced motion uses the same textual state. |
| Long preparation/check | Real stage label and bounded progress when available; otherwise a clear indeterminate indicator. | Avoid invented percentages or a fake 99% wait. Preserve cancel/retry semantics and distinguish queue from provisioning. |
| Normal correct result | Local check/result emphasis, roughly 250–450 ms. | Keep results and next action immediately usable. Do not auto-play sound. |
| First solve / meaningful milestone | One short companion/environment vignette, about 0.8–1.5 seconds, alongside the result. | Skippable/nonblocking; static equivalent under reduced motion. Replay is a deliberate viewing action, not another reward. |
| Incorrect result | Highlight the relevant evidence or failing test, then a clear recovery action. | No flashing or shame-driven character reaction. A colour change alone cannot communicate the problem. |
| New content | A small “New” label with version/date and why it is relevant. | Opening a panel clears its unread state, not its learning completion. Do not manufacture scarcity. |
| Lab lease nearly over | Persistent, readable remaining-time/status message with save/export actions. | Avoid repeated toasts or alarm effects; never reset the actual lease because an animation or tab changed. |
| Offline / expired session | Show last confirmed state and a safe recovery route. | Protect drafts, clear other-account caches, and do not show local optimistic success as a verified pass. |

Use CSS transforms/opacity and small SVG state changes for the first implementation. A vector animation runtime can be considered for complex authored vignettes after measuring bundle cost; a general WebGL scene is not needed merely to make cards look alive. Pause decorative loops when offscreen or when the tab is hidden. Honour reduced motion, keep sound opt-in, and retain text/status equivalents. These are client-side concerns; they do not consume another hosted lab slot, though bandwidth, battery, and main-thread performance still matter.

## Keeping challenges continuous and content fresh

| Platform mechanism | Evidence | Adaptation for Ascend |
| --- | --- | --- |
| PortSwigger publishes new research topics/labs while retaining topic study and mystery practice. | Current public Academy page and preparation guidance. [O-PS], [PS-PREP] | A small “New investigations” area can coexist with the learner's current track and saved work. |
| TryHackMe separates paths, rooms, difficulty, and new-content scoring. | Current public filters and points/levels help. [O-TH], [TH-POINTS], [TH-LEVELS] | New content needs a meaningful level/skill match. Avoid using release recency as proof that an exercise is better for this learner. |
| HTB releases weekly seasonal machines and maintains active/retired content rules. | Seasons and Challenges documentation. [HT-SEASONS], [HT-CHALLENGES] | A recurring authored case can provide shared interest, but allow asynchronous participation and preserve archived learning. Two slots cannot fairly support a launch-time speed race. |
| Codewars expands through community authoring, translation, and review. | Authoring and Honor documentation. [CW-AUTHOR], [CW-HONOR] | Later allow reviewed variants and test contributions. Keep content review, solvability, resource bounds, and licensing as real gates. |
| Exercism combines practice, mentorship, and contribution. | Reputation, practice-mode, and mentoring sources. [EX-REPUTATION], [EX-MODE], [EX-MENTOR] | Let practitioners review a solution or improve an exercise after solving; do not present every learning session as a new beginner lesson. |
| HackerRank combines finite curated preparation with independent practice and events. | Kits, filters, and contest listing. [HR-PREP], [HR-PRACTICE], [HR-CONTEST] | A preparation plan can have an end while practice continues. Do not imply the finite kit itself is an endless adaptive content stream. |
| DataCamp connects assessment, recommendations, practice, and new courses/projects. | Signal and XP guidance. [DC-SIGNAL], [DC-XP] | Reassessment should point to a useful next task. A new content item should identify the gap or curiosity it serves. |
| Duolingo combines path study with practice, social quests, and milestones. | Current Practice tab and historical feature articles. [DU-PRACTICE], [DU-QUESTS], [DU-MOTION] | Keep on-demand practice available when no milestone is due. Make return visits meaningful through review/transfer, not only attendance rewards. |

Ascend needs a content lifecycle: **draft → validate → publish → revise → retire/archive**. Each task retains a stable identity and version, evidence rubric, novelty family, and reward key. Freeze an attempt to its original version. Publish a short change note when requirements change; a revised lesson does not silently invalidate old verified work. Retired unsafe/broken content should explain its replacement and preserve the learner's history.

Use a sustainable release promise, such as a small reviewed case batch once the team can reliably author and verify it. Do not launch a mandatory weekly season before there is a content pipeline. Cosmetic renaming is not fresh practice. A content budget and a maintenance owner are as necessary as a motion designer.

## Accounts, teams, and progress ownership

| Platform | Evidence and limit | Ascend lesson |
| --- | --- | --- |
| **PortSwigger** | Public navigation distinguishes sign-up/login/account from open learning material; account-scoped Academy progress is described. Internal organisation administration was not inspected. | Allow browsing without implying saved personal progress. On save/start, make the actual account context clear. |
| **TryHackMe** | Current teams help documents team membership, owner controls, shared room scoring, and consequences of resetting a team room. Separate help describes preserving achievements when moving business/education licenses. [TH-TEAMS], [TH-LICENSES] | Membership and personal identity are different. A team operation must state who it affects; never use a shared login as the collaboration model. Preserve personal work when organisational membership changes. |
| **HTB** | Academy registration links an Academy account with an HTB Account. Cubes remain Academy-specific and cannot be transferred between accounts. [HT-ACADEMY] | A shared identity can span experiences without merging all currencies, progress, or permissions. A platform switch should not imply data was copied or unified when it was not. |
| **HackerRank** | Public navigation separates learner preparation from hiring products. Organisation administration and candidate-account linking were not directly inspected in this review. | Do not guess that consumer and employer roles share unrestricted access. Author/admin/reviewer views need explicit permissions. |
| **Codewars** | Personal profile, ranks, Honor, authored content, and contribution privileges are documented. A guessed clans-documentation URL failed, so detailed current clan administration is unverified here. [CW-RANK], [CW-HONOR] | Separate public profile presentation from private work, and contribution status from administrator permissions. |
| **Exercism** | Personal learning/mentoring/reputation is documented. The Teams Edition page contains an old shutdown/relaunch-in-2023 statement; it cannot establish an operating 2026 team product. [EX-REPUTATION], [EX-TEAMS] | Do not expose a team-management feature merely because a footer mentions it. Ship account roles only with functional workflows and explicit data boundaries. |
| **DataCamp** | Current help distinguishes all-time personal XP from organisation/timeframe-filtered boards; progress remains with the same login when classroom/business context changes. [DC-XP], [DC-TEAM] | Always label the scope of a total. The account identity, selected organisation, and time filter should be visible before presenting apparently conflicting numbers. |
| **Duolingo** | The historical family-plan article describes several separate learner accounts under a manager's subscription; league privacy controls are separately documented. Current billing details were not tested. [DU-FAMILY], [DU-LEAGUES] | Shared payment or a household should not combine learning evidence. Competition opt-in should not require learners to expose unrelated private work. |

For Ascend, begin with a clear **personal account → private work/history → optional public profile**, then add organisation membership, assignment/reviewer roles, or peer collaboration only when needed. Show an explicit active-account/workspace indicator. On switching or signing out, preserve drafts under the correct account, end access to the previous account's live data, and prevent cached notebooks, rewards, or lab identifiers appearing for another user. Saved work, pending results, reward receipts, and queue tickets need the same account boundary. The existing two-lab limit remains an admission rule per authenticated user, not a reason to share accounts.

## What to carry into implementation

1. **Base shell first:** hierarchy, typography, spacing, quiet surfaces, navigation, responsive layouts, and clear task/page boundaries. Illustration cannot repair an ambiguous action or save state.
2. **State and event semantics next:** define loading, saved, waiting, ready, passed, assisted, reviewed, ended, expired, and failed states before animating them.
3. **An original visual vocabulary:** one companion, a small set of domain objects, restrained accents, and one optional landscape/arena view. Use the same task data for the visual and list representations.
4. **Reward truth:** drive result/XP/milestone feedback from distinct authoritative events. Keep a cosmetic redesign from implicitly changing existing awards or timing; any deliberate scoring change needs a stated, versioned policy and migration.
5. **Content and account continuity:** stable versions, clear new-content updates, persistent personal work, scoped team views, and useful practitioner return routes.
6. **Validate on actual tasks:** test finding a challenge, starting it, understanding the finish line, saving work, failure recovery, lab waiting, returning after expiry, claiming a reward once, switching accounts, keyboard navigation, reduced motion, and narrow-screen editing. Include a regular practitioner and a new learner; measure whether motion helps comprehension rather than only whether it looks appealing.

The remaining competitor-specific verification is to inspect authenticated lesson success/failure, XP receipt, milestone, account-switch, and organisation flows in accounts explicitly available for that purpose. Until then, those parts of this audit remain documentation-based. Ascend's own implementation can still be specified and tested without assuming unseen competitor behaviour.

[O-PS]: https://portswigger.net/web-security "Public Academy page, browser observed 2026-11-03"
[O-TH]: https://tryhackme.com/ "Public homepage and experience filters, browser observed 2026-11-03"
[PS-PREP]: https://portswigger.net/web-security/certification/how-to-prepare "Certification preparation and experienced route"
[TH-POINTS]: https://help.tryhackme.com/en/articles/6563910-points-explained "Points Explained"
[TH-LEVELS]: https://help.tryhackme.com/en/articles/6496044-what-are-levels-on-tryhackme "What Are Levels on TryHackMe"
[TH-LEAGUES]: https://help.tryhackme.com/en/articles/10517530-how-leagues-work "How Leagues Work"
[TH-TEAMS]: https://help.tryhackme.com/en/articles/10364234-teams-explained "Teams explained"
[TH-LICENSES]: https://help.tryhackme.com/en/articles/8486133-preserve-points-when-migrating-between-b2b-and-edu-licenses "Preserve Points When Migrating Between B2B and EDU Licenses"
[HT-ACADEMY]: https://help.hackthebox.com/en/articles/12256202-introduction-to-htb-academy "Introduction to HTB Academy"
[HT-MODULES]: https://help.hackthebox.com/en/articles/12741910-academy-modules-paths "Academy Modules & Paths"
[HT-CHALLENGES]: https://help.hackthebox.com/en/articles/5185436-how-to-play-challenges "How to Play Challenges"
[HT-SEASONS]: https://help.hackthebox.com/en/articles/7041927-introduction-to-htb-seasons "Introduction to HTB Seasons"
[HR-PREP]: https://www.hackerrank.com/interview/preparation-kits "Interview Preparation Kits"
[HR-PRACTICE]: https://www.hackerrank.com/domains/algorithms "Algorithm practice filters"
[HR-SCORE]: https://www.hackerrank.com/scoring "Scoring Documentation"
[HR-CONTEST]: https://www.hackerrank.com/contests "Current contest listing"
[CW-TRAIN]: https://docs.codewars.com/getting-started/finding-kata/ "Finding Kata"
[CW-SOLVED]: https://docs.codewars.com/getting-started/kata-solved/ "After Solving a Kata"
[CW-RANK]: https://docs.codewars.com/gamification/ranks/ "Ranks"
[CW-HONOR]: https://docs.codewars.com/gamification/honor/ "Honor"
[CW-AUTHOR]: https://docs.codewars.com/authoring "Authoring Content"
[EX-REPUTATION]: https://exercism.org/docs/using/product/reputation "Reputation"
[EX-MODE]: https://exercism.org/docs/building/product/unlocking-exercises "Learning and Practice Mode"
[EX-MENTOR]: https://exercism.org/mentoring "Mentoring"
[EX-TEAMS]: https://exercism.org/docs/using/editions/teams "Teams Edition; contains stale shutdown/relaunch notice"
[DC-TRACKS]: https://www.datacamp.com/tracks/career "Career and skill track comparison"
[DC-SIGNAL]: https://www.datacamp.com/signal "Adaptive assessment and recommendations"
[DC-XP]: https://support.datacamp.com/en-us/articles/17598880-understanding-xp-and-progress-on-datacamp "Understanding XP and Progress on DataCamp"
[DC-FINISH]: https://support.datacamp.com/en-us/articles/17598980-will-i-receive-a-grade-or-bonus-xp-when-i-finish-a-course "Course completion and XP"
[DC-CURRENCY]: https://support.datacamp.com/en-us/articles/17598975-can-i-use-xp-to-redeem-datacamp-content "XP cannot redeem content"
[DC-TEAM]: https://support.datacamp.com/en-us/articles/17599134-why-is-there-a-difference-between-the-xp-on-a-member-s-profile-page-vs-the-xp-on-my-organization-leaderboard "Personal versus organisation XP totals"
[DU-MOTION]: https://blog.duolingo.com/streak-milestone-design-animation/ "Streak milestone animation design"
[DU-CHARACTER]: https://blog.duolingo.com/duolingo-art-intern-animation-case-study/ "Character animation production case study, 2023"
[DU-LEAGUES]: https://blog.duolingo.com/duolingo-leagues-leaderboards/ "League and privacy explanation, 2023"
[DU-QUESTS]: https://blog.duolingo.com/friends-quests/ "Friends Quests"
[DU-FAMILY]: https://blog.duolingo.com/plus-family-plan/ "Separate accounts under a family plan; historical article"
[DU-PRACTICE]: https://blog.duolingo.com/guide-to-duolingo-practice-hub/ "Practice tab, February 2026"
[DU-OUTAGE]: https://blog.duolingo.com/protecting-streaks-from-site-issues/ "Protecting streaks from site issues"
