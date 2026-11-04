# Measure service signals and an SLO

Measure traffic, latency, errors and saturation without hiding failed work.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Python 3.11+; optional Prometheus/Grafana installed on the learner PC for live monitoring.

Download /training/devops-reliability-orchestration.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-reliability-orchestration folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/service-signals.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

Latency, traffic, errors and saturation describe different aspects of service behaviour. Count failed/dropped work in the denominator; a lower average after rejecting most traffic is not improved capacity.

## Guided practice

### Step 1

Inspect the recorded baseline and incident CSV fixtures. Both contain 50 attempted requests in the stated 60-second window. Predict which thresholds fail.

### Step 2

```sh
python3 shared/analyze.py fixtures/baseline.csv --window-seconds 60
python3 shared/analyze.py fixtures/incident.csv --window-seconds 60
```

### Step 3

Start a real v1 Relay in Terminal A, then inspect /metrics before and after several checks in Terminal B. The counter names distinguish responses, active connections and admission rejections.

### Step 4

```sh
python3 shared/relay.py --data work/signals.sqlite --release v1
```

### Step 5

```sh
curl http://127.0.0.1:8000/metrics
python3 shared/check_service.py --expect-release v1
curl http://127.0.0.1:8000/metrics
```

### Step 6

For the live extension, start a local Prometheus with short bounded retention. The supplied target expects Relay on the same host; use the correct actual address if you choose another topology.

### Step 7

```sh
prometheus --config.file=configs/prometheus.yml --storage.tsdb.path=work/prometheus --storage.tsdb.retention.time=1h --storage.tsdb.retention.size=128MB --web.listen-address=127.0.0.1:9090
```

### Step 8

Query rate(relay_admission_rejected_total[1m]) and target up. Optionally import configs/grafana-dashboard.json into your own local Grafana and select the actual datasource.

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Change the measurement window or omit failed requests in a scratch calculation and show why the claim changes misleadingly.

2. Generate a few deliberate failures against your own service, observe the actual counters, and state what remains unmeasured by these simple signals.

3. Define an SLI numerator/denominator/window and a proposed objective justified for this lab, not a universal business promise.

## Finish line

Correct calculations include all attempts and units; live metrics are distinct from recorded datasets; the learner rejects a misleading green/low-CPU conclusion. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://sre.google/workbook/implementing-slos/)
