# Operate within a resource and storage budget

Measure resource use and recover from an explicitly bounded resource failure.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Owned Linux VM/container environment; physical Pi/spare host optional. No disk-pressure test on the shared server.

Download /training/devops-reliability-orchestration.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-reliability-orchestration folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/operating-budget.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

Memory, CPU quota, write volume, retained metrics, image cache and free space are independent constraints. A 16-core desktop with 16 GB RAM is not an unlimited cluster; a microSD server needs controlled writes and recovery.

## Guided practice

### Step 1

Inventory only the lab's processes/containers/volumes and record host reserve. Use OS tools and the actual resource controls before proposing more replicas.

### Step 2

```sh
df -h
df -i
docker system df
docker stats --no-stream
```

### Step 3

Review the supplied container/Pod memory and CPU limits. Record whether the chosen boundary is a quota, weight, request or maximum, and inspect actual events when a bounded owned workload exceeds it.

### Step 4

For a concrete memory-bound experiment, first confirm ascend-relay-budget is an unused container name. The following container has no network or persistent volume and an explicit 48 MiB cap; it attempts one 80 MiB allocation. An unsupported memory controller or swap setting is a setup failure to diagnose, not evidence that the limit worked.
```sh
docker run --name ascend-relay-budget --memory 48m --memory-swap 48m --cpus 0.25 --network none python:3.12-slim python -c "sample = bytearray(80 * 1024 * 1024); print(len(sample))"
docker inspect ascend-relay-budget --format 'OOMKilled={{.State.OOMKilled}} ExitCode={{.State.ExitCode}}'
docker rm ascend-relay-budget
```

### Step 5

Keep logs and Prometheus retention bounded on the learner PC. For a systemd guest, inspect its journal usage and configure a guest-local retention policy after retaining required evidence.

### Step 6

```sh
journalctl --disk-usage
systemctl show ascend-relay -p MemoryMax -p TasksMax
```

### Step 7

When available, run the same service on a supported Pi or spare PC. Record uname -m, actual memory, power/cooling and storage observations, with the same release and workload. The advantage is an independent, always-on physical host; a VM on your PC covers software practice without buying hardware, but does not measure flash endurance or a separate power failure.

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Change one budget in an owned disposable workload and diagnose the resulting throttle, rejection or failure using observed counters rather than guessed hardware capacity.

2. Restore the valid budget, verify service/data recovery and list the images/volumes still intentionally retained.

3. Plan a later SSD/RAM/second-host upgrade around the measured constraint, preserving the existing runbook and earlier skill evidence.

## Finish line

The learner accounts for aggregate resources and writes, demonstrates bounded failure/recovery, and distinguishes PC models from physical-device measurements. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://prometheus.io/docs/prometheus/latest/getting_started/)
