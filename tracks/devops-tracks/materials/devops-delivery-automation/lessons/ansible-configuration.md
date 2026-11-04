# Configure an owned guest idempotently

Apply repeatable guest configuration and recover a drifted service.

Guided practice: about 90 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Owned Debian/Ubuntu-class guest, verified SSH identity, sudo within that guest and Ansible on the learner PC.

Download /training/devops-delivery-automation.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-delivery-automation folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/ansible-configuration.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

Infrastructure creates resources; configuration management establishes software/service state. Idempotence concerns the specified desired state, not whether a command prints changed=0 after ignoring failures.

## Guided practice

### Step 1

Edit the documentation address/user in configs/ansible/inventory.ini for one owned guest. Inspect the inventory and exact target before any playbook run.

### Step 2

```sh
ansible-inventory -i configs/ansible/inventory.ini --graph
ansible relay_targets -i configs/ansible/inventory.ini --limit relay1 -m ping
```

### Step 3

Read the playbook and service template. Run in check/diff mode, then apply only to that guest. Do not publish inventory credentials or raw facts containing private data.

### Step 4

```sh
ansible-playbook -i configs/ansible/inventory.ini configs/ansible/playbook.yml --limit relay1 --check --diff
ansible-playbook -i configs/ansible/inventory.ini configs/ansible/playbook.yml --limit relay1
```

### Step 5

Run the same playbook again and inspect actual service state. Reach the private service through the guest SSH forwarding route from the first track.

### Step 6

```sh
ansible-playbook -i configs/ansible/inventory.ini configs/ansible/playbook.yml --limit relay1
ssh -N -L 127.0.0.1:18000:127.0.0.1:8000 YOUR_OWN_GUEST
```

### Step 7

```sh
python3 shared/check_service.py --url http://127.0.0.1:18000 --expect-release ansible-v1
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Introduce drift in the owned unit's release/configuration and rerun the playbook to recover the intended state.

2. Add a second owned guest only when your local memory envelope permits it; target one guest and demonstrate the other is unchanged.

3. Explain the check-mode limits and prove the service actually responds after convergence.

## Finish line

The intended configuration is applied and a repeated run is idempotent; a drifted service recovers without mutating an unrelated target. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://docs.ansible.com/ansible/latest/getting_started/)
