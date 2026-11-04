# Deploy to an owned remote guest

Deploy to an owned guest and reach its private service through authenticated SSH access.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Owned Linux guest reachable by SSH, verified host-key fingerprint and an SSH client. A local VM is sufficient.

Download /training/devops-service-foundations.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-service-foundations folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/ssh-deployment.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

SSH gives a route and authenticated access to a guest OS; it does not grant hypervisor administration. Host keys identify the server. Copying an artifact, starting a process and publishing a website are separate operations.

## Guided practice

### Step 1

Copy configs/ssh_config.example to a working file, replace its documentation address/user with your owned guest, and choose a dedicated key. Verify its public host-key fingerprint through the guest console before accepting it.

### Step 2

```sh
mkdir -p work
cp configs/ssh_config.example work/ssh_config
ssh -F work/ssh_config relay-lab
```

### Step 3

On the guest, prepare a private learning folder; from your PC copy only the reviewed shared tools and service materials. Keep synthetic credentials out of the artifact.

### Step 4

```sh
ssh -F work/ssh_config relay-lab 'mkdir -p ascend-relay-lab'
scp -F work/ssh_config -r shared configs relay-lab:ascend-relay-lab/
```

### Step 5

Inside the guest, use the service-lifecycle procedure, or start this foreground equivalent from ascend-relay-lab: python3 shared/relay.py --data work/relay.sqlite --release service-v1. Keep that guest terminal open. From a separate PC terminal, forward one private service port.

### Step 6

```sh
ssh -F work/ssh_config -N -L 127.0.0.1:18000:127.0.0.1:8000 relay-lab
```

### Step 7

```sh
python3 shared/check_service.py --url http://127.0.0.1:18000 --expect-release service-v1
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Create an access failure by using the wrong forwarded destination port in a separate client command. Diagnose it while the guest service remains healthy.

2. Recover access without disabling host verification or exposing guest administration publicly.

3. Record guest identity, artifact/version, private route and console recovery path; close the forwarding process and confirm access ends.

## Finish line

The intended guest and release are reached through a scoped authenticated path; a wrong destination is diagnosed and forwarding cleanup is observed. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://man.openbsd.org/ssh)
