# Rewards and result feedback

Implemented against the [platform UI/motion audit](../design/platform-ui-motion-audit.md) and [experience design](../design/ascend-experience-redesign.md), including the owner's later request that meaningful unscored practice also earn recognition. The audit supports separating effort, scored results and milestones. The exact Practice point amounts below are Ascend product choices, not measured competitor rules or a proven retention result.

## Three distinct rewards

| Reward | What it recognizes | Rule |
| --- | --- | --- |
| **Practice points** | Participation, reflection and practical attempts | 5 per distinct activity per learning day, capped at 30 per account/day. Points are not spendable and do not verify skill or unlock execution privileges. |
| **XP** | Scored results | Existing formulas remain unchanged: eligible quick practice, first-solve standalone challenges, and track timer/correctness scoring. Manual completion, worked examples and local/hosted work remain unscored. |
| **Milestones** | Completed track stages and their saved work | A colored medal links to the actual task. It identifies assessed evidence, an artifact check, or completion recorded by the learner. Skips are excluded. A milestone does not invent an extra XP bonus. |

Practice points can be earned by finishing a worked example, submitting a complete and well-formed assessment answer, explicitly saving a reflection of at least 20 characters, repairing a hidden fault in a free workspace, or recording a qualifying local/hosted lab result. A valid incorrect answer can acknowledge effort while its grade remains incorrect. Free experimentation earns credit through its saved reflection or a demonstrated hidden-fault repair; simply running the initial example is not a credit event.

Opening a task, watching a tour, making a prediction in that tour, autosaving a draft, entering a queue, starting/stopping compute, replaying an animation, malformed input, and failed saves do not earn points. The existing configured timezone and 04:00 learning-day boundary apply. Unassigned reflection logs share one daily activity bucket. Prior scored XP and completed milestones are retained; the Practice ledger begins with newly recorded qualifying events rather than fabricating past participation.

## Saved results and idempotency

[Migration 0013](../../ascend/storage/migrations/0013_practice_rewards.sql) adds an account-scoped ledger. An immutable event can be recorded only once for its lifetime, even when replayed on a later day. A partial unique index permits only one positive Practice credit for an activity/day, and the daily cap is checked under the SQLite write lock. Suppressed events receive a zero-point receipt, so replaying a capped event tomorrow cannot turn it into a new award.

Graded work uses its original attempt ID. Explicit reflection events use a digest scoped to their activity; resaving the same reflection does not become a new event on another day. Changed reflections or new deliberate attempts may qualify on a later learning day. Notes themselves are not copied into the reward ledger.

[The reward service](../../ascend/rewards.py) exposes the Practice balance, recent ledger and milestone evidence. API reads restore calm receipts with `newly_awarded: false`. Action responses identify new grants. Track assessment XP receipts come from the particular account and pack/node award row, rather than subtracting unrelated dashboard totals. A permission exercise can therefore retain its partial XP score without being called a completed milestone.

The server's hosted adapter accepts only authenticated runner observations of completed, checked work. It reconciles eligible current-day pass/fail records once; launches, abandoned jobs, unsupported checks and cleanup-only operations do not grant participation credit. Local evidence keeps its original authority label. Neither source becomes a verified track completion because it earns Practice points.

## Feedback hierarchy

- **Correct answer:** a small external toast with a check mark, no focus grab, and only actual recorded reward amounts. The question retains a short result and an expandable explanation. Prediction choices have no XP or Practice point award. Partial and incorrect results retain their explicit explanation and grade.
- **Challenge completion:** a saved result receipt, original companion illustration, relevant evidence and an immediately usable next action.
- **Milestone:** a larger finite companion/medal scene naming the actual completed task and next task. Its evidence label stays visible. Manual work and inherently unscored examples foreground their Practice points; they do not display a discouraging zero-XP pill. Real assessed zero scores remain explicit.

Animation uses the existing `AscendMotion` lifecycle. Effects finish within roughly 1.3 seconds; the answer toast uses a shorter confirmation. Operating-system reduced motion and the application's Off setting stop decorative motion while retaining text, actions, illustrations and the receipt. The toast dismisses after eight seconds, pauses dismissal while hovered/focused, can be closed, and is cleared on navigation or a worked-example step change. It does not replace an unresolved error.

Fresh presentations are deduplicated per account and receipt in browser storage, with a tab-memory fallback. Reloading or reopening saved work does not replay celebrations. An explicit **Replay celebration** on larger results is a viewing action only; it does not submit, modify XP or award points. Milestones do not also produce an answer toast.

The Profile and Progress pages show separate balances and the recent Practice ledger. Progress also shows medals across installed tracks with links to the saved task and its evidence label. No leaderboard, paid currency, random reward, queue advantage or additional hosted lab capacity was introduced.

## Implementation boundaries

- [rewards.js](../../web/rewards.js) and [rewards.css](../../web/rewards.css): scenes, compact answer toast, inline answer state, balances, ledger, medals and presentation deduplication.
- [effects.js](../../web/effects.js): finite scenes within existing visibility/reduced-motion cancellation.
- [challenge-work.js](../../web/challenge-work.js), [playground.js](../../web/playground.js), [local-labs.js](../../web/local-labs.js), and the result sections of [app.js](../../web/app.js): real saved-result integration.
- [rewards.py](../../ascend/rewards.py), track/notebook/Playground/local-attempt hooks, and the hosted adapter: authoritative participation and result receipts. Existing XP award rules remain unchanged.

The production visual-layout revision and hidden account administration are separate coordinated changes. Reward feedback does not provision environments or claim native VM/device/public-deployment testing.

## Validation

[Backend tests](../../tests/test_rewards.py) cover worked-example participation with zero XP, drafts and malformed input, manual completion, valid incorrect answers, exact XP receipt scope, concurrent cap enforcement, account separation, next-day replay, local evidence authority and hidden-fault repair. Existing Playground concurrency and migration checks now include the additional ledger and its true-once action flag.

[Browser tests](../../tests/test_reward_feedback.py) use disposable profiles and verify saved-result ordering, failed-save behavior, mobile/desktop geometry, reduced motion, unchanged XP on replay, reload without animation, compact external answer feedback, optional explanations and prediction deduplication. Existing feedback, complete-task, MCQ and partial-permission browser flows were also exercised. These checks validate behavior and presentation; they are not a learner study or a claim of universal accessibility certification.
