# Recreate the release path

Recreate an identifiable release on a clean target and recover a failed activation.

Guided practice: about 120 minutes. Independent application: about 180 minutes, split over sessions when needed.

## Before you start

The owned local/container or guest environment used in this track; real CI variant requires the learner's repository.

Download /training/devops-delivery-automation.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-delivery-automation folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/delivery-capstone.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

A useful pipeline can reproduce a clean target, choose the tested immutable artifact and recover a failed activation. Its inventory, secrets and data ownership must remain understandable.

## Guided practice

### Step 1

Choose the local Docker/OpenTofu route or the owned guest/Ansible route. Record the actual source → test → artifact → target chain and separate credentials.

### Step 2

Create a fresh target, deploy a verified artifact, observe the required version and add one synthetic update.

### Step 3

Introduce a faulty release decision or configuration, detect it with the appropriate service/version control, and recover using the recorded earlier artifact.

### Step 4

Retain the exact plan/configuration, CI or local run identity, artifact hash, current runtime observations and a cleanup inventory in your notebook/runbook.

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Have a fresh terminal or reviewer reproduce the target from the runbook without reusing an unexplained existing container/guest.

2. Use an old but healthy artifact as the incident; the correct version check must catch it.

3. Restore the expected version and data, then either retain the target explicitly or destroy only the owned resources with evidence.

## Finish line

A clean target reproduces the release and fails/recover controls correctly; the handover explains identity, state, trust and remaining external limits. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://sre.google/workbook/implementing-slos/)
