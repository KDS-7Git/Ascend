# Use the Linux shell and service files

Use paths, permissions and process observations to repair a small Linux service.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Python 3.11+; Linux VM or Linux PC for POSIX permission/process commands.

Download /training/devops-service-foundations.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-service-foundations folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/linux-shell.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

Quoting, paths, permissions, pipes, redirection, exit status and process signals explain why a service starts in one terminal but fails elsewhere. Use a disposable Linux guest for OS operations; owning a terminal does not grant host administration.

## Guided practice

### Step 1

Read shared/README.md. In your extracted folder create named working locations, and keep terminal output separate from application state.

### Step 2

```sh
mkdir -p work notes
python3 --version
pwd
ls -la shared
python3 shared/relay.py --help > notes/relay-help.txt
```

### Step 3

Start Relay in Terminal A using a data path containing a space; quote it. Observe the process and listener from Terminal B.

### Step 4

```sh
python3 shared/relay.py --data 'work/first service/relay.sqlite' --release shell-v1
```

### Step 5

```sh
ps -ef | grep '[r]elay.py'
ss -ltnp
python3 shared/check_service.py --expect-release shell-v1
```

### Step 6

While the service is stopped, create a new synthetic token file with restricted permissions and inspect its owner. Do not copy a real key into the archive.

### Step 7

```sh
mkdir -p secrets
printf '%s\n' 'synthetic-first-token' > secrets/write-token.txt
chmod 600 secrets/write-token.txt
ls -l secrets/write-token.txt
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. On the owned Linux guest, create an unwritable exercise directory and try using it as a new database location. Record the actual permission error.

2. Repair ownership or the selected path for the intended service user; do not use chmod 777 or run the application as host root.

3. Demonstrate that quoting preserves one path argument and that the valid service still responds after the repair.

## Finish line

The learner explains actual stdout/stderr and exit behaviour, repairs a file/identity fault with narrow permissions, and proves the legitimate path works. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://docs.python.org/3/tutorial/)
