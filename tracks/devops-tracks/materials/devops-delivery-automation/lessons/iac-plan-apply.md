# Provision owned infrastructure with OpenTofu

Create a small owned deployment from a reviewed infrastructure plan and reconcile drift.

Guided practice: about 90 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Owned local Docker daemon, OpenTofu 1.6+ and network access for the reviewed Docker provider. Do not point this at Ascend's daemon.

Download /training/devops-delivery-automation.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-delivery-automation folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/iac-plan-apply.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

Desired configuration, a plan, applied resources and state are distinct. A plan can replace or destroy resources even when it appears to be a small edit. Provider plugins act with the learner's permissions.

## Guided practice

### Step 1

Build the local Relay image and record its exact image ID. Inspect configs/tofu/main.tf: it creates a named lab network, volume and container with a loopback publication.

### Step 2

```sh
docker build -t ascend-relay:v1 .
docker image inspect ascend-relay:v1 --format '{{.Id}}'
cd configs/tofu
tofu init
```

### Step 3

Replace the example image ID below with your observed sha256 ID. Inspect the plan before applying it; retain .terraform.lock.hcl with the reviewed source, while state stays private.

### Step 4

```sh
tofu plan -var='relay_image_id=sha256:REPLACE_WITH_LOCAL_IMAGE_ID' -out=reviewed.plan
tofu show reviewed.plan
tofu apply reviewed.plan
```

### Step 5

From the track root, run the following version/write check. Change the release variable in a new reviewed plan and inspect whether replacement is required before applying. Keep a backup before any operation that could remove the owned data volume.

### Step 6

```sh
cd ../..
python3 shared/check_service.py --url http://127.0.0.1:18000 --expect-release tofu-v1 --write
```

### Step 7

Inspect the actual named container/network/volume and compare with tofu state list. A saved plan alone is not evidence of provisioned infrastructure.

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Change or remove the owned container outside OpenTofu, then inspect refresh/plan output before reconciling.

2. Reject a plan that would destroy data you have not backed up. Retain a valid backup before the final reviewed tofu destroy.

3. After destruction, inspect actual owned resources rather than assuming a zero exit code accounted for every leftover.

## Finish line

Plan, applied inventory and observed service agree; drift is detected; restoration or teardown follows an explicit data/ownership decision. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://opentofu.org/docs/intro/core-workflow/)
