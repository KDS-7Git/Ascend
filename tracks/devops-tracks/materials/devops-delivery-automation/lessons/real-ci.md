# Run checks in a real CI workflow

Connect a real CI run to its source revision and the artifact it produced.

Guided practice: about 90 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Python/Git locally; a learner-owned GitHub repository and its current Actions allowance are required for real CI completion. Local rehearsal is available as partial preparation.

Download /training/devops-delivery-automation.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-delivery-automation folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/real-ci.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

A CI runner executes code with a specific identity and permissions. A passing local command is preparation; a CI run records the revision and environment that actually executed it.

## Guided practice

### Step 1

Start with the local rehearsal and inspect configs/workflow.yml. It grants only contents:read, receives no deployment secrets and uploads a source artifact after tests.

### Step 2

```sh
python3 shared/selfcheck.py
mkdir -p .github/workflows
cp configs/workflow.yml .github/workflows/relay.yml
```

### Step 3

In your own repository, commit the reviewed workflow/shared files and push using your chosen credentials. Check repository visibility and Actions allowance first. Record the run URL, revision and artifact identity from the actual workflow.

### Step 4

Send a deliberately failing source change to that same learning repository. Confirm the test job fails and the upload step does not produce a promotable artifact for that failed job.

### Step 5

If no repository/account is available, run the same commands locally and record this as a local rehearsal; leave the external CI observation outstanding.

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Make a corrected revision pass in CI and download its named artifact into a new directory.

2. Verify its manifest using shared/release.py and compare the manifest revision with the actual run's commit.

3. Reject a passing artifact from another revision when the release task expects the newly tested change.

## Finish line

The real-variant record links passing/failing CI runs to commits and artifacts; local-only work is labelled as rehearsal rather than a hosted CI receipt. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://docs.github.com/en/actions)
