# Recover a complete deployment

Reproduce a complete deployment and recover its release, route and saved data.

Guided practice: about 120 minutes. Independent application: about 180 minutes, split over sessions when needed.

## Before you start

The local tools and owned guest/container route used in this track.

Download /training/devops-service-foundations.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-service-foundations folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/foundation-capstone.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

A reliable explanation connects client, edge, process, release and data rather than stopping at a green status. A fresh target is a stronger replay than the terminal where the original setup happened.

## Guided practice

### Step 1

Use a fresh local process first; the owned-guest extension can use its systemd data path. From the track root, build/select an identifiable artifact and start it in Terminal A.

### Step 2

```sh
python3 shared/release.py build --source shared/relay.py --out work/foundation-artifact --release foundation-v1 --revision local-capstone
python3 shared/release.py select --artifact work/foundation-artifact --state work/foundation-current.json
python3 shared/release.py serve --state work/foundation-current.json -- --port 8000 --data work/foundation.sqlite
```

### Step 3

In Terminal B start the supplied teaching edge; in Terminal C require the intended release directly and through the edge. Write one synthetic update directly, since the teaching edge is GET-only.

### Step 4

```sh
python3 shared/edge.py --config configs/route.json --port 9000
```

### Step 5

```sh
python3 shared/check_service.py --expect-release foundation-v1 --write
python3 shared/check_service.py --url http://127.0.0.1:9000 --expect-release foundation-v1
python3 shared/backup.py create --source work/foundation.sqlite --destination backups/foundation.sqlite
```

### Step 6

Record the update ID, artifact identity and actual state path. Stop only the teaching edge, then restart it using configs/route-fault.json. Diagnose the failure with direct and edge observations before repairing the route in a working copy.

### Step 7

Write a handover with the actual release, start/stop commands, restore-to-new-path command, access method, save locations and known limits. A guest variant must inspect its actual /var/lib/ascend-relay state location instead of copying the local work path.

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Recreate the service on a new disposable data/target path and restore the required synthetic data.

2. Introduce a second cause: an old but healthy release or an unavailable data path. Recover the expected user behaviour and version.

3. Have a fresh terminal or reviewer follow the handover; confirm intended cleanup without deleting unrelated guests, volumes or files.

## Finish line

A fresh target reproduces the correct release and retained data; the learner diagnoses two distinct faults and provides a usable runbook. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://sre.google/workbook/implementing-slos/)
