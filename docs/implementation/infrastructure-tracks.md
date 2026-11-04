# Infrastructure track implementation

The Infrastructure & Internet Operations sequence is implemented as nine installable proficiency packs. Each has eight main levels, a short entry assessment, guided practice, independent operational milestones and optional return-later tasks: **72 levels, 225 nodes, 72 milestones, 144 portable diagnostic cases and 48 native input files**.

The maintained authored source is [infrastructure-paths.json](../curriculum/infrastructure-paths.json). [build_infrastructure_tracks.py](../../scripts/build_infrastructure_tracks.py) deterministically renders 390 files: nine packs, the domain catalog fragment, and 380 per-track material files. The source runtime at `tracks/infrastructure-tracks/materials/shared/lab.py` is copied into each track. Shared service/release/backup/probe tools come from `tracks/engineering-common/` when the parent packaging script builds each ZIP.

| Order | Pack | Practical scope |
|---|---|---|
| 1 | `io-linux-network` | A real HTTP request, shell/permissions, network routes, DNS, TLS, NAT/CGNAT and service recovery |
| 2 | `io-vm-administration` | KVM/libvirt guest creation, cloud-init, virtual networks, SSH/console access, hosting, resource changes, backup restoration and fleet inventory |
| 3 | `io-public-hosting` | Static/dynamic artifacts, reverse proxy, local/public DNS and TLS, VPS/home origins, free hosting and cloudflared |
| 4 | `io-private-access` | SSH identity and forwards, WireGuard, managed/self-hosted coordination, subnet routes, client-assisted tunnels and a maintained frp relay |
| 5 | `io-delivery-automation` | Artifact identity, Docker/Compose, CI controls, promotion/rollback, OpenTofu/libvirt and Ansible |
| 6 | `io-mail-state` | Mailpit, loopback Postfix, Dovecot 2.3/IMAP, authenticated SMTP submission, local DKIM signing/tamper checks, public-mail feasibility and state recovery |
| 7 | `io-traffic-capacity` | Workload/window arithmetic, readiness-based balancing, write ownership/idempotency, concurrency, bounded overload, open/closed load and sizing |
| 8 | `io-resilient-hardware` | Boot/uptime, log retention, backups, microSD constraints, Raspberry Pi/PC alternatives, cgroups, outages and migration |
| 9 | `io-private-cloud-platform` | Incus projects/profiles, two restricted learner identities, quota/resize operations, guest publishing, restore, orchestration and a college-style platform capstone |

The sequence uses `domain=infrastructure`, `category=Infrastructure`, `track_order=1..9` and `recommended_after` in `packs/community/infrastructure/catalog.json`. Recommendations do not become cross-track gates. Default main-level progression uses the preceding milestone. A practitioner may use existing early-unlock and attempt a later independent milestone without completing its worked practice. An entry choice or a local reference does not confer credit for other levels.

## Learner experience and materials

Each bundle contains `README.md`, an environment bootstrap, a notes template, eight lesson guides, native inputs, guided/transfer cases and `lab.py`. The starter service and checker give an observable result before advanced tools are introduced. Inputs include cloud-init, a libvirt network, Caddy/systemd, WireGuard/frp, container/IaC/Ansible/CI files, synthetic mail, a local SMTP submission client, DKIM DNS preparation, k6 workloads and a Kubernetes manifest.

The workspace instructions name all save locations. Files stay on the learner's PC in the chosen extracted folder; entering a challenge does not create or upload them. The case preparer prints the absolute output directory and refuses an existing destination. Notes record predictions, commands, machine roles, observed results, help used and cleanup. Actual file upload/notebook controls are handled by the application.

The beginner bootstrap can use an owned existing Linux environment or a prepared Multipass guest. Full VM administration is then taught explicitly with Ubuntu 24.04/libvirt. Native commands identify HOST, GUEST, CLIENT and EDGE roles, give version/access requirements, and require replacing sample addresses and public-key placeholders deliberately.

Hardware lesson 05 includes the complete Pi Imager/model/media/account sequence, trusted host-fingerprint enrollment, concrete SSH/SCP transfer, a dedicated systemd service and private client forwarding. It has equally explicit Multipass and owned Linux-PC routes. Readiness and clean reboot/state controls are non-destructive; actual Pi thermal/power/storage observations remain separate from the VM's software result. Hardware lesson 01 uses this same installation. The VM first-boot lesson includes a stopped-guest cold backup/cloud-init reseed route for failed key injection, and requires establishing a tested console password before a later intentional SSH lockout.

Worked tasks expose two meaningful partial checkpoints: diagnosing the failed control and retaining native observations. “Next step” names the remaining operation. Independent tasks preserve the distinct changed condition and actual finish line.

## Evidence and resource boundaries

Every operational node uses `verify = {type = "manual"}` and `auto_complete = false`. Packs remain `source = "ai-draft"`, `reviewed = false`.

`lab.py` interprets an explicit data rubric without executing learner strings or provisioning resources. It checks editable configuration/explanation models, accepts valid alternative resource allocations, and provides visible references for learning. Setting a field to true is not an observation. Passing that model does not create a VM, prove physical behaviour, establish external reachability or produce a trusted Ascend receipt. The native milestone still requires the actual operation and its positive/negative/recovery controls.

The local CSV analyzer includes errors in latency accounting and uses the full observed window. VM XML inspection distinguishes configured CPU values from running-guest evidence; message-header inspection does not verify authentication claims. Input bounds and malformed-data failures are explicit. The framing exercise demonstrates bounded encoding/decoding only.

All heavy/native operations run on learner-owned environments. The shared Ascend runner stays at **two simultaneous hosted labs**, with the existing approximately 4-core, 4–8 GB RAM, 100–120 GB microSD server envelope. The 16 GB learner-PC route starts with one small guest and a roughly 8 GiB total lab planning allowance, subject to measurement. Optional Pi/spare-PC/mini-PC/VPS routes identify their advantages and limits; virtual devices do not substitute for physical power, storage-endurance or independent-host observations. Additional resources can extend the same track evidence later.

The libvirt restore uses the retained cold backup as its input and prepares a separate guest identity. It does not obtain the supposed restore by copying the live source. Incus learners use separately restricted TLS certificates; changing the client project's selection is not treated as authorization. Public hosting/mail/tunnel variants name their domain, account, policy and external-client requirements.

## Validation performed

```sh
.venv/bin/python scripts/build_infrastructure_tracks.py --check
.venv/bin/python -m pytest -q tests/test_infrastructure_tracks.py
.venv/bin/ruff format --check scripts/build_infrastructure_tracks.py tests/test_infrastructure_tracks.py tracks/infrastructure-tracks/materials/shared/lab.py
.venv/bin/ruff check --select F401,F841 scripts/build_infrastructure_tracks.py tests/test_infrastructure_tracks.py tracks/infrastructure-tracks/materials/shared/lab.py
```

Result: **182 tests pass**. Coverage includes every broken/reference case, distinct transfer inputs, required-field failures, feasible resource alternatives and overcommit, pack reachability/early entry, generated-file consistency, workspace preservation, CSV arithmetic/invalid inputs, bounded XML/mail parsing, framing truncation/size controls, native Python/shell syntax and dnsmasq configuration syntax where that executable is available. Native-command input references are checked against their own bundle. The actual device-unit CLI arguments are parsed and used for a temporary loopback readiness-failure/recovery test that preserves synthetic records; that does not claim a systemd or Pi boot replay.

The operational integration test starts one temporary loopback Relay, verifies real HTTP/write/idempotency and wrong-release controls, creates an independent SQLite backup, stops the source, restores into a new path and checks the retained records through a new service. It also confirms the local report is not authoritative track evidence. Temporary listeners and data are cleaned up by the test.

No VM, container platform, network interface, provider resource or device was provisioned in this implementation session. No external mail or stress workload was sent. Native recipes are authored and syntax-checked; KVM/Incus, systemd, WireGuard, Postfix/Dovecot/DKIM, cloud accounts, public reachability and physical-device paths require version-specific operational replay before those paths receive a tested/reviewed label. This is recorded in the curriculum and learner material rather than presenting a portable fixture as that replay.

The source carries the original platform/connectivity/capacity/virtualization audit links. Additional official Incus project-confinement and Debian OpenDKIM manual checks informed the concrete client-enrollment and signing commands; reading those documents does not count as native validation.

## Integration handoff

The parent implementation owns registry discovery, application/category presentation, ZIP delivery and browser integration. All nine `io-*.toml` packs and the infrastructure `catalog.json` fragment are ready for those steps. Each node links to `/training/<pack-id>.zip`; package the corresponding `tracks/infrastructure-tracks/materials/<pack-id>/` plus `tracks/engineering-common/` under the bundle's `shared/` directory and the project license.

After changes to the authored source or runtime, regenerate the infrastructure files before refreshing registry hashes and ZIPs. Do not copy generated material changes back into the earlier design documents. The separate DevOps sequence can recommend these infrastructure capabilities without silently granting cross-track credit.
