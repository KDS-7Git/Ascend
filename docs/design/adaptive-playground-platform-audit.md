# Learning intent, experienced entry, and sustained practice: eight-platform audit

Reviewed **2026-11-03**. This is a public first-party documentation and product-page audit, not a signed-in usability study. It answers how platforms support job/interview preparation, interest-led learning, and people who already practise regularly. The accompanying [Ascend proposal](adaptive-playground-proposal.md) translates the findings into implementation milestones within the owner's confirmed **two simultaneous hosted labs** budget.

“Placement” here means preparing for employment. A **starting-level assessment** is a different function: finding useful material without making an experienced newcomer repeat a beginner course. Six months of practice is useful background, but it does not establish the same proficiency in every subject.

The strongest combination to adopt is **separate goals, an experienced entry route, fresh practical challenges, and feedback that changes the next recommendation**. These capabilities do not require every exercise to have its own persistent machine. Neither feature descriptions nor completion counts establish that a platform improves learning or retention; the recommendations below are design judgments to test.

## Method and evidence limits

The sample contains three security platforms, three programming practice platforms, one data-skills platform, and one language-learning comparator. For each, inspect intent, entry level, practitioner engagement, adaptation, and environment delivery. Observations are attributed to the linked sources; suggestions for Ascend are explicitly separate.

The [source ledger](adaptive-playground-sources.json) records URLs, retrieval timestamps, response hashes, supported observations, and access failures. Source bodies are not copied into the repository. Most pages describe currently offered features; Duolingo's 2018/2020 engineering articles are **historical explanations**, not verification of the exact algorithm deployed in 2026. Public documentation also cannot establish whether an undocumented feature is absent.

LeetCode study-plan, contest, and support pages returned access errors, so it is **not** counted among the eight audited platforms. HackerRank provides readable first-party evidence for the interview-preparation comparison. TryHackMe's public paths page was inaccessible; its help articles provided the path and room evidence. DataCamp's career-track and Signal pages were readable, while its separate skill-track/projects pages were blocked. No access controls were bypassed, competitor accounts created, or live competitor labs run.

## Comparison

| Platform | Job preparation and interest-led routes | Entry and continued challenge for practitioners | Adaptation actually evidenced |
| --- | --- | --- | --- |
| **PortSwigger Web Security Academy** | Certification preparation gives a defined outcome; topic study and labs support independent security interests. | An explicit experienced route samples a practitioner lab from each topic, directs remediation to gaps, then adds selected core labs, five mystery labs, and a practice exam. Mystery labs remove title/description clues. [PS1], [PS2], [PS3] | Authored progression and self-assessment guidance. These sources do not establish an automatic learner model. |
| **TryHackMe** | Structured security/SOC paths and SAL1 support career goals; individual walkthrough/challenge rooms allow topic-led practice. | Difficulty filters include intermediate and advanced content. Its Capability Score rewards harder/current content, depth, breadth, and consistency. [TH1], [TH2], [TH3], [TH4] | The documented score combines completions and activity adjustments. This is evidence of a changing score, not automatic question-difficulty adaptation or verified job competence. |
| **Hack The Box** | Academy explicitly separates **Job Role Paths** and **Skill Paths**. Labs adds independent challenges and investigations. | Advanced modules, corporate-network Pro Labs, community challenge submissions, and 13-week Seasons give several ways to continue. Guided Mode is optional on specific machines. [HT1], [HT2], [HT3], [HT4], [HT5] | Difficulty selection, selective guidance, user ratings, and competition. Automatic individual difficulty adaptation is not established by these sources. |
| **HackerRank** | Explicit **Prepare / Certify / Compete** navigation; interview kits are organised around one week, one month, or three months. Topic practice also stands alone. | Skill/difficulty filters, skill and role certification tests, contests, and documented ratings provide routes beyond beginner practice. [HR1], [HR2], [HR3], [HR4], [HR5] | Curated kits, manual filters, test-case scoring, and contest ratings. An Elo contest rating is not evidence that the next practice problem adapts to learning needs. |
| **Codewars** | Open-ended language/topic practice is central; no structured job-preparation route was established in the reviewed sources. | The trainer explicitly offers **Fundamentals** and **Rank Up**; harder kata advance rank faster. Solution discussion, translations, and authoring provide work beyond solving. [CW1], [CW2], [CW3], [CW4] | Documented trainer recommendations by language/focus, with Rank Up advancing to harder problems. No published calibrated skill-estimation model was established here. |
| **Exercism** | Language fluency, idiomatic code, mentoring, and contribution suit both professional development and curiosity; they are not a job-placement guarantee. | Its product documentation allows switching from Learning Mode to **Practice Mode**, unlocking exercises. Mentors help refine solutions; experienced users can mentor or contribute. [EX1], [EX2], [EX3], [EX4] | Explicit learner control over sequencing plus human feedback. No automatic difficulty model was established by these sources. |
| **DataCamp** | Longer **career tracks** organise learning by role; shorter **skill tracks** target narrower abilities. | Signal assesses existing skills, recommends learning, and supports reassessment; the career catalog includes advanced subject matter. [DC1], [DC2] | Signal explicitly changes question difficulty according to performance. This establishes adaptive assessment, not automatic adaptation of every course or project. |
| **Duolingo** | Relevant as a learning-design comparator, not a software/security employment platform. Current practice lets people target a skill or revisit immersive material. | Historical placement-test work addresses knowledgeable newcomers; Birdbrain describes matching exercise difficulty to the learner. The 2026 Practice tab offers mistakes, words, speaking, and listening. [DU1], [DU2], [DU3], [DU4] | Historical engineering sources describe adaptive placement and lesson selection. Current Practice availability is separately documented; exact present-day algorithm behaviour was not tested. |

## 1. PortSwigger: sample competence instead of requiring the whole course

**Observed.** The certification guide has separate sections for learners developing fundamentals and learners with extensive experience. The experienced route starts with one practitioner lab from each topic, solved without consulting solutions. A failed topic sends the learner to that topic's material and labs. Later steps include selected cross-cutting skills, five mystery labs, and a practice exam. This is a concrete way to respect prior experience while still checking coverage. [PS2]

Mystery labs conceal the title and description. This changes the task from applying a named technique to discovering which technique is relevant. The preparation progression also moves from topic-specific mysteries to mixed-topic discovery. [PS2], [PS3]

**Engagement mechanism.** Independence, discovery, and broader transfer offer challenge after basic technique execution becomes routine. This is a plausible engagement mechanism, not measured retention evidence from this audit.

**Environment.** Learners launch hosted target labs and use appropriate testing tools. Removing contextual clues can make an existing class of target harder without adding a larger machine. No public infrastructure cost or concurrency figure was verified.

**Ascend adaptation.** Offer an optional practical starting-level check, remediate only sampled gaps, and reserve mixed mysteries for supported prerequisite skills. Keep the task's objective and submission requirements clear even when the diagnosis is hidden. Merely hiding confusing instructions would reproduce the owner's earlier problem.

## 2. TryHackMe: structured paths plus a broad challenge catalog

**Observed.** Walkthrough rooms teach with explanations; challenge rooms test application. Difficulty filters distinguish beginner/easy, intermediate, and advanced/insane material. Current help identifies Cyber Security 101 and SOC Level 1/2 as replacements for retired paths. SAL1 explicitly targets students, career switchers, and early-career analysts. [TH1], [TH2], [TH3]

The March 2026 Capability Score explanation describes a baseline from completions across difficulty tiers plus consistency, relevance, versatility, and depth adjustments. It also describes inactivity and content-retirement decay. [TH4]

**Interpretation.** Showing breadth and depth gives practitioners more than a beginner checklist. However, a number that depends partly on logins and retained room availability is a product metric; it should not be treated as independently verified professional competence. The source's claim of measuring current capability is the platform's claim, not a finding established by this review.

**Environment.** AttackBox is a browser-accessible cloud VM, distinct from the target machine. The help page describes a one-hour daily allowance for free AttackBox use, paid extended access, and a learner-machine VPN alternative. Persistent AttackBox storage is described as a MAX feature. “Use your own machine” here can replace the attack workstation; it does not necessarily move the target off the provider. [TH5]

**Ascend adaptation.** Make practical depth and current interests visible, and explain what an environment is before launch. Keep skill evidence separate from habit measures. Returning after a break should offer a useful recheck without deleting achievements or relabelling the learner a beginner because they stopped logging in.

## 3. Hack The Box: distinct routes for careers, specialisms, and competition

**Observed.** Academy's landing page directly offers Job Role Paths and Skill Paths, with modules from beginner to advanced. Its certification presentation emphasises realistic engagements and reporting. Pro Labs describes enclosed corporate networks and scenarios for junior through experienced testers and hobbyists. [HT1], [HT5]

The Challenges guide documents topic/difficulty filters, files or Docker targets, new releases, active/retired states, and user-submitted challenges. Active challenges restrict published walkthroughs; retired challenges support learning without active-challenge points. [HT2]

Seasons gives everyone a fresh competitive starting point over 13 weeks, with one weekly machine and a seven-day seasonal scoring window. **Seasons currently covers Machines, not every Challenge or content type.** Guided Mode is separately documented on specific machines, with an explicit toggle and optional hints. [HT3], [HT4]

**Engagement mechanism.** New scenarios, realistic multi-stage work, optional competition, and contribution can serve different practitioners. Neither global leaderboards nor timed seasons should be assumed to motivate everyone.

**Environment.** Some challenges only require files; others use containers. Pro Labs supplies larger persistent network scenarios. These are materially different delivery costs and learning experiences. [HT2], [HT5]

**Ascend adaptation.** Use role-aligned case sequences and optional periodic challenges. Start with artifact investigations and reviewed small environments; a simulated case is not a full corporate-network lab. Make season-like events asynchronous and optional so two hosted slots do not become a race for access.

## 4. HackerRank: employment preparation is an explicit product route

**Observed.** Public navigation separates Prepare, Certify, and Compete. Interview kits offer time-horizon choices; the public cards show 21, 54, and 104 challenges for their respective kits at retrieval. Although the page's introduction mentions mock tests, the inspected cards display **zero mock tests**. Do not infer that every kit currently includes one. [HR1]

Certification is presented by role and by skill/level. Algorithm practice has skill, difficulty, and topic filters. Scoring documentation distinguishes practice points, domain leaderboards, and Elo-based rated-contest results; it also explains test-case-based partial scores and consequences of unlocking editorials for progress. [HR2], [HR3], [HR4]

**Engagement mechanism.** A practitioner can pursue targeted interview preparation, deeper topic practice, or competition. The live contest page inspected in this audit features hackathons and archives; the scoring documentation alone does not prove a current weekly cadence of rated algorithm contests. [HR5]

**Environment.** The execution-environment page publishes language-specific CPU-time and memory limits and a submission-size limit. It demonstrates that bounded submitted work is a different service from providing a full personal VM. These provider limits should not be copied into Ascend without its own execution isolation and measurements. [HR6]

**Ascend adaptation.** Give job-focused learners a role, an optional target date, practical gap coverage, and reviewable work samples. Show exercise results and evidence scope; avoid presenting practice XP or a generated certificate as proof of employment readiness. Use estimated effort and checkpoints instead of promising every learner the same completion date.

## 5. Codewars: the experienced route is visible and controllable

**Observed.** The trainer's Fundamentals focus selects easier kata; Rank Up is explicitly recommended for experienced developers and progresses from easy/medium to harder challenges. Users can skip a suggestion or browse by topic, difficulty, and previous practice. [CW1]

Ranks exist overall and per language. Harder kata yield substantially more rank progress; the same kata does not repeatedly award overall progress. Accepted solutions can be discussed and rated for best practices or cleverness. Content creation and translation require tests, clear requirements, and reviewer communication. [CW2], [CW3], [CW4]

**Engagement mechanism.** Visible challenge choice, comparing alternative solutions, and becoming a contributor extend practice beyond collecting beginner completions. Rank still measures the platform's completion policy; it does not prove broad engineering ability.

**Environment.** Kata use code and test submissions. The reviewed sources do not specify enough infrastructure details to estimate provider compute cost or isolation. Do not infer that an in-browser editor executes entirely on the learner's device.

**Ascend adaptation.** Put “I already practise” and “Give me a harder challenge” near the entry point. Let someone choose harder work without claiming it has already been mastered. Offer review of alternative approaches after a case is completed or ended, then test transfer on a meaningfully different case.

## 6. Exercism: fluency can deepen through review and contribution

**Observed.** The Python track combines concepts, exercises, and mentoring. The product documentation distinguishes tracks with Learning Exercises from those without: Learning Mode unlocks content as prerequisites are completed; **Practice Mode unlocks exercises from the start** and can be selected from the track menu. Mentoring remains available in either mode. This is stronger evidence for experienced entry than the public exercise catalog alone. [EX1], [EX2]

Exercism describes mentoring as a way to reinforce knowledge and communication. Its getting-started guide also invites contributions, ranging from small tasks to substantial development. [EX3], [EX4]

**Engagement mechanism.** A solution passing tests is followed by opportunities to improve idiom, clarity, and design. Teaching and maintaining exercises can challenge a practitioner in a different way from another test of the same syntax.

**Environment.** The CLI downloads instructions, tests, stubs, and optional hints; learners work in their own environment and submit solution files. This is a concrete precedent for retaining a familiar local toolchain while keeping learning history online. The source does not establish that all platform-side verification disappears. [EX5]

**Ascend adaptation.** Allow an experienced route that changes recommendation defaults without falsely marking the track complete. Preserve browser and learner-local choices. Add human review or contribution only with an actual reviewer workflow; an empty “mentor” button is not a mentoring service.

## 7. DataCamp: assess first, then focus the learning plan

**Observed.** Career tracks group skills for a role; the same page contrasts them with shorter, focused skill tracks. Courses and exercises are presented as usable in the browser. Track completion yields a statement of accomplishment, which is a distinct product from a separate certification assessment. [DC2]

Signal explicitly states that question difficulty adjusts to the learner's performance. Its flow is assess existing skills → receive learning recommendations → inspect results/mistakes → reassess after practice. The page describes coding-based assessment; the whitepaper landing page characterises the system as adaptive testing and psychometrics. The paper itself was not downloaded. [DC1], [DC3]

**Engagement mechanism.** A learner can spend time on gaps instead of restarting a complete track, and reassessment can show a change in the sampled skill. That does not establish that every broader job skill has been assessed.

**Environment.** Browser delivery is documented. It is **not evidence of client-only computation**, nor a public statement of concurrent runtime cost.

**Ascend adaptation.** Introduce a small diagnostic for authored, observable skills and expose its uncertainty. Start with explainable rules because Ascend's catalog and response data are too small to justify claims of a calibrated adaptive testing model. Do not call a handful of observations a percentile or a statistically precise ability score.

## 8. Duolingo: place learners near useful difficulty, then offer targeted practice

**Observed.** The 2018 placement-test article describes adaptive question selection and the problem of treating partially correct answers as entirely wrong. The 2020 Birdbrain article describes estimating learner ability and exercise difficulty to inform lesson selection. A separate 2020 article describes adapting later exercises in a lesson. These are historical engineering descriptions; they do not establish current UI details or model parameters. [DU1], [DU2], [DU3]

The February 2026 Practice tab article is current product evidence: mistakes, words, speaking, and listening practice is available on iOS/Android; other material depends on the course, and some session-review features depend on subscription. [DU4]

**Engagement mechanism.** Relevant challenge plus the freedom to select a practice need can make return visits useful. Birdbrain's article reports favourable internal experiments, but this audit did not inspect experiment data or reproduce the results. Language-task adaptation cannot be assumed to transfer unchanged to open-ended engineering work.

**Ascend adaptation.** Use outcomes on specific rubric components to distinguish a small procedural error from a missing concept. Reassess the next task after useful evidence arrives. Preserve a fixed challenge, rubric, timer policy, and reward contract during an assessed attempt; silently swapping an active challenge is inappropriate for Ascend's current scoring.

## Findings to carry into Ascend

1. **Intent and proficiency are separate.** A job seeker may be new or experienced; a hobbyist may be an expert. HTB/DataCamp make role versus skill routes explicit; PortSwigger/Exercism show that an experienced route can coexist with structured teaching.
2. **Experienced entry needs an action.** Offer a small practical check or direct challenge selection. A label saying “intermediate” is insufficient if recommendations still route everyone through beginner examples.
3. **Practitioners need meaningful novelty.** Discovery, transfer, realistic constraints, reviewing solutions, and contribution give more dimensions than repeated flags. New names and shuffled answer positions do not produce a fresh reasoning problem.
4. **Use different engagement measures.** Skill evidence, practice habits, competition results, and job-preparation coverage answer different questions. Combining them into one attractive number obscures why the next task is appropriate.
5. **Learning support can be selective.** Offer separate examples for missing knowledge and explicit assistance when authored. Preserve the distinction between exposure, assisted success, familiar practice, and an independent fresh solve.
6. **Allocate persistent environments to the parts that need them.** Files, bounded checks, hosted targets, browser workstations, and local work are different products. Public browser access by itself says nothing about where computation runs.
7. **The candidate advantage is a combination to validate.** Explainable adaptation plus rich small cases, portable work, and honest environment availability could suit Ascend. This audit does not establish that the combination is unique or better than competitors.

The [proposal](adaptive-playground-proposal.md) supplies the learner flows, initial selection rules, practitioner case ideas, capacity accounting, and milestones needed to make these findings reviewable.

[PS1]: https://portswigger.net/web-security/getting-started "Getting started with the Web Security Academy"
[PS2]: https://portswigger.net/web-security/certification/how-to-prepare "How to prepare for the Burp Suite Certified Practitioner exam"
[PS3]: https://portswigger.net/web-security/mystery-lab-challenge "Mystery lab challenge"
[TH1]: https://help.tryhackme.com/en/articles/6611846-room-difficulty-levels "Room difficulty levels"
[TH2]: https://help.tryhackme.com/en/articles/10632551-big-changes-on-tryhackme-retired-three-learning-paths "Retired and replacement learning paths"
[TH3]: https://help.tryhackme.com/en/articles/10625001-is-sal1-right-for-me "Is SAL1 Right For Me?"
[TH4]: https://help.tryhackme.com/en/articles/14345338-how-your-capability-score-is-calculated "How Your Capability Score is Calculated"
[TH5]: https://help.tryhackme.com/en/articles/6721845-the-attackbox-explained "The AttackBox Explained"
[HT1]: https://academy.hackthebox.com/ "HTB Academy: Job Role Paths and Skill Paths"
[HT2]: https://help.hackthebox.com/en/articles/5185436-how-to-play-challenges "How to Play Challenges"
[HT3]: https://help.hackthebox.com/en/articles/7041927-introduction-to-htb-seasons "Introduction to HTB Seasons"
[HT4]: https://help.hackthebox.com/en/articles/8117054-guided-mode-on-htb-labs "Guided Mode on HTB Labs"
[HT5]: https://help.hackthebox.com/en/articles/5185470-how-to-play-pro-labs "How to Play Pro Labs"
[HR1]: https://www.hackerrank.com/interview/preparation-kits "Interview Preparation Kits"
[HR2]: https://www.hackerrank.com/skills-verification "Certification Tests"
[HR3]: https://www.hackerrank.com/domains/algorithms "Solve Algorithms"
[HR4]: https://www.hackerrank.com/scoring "Scoring Documentation"
[HR5]: https://www.hackerrank.com/contests "Contests"
[HR6]: https://www.hackerrank.com/environment "Execution Environment; redirects to HackerRank Knowledge Base"
[CW1]: https://docs.codewars.com/getting-started/finding-kata/ "Finding Kata"
[CW2]: https://docs.codewars.com/gamification/ranks/ "Ranks"
[CW3]: https://docs.codewars.com/getting-started/solutions "Viewing Solutions"
[CW4]: https://docs.codewars.com/authoring "Authoring Content"
[EX1]: https://exercism.org/tracks/python "Python on Exercism"
[EX2]: https://exercism.org/docs/building/product/unlocking-exercises "Unlocking Exercises and Learning/Practice Mode"
[EX3]: https://exercism.org/mentoring "Mentoring on Exercism"
[EX4]: https://exercism.org/docs/using/getting-started "Getting Started"
[EX5]: https://exercism.org/docs/using/solving-exercises/working-locally "Working Locally"
[DC1]: https://www.datacamp.com/signal "DataCamp Signal"
[DC2]: https://www.datacamp.com/tracks/career "Career tracks and comparison with skill tracks"
[DC3]: https://www.datacamp.com/resources/whitepapers/datacamp-signal "DataCamp Signal whitepaper landing page"
[DU1]: https://blog.duolingo.com/partial-credit-improvements-to-duolingos-placement-test/ "Placement test engineering, 2018"
[DU2]: https://blog.duolingo.com/learning-how-to-help-you-learn-introducing-birdbrain/ "Introducing Birdbrain, 2020"
[DU3]: https://blog.duolingo.com/keeping-you-at-the-frontier-of-learning-with-adaptive-lessons/ "Adaptive lessons, 2020"
[DU4]: https://blog.duolingo.com/guide-to-duolingo-practice-hub/ "Practice tab, February 2026"
