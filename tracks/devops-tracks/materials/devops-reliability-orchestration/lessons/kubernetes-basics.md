# Deploy a small Kubernetes workload

Operate a small local Kubernetes service and diagnose endpoint selection.

Guided practice: about 90 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Owned local Docker environment, kind and kubectl; budget roughly 4–6 GiB for this sequential cluster lab and inspect actual use.

Download /training/devops-reliability-orchestration.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-reliability-orchestration folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/kubernetes-basics.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

A controller reconciles declared state; a Service selects endpoints by labels. Pod readiness controls routing eligibility. Container image identity and guest/host boundaries still matter.

## Guided practice

### Step 1

Stop conflicting local deployments. Check kind get clusters first; if ascend-relay already exists, identify its owner and choose an unused lab name or intentionally resume your own cluster. The commands below assume this is a new, distinctly named learner-owned cluster.

### Step 2

```sh
docker build -t ascend-relay:v1 .
kind create cluster --name ascend-relay
kind load docker-image ascend-relay:v1 --name ascend-relay
kubectl --context kind-ascend-relay apply -f configs/namespace.yaml
```

### Step 3

Inspect deployment.yaml before applying. It runs two read-only replicas with bounded resources and an ephemeral scratch volume; it is not a writable replicated SQLite design.

### Step 4

```sh
kubectl --context kind-ascend-relay apply -f configs/deployment.yaml -f configs/service.yaml
kubectl --context kind-ascend-relay -n ascend-relay rollout status deployment/relay --timeout=120s
kubectl --context kind-ascend-relay -n ascend-relay get pods,service,endpoints
```

### Step 5

Keep a port-forward in one terminal and verify the actual service from another.

### Step 6

```sh
kubectl --context kind-ascend-relay -n ascend-relay port-forward service/relay 18000:80
```

### Step 7

```sh
python3 shared/check_service.py --url http://127.0.0.1:18000 --expect-release k8s-v1
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Apply service-fault.yaml. Observe running pods but an empty/mismatched endpoint selection. Diagnose and restore the intended selector.

2. Demonstrate that writes are rejected by the read-only workload; this is expected, not a database outage.

3. Retain the actual context/namespace/image/endpoint observations and owned-cluster cleanup command.

4. When the next rollout lesson and your evidence are complete, remove only this owned cluster with kind delete cluster --name ascend-relay. Inspect kind get clusters and retained Docker images afterward; deleting a cluster is not a generic image-prune operation.

## Finish line

A real cluster serves the expected version; readiness/selection and read-only controls are demonstrated without claiming physical HA. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://kind.sigs.k8s.io/docs/user/quick-start/)
