# Promote one artifact and roll it back

Activate a tested release, detect the wrong version and restore the earlier artifact.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Python 3.11+ and two terminals; optional owned staging guest.

Download /training/devops-delivery-automation.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-delivery-automation folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/promotion-rollback.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

Delivery selects a tested artifact; deployment makes it active. Changing the pointer does not change already running code. Stateless rollback does not undo an incompatible data migration.

## Guided practice

### Step 1

Build v1 and v2 artifacts from known source revisions. Select v1 and start the selected service in Terminal A.

### Step 2

```sh
python3 shared/release.py build --source shared/relay.py --out work/releases/v1 --release v1 --revision reviewed-a
python3 shared/release.py build --source shared/relay.py --out work/releases/v2 --release v2 --revision reviewed-b
python3 shared/release.py select --artifact work/releases/v1 --state work/current.json
python3 shared/release.py serve --state work/current.json -- --data work/state.sqlite --port 8000
```

### Step 3

Check v1, then change the selected pointer from Terminal B. Observe that the running process still reports v1 until deliberately restarted.

### Step 4

```sh
python3 shared/release.py select --artifact work/releases/v2 --state work/current.json
python3 shared/check_service.py --expect-release v1
```

### Step 5

Restart the selected service and require v2. Treat an unexpected response as a failed release; restore the v1 selection and restart to recover.

### Step 6

```sh
python3 shared/release.py select --artifact work/releases/v1 --state work/current.json
```

### Step 7

Inspect fixtures/pipeline.json. Explain why its selected failed commit is not eligible for release, then compare that reasoning with your real test/artifact records.

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Modify a copy of a built artifact after its manifest was written; selection must reject it without changing the current pointer.

2. Create a synthetic update before a restart/promotion and verify its continued presence afterward.

3. Explain how an incompatible database migration would change this rollback procedure; do not claim the code pointer reverses data changes.

## Finish line

Only a verified artifact is selected; process activation is observed independently; recovery returns the correct version and preserves the required data. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://docs.github.com/en/actions)
