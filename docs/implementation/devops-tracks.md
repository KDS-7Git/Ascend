# DevOps track implementation

Implemented on 2026-11-03 from [the researched DevOps design](../design/devops-track-design.md), with editable authoring data in [devops-paths.json](../curriculum/devops-paths.json). Content remains an unreviewed teaching draft (`source = "ai-draft"`, `reviewed = false`).

## Delivered sequence

| Order | Pack ID | Practical coverage |
| --- | --- | --- |
| 1 | `devops-service-foundations` | HTTP request path, Linux processes/files, Git/artifact identity, systemd lifecycle, private reverse proxy/TLS, SSH deployment, containers/volumes, deployment recovery |
| 2 | `devops-delivery-automation` | Meaningful regression tests, real CI, source/base/image identity, immutable promotion and rollback, OpenTofu resource creation/drift, Ansible convergence, pipeline trust, reproducible delivery |
| 3 | `devops-reliability-orchestration` | Service signals/SLO accounting, bounded concurrency/load models, credential rotation/signatures, consistent backup/restore, local Kubernetes, rollout/RBAC recovery, resource/storage budgets, integrated operations |

There are **24 main levels**, each with guided practice and an independent changed-condition milestone. The packs also contain 24 optional recall tasks and three short entry demonstrations: **75 nodes total**. Every main level has an M/L milestone. Final capstones use 180-minute independent budgets and can be split over sessions.

Earlier whole tracks are recommendations, not hard gates. The existing level early-unlock feature can open a later level. A learner with prior experience can attempt an open milestone directly without recording its guided practice as done. This is self-directed entry, not an automated proficiency placement claim.

All operational verifiers are `manual`; none grants automatic skill verification from local file presence, a fixture flag or a process's green status. Required external operations remain incomplete without the corresponding real environment and observation.

## Files and generation

- `scripts/build_devops_tracks.py` renders three TOML packs, the DevOps catalog fragment, three standalone READMEs and 24 lesson guides.
- `packs/community/devops/catalog.json` supplies category `DevOps`, domain `devops`, sequential `track_order`, advisory `recommended_after`, entry/background/limits, aliases and capabilities.
- `tracks/devops-tracks/materials/` contains **67 source files**, including the generated guides, Docker/Compose, systemd, Caddy/TLS, SSH, GitHub Actions, OpenTofu, Ansible, Prometheus/Grafana, k6 and Kubernetes starters, recorded fixtures and a runnable local pipeline-policy experiment.
- `tracks/engineering-common/` contains **nine shared files**: a README and eight inspectable Python tools. The domain packager includes these as `shared/` in each engineering bundle.
- Each task links `/training/<pack-id>.zip`. Global catalog/registry, archive publication and web/API integration are handled by the parent implementation.

Regenerate or check generated outputs from the repository root:

```sh
.venv/bin/python -m scripts.build_devops_tracks
.venv/bin/python -m scripts.build_devops_tracks --check
```

The generator validates every pack with the application's real parser. Tests also traverse real `next_nodes` progression to every node and exercise independent milestone entry.

## Runnable tool contracts

From an extracted track folder on the learner's PC:

```sh
python3 shared/relay.py --host 127.0.0.1 --port 8000 --data work/relay.sqlite --release v1
```

The foreground service prints its actual address, port, release and data path. A second terminal can observe it and explicitly create one synthetic update:

```sh
python3 shared/check_service.py --url http://127.0.0.1:8000 --expect-release v1 --write
python3 shared/backup.py create --source work/relay.sqlite --destination backups/first.sqlite
python3 shared/backup.py restore --source backups/first.sqlite --destination restored/relay.sqlite
python3 shared/selfcheck.py
```

The checker validates endpoint payloads, release/readiness, unknown-route failure, and optional write/replay/conflicting-key behavior plus a subsequent read of the saved update. It emits `authority = "learner-local observation"` and `satisfies_track_evidence = false`. `--token-file` supports synthetic credential rotation, and `--ca-file` scopes trust to that client invocation with TLS verification retained.

Relay supports `--read-only`, `--ready-file`, `--token-file`, `--workers` (1–64) and `--delay-ms` (0–1000). Its data is SQLite with explicit transactions; backup uses SQLite's consistent backup API and refuses an existing destination. Relay is a teaching HTTP implementation, not a hardened public application server.

`release.py build/verify/select/resolve/serve` checks source bytes and an immutable manifest, uses an exclusive lock and atomic pointer replacement for selection, and requires a deliberate process restart for activation. It never makes a changed selection look like a restarted process. Artifact hashes are not signer authentication, and these helpers must not become a server-side uploaded-code executor.

`edge.py --config configs/route.json --port 9000` is a loopback-only GET teaching proxy. The supplied Caddy configurations provide the real reverse-proxy/TLS extension.

`probe_load.py --clients 4 --requests 24 --output notes/load.csv` runs a bounded closed-client experiment and prints the actual observation window. It limits clients/requests, preserves prior output, and requires explicit opt-in for an owned non-loopback target. `analyze.py <csv> --window-seconds <actual-seconds>` includes failed requests in its denominator and exits nonzero when selected error/latency objectives are missed. These observations do not establish fixed-arrival, public Internet or physical hardware capacity.

The delivery bundle's `tools/pipeline_policy.py` exercises revision, test, artifact and trust-condition decisions using an authored fixture. A passing local decision does not authenticate the fixture, represent a CI receipt, or verify a provider identity.

## Verification performed

```sh
.venv/bin/python -m pytest tests/test_devops_tracks.py -q
.venv/bin/ruff check scripts/build_devops_tracks.py tests/test_devops_tracks.py tracks/engineering-common tracks/devops-tracks/materials/devops-delivery-automation/tools
.venv/bin/python -m scripts.build_devops_tracks --check
```

The focused suite has **11 passing tests**, including:

- Generated consistency, all 13 original design capability groups represented, reachable progression and independent entry at all 24 levels.
- Every referenced static input present in independently extracted ZIPs.
- Eight bundled selfchecks executed without repository imports: real endpoint/replay controls, token/readiness changes, read-only restart/persistence, consistent snapshot/restore, artifact tampering, edge failure/repair, bounded admission/recovery and complete measurement accounting.
- Actual child-process release activation/rollback and fresh restore from extracted files; wrong healthy release, read-only write, changed artifact and overwritten-destination negative controls.
- Failed/untrusted/mismatched pipeline decisions and recorded SLO failures rejected for their intended reasons.
- Real local TLS with an OpenSSL-generated certificate: correct CA/name accepted, missing trust and wrong hostname rejected. This validates the client and TLS behavior; it is not a runtime test of Caddy.

All three Compose files also passed `docker compose -f <path> config --quiet`. This validates configuration syntax, not image build, container execution or resource-controller behavior.

No cloud resources, hosted CI jobs, public registry publications, OS services, VMs, hypervisors, OpenTofu resources, Ansible targets, physical Pi hosts or Kubernetes clusters were provisioned by these checks. Their concrete recipes and prerequisites are included; those variants need their own runtime acceptance in learner-owned environments. OpenTofu, Ansible, kind, kubectl and Caddy were unavailable in this workspace; no external runtime success is inferred from the local controls.

## Resource and learning boundaries

The core tools use Python 3.11+ and its standard library. They run on the learner's PC without a paid account. Linux/systemd/SSH tasks use a disposable owned Linux guest or spare host; containers and local Kubernetes have separate prerequisites. A kind lab carries an initial 4–6 GiB planning allowance that must be checked against actual host usage, with other unused labs stopped. Extra VMs, metrics and image caches are not assumed to fit simultaneously.

Pi/spare-host variants explain independent power/uptime, architecture, cooling and flash behavior while preserving a VM/PC software route for learners without hardware. The constrained-operations lesson includes a specifically capped, isolated memory-failure container and scoped cleanup; it does not create host disk pressure.

The two hosted lab slots and the application's 4-core, 4–8 GB, microSD-based budget remain separate. Engineering downloads do not silently consume those slots or execute learner scripts on the application server. Notes and outputs have explicit learner-chosen local locations; nothing is silently uploaded or treated as an automatic grade.
