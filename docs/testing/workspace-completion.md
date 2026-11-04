# Practice Playground and workspace completion

The 2026-11-03 integration pass completes the software work recorded in the [Playground plan](../design/practice-playground-plan.md) and [workspace rollout](../implementation/workspace-rollout.md), including the owner's latest visual corrections.

## Delivered content

| Domain | Installable tracks | Main levels | Milestones | Tasks |
| --- | ---: | ---: | ---: | ---: |
| Infrastructure & Internet Operations | 9 | 72 | 72 | 225 |
| DevOps | 3 | 24 | 24 | 75 |

Counts were read from the generated TOML packs. All 12 archives match their maintained source and contain actual lessons, local inputs and shared tools. They are in the 40-pack bundled catalog. Existing profiles retain their selected mission and installed packs; the new tracks can be installed from Browse learning tracks.

## Integration coverage

- Production Today glow starts on visibility, finishes and does not replay on a data refresh or tab return. Page transitions, companion gestures, card feedback and saved-result celebrations honor motion settings and device reduced motion.
- The restored page/card grid highlights share the paper background's viewport origin and responsive spacing, including the challenge-card texture. Alignment survives card movement and scrolling. Activity cards have neutral borders. Tracks/Profile panels and action controls follow the same light/dark workspace styling, including native file pickers and Playground tabs.
- Desktop and phone result checks cover correct-answer toasts, compact expandable explanations, worked-example Practice points, milestone receipts, replay without new awards and restored results without another celebration.
- Playground autosave/manual-save ordering and recovery preserve newer edits after a failed save. Copying saved work requires confirmation before ending an active assessed attempt. Previously repaired copies cannot manufacture a new repair reward.
- The installed-wheel check covers real assets, all new downloads, migrations and API behavior. Offline documentation restores the workspace, account and reward modules and their styles.
- The local service was restarted with the original process arguments/environment after a consistent SQLite backup. Health and rewards respond successfully; no artificial learning progress was added to that profile.

## Reproduction

Final result: **658 tests passed in 340.20 seconds**. The synchronized-grid checks cover both themes, card movement, scrolling and motion preferences. Both curriculum generators, the bundled registry and every learning-material archive passed consistency checks. Six additional distribution/catalog/generator checks passed after removing a trailing space from an authored shell example and refreshing its generated materials. Seven LaTeX documents were rebuilt with no missing glyphs, unresolved references or overflow above 1 pt.

The pending Python changes pass formatting and the CI unused-code lint check. The full-repository formatter still flags 27 untouched files from earlier commits; these pre-existing formatting failures remain outside the completed stages.

```sh
.venv/bin/pytest -q
.venv/bin/python scripts/build_infrastructure_tracks.py --check
.venv/bin/python -m scripts.build_devops_tracks --check
.venv/bin/python scripts/build_registry.py --check
.venv/bin/python scripts/package_learning_materials.py --check
.venv/bin/python scripts/build_docs.py
```

The final regression output is kept locally in `workspace-final-regression.txt`. `test_workspace_ui.py` exercises panel geometry at 390, 768 and 1440 CSS pixels in both themes and delayed/failed-save recovery. `test_integration.py` checks glow, effective motion controls, offline loading and stale-server recovery. Reward behavior and presentation are covered by `test_rewards.py` and `test_reward_feedback.py`.

Local captures are under `docs/screenshots/workspace/`; `production-motion.webm` records the actual production UI with a disposable profile. They illustrate UI behavior, not real learner accomplishments.

The authored curriculum remains an unreviewed teaching draft. Real CI/provider/VM/hypervisor/Pi/mail/cluster variants require their own environments and observed results. Beginner transfer sessions and the proposed two-week observation window remain empirical follow-up; software tests do not establish those outcomes.
