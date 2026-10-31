# Ascend CLI demonstration

These are synthetic demonstration records in a disposable profile, not the owner's learning log.
Desktop notification delivery is replaced by a local stub; no live desktop delivery is claimed.

```console
$ ascend pack install home-hack-lab
{
  "id": "home-hack-lab",
  "nodes": 34,
  "commands": [
    "ping -c 1 -W 2 192.168.1.50",
    "ssh -o BatchMode=yes -o ConnectTimeout=5 pi@192.168.1.50 true",
    "ssh -o BatchMode=yes -o ConnectTimeout=5 pi@192.168.1.50 docker --version",
    "curl -sf --max-time 5 http://192.168.1.50:3000"
  ],
  "plugins": [],
  "reviewed": false
}
```

```console
$ ascend mission start home-hack-lab
{
  "id": 1,
  "title": "Home hack lab: attack and harden my own Pi"
}
```

```console
$ ascend backfill pi-reachable ssh-key-login
[
  {
    "node": "pi-reachable",
    "status": "done",
    "how": "manual"
  },
  {
    "node": "ssh-key-login",
    "status": "done",
    "how": "manual"
  }
]
```

```console
$ ascend levels
Build the lab (main, open) [#####-----] 2/4 steps · 0 active days · 0 min
Recon and attack the basics (main, locked) [----------] 0/4 steps · 0 active days · 0 min
Go deeper: more of the OWASP Top 10 (main, locked) [----------] 0/3 steps · 0 active days · 0 min
Harden and report (main, locked) [----------] 0/2 steps · 0 active days · 0 min
Daily warm-up (Bandit) (side, open) [----------] 0/21 steps · 0 active days · 0 min
```

```console
$ ascend
Mission : Home hack lab: attack and harden my own Pi
Level   : Build the lab [#####-----] 2/4 steps · 0 active days
Next    : docker-on-pi — Docker running on the Pi [draft] (~120 min); `docker --version` works on the Pi and `docker run hello-world` succeeds
Quick win: bandit-13 — OverTheWire Bandit, level 13 [draft] (~30 min)
Streak  : 0 days (best 0) · freeze available: 1
Today   : Pending — log before your 04:00 rollover
```

```console
$ ascend 20
Mission : Home hack lab: attack and harden my own Pi
Next    : No step fits or remains open; try ascend split or ascend levels
Streak  : 0 days (best 0) · freeze available: 1
Today   : Pending — log before your 04:00 rollover
```

```console
$ ascend done 'I can explain how file permissions affect access' 'Continue with the next small exercise' --node bandit-13 --complete --minutes 20
Logged entry 1 for 2026-10-31. Node complete. Manually confirmed against done_when
```

```console
$ ascend stats
Streak: 1 days · best: 1
Days logged in last 30: 1
Freezes used this week: 0
Minutes this week: 20
  Build the lab: 0 min total
  Recon and attack the basics: 0 min total
  Go deeper: more of the OWASP Top 10: 0 min total
  Harden and report: 0 min total
  Daily warm-up (Bandit): 20 min total
```

```console
$ ascend config nudge-time 21:30
{
  "nudge_time": "21:30"
}
```

```console
$ ascend config nudge-test
{
  "sent": true,
  "test": true
}
```

```console
$ ascend install-nudge --dry-run
{
  "ascend-nudge.service": "[Unit]\nDescription=Ascend daily reminder\n\n[Service]\nType=oneshot\nEnvironment=\"ASCEND_HOME=<demo-home>/profile\"\nExecStart=\"/home/kds-hacker/Documents/Projects/ascend/.venv/bin/python\" -m ascend nudge\n",
  "ascend-nudge.timer": "[Unit]\nDescription=Check Ascend reminder schedule\n\n[Timer]\nOnCalendar=*-*-* *:*:00\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n"
}
```
