# Cyber tracks, version 3

Five proficiency tracks, each with eight main levels. The 40 milestones now
require an experiment, a changed case, a contrasting control, and an explanation.
There are 40 optional return-later checks, five lab-readiness checks and a Windows
baseline, alongside the practical challenges and short discoveries from v2.

These are evidence-informed drafts, not empirically proven courses. File checks
confirm artifacts; they cannot grade reasoning. The complete assessment rubric,
source review, prerequisites, hardware constraints, installation instructions and
learning-outcome limits are in the LaTeX handbook (`handbook.pdf` in the v3 ZIP;
`docs/handbook.pdf` in the repository). Its sources live under `docs/latex/`.

The five IDs are:

- `networking-for-security`
- `web-application-security`
- `network-penetration-testing`
- `reverse-engineering-and-binary-exploitation`
- `defensive-security-and-detection`

Networking is a useful starting point if packets and ports are unfamiliar. Choose
one active mission; pause it to switch tracks. Your progress is retained.

```sh
ascend pack install networking-for-security
ascend mission start networking-for-security
```

For an existing installation, back up private edits and compare before updating:

```sh
ascend pack diff packs/community/networking-for-security.toml
ascend pack install packs/community/networking-for-security.toml
```

All earlier node IDs remain. Existing completions are preserved but do not
retroactively certify the stronger v3 assessment. Use the new recall checks or
reopen a milestone. Changed content resets review and execution trust. All packs
remain `source = "ai-draft"` and `reviewed = false`.

The repository retains the original and v2 ZIPs for compatibility and comparison.
`docs/testing/cyber-track-links-v3.json` records current link results, replacements
and access restrictions. Labs, supported hardware and any paid accounts are
provided separately; Ascend does not provision hosted training machines.
