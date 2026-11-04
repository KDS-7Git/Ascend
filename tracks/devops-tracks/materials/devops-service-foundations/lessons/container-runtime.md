# Package and recreate a container

Build a runtime image and prove which data survives container replacement.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Owned Docker/Podman-capable Linux environment; sufficient space for a Python base image. No public registry publication required.

Download /training/devops-service-foundations.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-service-foundations folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/container-runtime.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

An image is an artifact; a container is a running instance; a volume owns persistent state. Port publishing and the process's internal bind are separate. A tag can move, so record the actual image identity.

## Guided practice

### Step 1

Inspect Dockerfile and .dockerignore. Resolve the selected base image and retain its digest; this initial fixture accepts an explicit PYTHON_IMAGE build argument.

### Step 2

```sh
docker pull python:3.12-slim
docker image inspect python:3.12-slim --format '{{json .RepoDigests}}'
docker build -t ascend-relay:v1 .
docker image inspect ascend-relay:v1 --format '{{.Id}}'
```

### Step 3

Ensure your earlier port-8000 process is stopped, then start the named Compose project. Its published port binds loopback, its application is unprivileged, and its named volume stores state.

### Step 4

```sh
docker compose -p ascend-devops-foundation up -d --build
python3 shared/check_service.py --expect-release compose-v1 --write
docker compose -p ascend-devops-foundation ps
```

### Step 5

Recreate only the service and verify the update still exists. Stopping a project keeps its data volume by default.

### Step 6

```sh
docker compose -p ascend-devops-foundation up -d --force-recreate
curl http://127.0.0.1:8000/api/updates
docker compose -p ascend-devops-foundation down
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Run a disposable container without the persistent volume, create a synthetic update, remove/recreate that container, and observe the loss.

2. Restore the declared volume-based deployment and show why its state survives a container replacement.

3. Record the resolved base/image identities and all owned containers/volumes. Remove a data volume only after retaining the required backup.

## Finish line

Image identity, process identity, port policy and state ownership are observed; the disposable-state negative case differs from the durable deployment. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://docs.docker.com/get-started/)
