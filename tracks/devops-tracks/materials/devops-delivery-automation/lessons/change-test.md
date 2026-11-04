# Make a change fail usefully

Make a behavioural regression fail a meaningful test, then repair the source.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Python 3.11+ and Git in an extracted learning repository.

Download /training/devops-delivery-automation.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-delivery-automation folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/change-test.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

A test is useful when an incorrect behaviour fails for the intended reason. Source edits and generated release files must be kept separate. Do not make a failing test green by removing its assertion.

## Guided practice

### Step 1

Read gitignore.example and initialize an isolated learning repository in the extracted folder if you do not already have one. Record the original shared files before the experiment. Run the reference checks: they create temporary loopback services and verify actual response, data, release and recovery behaviour.

### Step 2

```sh
python3 shared/selfcheck.py
```

### Step 3

In a working source copy, change the unknown-endpoint response from 404 to 200. Predict which control will fail, rerun the selfchecks, and retain the actual failure.

### Step 4

Restore the correct behaviour through Git or your saved source copy. Add a new control not already present, such as rejecting a missing message field, and make an intentional regression prove that control fails for the intended reason.

### Step 5

```sh
git diff -- shared/relay.py shared/selfcheck.py
python3 shared/selfcheck.py
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Introduce a different behavioural regression: accept a reused idempotency key with different content or permit a write on the read-only route.

2. Show a test that fails before the repair and passes afterward while the ordinary write still works.

3. Record the commit/revision and the failing/passing control, not only an overall success message.

## Finish line

An intended wrong behaviour is detected; the legitimate control stays covered and the source change is traceable. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://git-scm.com/book/en/v2)
