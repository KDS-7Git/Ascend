# Build a versioned artifact

Build an identifiable release and detect a changed artifact before deployment.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Python 3.11+; Git for the source-history portion.

Download /training/devops-service-foundations.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-service-foundations folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/versioned-artifact.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

Source revision, immutable build output, runtime configuration and persistent data serve different purposes. A checksum detects an artifact change; it does not authenticate who produced it.

## Guided practice

### Step 1

Initialize a separate learning repository in the extracted track folder if needed. Copy gitignore.example to .gitignore before recording source; leave keys, databases and notes untracked.

### Step 2

```sh
git init
cp gitignore.example .gitignore
git add shared Dockerfile configs .gitignore
git status
```

### Step 3

Commit using your chosen local identity, then record the resulting commit ID. Build two copies with the same source and revision; the manifests should match.

### Step 4

```sh
git -c user.name='Relay Learner' -c user.email='learner@example.invalid' commit -m 'Start Relay lab'
python3 shared/release.py build --source shared/relay.py --out work/releases/v1 --release v1 --revision "$(git rev-parse HEAD)"
python3 shared/release.py build --source shared/relay.py --out work/releases/v1-copy --release v1 --revision "$(git rev-parse HEAD)"
diff work/releases/v1/manifest.json work/releases/v1-copy/manifest.json
```

### Step 5

Inspect the manifest, select the artifact, and run the selected release in a terminal. Configuration and data stay outside the artifact.

### Step 6

```sh
python3 shared/release.py verify --artifact work/releases/v1
python3 shared/release.py select --artifact work/releases/v1 --state work/current.json
python3 shared/release.py serve --state work/current.json -- --port 8000 --data work/runtime.sqlite
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Copy the v1 artifact to a new scratch directory, alter its relay.py and run the verifier: it must fail.

2. Build a genuinely new v2 artifact from the intended source revision rather than editing a released directory in place.

3. Show both artifact digests, the selected release and the HTTP version. Explain why a manifest hash alone is not provenance.

## Finish line

Two identical inputs produce identical manifests; a modified artifact is rejected; v2 has a traceable source/release identity and separate runtime state. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://git-scm.com/book/en/v2)
