# Open-source labs and a concrete learning path

Reviewed 2026-11-02. The owner requested research beyond the best-known training
platforms, on-demand downloads, execution on learners' PCs, and meaningful
verification. **Linux is the first client platform**, as explicitly selected by
the owner. This is a research and implementation proposal. The newly listed labs
have not been installed, benchmarked, or integrated into Ascend by this work.

The recommendation is to keep a small source catalog in Ascend and run selected
labs on the learner's Linux computer. Use upstream curricula and environments
where they add depth, then author the prerequisites, evidence requirements, and
transfer exercises that connect them to Ascend. The companion
[execution plan](local-lab-execution-plan.md) covers fetching, storage, cleanup,
and verification. The [candidate register](../curriculum/open-source-lab-candidates.json)
records the repositories, review status, known licenses, and track mappings;
it is research data, not an executable pack registry.

## What Ascend currently uses

| Area | Evidence in the inspected working tree | Meaning |
| --- | --- | --- |
| Playground | [catalog.py](../../ascend/playground/catalog.py) contains 37 authored/generated browser activity definitions, including worked examples and workspaces. | These are Ascend exercises, not cloned upstream lab environments. |
| Tracks | [sources.json](../curriculum/sources.json) references Juice Shop, WebGoat, DVWA, crAPI, GOAD, Damn Vulnerable GraphQL Application, Atomic Red Team, CloudGoat, FLARE-VM, and the adversary emulation library. | There is already some open-source research, but a reference or toolkit is not an installed, graded lab. |
| Local services | [labs.compose.yml](../../docker/labs.compose.yml) defines Juice Shop, WebGoat, and Mosquitto profiles. | Two training applications and an MQTT service have administrator-managed setup support. This is not a general per-learner runner. |
| External evidence | [collect_lab_proof.py](../../scripts/collect_lab_proof.py) collects account-bound signed observations for Juice Shop and Bandit. | Useful existing infrastructure, under its administrator/key-holder trust assumption. It is not attestation of an arbitrary learner-owned PC. |

## Shortlist beyond the existing references

Difficulty below is an Ascend sequencing recommendation based on prerequisites
and task scope, unless an upstream scale is explicitly identified. It is not a
measured equivalence between projects. Ranking considers instructional structure,
repeatable setup, feedback, legitimate-control tests, resource fit, reuse terms,
and maintenance evidence. Popularity alone does not establish quality.

| Source | Level and preparation | Why it is useful | Delivery and proposed place |
| --- | --- | --- | --- |
| [Linux Upskill Challenge](https://github.com/livialima/linuxupskillchallenge) | Starter; follows a published day-by-day sequence. | Source lessons cover shell navigation, services, logs, users, permissions, and scripting. Day 0 includes a local-server option; the README links its Reddit and Lemmy learning communities. | Local disposable Linux VM; foundation reference before security labs. No automatic completion checker was established in this review. |
| [Labtainers](https://github.com/mfthomps/Labtainers) | Starter through advanced; the [NPS catalog](https://nps.edu/web/c3o/labtainer-lab-summary1) supplies numeric difficulty ratings and the framework has ordered Labpacks. | More than 50 exercises across networking, traffic analysis, cryptography, system security, reverse engineering, and ICS. Per-lab downloads and student/instructor assessment are already designed into the framework. | First pilot: `network-basics` and `telnetlab`. Run locally, preferably in the upstream VM for labs requiring host-level capabilities. Review each lab's actual assessment before assigning credit. |
| [VAmPI](https://github.com/erev0s/VAmPI) | Starter-to-intermediate after HTTP, JSON, tokens, and ownership rules. | Small Flask API with OpenAPI/Postman resources and a vulnerable/non-vulnerable switch, useful for checking both a finding and the corresponding legitimate behavior. | First API pilot using a reviewed local container recipe. Ascend needs a specific checker; successful startup is not completion. |
| [Damn Vulnerable RESTaurant](https://github.com/theowni/Damn-Vulnerable-RESTaurant-API-Game) | Intermediate; API basics and Python/FastAPI for the repair route. | Separate developer repair game and penetration-testing route. The upstream documents `start_game.sh`, `start_app.sh`, and `stop_app.sh`. | Follow VAmPI with a selected repair task. Local Docker Compose/PostgreSQL; source edits can take effect while the game runs. Stops preserve data, so final cleanup is a separate operation. |
| [WrongSecrets](https://github.com/OWASP/wrongsecrets) | Starter-to-advanced depending on the challenge; distinguish local, Kubernetes, and cloud prerequisites. | Focused secrets-management challenges, hints, and CTF integration. Useful for secure development and explaining why a discovered secret was exposed. | Pilot only the documented Docker/`no-vault` subset after the first API labs. Kubernetes, cloud, and desktop-with-Docker-socket options have separate requirements. |
| [StratoCyberLab](https://github.com/stratosphereips/stratocyberlab) | Starter-to-advanced, with per-challenge difficulty and class environments. | A local cyber range with a dashboard, WebSSH, challenge start/stop, flags, and source for adding challenges. Particularly relevant to the desired Playground experience. | Evaluate as an optional local VM range and design reference. Upstream estimates 3 GB disk and 2 GB spare RAM; these are not Ascend measurements. Its dashboard controls Docker, so it must not be transplanted into Ascend's application container. |
| [Security Datasets](https://github.com/OTRF/Security-Datasets) | Starter with a prepared evidence slice; intermediate-to-advanced for independent detection work. | Malicious and benign telemetry can support investigations and positive/negative detection tests without deploying an enterprise SIEM. | First data pilot: fetch individual reviewed files to the PC. Author an Ascend evidence rubric. The full repository is unnecessary for one exercise. |
| [EVTX-ATTACK-SAMPLES](https://github.com/sbousseaden/EVTX-ATTACK-SAMPLES) | Intermediate; Windows event semantics and basic filtering. | Windows/Sysmon samples organized around ATT&CK techniques. Useful for SOC, DFIR, and threat-hunting exercises. | Fetch selected artifacts, then validate a Linux-compatible parser. The supplied Winlogbeat replay script is PowerShell, so it is not a ready-made Linux adapter. Known attack samples need benign controls. |
| [KC7](https://github.com/KC7-Foundation/kc7) | Starter-to-intermediate; query instruction is part of the learning experience. | Investigations in a fictional company spanning web, email, and endpoint events; useful as an example of an approachable detection path. | External learning option and curriculum reference. The published game uses Azure Data Explorer: cloning its generator does not reproduce a complete offline game. The separate `kc7_data` repository's license was not established. |
| [BGP Labs](https://github.com/bgplab/bgplab), with [netlab](https://github.com/ipspace/netlab) | Intermediate after IP addressing and routing; progresses from basic BGP to policy and advanced scenarios. | Source topologies, a published progression, and a local validation framework that actually interrogates the running lab. | Local Linux networking extension, initially using open FRRouting images. Commercial network OS images retain their own licensing and resource requirements. |
| [RPISEC Modern Binary Exploitation](https://github.com/RPISEC/MBE) | Intermediate-to-advanced; C, assembly, and Linux familiarity are explicit prerequisites. | A real course sequence, source labs, and cumulative projects rather than a collection of unrelated links. | Later reverse-engineering path. The original environment is Ubuntu 14.04, 32-bit; use a dedicated compatibility VM or review a port. Do not run its system setup script on the learner's everyday host. |
| [CloudFoxable](https://github.com/BishopFox/cloudfoxable) | Intermediate-to-advanced after IAM and cloud fundamentals. | Guided cloud challenges with individually enabled Terraform modules; a concrete example of provisioning only selected exercises. | Optional learner-owned AWS account. A local launcher still creates real cloud resources; it is not an offline Docker lab. Preserve Terraform state until destruction is confirmed. |
| [Kubernetes Goat](https://github.com/madhuakula/kubernetes-goat) | Intermediate-to-advanced after containers, RBAC, and Kubernetes networking. | Scenario-based cluster security with setup and access scripts. | Dedicated disposable cluster on the learner's Linux machine/VM; later adapter. Upstream requires cluster administration, `kubectl`, and Helm. |
| [MASTG Hacking Playground](https://github.com/OWASP/MASTG-Hacking-Playground) | Intermediate after Android application fundamentals. | Intentionally insecure Android/iOS apps mapped to MASTG test cases, with source and build/install guidance. | Linux-first scope is Android in an emulator or owned test device. Kotlin also needs its backend. Toolchain age, app-level licensing, and verification need further review; iOS is a separate platform path. |
| [Damn Vulnerable LLM Agent](https://github.com/ReversecLabs/damn-vulnerable-llm-agent) | Intermediate-to-advanced; API/tool authorization and prompt-injection concepts. | A concrete ReAct-agent application, with remote-provider and local Ollama options. | Later AI-security extension. Local model weights can dominate disk/RAM; upstream warns that small models may not behave reliably. Keep deterministic Ascend exercises as preparation. |

The new shortlist complements the existing projects. In particular, a new Linux
runner does not make GOAD's Windows VMs, physical wireless tasks, mobile emulators,
or real cloud enforcement work inside a small generic container.

## Concrete progression for tracks and Playground

Keep upstream level labels and Ascend prerequisites separately. NPS's catalog
rates `network-basics` and `telnetlab` at 1, `nmap-discovery` and `iptables2` at 2,
and `pcap-lib` at 3; this is useful published ordering, not a universal difficulty
scale. Exact task duration remains unmeasured, including initial downloads.

| Path | Ordered exercises/resources | Evidence required before moving on |
| --- | --- | --- |
| Linux and networking foundation | Linux Upskill Day 0 local VM, then days 1–2, 8, 13–14 → Labtainers `network-basics` → `telnetlab` → `nmap-discovery` → `iptables2`. | Explain observations, identify the selected service, and show allowed traffic still works after a restriction. A command invocation count alone is insufficient. |
| Web/API and secure development | Ascend request-decision preparation → VAmPI owner/non-owner comparison → selected RESTaurant repair → a changed API case → local WrongSecrets challenges. | A bounded reproduction, a justified fix, and a legitimate-control test. For a patch, rerun trusted tests on the submitted patch before calling it server-tested. |
| SOC, DFIR, and hunting | Ascend event/timeline preparation → one small Security Datasets case → a benign comparison → a selected EVTX case → independent detection/reporting. KC7 is an optional guided external branch. | Query/rule, matching event identifiers, a justified timeline, and false-positive discussion. A correct incident label does not establish a working detector. |
| Network engineering/security | Addressing and routing basics → BGP Labs `basic/0-frrouting` → `basic/1-session` → `basic/3-originate` → `basic/6-protect` → `policy/3-prefix`. | Expected sessions/routes, rejection of an undesired route, and preservation of the allowed route. Use the selected lab's `netlab validate` tests where present. |
| Reverse engineering | Labtainers `gdblesson`/`overrun` preparation → MBE lab 01 → lab 02 → later selected labs/projects in the compatibility environment. | Reproducible observations tied to a particular binary and a changed input, with toolchain/architecture recorded. Kernel exercises require a separate VM capability class. |
| Cryptography and OT | Labtainers `onewayhash`/`symkeylab` → `sshlab`/`ssl`; separately, existing OT preparation → `plc-forensics` → `plc-forensics-adv`. | Predict a changed case, inspect the supplied evidence, and distinguish protocol observations from real-world operational/safety claims. Verify each selected lab's actual rubric. |
| Specialist branches | IAM preparation → selected CloudFoxable module; Kubernetes fundamentals → selected Kubernetes Goat scenario; Android fundamentals → selected MASTG app case; AI boundaries → selected LLM-agent experiment. | Environment-specific evidence. Cloud authorization, Kubernetes enforcement, mobile runtime behavior, and stochastic model behavior need different checkers. |

Tracks should supply prerequisites and ordered milestones. Playground should let
the same eligible lab appear as independent practice with its own attempt, notes,
and history. Both reference one recipe/version; neither duplicates the repository
inside its pack. Existing track completion and rewards must retain their current
verification requirements.

Public flags, walkthroughs, attack-labelled filenames, and auto-solvers can reveal
a task's answer. Use these labs as named practice unless a genuinely different
assessment has been authored. Renaming a published challenge does not turn it
into a blind mystery. Guided preparation should use a separate example, followed
by a changed case and a legitimate control.

There are still coverage gaps: this review does not supply a new turnkey AD
range, live-malware environment, radio/hardware lab, complete GRC curriculum, or
complete vulnerability-management dataset. Findings from the selected labs can
feed reporting and prioritization tasks, but do not substitute for those domains.

## What community and developer discussions changed

These are specific reports and design discussions, not a claim of community
consensus or proof that a historical defect still affects the latest release.

| Discussion inspected | Finding | Consequence for Ascend |
| --- | --- | --- |
| [Labtainers #87](https://github.com/mfthomps/Labtainers/issues/87) and [#85](https://github.com/mfthomps/Labtainers/issues/85) | Users report a result-tag mismatch and command-count checks that miss intended work. The student guide independently says `checkwork` is not a grade. | Test every adapter with known-good, known-bad, incomplete, and legitimate-control fixtures; document exactly what a check proves. |
| [Chall-Manager #1046, maintainer explanation](https://github.com/ctfer-io/chall-manager/issues/1046#issuecomment-3503540087) | A missing/crashed container can leave infrastructure state inconsistent. The maintainer deliberately retains failed-deletion state rather than hiding possible remaining resources; the thread discusses operator recovery. | Keep a visible `cleanup_failed` state, resource inventory, and reconciliation path. Never equate deleting an app's database row with destroying infrastructure. |
| [Chall-Manager #1109](https://github.com/ctfer-io/chall-manager/issues/1109) | A v0.6.0 user reported PID growth across creation/destruction cycles. | Measure repeated lifecycle cycles, process counts, and residual resources before adopting a runner. One successful launch is insufficient. |
| [DevPod #1949](https://github.com/loft-sh/devpod/issues/1949) and [#945](https://github.com/loft-sh/devpod/issues/945) | Users discuss a workspace storage limit despite free host disk, and reusing persistent volumes across workspace deletion/recreation. | Inspect the filesystem/volume that actually stores the lab, and define saved-work ownership independently of runtime lifecycle. These reports concern particular providers. |
| [Stack Overflow: Compose down versus Ctrl+C](https://stackoverflow.com/questions/55282552/difference-between-docker-compose-down-and-ctrl-c) | Stopping containers differs from removing containers and networks. | Define stop, finish, reset, and cache eviction separately; confirm current behavior with [Docker's down documentation](https://docs.docker.com/reference/cli/docker/compose/down/). |
| [Information Security Stack Exchange: local pentest VM](https://security.stackexchange.com/questions/8445/securely-building-a-local-pentest-lab-in-a-vm) | The historical discussion raises network separation and VM boundaries, but also contains outdated blanket safety claims. | Treat it as historical context. Use current upstream requirements and Ascend's existing isolation design for actual deployment decisions. |

## Reuse and review limits

The candidate register distinguishes a license file that was read from a license
reported by GitHub metadata. Linux Upskill declares **CC BY 4.0**. VAmPI, BGP Labs,
netlab, and Kubernetes Goat have MIT terms in the files inspected. WrongSecrets
currently has an **AGPLv3** license file. Labtainers has its own NPS distribution
notice plus third-party and SEED-derived material with separate terms.

Security Datasets illustrates why badges are insufficient: its README has both
MIT and GPL statements, while the inspected root `LICENSE` is MIT. Record that
conflict and check the particular dataset's notices before redistribution. KC7's
code license does not automatically license the separate scenario-data repository.
MASTG app-level terms remain unresolved in this pass. Reference links can be
cataloged while packaging and execution remain disabled.

GitHub repository search was used directly for API targets, security datasets,
local cyber ranges, Linux challenges, and LLM applications. Personal solution
collections, unrelated tools, missing-license collections, and search-only hits
were not promoted into runnable lab recommendations. Repository push dates are
maintenance signals, not tests of quality or reproducibility; older fixed datasets
can still be useful.

Reddit's JSON search and RSS endpoint and Quora search returned HTTP 403. Google
returned a JavaScript interstitial, DuckDuckGo a bot challenge, and the inspected
Bing result did not support the requested community claims. No Reddit/Quora
consensus is asserted. The usable community evidence here is from public GitHub
issues/comments and Stack Exchange APIs, checked against upstream documentation.
No forum messages were posted and no maintainers were contacted.

Verification for this research consists of reading the cited sources, checking
selected immutable revisions, and validating the local register and links.
Runtime reliability, Linux architecture support, disk/RAM measurements, and
learning outcomes remain explicit pilot work in the execution plan.
