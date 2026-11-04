# Ship, observe and recover the complete service

Ship, measure and recover an identifiable service with a reproducible handover.

Guided practice: about 120 minutes. Independent application: about 180 minutes, split over sessions when needed.

## Before you start

An owned guest/container target or the separately qualified Kubernetes route; real learner-owned CI if claiming a hosted pipeline.

Download /training/devops-reliability-orchestration.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-reliability-orchestration folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/operational-capstone.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

A capstone combines artifact identity, appropriate access, service health, state recovery, permissions and a handover that another person can reproduce. Passing a single endpoint check does not satisfy the whole operation.

## Guided practice

### Step 1

Select a VM/container deployment route or the stateless Kubernetes route and state its evidence limits. Build/test an identifiable release through the previous track's actual pipeline or clearly labelled local rehearsal.

### Step 2

Deploy it, record the current route/version, and verify the relevant read/write or read-only controls. Retain a consistent snapshot for the stateful route.

### Step 3

Define a modest workload and service objective, observe actual results, then introduce a fresh incident: old healthy artifact, denied credential, route failure, readiness error or lost active data.

### Step 4

Recover the expected behaviour and required data, measure the result, and hand over a runbook with artifact, access, configuration, resource, backup and cleanup details.

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Use a fresh target or a fresh reviewer to reproduce the deployment and required restoration without relying on unexplained pre-existing state.

2. Demonstrate one correct denial as well as success, and state remaining public-network, hardware, provider or scale assumptions.

3. Delete only the owned cluster/resources when finished, or explicitly retain the chosen service and its ongoing resource responsibilities.

## Finish line

The actual release, detection, recovery, state/permission controls and handover all work within the stated environment; local/physical/public claims remain distinct. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://sre.google/workbook/implementing-slos/)
