# Operate a persistent Linux service

Keep a service running across process failure and a guest reboot while preserving its data.

Guided practice: about 90 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

An owned Debian/Ubuntu-class Linux guest with systemd, Python and sudo; guest console recovery available.

Download /training/devops-service-foundations.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-service-foundations folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/service-lifecycle.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

systemd owns a process lifecycle, identity, working directory and restart policy. Liveness, readiness and durable data differ. Restart=on-failure is not an availability guarantee when the host loses power.

## Guided practice

### Step 1

Perform the following only inside your disposable guest, after copying the extracted track there. Inspect configs/relay.service; it uses DynamicUser and StateDirectory to avoid a permanent privileged application user.

### Step 2

```sh
sudo install -d /opt/ascend-relay/shared
sudo install -m 0644 shared/relay.py /opt/ascend-relay/shared/relay.py
sudo install -m 0644 configs/relay.service /etc/systemd/system/ascend-relay.service
sudo systemctl daemon-reload
sudo systemctl enable --now ascend-relay
```

### Step 3

Check lifecycle and application state independently. Record the service user and its actual data path.

### Step 4

```sh
systemctl status ascend-relay --no-pager
systemctl show ascend-relay -p MainPID -p User -p StateDirectory
journalctl -u ascend-relay -n 20 --no-pager
python3 shared/check_service.py --expect-release service-v1 --write
```

### Step 5

Stop just the owned process through systemd's signal interface, observe recovery, then deliberately stop the unit. A requested stop should remain stopped.

### Step 6

```sh
sudo systemctl kill --signal=SIGKILL --kill-whom=main ascend-relay
sleep 3
systemctl is-active ascend-relay
sudo systemctl stop ascend-relay
systemctl is-active ascend-relay
```

### Step 7

Start it again, reboot the owned guest through its normal controls, reconnect and verify that the saved synthetic update survives. Do not reboot the shared Ascend server.

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Introduce a wrong ExecStart path in a copied unit installed only in the guest; inspect the failure and journal before repairing it.

2. Recover the intended unit, confirm process identity/readiness/version and prove the earlier update remains.

3. Disable and remove only ascend-relay when finished, or explicitly retain it for the next guest deployment task.

## Finish line

A process failure recovers, a deliberate stop remains stopped, reboot restores the service, and required state survives; wrong configuration is diagnosed from observed evidence. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
