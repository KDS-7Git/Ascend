# Restore consistent data and report loss

Restore a consistent snapshot into a clean service and measure the data lost.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Python 3.11+ and a running owned Relay service with synthetic data.

Download /training/devops-reliability-orchestration.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-reliability-orchestration folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/consistent-recovery.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

A snapshot is useful when it restores the required records into a clean target. SQLite's backup API produces a consistent snapshot; a live file copy can omit WAL state. RPO and RTO describe data loss and recovery time.

## Guided practice

### Step 1

Start a dedicated stateful service and add a named synthetic update. Record its ID and the clock time before the backup.

### Step 2

```sh
python3 shared/relay.py --data work/recovery.sqlite --release recovery-v1
```

### Step 3

```sh
python3 shared/check_service.py --expect-release recovery-v1 --write
python3 shared/backup.py create --source work/recovery.sqlite --destination backups/before-incident.sqlite
```

### Step 4

Write another update after the snapshot while the service is still running; retain the new ID.

### Step 5

```sh
python3 shared/check_service.py --expect-release recovery-v1 --write
```

### Step 6

Now stop the original service with Ctrl+C. Restore into a new path; the helper refuses to overwrite an existing database.
```sh
python3 shared/backup.py restore --source backups/before-incident.sqlite --destination restored/relay.sqlite
python3 shared/backup.py inspect --source restored/relay.sqlite
```

### Step 7

Start a new service using restored/relay.sqlite while the original is stopped. Compare IDs, record counts and logical-record hashes, including the deliberately lost later write.

### Step 8

```sh
python3 shared/relay.py --data restored/relay.sqlite --release recovered-v1
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Create a damaged copy of a backup, inspect its failure, and preserve the original known-good snapshot.

2. Recover into another fresh path and report observed recovery time and the exact missing writes against your stated objective.

3. Place a backup on a separate device/host if available. Otherwise explain the unresolved common-disk failure domain.

## Finish line

A clean service uses restored data while the original is stopped; integrity/count/hash controls pass and data loss/recovery time are honestly measured. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://www.sqlite.org/backup.html)
