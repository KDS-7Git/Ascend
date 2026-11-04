# Engineering tracks, rewards and workspace rollout

This implementation follows the platform research and the user's UI review on 2026-11-03. The approved direction keeps neobrutalism, uses a compact mobile recommendation and a layered dark background, and separates small answer feedback from challenge and milestone celebrations. The latest correction requires correct-answer toasts and compact, expandable explanations in the question area.

## Practical tracks

| Domain | Tracks | Main levels | Tasks | Implementation detail |
| --- | ---: | ---: | ---: | --- |
| Infrastructure & Internet Operations | 9 | 72 | 225 | [Infrastructure handoff](infrastructure-tracks.md) |
| DevOps & deployment | 3 | 24 | 75 | [DevOps handoff](devops-tracks.md) |

The registry now contains 40 bundled packs. Twelve new deterministic ZIPs under `web/training/` include real lessons, local tools, native-operation inputs and the project license. Each engineering bundle includes the shared Relay service and inspection, release, backup and measurement tools. Existing cyber material ZIPs retain their original bytes.

In the app, open **Tracks → Browse learning tracks**, choose Infrastructure or DevOps and install a track. The numbered order and entry skills are recommendations. Start the chosen mission, then open and start a task to reveal its instructions and material download. An experienced learner can attempt the independent milestone without recording the worked lesson as complete; **Unlock level early** remains available for entering a later level.

Infrastructure covers Linux/networking, VMs and host administration, VPS/public hosting, cloudflared, SSH/VPN/tunnels, delivery automation, mail/state, traffic/concurrency/capacity, constrained hardware/Pi, and private-cloud administration. The Pi material contains a real headless setup and deployment sequence plus a PC/VM route. DevOps continues through service deployment, Git and immutable artifacts, containers, CI, OpenTofu/Ansible, observability, recovery and Kubernetes.

Each lesson names the machine role, files and save location, changed-condition exercise, observations and cleanup. The application does not silently create those local files. Portable checks validate their declared model or actual local service observations; they do not claim that a VM, public tunnel or physical-device operation occurred. Native operational outcomes remain manual and the packs retain their unreviewed teaching-draft status.

The hosted runner remains limited to two labs. Heavy engineering exercises use the learner's own PC/guest/device. Materials include the supplied small-server envelope (about four cores, 4–8 GB RAM and 100–120 GB microSD) and a 16 GB learner-PC route while allowing later expansion. Physical endurance, power and Internet reachability require observations in those actual environments.

## Rewards and accounts

Practice points acknowledge participation; scored XP retains assessment rules; milestones preserve completed stages and their evidence. Meaningful practice earns five Practice points per distinct activity/day, capped at 30/day. Drafts and clicks do not earn points, and replaying an old event does not create another day's credit. Worked examples can earn Practice points with zero scored XP. Results and amounts come from persisted, account-scoped receipts.

The default dashboard remains a single local user. [Optional account controls](accounts.md) are implemented behind an off-by-default flag: password changes, session expiry/revocation and operator recovery. Account transitions reload the document; an old pending notebook is not submitted under a newly signed-in identity. No existing learner profile was converted or seeded with artificial progress.

## Validation and activation

The material generators, archive consistency, registry integrity, semantic catalog/API tests, practical-tool tests and documentation build are exercised with disposable profiles. The checks include real loopback HTTP/write controls, independent SQLite restore, release rollback, TLS trust/name failures, resource/capacity arithmetic, browser downloads, saved notes and entry into a later track. The saved content-pattern audit reports 40 packs, 1,302 nodes and zero known-pattern flags; this is a diagnostic, not a pedagogical quality score.

Five LaTeX handbooks have been rebuilt with updated catalog, account and reward references. Native VM/hypervisor/provider/Pi/mail delivery and cluster recipes have not been operationally replayed in this workspace. Their authored commands and local controls must not be presented as that runtime validation.

The local server on port 8420 has been gracefully restarted with its original configuration after a SQLite backup. Health and the new rewards endpoint return 200. The 40-pack catalog includes all nine Infrastructure and three DevOps tracks; these are available through **Tracks → Browse learning tracks**. Installing a new pack remains an explicit learner action.

The final UI corrections restore the 2.4-second challenge border glow when the card first becomes visible, retain page/companion/reward motion, and synchronize the fixed page grid, challenge-card texture and mouse highlights. Moving across cards also shifts their hard shadows and decorative artwork. Worked-example cards use neutral outlines without purple side stripes. Tracks and Profile use opaque panels consistent with the sidebar. Buttons, file pickers, profile controls and Playground tabs share outlined, raised styling. Profile explains whether motion is enabled, disabled, or suppressed by the device preference.

Playground saves are serialized. A completed earlier save updates the recovery version without deleting newer unsynced edits, and a failed following save can be recovered after reload. Copying a workspace explicitly confirms ending another timed challenge. Copying an already repaired workspace cannot earn repair credit again.

The offline shell now includes rewards, account controls and the workspace styles/scripts. The completion record and validation commands are in [workspace completion](../testing/workspace-completion.md). Browser screenshots and a recording under `docs/screenshots/workspace/` use disposable learner profiles.

The owner's subsequent hover review replaces the subtle pointer highlight with a visible 3 px card lift, an 8 px hard shadow and pressed states. Level headers now fit the panel edge to edge, with flat amber hover/focus feedback and matching corners; the inset gray rectangle is removed. This correction passed 23 existing browser checks, plus rendered light/dark checks at 390 and 1440 px for header alignment, opening/closing, pressed feedback, overflow and reduced motion.

The 2026-11-04 follow-up adds mouse movement alongside those normal hover effects. Moving across the Today challenge, its shortcut cards, Playground cards or Path headers shifts the hard shadow between 4 and 12 px. The companion, icon or level badge follows by up to 5 px horizontally and 4 px vertically with a small rotation. Text and buttons retain their settled hover positions. Card movement resets on leaving, pressing, scrolling, navigation, hiding the tab and changing motion preferences.

The owner's final selection restores the earlier grid effect. The paper background, challenge-card texture, page highlight and card highlight share one viewport origin and one spacing value: 28 px on desktop and 22 px on narrow screens. The selected cell snaps to that same grid. Coordinate updates compensate for card borders, scrolling, card lifts and finite page entrance transforms, then stop when geometry settles. The native pointer remains available. The grid layers are accessibility-hidden and never intercept input. Touch input does not start mouse highlights. Leaving the window, losing focus, hiding the tab or disabling motion clears the highlights; reduced-motion and forced-color preferences are honored.

The cursor regressions now cover rendered alignment of the background, challenge texture, highlighted grid and selected cell in both themes, including card movement, pressing and scrolling. They also exercise dialog typing/clicking, pointer exit/re-entry, focus loss, forced colors, motion controls, touch input and the existing card interactions. Earlier captures under `docs/screenshots/persistent-mouse/` show a superseded cursor option; the current effect uses the synchronized grid.
