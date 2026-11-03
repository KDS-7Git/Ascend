# Shared runners and specialist capability gates

Reviewed 2026-11-03 as stage 6 of the
[local-lab execution plan](local-lab-execution-plan.md).

Ascend now uses its own temporary, data-only worker for one small policy
submission. Interactive environments can stay on the learner's PC or use the
separate [browser lab runner](server-lab-runner.md) for the seven reviewed
recipes. A general infrastructure orchestrator remains unnecessary for the
bounded JSON policy task; the deployed runner uses Ascend's fixed adapters.

## Chall-Manager evaluation

The inspected [Chall-Manager source](https://github.com/ctfer-io/chall-manager/tree/4ae8e4702268e012a63e9dc05e26e8a61603c1d5)
is pinned to `4ae8e4702268e012a63e9dc05e26e8a61603c1d5`. Its README still describes
public beta status. It supplies instance lifecycle, infrastructure scenarios,
optional pools and CTFd integration. Answer grading belongs to the surrounding
learning/CTF application.

The [quickstart](https://github.com/ctfer-io/chall-manager/blob/4ae8e4702268e012a63e9dc05e26e8a61603c1d5/README.md)
explicitly says it does not deploy target resources. The actual
[`examples/additional/main.go`](https://github.com/ctfer-io/chall-manager/blob/4ae8e4702268e012a63e9dc05e26e8a61603c1d5/examples/additional/main.go)
serializes request configuration into connection information and creates no
provider resource. Running that example would not validate a lab deployment.

Its [security design](https://github.com/ctfer-io/chall-manager/blob/4ae8e4702268e012a63e9dc05e26e8a61603c1d5/webdocs/design/security/index.md)
explains that scenarios can run arbitrary Go/Pulumi code. It delegates client
authentication and authorization to another service and recommends restricting
the API to trusted services with mTLS. Installing it next to Ascend does not
create an execution boundary for arbitrary learner patches.

If a hosted runner is added, use a separate administrative service with
allowlisted, versioned scenarios; no browser access to its raw scenario API.
Bind instance requests to Ascend account/attempt IDs, use a dedicated provider
identity and infrastructure boundary, start with a zero-size warm pool, and
record provider IDs before announcing readiness. A failed deletion must retain
the inventory and remain retryable. A separate trusted checker produces the
learning receipt; an instance-specific flag alone does not establish every
action the learner took.

The historical [failed deletion discussion](https://github.com/ctfer-io/chall-manager/issues/1046#issuecomment-3503540087)
and [PID growth report](https://github.com/ctfer-io/chall-manager/issues/1109) inform
the required crash/deletion/repeated-cycle tests. They are not a claim that those
reports remain unresolved in this pinned version. No Chall-Manager runtime or
provider deployment was performed in this implementation.

## Concrete specialist paths

Each recipe has `ascend lab plan ID`, pinned selected-file hashes, lifecycle and
export requirements, a manual report template and an explicit runtime gate.
`ascend local-lab record ID report.json` saves/synchronizes only the small report.
The receipt says **Practice recorded (manual observations)**; its `pass` status
means the learner reported the entire named checklist. Ascend did not run or
verify that specialist environment. These records award no XP.

| Capability and recipe | Reviewed finding | Runtime gate still to clear |
| --- | --- | --- |
| Cluster: `kubernetes-goat-rbac` | The selected manifest grants `cluster-admin` to `kube-system/superadmin`. A namespace alone cannot contain that permission. | Dedicated disposable cluster, pinned node/tool images, actual authorization controls and complete cluster/object teardown. |
| VM: `mbe-intro-reversing` | RPISEC's original 32-bit environment matters; its setup script changes the whole guest. Code is BSD-2-Clause; slides have separate noncommercial terms. | Pinned VM artifact, guest/tool compatibility, debugger controls, snapshot recovery and VM/disk measurements. |
| Cloud: `cloudfoxable-secret` | The module creates SSM parameters and an IAM policy attachment. Fixed names can collide outside a dedicated account. Its flag value is public source. | Dedicated AWS account, explicit resource/cost scope, provider lockfile, actual allow/deny observations, cost measurements and independently confirmed destruction. |
| Android: `mastg-android-storage` | The Java activity uses `MODE_PRIVATE` SharedPreferences; debug/root inspection is different from ordinary app access. Its SDK/build tools are old; root license is GPL-3.0. | Pinned APK/toolchain and explicitly selected emulator image/serial, app/storage controls, device-safe reset/export/teardown and disk/RAM measurements. |
| LLM: `llm-agent-transactions` | Dependencies are partly unpinned; upstream publishes payloads and warns that small models can behave inconsistently. | Dependency/model hashes, model license and measured disk/RAM, synthetic data/tool boundary, repeated paired baseline/injection trials and owned model-cache cleanup. |

For manual observations, require the exact source revision plus relevant
environment identifiers and artifact hashes. Model reports need at least three
trials; a report still does not authenticate those claimed trials. Do not upload
VM disks, Terraform state, credentials, model weights or full local repositories.

This workstation has Linux x86-64 Docker, VM tools and `adb`, but no registered
libvirt/VirtualBox VM, configured disposable cluster or selected emulator was
available. No cloud account or model download/budget was configured. Tool
presence alone never satisfies a runtime acceptance gate. The next deployable
step is to supply the particular disposable environment and validate that
recipe's recorded acceptance list; gates do not disappear when the catalog is
edited to say "reviewed".
