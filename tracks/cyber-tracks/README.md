# Cyber tracks, version 2

Five proficiency tracks, each with eight main levels and a milestone per level.
Version 2 makes the opening levels into hands-on investigations with concrete
steps, optional hints, and realistic time estimates. Each track also has three
optional discoveries lasting 10, 15, and 20 minutes. The later curricula remain
editable drafts, not full hosted courses.

| Track | First challenge | Useful background |
| --- | --- | --- |
| `networking-for-security` | Catch a request in the act | None; start here if packets and ports are unfamiliar |
| `web-application-security` | Make a lab reveal a hidden row | HTTP requests and responses |
| `network-penetration-testing` | Discover what your lab is listening for | TCP/IP and an owned lab target |
| `reverse-engineering-and-binary-exploitation` | Catch a function changing a register | Comfortable reading a little C |
| `defensive-security-and-detection` | Leave a breadcrumb, then find it in the logs | A Linux host you control |

Choose the subject that makes you curious. Networking is a useful foundation,
not a requirement to finish an entire track before touching anything else.
Ascend keeps one mission active at a time; pause it to switch tracks. Progress is
retained. Offensive and defensive exercises can use the same isolated lab so
an action can become the next investigation.

## Using the revised tracks

These packs are also included in the repository's `packs/community/` registry.
Install by ID with the updated app, or upload a TOML file in More → Packs.

```sh
ascend pack install defensive-security-and-detection
ascend mission start defensive-security-and-detection
```

To update an existing installation, review the new file and compare it first:

```sh
ascend pack diff packs/community/defensive-security-and-detection.toml
ascend pack install packs/community/defensive-security-and-detection.toml
```

Every pre-existing node ID is retained. Completed and skipped tasks keep their
status. Installation replaces the private pack file, so keep any local edits
before updating; per-user variable settings remain separate. Changed pack content
resets review and executable-check trust. All files deliberately retain
`source = "ai-draft"` and `reviewed = false`.

## A useful session

1. Open a challenge and look at its finish line.
2. Try the first step. Open a hint only when it helps.
3. Save the result: a capture, working program, comparison, or short evidence note.
4. Log what happened. Check **Mark as done** only when the finish line is met;
   otherwise save partial progress and a useful next step.

File checks establish that an artifact exists; they do not independently grade
understanding. The updated nmap opening checks exercise evidence rather than the
tool's version. No task is automatically trusted or executed by installation.

The original archive `../cyber-tracks.zip` is retained for comparison. The revised
archive is `../cyber-tracks-v2.zip`. The repository's
`docs/design/engagement-audit.md` explains the design decisions, and
`docs/testing/cyber-track-links.json` records link-check results and access limits.
