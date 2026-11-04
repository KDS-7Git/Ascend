# Build and identify a runtime image

Follow source, base and runtime image identities through an actual container build.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Owned Docker environment; optional learner-owned registry namespace for publication.

Download /training/devops-delivery-automation.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-delivery-automation folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/image-identity.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

OCI tags name references; digests identify image content. Source artifact identity, base image identity and built image identity each answer a different question. Registry access is a separate capability.

## Guided practice

### Step 1

Build and verify a source artifact, then copy its verified entrypoint into a fresh minimal build context. This ties the image bytes to the artifact, rather than building an unrelated working-tree copy. Record the resolved base reference and image ID.

### Step 2

```sh
python3 shared/release.py build --source shared/relay.py --out work/ci-artifact --release image-v1 --revision local-reviewed
python3 shared/release.py verify --artifact work/ci-artifact
mkdir -p work/image-context/shared
cp work/ci-artifact/relay.py work/image-context/shared/relay.py
cp Dockerfile work/image-context/Dockerfile
cmp work/ci-artifact/relay.py work/image-context/shared/relay.py
docker pull python:3.12-slim
docker image inspect python:3.12-slim --format '{{json .RepoDigests}}'
docker build -t ascend-relay:v1 work/image-context
docker image inspect ascend-relay:v1 --format '{{.Id}}'
```

### Step 3

For a repeatable rebuild, replace the mutable PYTHON_IMAGE default with the actual repo@sha256 digest you just inspected using docker build --build-arg PYTHON_IMAGE=YOUR_RECORDED_BASE_REFERENCE. Keep the Dockerfile and that reference with the image record.

### Step 4

Run the image under a disposable name and loopback port. Compare runtime /version with the image metadata and configuration.

### Step 5

```sh
docker run --rm --name ascend-relay-image -p 127.0.0.1:18000:8000 ascend-relay:v1
```

### Step 6

```sh
python3 shared/check_service.py --url http://127.0.0.1:18000 --expect-release container-v1
```

### Step 7

For the registry variant, authenticate only to your owned namespace, push the chosen image, record its repository digest, then pull/run that exact digest in another disposable environment. Keep registry secrets out of the notebook.

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Build a second image under a different tag, move a familiar tag to it, and show that the familiar name is not content identity.

2. Use the recorded digest/ID to select the intended image and verify the correct source/runtime combination.

3. Show that publication/pull evidence exists only when a real registry operation occurred.

## Finish line

The learner distinguishes source, base, image and runtime identity; a moved-tag negative case cannot silently replace the intended release. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://docs.docker.com/get-started/)
