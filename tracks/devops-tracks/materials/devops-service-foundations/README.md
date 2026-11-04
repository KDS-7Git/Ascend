# DevOps 1: Service & Deployment Foundations

Take Relay from a local process to a versioned service, private edge, guest deployment and container.

## Choose your starting point

Start here if processes, HTTP, Linux service operation or deployment boundaries are new.

Basic file/editor use. A guided Linux guest setup is available through the Infrastructure VM track; Python, shell and networking are explained as used.

The three tracks form a recommended sequence: Service Foundations → Delivery Automation → Reliability and Orchestration. Prior experience can satisfy the background. Earlier whole tracks are not locked prerequisites. Inside Ascend, use an independent application first when you know a level; use the existing early-unlock action for a later level. A successful local selfcheck checks the supplied tools, not your proficiency.

## Your workspace and first real check

Download /training/devops-service-foundations.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-service-foundations folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/entry.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

Run these from the extracted folder:

```sh
python3 --version
python3 shared/selfcheck.py
```

The checks use temporary loopback services and temporary data. They report both success and intentional failure controls. They do not start a persistent server, provision VMs, change system configuration, or contact a cloud account.

For a persistent exercise, start Relay in Terminal A:

```sh
python3 shared/relay.py --host 127.0.0.1 --port 8000 --data work/relay.sqlite --release v1
```

In Terminal B, create and verify one synthetic update:

```sh
python3 shared/check_service.py --url http://127.0.0.1:8000 --expect-release v1 --write
```

Stop that foreground service with Ctrl+C before a lesson starts another service on port 8000. Use a fresh output path for repeated backup, artifact and load experiments; the helpers preserve existing outputs instead of silently overwriting evidence.

## Practical sequence

Each level has guided practice and an independent changed-condition application. Return-later tasks are optional. The finish line names the actual behaviour to demonstrate.

1. [Trace a real request](lessons/request-path.md) — Trace a real HTTP request and distinguish a stopped service, a missing route and the wrong release.
2. [Use the Linux shell and service files](lessons/linux-shell.md) — Use paths, permissions and process observations to repair a small Linux service.
3. [Build a versioned artifact](lessons/versioned-artifact.md) — Build an identifiable release and detect a changed artifact before deployment.
4. [Operate a persistent Linux service](lessons/service-lifecycle.md) — Keep a service running across process failure and a guest reboot while preserving its data.
5. [Reach a service through an edge](lessons/edge-tls.md) — Route requests through a private edge and prove TLS name and trust behaviour.
6. [Deploy to an owned remote guest](lessons/ssh-deployment.md) — Deploy to an owned guest and reach its private service through authenticated SSH access.
7. [Package and recreate a container](lessons/container-runtime.md) — Build a runtime image and prove which data survives container replacement.
8. [Recover a complete deployment](lessons/foundation-capstone.md) — Reproduce a complete deployment and recover its release, route and saved data.

## Choose the environment that fits

- Core Python practice runs on the learner PC without Docker, hardware purchases or a paid cloud account. Keep a few hundred MiB free for small lab data; measure actual use before adding tools.
- Linux/systemd/SSH/Ansible practice uses an owned disposable Linux VM or spare PC. Begin with one guest and preserve host memory/disk reserve. The Infrastructure VM tracks cover guest creation and host administration.
- Container practice needs a learner-owned Docker environment and room for images. A single Relay container is capped in the example configuration; this does not include Docker/VM overhead.
- The local kind Kubernetes variant needs its own roughly 4–6 GiB planning allowance. Stop unused labs and inspect actual usage. A 16 GB PC can run this sequential exercise with reserve; do not pile every VM, monitor and cluster together.
- A Pi or spare always-on host is an optional deployment target, with a Linux VM route available for the same software concepts. Physical power, cooling, flash wear and independent-host failures need actual hardware observations.
- Real hosted CI, registry publication and provider identity variants require the learner's chosen accounts and current free allowance. Local rehearsal does not count as an external run. Choose free local routes first; no paid resource is provisioned by these files.

Ascend's two hosted lab slots are a separate service budget. These engineering bundles execute on the learner's PC or explicitly chosen guest; they do not consume hosted slots or enlarge the server's 4-core, 4–8 GB, microSD-based envelope.

## Evidence and limits

Local tools and owned Linux guests. No cloud subscription required. Public exposure and physical hardware are optional later variants; manual operational completion is not an automatic verified skill result.

All operational tasks use manual review. Retain the intended success, the changed failure, recovery, environment identity, help used and untested assumptions. A local report is an observation, not a signed server grade. Do not mark an unavailable required VM/CI/cluster operation complete as a reading exercise.

The included Relay is a readable synthetic-data teaching service. Use a suitable production server, authentication, edge and state architecture for a real application. Run the operating-system and cleanup recipes only against the particular learner-owned guest/project named in your notes.

Read [shared/README.md](shared/README.md) for tool interfaces. Keep credentials, databases and private inventories out of Git; review gitignore.example before the first commit.
