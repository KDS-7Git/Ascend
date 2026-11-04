# Trace a real request

Trace a real HTTP request and distinguish a stopped service, a missing route and the wrong release.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Python 3.11+ and two terminals on your PC; no account or VM needed.

Download /training/devops-service-foundations.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-service-foundations folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/request-path.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

A port belongs to a listening process. DNS/address selection, transport connection, HTTP status, readiness and release identity are separate observations. A 200 from the wrong release is still a failed deployment.

## Guided practice

### Step 1

Extract the ZIP into its own folder. Terminal A stays open while the service runs. The startup record gives the actual database location. Only synthetic notes belong here.

### Step 2

```sh
python3 shared/relay.py --host 127.0.0.1 --port 8000 --data work/relay.sqlite --release v1
```

### Step 3

In Terminal B, predict each response before checking it. The explicit write creates one sample update and verifies replay/conflict handling.

### Step 4

```sh
python3 shared/check_service.py --url http://127.0.0.1:8000 --expect-release v1 --write
```

### Step 5

Compare the working URL with port 8001 (where you have started nothing) and /not-an-endpoint. Connection refusal and HTTP 404 come from different layers.

### Step 6

```sh
curl -i http://127.0.0.1:8000/version
curl -i http://127.0.0.1:8001/version
curl -i http://127.0.0.1:8000/not-an-endpoint
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Start a second owned Relay process on port 8002 with --release v2 and a different data path. Both /health endpoints should work.

2. A client expects v2 but still uses the first URL. Diagnose with release evidence, update the client address, and retain the before/after results.

3. Stop only your two foreground services with Ctrl+C and rerun one check to distinguish a stopped process from an HTTP failure.

## Finish line

A request trace identifies the process/address, three distinct failure types and the correct version; actual update and replay results are retained. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://developer.mozilla.org/en-US/docs/Web/HTTP)
