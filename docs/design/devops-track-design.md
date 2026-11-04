# DevOps track: deploy, observe, recover, and explain

**Research and curriculum design, 2026-11-03.** This proposes a new Ascend track; it does not install a pack, execute a lab, publish a repository, provision a cloud account, or change existing scoring. It complements the [adaptive Playground proposal](adaptive-playground-proposal.md), [current runner design](server-lab-runner.md), and [local execution plan](local-lab-execution-plan.md).

The owner confirmed **at most two hosted labs**. This foundation plan originally used an 8 GB RAM / four-core / 80 GB disk planning baseline. The subsequent [Infrastructure & Internet Operations domain](infrastructure-internet-domain-design.md) expands this into nine sequential tracks and uses the newer small-server scenario (4–8 GB RAM, about four cores, 100–120 GB physical microSD) plus the learner's 16 GB PC. Use its measured-per-recipe resource policy when authoring the expanded lessons; nominal storage is not free lab space.

The intended outcome is: **independently deliver and operate a small service, diagnose a failed release, recover its data, and explain the relevant tradeoffs**. This is a substantial foundation for developer, junior DevOps, and operations work. Completing it is not proof of expertise across every cloud, tool, scale, or on-call environment.

## Teaching approaches audited

The [DevOps source ledger](devops-track-sources.json) records 18 first-party sources, retrieval dates, response hashes, and access limitations. This was a documentation/syllabus audit. Paid classes were not attended and external labs were not run. Provider descriptions of employment outcomes, completion times, and learner success were not independently validated.

| Source | Observed teaching approach | Decision for Ascend |
| --- | --- | --- |
| **KodeKloud** [DK1] | Its DevOps path starts with prerequisites, Linux and scripting, then covers Git, CI, containers, orchestration, automation, and observability. Topic and role paths coexist. The public page links practical challenges and readiness checks. | Make prerequisites and role relevance explicit, but connect the tools through a working service. Its advertised duration is not an Ascend timing estimate. The Engineer application itself returned a JavaScript shell, so its signed-in task mechanics were not audited. |
| **TechWorld with Nana** [DK2] | The public syllabus describes learning build/package work manually before automating it, then combining tools in infrastructure, CI/CD, container, and monitoring projects. It explicitly links later modules back to earlier projects. | Use an evolving project and teach one representative tool per function before alternatives. Do not adopt the page's job/salary claims as evidence of competence. |
| **Killercoda** [KL1], [KL2] | Browser environments combine scenario instructions with optional step verification. Author content is versioned in Git and syncs on push. Documentation says interactive environments use **VMs for stronger isolation**, despite the surrounding service using containers. | Reuse the scenario/step/check authoring pattern, but do not mistake Ascend's fixed container adapters for a safe general shell/CI runner. Label temporary environment lifetime and save/export explicitly. |
| **Docker's official tutorial** [DO1] | Run an existing image → run a Compose application → build an image → publish it → clean up. It distinguishes the artifact from the running instance and names account/tool prerequisites. | Teach the full artifact lifecycle. Include image identity, volumes, restart behaviour, and removal of owned resources, rather than ending at `docker run`. The current tutorial redirects from the older workshop URL. |
| **GitHub Skills and Actions documentation** [GH1], [GH2], [GH3], [GH4], [GH5] | Small exercises state audience, prerequisites, expected output, and steps inside a learner-owned repository. The sequence covers workflows, failing tests, merge protection, and publishing images. Deployment environments and OIDC have separate operational documentation. | Teach from a real change and a visible workflow result. Reuse one artifact through staging and promotion. Explain repository/account permissions, plan-dependent protection features, and identity before enabling deployment credentials. |
| **Kubernetes Basics and kind** [KU1], [KU2] | Background explanations accompany create/deploy/explore/expose/scale/update tutorials. A practice cluster is a separate environment prerequisite. kind provides a local cluster workflow and explicit cluster deletion. | Teach orchestration after process, network, and container fundamentals. Run real cluster exercises locally or in an explicitly chosen external sandbox; do not present a YAML quiz as operational Kubernetes proof. |
| **Terraform and OpenTofu** [TF1], [OT1] | Tutorials teach building, changing, and destroying resources. OpenTofu describes write → plan → apply, providers, dependencies, state, and collaboration. Terraform also supplies a Docker-based getting-started path. | Teach ownership, state, drift, replacement risk, and teardown through repeated changes. A plan alone is not an applied environment; a successful apply alone is not a healthy application. |
| **Ansible** [AN1] | The starting model is a control node, an inventory, and managed nodes, followed by playbooks. | Separate provisioning resources from configuring hosts. Verify repeatability and a second idempotent run rather than merely the presence of a YAML file. |
| **Prometheus and Google SRE** [PM1], [SR1], [SR2] | Prometheus introduces a configured target and queries; the SRE Workbook connects measurable SLIs/SLOs to decisions, practiced incident coordination, and learning from incidents. | Measure user-visible service behaviour, then use that evidence to make a release or recovery decision. Dashboards and a green health check are useful only if the learner understands what they omit. |

The recurring pattern is **explain a mechanism → perform a small operation → observe a result → introduce a controlled failure → recover → automate the proven procedure**. That is a stronger track structure than collecting badges for installing many tools.

## The reference application and learning story

Use an Ascend-authored service called **Relay**, a small status/update application with synthetic data. It is a disposable teaching target, separate from Ascend's own installation and data.

Relay provides a small UI/API, `/health`, a readiness check, a `/version` response containing a release identifier, structured request logs with correlation IDs, a few counters, and a SQLite-backed update list in its single-instance mode. Supply its application source and tests so early tasks focus on deployment rather than requiring a full web-development course first.

The learner first sees a request move from client to edge to application to storage. They then carry the same service through packaging, a Linux service, remote deployment, containerisation, CI, controlled promotion, infrastructure recreation, monitoring, backup/restore, and a capstone incident. Each stage gives the service a new operational capability.

Keep database and availability claims precise. Blue/green introductory tasks can use Relay's **stateless/read-only release endpoint**. Do not scale a writable SQLite application across containers and call it a production HA design. Kubernetes fundamentals use the stateless mode; a PostgreSQL-backed persistent multi-replica version belongs to the later stateful-services branch.

### The project hub

The DevOps track's persistent hub should show:

- **Release:** the last recorded artifact/version and its evidence source.
- **Environment:** browser case, learner-local VM/cluster, or temporary hosted lab.
- **Service path:** client → edge → app → data, with the component relevant to today's task highlighted.
- **Next action:** a concrete operation or investigation, not a generic “Next step”.
- **My work:** configuration, deployment manifest, result reports, and runbook, with actual save locations and download actions.

A request travelling along the service diagram is a useful learning animation when connected to an observation. Mark simulated traffic as simulated. Do not present decorative green lights or looping synthetic metrics as evidence that a learner's real deployment is healthy. Respect reduced motion and keep the same information available as text.

## Entry, prerequisites, and routes

Require ordinary file/editor use and a willingness to work in a terminal for the full practical route. Linux, Git, networking, and basic scripting are taught in the track. Offer short supplementary Python/shell preparation when a learner cannot yet follow the supplied scripts. Do not require a paid cloud account to begin.

| Learner | Entry and emphasis |
| --- | --- |
| New to deployment | Follow the service path demonstration, then perform small process/network tasks before tools that orchestrate them. |
| Developer or approximately six-month practitioner | Choose a practical starting check or enter a scoped challenge directly. Sample Git/artifacts, HTTP/process diagnosis, container identity, and CI reasoning; recommend only relevant gaps. |
| Experienced operator | Start with a changed-condition release/recovery case. Require evidence of transfer before recommending deeper automation or orchestration work. |
| Job preparation | Follow named capabilities, retain reproducible work samples, practice technical explanation and a handover. Include “what I would change for a larger production service.” |
| Interest-led learning | Follow the same skills through selected experiments, choose optional branches, and maintain a personal service. Formal interview/report exercises remain optional unless selected as the task objective. |

Starting-level checks suggest placement; they do not automatically complete track nodes. Prior experience is per skill: being good at Docker does not establish DNS, state management, or recovery competence. Use the adaptive proposal's fresh-case, assistance, transfer, and uncertainty rules.

The full curriculum is designed as **13 main levels**, compatible with the current proficiency-pack requirement of 8–15 main levels. The initial work estimates total approximately **84–111 hours**, excluding unpredictable downloads, account setup, and substantial remedial learning. These are authoring estimates to validate in learner sessions, not a promise of completion in a fixed number of weeks.

## Main curriculum

Each level contains short explanations, a separate worked example, independent practice, and an M/L milestone with observable evidence. Break longer work into authored 10–25-minute checkpoints; a checkpoint does not automatically satisfy the parent's full assessment.

| Level | Mechanisms and representative tools | Example and independent practical work | Milestone evidence | Estimate |
| --- | --- | --- | --- | ---: |
| **1. Follow a request** | Client/server, DNS name vs address, port, HTTP status, edge, process, storage; browser network panel and `curl`. | Trace a successful request. Compare a stopped service with an incorrect route on a different fixture. | Correctly locate a failure using discriminating observations and predict a changed case. | 2–3 h |
| **2. Operate a Linux host** | Files, permissions, users, processes, signals, environment, listening sockets, logs; Bash, `ps`, `ss`, `curl`, `dig`, exit codes. | Run Relay as an unprivileged user; fix a path/permission/config issue without granting broad permissions. | Recover a fresh broken launch, retain the exact observations, and demonstrate the legitimate workflow still works. | 6–8 h |
| **3. Build a versioned release** | Git history/branches/PRs, reproducible inputs, dependencies, tests, artifact identity; Git, Python environment, checksums. | Package a release manually from a known commit; distinguish source, build output, configuration, and data. | Produce an artifact manifest linking source revision, dependency lock, tests, and artifact digest; reproduce it from a clean workspace within its stated reproducibility scope. | 4–6 h |
| **4. Run a reliable service** | Process lifecycle, service user, configuration/secrets, restart policy, health vs readiness, persistence; systemd, `journalctl`. | Install Relay in a disposable learner VM; restart it and preserve data. Diagnose a restart loop with a real failed dependency. | A controlled process stop is recovered according to the declared policy; a bad configuration remains visible rather than looping unnoticed; saved data survives. | 6–8 h |
| **5. Deploy behind a secure edge** | SSH host identity, file transfer, reverse proxy, DNS/TLS, firewall boundaries, deployment paths; OpenSSH, NGINX, `curl`, `openssl`. | Move the same release to a separate learner-owned Linux target. A scoped certificate test can use an explicit local CA file; public-domain issuance is optional. Diagnose the independent 502 case. | Reach the expected version through the edge; prove unwanted direct access is blocked, inspect a certificate/name mismatch, and retain the deployment/rollback commands and observations. | 8–10 h |
| **6. Package with containers** | Image vs container, OCI registry/digest, layers, `.dockerignore`, runtime identity, volume/network lifecycle; Docker, Compose. | Containerise Relay, run it non-root, declare its services, preserve its data across recreation, publish an image when account access is available. | Run the same immutable image in a clean target; verify network/config/volume behaviour and remove only the lab's owned resources. | 7–9 h |
| **7. Test every change in CI** | Triggers, jobs, dependencies, runner identity, caches vs artifacts, status checks, token permissions; GitHub Actions. | Make a deliberately failing change, inspect its workflow, repair it, and prevent the failed version from promotion. | A real learner-owned repository records passing/failing checks for the relevant commits and a versioned artifact. Demonstrate that untrusted changes cannot use deployment secrets. | 7–9 h |
| **8. Release and roll back** | CI vs delivery vs deployment, staging, immutable promotion, smoke tests, concurrent releases, release history, database compatibility. | Promote the tested artifact, perform an explicit release decision, detect a supplied regression, and roll back the stateless/read-only case. Discuss why code rollback may not reverse a destructive schema change. | The promoted digest matches the tested artifact; the bad release is detected; recovery restores the specified user behaviour and preserves required data. | 5–7 h |
| **9. Recreate infrastructure** | Desired state, providers, plan/apply, resource ownership, drift, state/locking, secret data, configuration idempotence; OpenTofu, Ansible. | In a learner-owned disposable environment, provision a small target/resource set, configure Relay, apply a change, introduce drift, reconcile, and destroy. | Review a plan including a dangerous replacement; prove a second configuration run is idempotent; recreate the declared environment and account for every owned resource after destruction. | 8–10 h |
| **10. Observe service health** | Logs, metrics, traces as different evidence, user-visible SLIs, SLOs, useful alerts, cardinality; Prometheus, Grafana, structured logs. | Query a small local metrics target and correlate a latency/error change with a release. Use recorded datasets for inexpensive repeat practice. | Define numerator/denominator/window for an SLI, detect a seeded issue, reject a misleading “CPU is low so the service is fine” conclusion, and give a justified action. | 6–8 h |
| **11. Protect and recover data** | Least privilege, secret rotation, dependency/supply-chain review, backup consistency, RPO/RTO, restore drills, incident timeline. | Rotate a synthetic application secret; inspect a pinned scan/SBOM fixture; create a valid SQLite backup, corrupt disposable live data, and restore into a clean target. | The old credential no longer works, the new legitimate client does; restored records pass checks; the learner reports observed recovery/data loss against the task's stated objectives. | 7–9 h |
| **12. Deploy to Kubernetes** | Desired state/controllers, Deployment/Service, labels, readiness/liveness, requests/limits, rollout/rollback, namespace/RBAC scope; kind, `kubectl`, manifests. | Deploy Relay's stateless mode to a learner-local cluster; expose it locally, update its version, repair a readiness/service-selector fault, and delete the owned cluster. | Actual cluster observations prove the expected endpoint and version, failed readiness prevents the intended traffic path, and a bad rollout is recovered. A YAML-only review is recorded separately. | 6–8 h |
| **13. Operate the capstone** | Integration, prioritisation, communication, handover, changed constraints. | Deliver Relay v2 through a real pipeline into a disposable target, handle a seeded release/recovery incident, and transfer the runbook to another reviewer or a fresh environment. | Reproducible release evidence, detection/recovery checks, data-preservation evidence, cleanup inventory, and a reviewed handover; see the capstone rubric below. | 12–16 h |

Teach basic secret handling from the first configuration task and CI trust boundaries from the first workflow; level 11 deepens them. The sequence is not permission to postpone safe credential handling until the end.

### What “all the tools” should mean

Teach the functions and one usable path end to end, then offer tool translations. Tool selection and versions belong to recipe review; do not claim every command in changing upstream documentation has been tested against Ascend's environment.

| Function | Core representative | Further branch / comparison |
| --- | --- | --- |
| Version control and collaboration | Git and GitHub | GitLab, trunk-based/release-branch tradeoffs. |
| Host/network diagnosis and automation | Linux CLI, Bash, small Python scripts, SSH | Windows/PowerShell and platform-specific service management. |
| Packaging and running services | Python packaging, systemd, Docker/Compose, OCI images | Other language build tools, Buildpacks, Podman, immutable VM images. |
| Edge and transport | NGINX, DNS, TLS | Caddy, cloud load balancers/CDNs, certificate automation. |
| CI/CD | GitHub Actions and an explicit release procedure | GitLab CI, Jenkins; translate the same pipeline and trust rules. |
| Infrastructure and configuration | OpenTofu plus Ansible | Terraform comparison, remote state/backends, provider-specific modules, Packer. |
| Monitoring and reliability | Prometheus, Grafana, structured logs | OpenTelemetry, Loki, Alertmanager, multi-window alerts, capacity/load testing. |
| Kubernetes | kind, `kubectl`, versioned manifests | Helm/Kustomize, Argo CD/GitOps, managed clusters, advanced networking and stateful services. |
| Supply chain and secrets | Locked dependencies, least-permission tokens, synthetic secret rotation, a pinned scan/SBOM exercise | Trivy/Syft/Cosign, cloud workload identity/OIDC, Vault or provider secret managers. |
| Cloud resources and cost | Provider-neutral responsibility, network/IAM, resource inventory, cost/teardown reasoning | One fully tested AWS VM/VPC/IAM/storage deployment first; Azure/GCP translations later. |

Avoid installing Jenkins, an artifact repository, a full observability stack, a cloud cluster, and several alternative tools merely to unlock the next lesson. Those services add maintenance and resource demands while often teaching the same underlying concept.

## Concrete case and lab design

The following are **proposed recipe IDs**, not executable entries in the current catalog. Every live recipe still needs pinned source/images, license review, an adapter, measurements, negative controls, lifecycle tests, and an evidence contract.

| Candidate | Environment and task | Required checks and evidence |
| --- | --- | --- |
| `devops-request-path` | Browser evidence case. Select observations that locate a request failure and predict the effect of one change. | Server checks the selected evidence/decision against a private assigned fixture. Include a superficially similar case with a different cause; do not ship the diagnosis in public metadata. |
| `devops-service-recovery` | Learner-local disposable Linux VM. Repair a systemd service's identity/path/config and recover from a controlled process failure. | Unit configuration, observed process identity, listener, readiness, restart behaviour, retained data, and explicit cleanup. A uploaded log remains learner-provided evidence unless separately replayed/observed. |
| `devops-edge-route` | New scoped hosted adapter or local equivalent. Repair a controlled edge-to-app route using a restricted configuration model and fixed targets. | Before/after edge status; direct backend control; legitimate `/version`/read path; reject an unrelated route and unauthorized configuration fields. Explain the boundary: this is a routing exercise, not arbitrary NGINX administration. |
| `devops-ci-gate` | Browser pipeline/commit/artifact fixture; real GitHub extension in the learner's repository. | A failed commit cannot be selected for promotion; the release references the correct artifact/commit; untrusted branch events lack deployment credentials. Data-only checks validate the model, not a real GitHub workflow. |
| `devops-release-switch` | New scoped hosted adapter using two fixed Relay versions and an edge; first exercise is stateless/read-only. | Test before switch; atomic selected route change; rejected bad version; correct recovery; distinguish release identity from a mutable tag. Do not promise general zero downtime from a few HTTP samples. |
| `devops-iac-drift` | Learner-local OpenTofu/Ansible work against a disposable resource inventory. | Plan/apply agreement, appropriate handling of drift/replacement, idempotent configuration, retained state until destruction is confirmed. Raw state files and credentials stay local. |
| `devops-observe-slo` | Browser recorded measurements plus a small learner-local Prometheus/Grafana extension. | Correct SLI calculation and time window; evidence linking symptoms to user impact; detect the seeded issue without declaring every spike an incident. Live monitoring evidence is labelled separately from dataset analysis. |
| `devops-backup-restore` | Local Relay/SQLite dataset and clean recovery target; possible future bounded artifact checker. | Backup consistency; recovered expected rows/checksums; synthetic lost writes identified; original backup retained; no accidental deletion of the learner's prior saved work. A copied live SQLite file during writes is not assumed to be a valid backup. |
| `devops-kubernetes-rollout` | Learner-local kind cluster or an explicitly selected external training environment. | Deployment revision, readiness/service routing, request/limit configuration, corrected rollout, permitted/denied scope, and owned-cluster deletion. Never grant browser clients generic cluster-admin access on Ascend's shared host. |

### First worked example and independent challenge

The example teaches **process → listening socket → edge route → response** with a stopped application. Its tour has named steps, observable outputs, and a Skip tour action. Completing it records exposure to that technique.

The independent challenge is **“The release is running, but users see 502.”** A small assigned case provides an edge request result, backend readiness output, process/listener observations, and an editable restricted route. The learner must choose a discriminating check and restore the intended request path while leaving unrelated behaviour correct. In one authored variant the edge points to the wrong backend port; other variants alter the readiness or network assumption. The learner-facing title does not state the cause.

The finish line is explicit: the required endpoint returns the expected release, a named legitimate control still works, a wrong route remains rejected, and the learner retains the relevant before/after observations. A short explanation supports review; merely writing text is not an automatically verified diagnosis. Guidance on an unknown prerequisite opens a separate example, and the current case remains the same until ended.

After an independent success, the harder continuation might keep the endpoint healthy but route traffic to an **old release**, requiring artifact/version evidence instead of stopping at HTTP 200. Another continuation introduces an incompatible data change and asks whether rollback is safe. Both add reasoning without requiring a larger hosted environment.

## Capstone: a release with a recoverable incident

Use a learner-owned disposable VM as the first complete target. A local VM reached over SSH is sufficient to learn remote-host mechanics; it does not prove public cloud deployment. A cloud-backed variant records the additional provider evidence. The Kubernetes mode is a separate target variant with its own requirements; its existence must not silently change the VM capstone's rubric.

The learner receives a clean Relay source version, acceptance tests, synthetic data, target constraints, and an incident envelope. They must:

1. Build and test a release from a known commit, retaining artifact identity.
2. Run real CI in their own repository, then deploy/promote that tested artifact to a staging target under the stated trust rules.
3. Perform an explicit release decision and demonstrate version/readiness/legitimate requests.
4. Detect a supplied regression using logs and a stated user-visible indicator, preserve observations, and choose a justified recovery procedure.
5. Recover the required service behaviour and prove required data is present; identify any unavoidable loss against the exercise's RPO/RTO objective.
6. Recreate or hand over the deployment using a runbook, then account for and remove the exercise-owned runtime resources while retaining useful work.

Do not inject an arbitrary surprise after starting an assessment. The incident type is drawn from a reviewed set within the published skill scope; the actual cause can remain unknown. Keep the scenario/version, evidence rubric, timer policy, and reward contract fixed during the attempt. A subsequent changed-condition exercise has a new identity.

| Rubric component | Pass condition | Rejection/control case |
| --- | --- | --- |
| Release provenance | Artifact identity is linked to the tested source revision and deployment. | A mutable tag or unrelated passing pipeline cannot substitute for the deployed artifact's evidence. |
| Delivery safety | Failed checks stop the intended promotion; concurrent release handling is explicit. | A deployment from an untrusted PR or an untested revision fails the control. |
| Configuration and identity | Runtime identity/configuration match requirements; credentials are appropriately scoped. | Broad administrative grants, exposed sample secrets, and secret-bearing uploaded state do not satisfy the task. |
| Service behaviour | Named user flows and version/readiness controls pass through the actual target path. | A healthy process with broken routing, or HTTP 200 from the wrong release, is insufficient. |
| Recovery and data | Recovery meets the authored behaviour and retained-data checks; limitations are reported. | Blind rollback over a destructive schema change, an untested backup, or a missing dataset fails. |
| Handover | A reviewer or clean environment can follow the recorded release/recovery procedure. | An attractive screenshot or a README with commands that were never exercised is not reproducibility evidence. |
| Ownership/cleanup | All owned resources are inventoried, removed, or explicitly retained under the exercise contract. | Lost infrastructure state, a still-running untracked VM, or deletion of unrelated resources fails. |

Some rubric components can be checked mechanically; others need a human review or a trusted replay. Show that distinction in the result. A learner-local report can complete a self-directed learning activity under its declared manual rules, but it cannot be silently presented as an independently observed deployment credential.

## Delivery within the two-lab budget

### Execution boundaries

| Work | Initial location | What Ascend should retain |
| --- | --- | --- |
| Request/CI/SLO reasoning | Browser and bounded server-side data checks. | Small assigned answers, result components, attempt/version, notes. |
| Scoped route/release exercises | Existing separate runner after new adapters pass review; at most two active hosted runs overall. | Allowed config changes, observed controls, small exports, runtime inventory. |
| Shell, systemd, image building, arbitrary CI scripts, IaC providers, Ansible, package installation | Learner-local disposable environment or the learner's own CI/cloud sandbox. | Explicitly submitted small artifacts/observations, with their real evidence authority. |
| Kubernetes administration, full observability stacks, stateful scaling | Learner-local cluster/VM; reviewed external environment as an optional route. | Small manifest/report/runbook evidence; no cluster snapshots or VM disks. |

A Dockerfile, CI workflow, provider plugin, Ansible task, or privileged Kubernetes manifest can execute code or acquire broad host authority. The existing runner's allowlisted HTTP/file/router operations do not provide isolation for arbitrary versions of these. Do not add a Docker socket, shell endpoint, or shared self-hosted GitHub runner to Ascend's web app to make these lessons convenient. A generic hosted code/build environment would require a separate disposable VM/sandbox design and new capacity evidence.

The hosted route/release adapters accept a small reviewed data model and invoke fixed administrative operations. They do not accept arbitrary images, Compose files, shell commands, proxy destinations, or infrastructure providers from the learner. Real toolchain proficiency is established in the corresponding learner-local/owned-sandbox exercise.

### Proposed envelopes, not measurements

For the first two hosted candidates, aim for an edge-route exercise within **256 MiB total capped working memory and 0.75 CPU**, and a stateless release-switch exercise within **384 MiB and 1.25 CPU**, including its bounded checking work. These are engineering targets to test, not existing allocations or observed usage. If an image/checker cannot fit safely, revise the recipe or keep it local.

Start with at most **256 MiB writable scratch per run**, small bounded exports consistent with the existing 256 KiB text interface, and a reviewed shared image-cache budget. Measure image compressed/expanded size, extraction/build cache, cold/warm launch, peak RSS/cgroups, CPU, disk, and repeated cleanup on the actual host. Two nominal slots do not guarantee every recipe pair fits; use the adaptive proposal's CPU/memory/disk reservation policy and retain the 10 GiB free-space reserve.

Do not prewarm a VM, Kubernetes cluster, registry, Jenkins instance, and monitoring stack for each learner. Where a case allows it, do reading/planning before the lab lease, reserve a short live phase, export observations, and perform analysis after releasing the runtime. A stop is not the same as finish/export/destroy; the existing stopped and cleanup-failed runs still occupy capacity.

When both hosted slots are occupied, keep the selected task visible and offer waiting, the corresponding local instructions, or a similarly demanding artifact case. Do not mark a simulated substitute as the same completed live milestone. The waiting ticket must not start a scored attempt or silently replace another foreground session.

For local work, show recipe-specific requirements before start. A Linux desktop/VM with Docker is the first supported authoring/test target. A 16 GB desktop with space for a disposable VM/cluster is a useful **planning recommendation** for the entire extended toolchain, not a hard measured minimum. Some individual file/container cases will need much less. Windows/WSL2, macOS, ARM, nested virtualisation, and corporate-network limitations need explicit recipe tests rather than a blanket compatibility badge.

### Accounts and external services

GitHub exercises run in a learner-owned repository, with clearly described public/private visibility and Actions usage implications. Do not create repositories, publish packages, add secrets, or send comments from Ascend merely because a person opens the track. A future connector must request only the capabilities required for the chosen exercise and make the external action concrete. The curriculum itself can remain readable without linking an account.

GitHub documents plan/repository-dependent environment protection features. Where required reviewers are unavailable, offer a supported manual release gate and describe the weaker assurance rather than pretending the unavailable protection is enabled. OIDC is appropriate when a selected provider actually supports the intended trust configuration; an `id-token` permission is not automatically a secure cloud deployment. Keep claims, audience, repository/ref/environment restrictions, and credential lifetime in the exercise. [GH4], [GH5]

Cloud variants need a learner-owned sandbox/account, a chosen region, a resource/cost budget, billing visibility, quota checks, a provider identity, and independently confirmed cleanup. Budgets often alert rather than cap charges. No paid cloud provisioning is part of this design audit. Public domains/certificates and external CI are optional requirements displayed on the applicable variants; localhost practice cannot be described as an Internet deployment.

## Integration with the current workspace

The current [pack format](../pack-format.md) and [parser](../../ascend/engine/packs.py) already support a proficiency pack, dependency DAG, main/side levels, clear previews/requirements, full briefs/setup/steps/materials, optional hints, and authored checkpoints. Main proficiency levels require an M/L milestone. Reuse these contracts.

Proposed files and boundaries for implementation:

| Area | Planned change |
| --- | --- |
| Canonical curriculum | Add a separate `docs/curriculum/devops-track.json` containing stable capability/module/node IDs, prerequisite mappings, case identities, source references, and environment/evidence requirements. Keep this out of the cyber-only specialist input. |
| Pack output | Generate `packs/community/engineering/devops-deployment-foundations.toml`, initially `source = "ai-draft"`, `reviewed = false`. Use 13 main levels plus optional side practice; provide real input assets and per-node references. Mark reviewed only after content/technical acceptance. |
| Materials | Add inspectable Relay source, tests, fixture variants, reference configs, and task files under a separate `tracks/devops-tracks/materials/` root. Package deterministic small archives under `web/training/`. Do not include tokens, database dumps with personal data, large images, or a whole upstream toolchain. |
| Generation/registry | Add a DevOps-specific generator and shared validation rather than copying the cyber curriculum wholesale. Extend `scripts/package_learning_materials.py`, whose source root is currently hard-coded to cyber materials. Update catalog metadata and run the existing registry generator against the new pack. |
| Playground | Reuse the same skill/case identities for short diagnostic, transfer, repair, and mystery variants. A track and Playground view of one assessment share its reward identity; neither duplicates first-solve credit. |
| Lab catalog | Add candidate references and recipes under `ascend/local_labs/resources/` only when their manifests are concrete. A recipe stays unavailable until a fixed adapter, platform measurements, and lifecycle controls pass `review_gaps`. |
| Evidence integration | Add an explicit versioned binding between a track requirement and an accepted evidence contract. Current `recipe_detail` returns `satisfies_track_evidence = false`; current hosted checks give zero XP. Merely adding a recipe ID or a green check cannot satisfy a verified track milestone. |
| Presentation | A project hub, distinct example/challenge/workspace cards, readable release/evidence views, and clear save/export state. Keep the active task on its dedicated route with the relevant service diagram and controls. |
| Storage and versioning | Add only the required account-scoped records through additive migrations. Preserve private installed packs, past receipts, active scenario snapshots, and existing strict assessed timers. A content update should not silently swap an in-progress case. |

There is no current native `verify.type = "devops"`, and no general `recipe_id` field in the parsed `Node` model. Define the binding deliberately in the shared application/catalog layer or extend the schema with validation; do not insert an invented verifier into a TOML file and expect it to work.

For early content review, ordinary manual/local exercise completion must be labelled accordingly. A file's existence/size verifies only that limited property. A later trusted checker should evaluate the learner's specific versioned artifact or observe the named controls in an assigned environment; it must not trust uploaded `passed: true`, arbitrary local logs, or learner-held signing keys.

Existing practice and track reward policies remain the starting point. Celebrate meaningful outcomes such as “Recovered a failed release” and show the evidence/result. Opening a lab, installing a tool, leaving a terminal running, or repeating a known green pipeline should not produce new verified mastery rewards. Contribution and peer review can motivate advanced learners, but require actual review and a separate contribution record.

## Advanced branches and continuous practice

After the core, learners can choose one branch without restarting the track:

| Branch | Practical continuation | Environment |
| --- | --- | --- |
| Cloud deployment | One reviewed provider: IAM, VM/network, DNS/TLS, storage, monitoring, cost inventory and teardown. Then translate the architecture to another provider. | Learner-owned sandbox; explicit spend/access requirements. |
| Kubernetes operations | Helm/Kustomize, GitOps/Argo CD, RBAC, network policy, workload identity, resource pressure, upgrades and recovery. | Local/disposable cluster; cloud cluster only through its own accepted recipe. |
| Stateful services | PostgreSQL-backed Relay, schema compatibility, backups, replicas, failover tradeoffs and data recovery. | Local environment sized for the chosen database; no automatic HA claims. |
| CI/platform engineering | Translate the pipeline to GitLab/Jenkins, reusable delivery templates, build caching, ephemeral runners and a small self-service deployment interface. | Learner-local/owned sandbox; never Ascend's production runner credentials. |
| Reliability engineering | Instrument a trace, investigate an SLO breach, tune alerting, run bounded load, practice a handover and postmortem. | Mostly artifact cases plus measured local live work. |
| Supply-chain security | Build provenance, image signatures, dependency changes, SBOM review and admission policy on known fixtures. | Bounded analysis/local signing environment with synthetic identities. |

Publish continuing cases around **changed assumptions**, not randomised filenames: a successful health probe hides an old version; a retry duplicates a write; an expired credential prevents rollback; a Terraform plan replaces a stateful resource; a readiness selector removes all healthy endpoints; a backup exists but cannot restore the expected data. Make the hard part selecting and verifying the right action.

Maintain content as versioned code: a proposed monthly link/deprecation review, scheduled lab replay on supported platforms, and a deeper quarterly curriculum review. Security or upstream breakage can temporarily disable an affected recipe while preserving saved work and explaining the reason. Test updated fixtures/adapters before making them defaults. Pin runnable dependencies/images separately from live reference links, publish change notes, and preserve the version of an existing attempt.

Learner-authored variants are a later contribution route. Require reproducibility, solvability, expected controls, resource limits, clear wording, license review, and reviewer sign-off before publication. A Git push or an AI-generated scenario is not sufficient content acceptance.

## Delivery milestones and gates

| Stage | Deliverable | Exit condition |
| --- | --- | --- |
| **D1. Curriculum and first slice** | Final 13-level map, capability/verification matrix, Relay source/test contract, first example and request-path independent case. | Reviewers can identify prerequisites, inputs, actions, save locations, finish line, and evidence limits without explanation. Existing-user entry can bypass redundant instruction without fabricated completion. |
| **D2. Local deployment loop** | Levels 1–6 as a coherent small pack slice for review, then full proficiency-pack generation when all required levels exist. | Real disposable Linux testing proves packaging, service recovery, edge behaviour, data persistence, and owned cleanup. Do not ship a six-level proficiency pack that violates the current 8–15-level schema. |
| **D3. CI, IaC, observation, recovery** | Real learner-owned pipeline instructions and cases for levels 7–11, plus bounded browser alternatives with accurate labels. | Failing controls fail; untrusted workflow/credential paths are constrained; restore and drift/teardown are actually exercised. Provider/account variants state tested scope. |
| **D4. First hosted DevOps adapters** | Restricted edge and stateless release-switch adapters after the common queue/reservation work. | Positive/negative checks, account isolation, payload/config bounds, measured resource envelope, cold/warm launch, restart/expiry/export/cleanup tests. Two slots remain an aggregate limit with other lab recipes. |
| **D5. Kubernetes and capstone** | Real local cluster workflow, versioned incident variants, capstone artifact/rubric and review workflow. | A fresh target or reviewer reproduces the runbook; release identity, failure detection, recovery and data controls pass; claims distinguish local report, tested submission and trusted observation. |
| **D6. Pilot and maintain** | Beginner/practitioner sessions, reviewed timing, content updates, optional branch backlog. | Measure comprehension, useful time-on-task, fresh independent transfer, repeat fatigue, resource/queue behaviour, and cleanup. A higher pass rate alone is not success if the tasks become easier. |

Application tests are not required for this design-only document. During implementation, use the existing pack/distribution/material checks, exercise meaningful negative cases in each evaluator, and run real lifecycle verification for each new adapter. Keep instructional clarity checks separate from technical assertions; both are required for a usable DevOps track.

[DK1]: https://kodekloud.com/learning-path/devops "KodeKloud DevOps learning path"
[DK2]: https://www.techworld-with-nana.com/devops-bootcamp "TechWorld with Nana: public DevOps syllabus"
[KL1]: https://killercoda.com/about "Killercoda environments and membership"
[KL2]: https://killercoda.com/creators "Killercoda creator documentation"
[DO1]: https://docs.docker.com/get-started/workshop/ "Docker: build and share a containerized application; redirects to current tutorial"
[GH1]: https://raw.githubusercontent.com/skills/hello-github-actions/main/README.md "GitHub Skills: Hello GitHub Actions"
[GH2]: https://raw.githubusercontent.com/skills/test-with-actions/main/README.md "GitHub Skills: Test with Actions"
[GH3]: https://raw.githubusercontent.com/skills/publish-packages/main/README.md "GitHub Skills: Publish Docker Images"
[GH4]: https://docs.github.com/en/actions/deployment/targeting-different-environments/managing-environments-for-deployment "GitHub: deployment environments; redirects to current documentation"
[GH5]: https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect "GitHub: OpenID Connect; redirects to current documentation"
[KU1]: https://kubernetes.io/docs/tutorials/kubernetes-basics/ "Kubernetes Basics"
[KU2]: https://kind.sigs.k8s.io/docs/user/quick-start/ "kind Quick Start"
[TF1]: https://developer.hashicorp.com/terraform/tutorials/docker-get-started "Terraform: Docker getting-started tutorials"
[OT1]: https://opentofu.org/docs/intro/ "OpenTofu introduction and workflow"
[AN1]: https://docs.ansible.com/ansible/latest/getting_started/index.html "Ansible: getting started; redirects to current documentation"
[PM1]: https://prometheus.io/docs/introduction/first_steps/ "First steps with Prometheus"
[SR1]: https://sre.google/workbook/implementing-slos/ "Google SRE Workbook: Implementing SLOs"
[SR2]: https://sre.google/workbook/incident-response/ "Google SRE Workbook: Incident Response"
