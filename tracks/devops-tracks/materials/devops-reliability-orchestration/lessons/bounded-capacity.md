# Bound concurrency and compare workloads

Compare controlled workloads and explain how concurrency limits change useful throughput.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Python 3.11+ and owned local target; optional k6 CLI for the fixed-arrival comparison.

Download /training/devops-reliability-orchestration.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-reliability-orchestration folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/bounded-capacity.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

Concurrency is work in progress; parallelism is simultaneous execution. Worker/pool/queue limits and CPU quota describe different boundaries. A closed client slows its offered work when the service slows.

## Guided practice

### Step 1

Start an isolated service with a short simulated dependency delay and small worker limit. It remains a local experiment, not a stress test of the shared Ascend machine.

### Step 2

```sh
python3 shared/relay.py --port 8000 --data work/load.sqlite --release load-v1 --workers 2 --delay-ms 120
```

### Step 3

Run a bounded client experiment and record its printed actual window. Use that window when analyzing the CSV rather than inventing a duration.

### Step 4

```sh
python3 shared/probe_load.py --clients 4 --requests 24 --output notes/load-two-workers.csv
```

### Step 5

Use the window_seconds printed by that run: python3 shared/analyze.py notes/load-two-workers.csv --window-seconds YOUR_OBSERVED_SECONDS. The default objectives are illustrative; rejected work may correctly make this overload experiment exit with status 1.

### Step 6

Repeat with one controlled change, such as --workers 1 or --delay-ms 250, using a new output filename. Inspect successful, rejected and failed work plus response durations.

### Step 7

With k6 installed, run the supplied low-rate ten-second fixed-arrival exercise and record dropped_iterations as well as latency/errors.

### Step 8

```sh
k6 run configs/k6.js
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Keep workload/dataset/client placement fixed while changing one worker or queue boundary. Explain both any improvement and any increased rejection.

2. Calculate a first CPU/memory/network budget from observed inputs and reserves. Do not use p95 in Little's Law or claim users-per-GB.

3. Recover normal work after the overload and verify the actual state/response controls still pass.

## Finish line

The comparison counts all work, identifies the limiting boundary, preserves correctness and states the measurement scope and generator limits. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/)
