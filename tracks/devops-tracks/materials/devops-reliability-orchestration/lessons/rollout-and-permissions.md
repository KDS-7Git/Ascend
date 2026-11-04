# Recover a rollout and inspect permissions

Recover an unhealthy rollout and observe allowed and denied API permissions.

Guided practice: about 90 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

The owned kind cluster from the preceding lesson; kubectl permissions for that lab.

Download /training/devops-reliability-orchestration.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-reliability-orchestration folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/rollout-and-permissions.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

A Deployment revision, ready endpoints and image availability determine a rollout. Kubernetes permissions must be checked against the API, not inferred from a UI button. A namespaced role does not grant host administration.

## Guided practice

### Step 1

Record the current working revision and readiness. Cause a scoped image failure by selecting an unavailable local image; imagePullPolicy Never makes the failure visible without pulling arbitrary content.

### Step 2

```sh
kubectl --context kind-ascend-relay -n ascend-relay rollout history deployment/relay
kubectl --context kind-ascend-relay -n ascend-relay set image deployment/relay relay=ascend-relay:missing
kubectl --context kind-ascend-relay -n ascend-relay get pods
kubectl --context kind-ascend-relay -n ascend-relay describe deployment relay
```

### Step 3

Recover the recorded good revision and require ready endpoints again.

### Step 4

```sh
kubectl --context kind-ascend-relay -n ascend-relay rollout undo deployment/relay
kubectl --context kind-ascend-relay -n ascend-relay rollout status deployment/relay --timeout=120s
```

### Step 5

Create a scoped observer service account and bind the provided read-only role only in this namespace. Use the lab administrator's impersonation capability to check intended permissions.

### Step 6

```sh
kubectl --context kind-ascend-relay -n ascend-relay create serviceaccount observer
kubectl --context kind-ascend-relay apply -f configs/read-only-role.yaml
kubectl --context kind-ascend-relay -n ascend-relay create rolebinding observer --role=observer --serviceaccount=ascend-relay:observer
kubectl --context kind-ascend-relay -n ascend-relay auth can-i get pods --as=system:serviceaccount:ascend-relay:observer
kubectl --context kind-ascend-relay -n ascend-relay auth can-i delete deployments --as=system:serviceaccount:ascend-relay:observer
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Change a readiness path in an owned copied manifest, observe why running containers are not sufficient, and repair that fault independently from the image case.

2. Verify the observer cannot read another namespace's private resources or mutate this deployment; keep credentials out of evidence.

3. Recheck the intended application/version after recovery and identify which authorization result was actually observed.

## Finish line

A failed rollout is recovered, correct ready endpoints return, and allowed/denied API permissions are observed in the declared lab scope. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://kubernetes.io/docs/tutorials/kubernetes-basics/)
