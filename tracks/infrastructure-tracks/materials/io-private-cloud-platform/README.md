# Private Cloud & Platform Engineering

Operate a small college-style VM service using an existing control plane, with scoped roles and honest failure boundaries.

Recommended sequence position: 9 of 9 in Infrastructure & Internet Operations.

## Choose your starting point

New to this subject: start with the worked operation in level 1. Already practising: attempt an independent operation first and use Ascend early-unlock for a later level when appropriate. It records your choice, not an automatic proficiency pass. Job preparation emphasizes the reproducible handover; interest-led work can extend the same technical evidence with a different owned environment.

Use the earlier tracks or equivalent practical experience. The sequence recommends background and does not require completing another whole track.

The nine tracks progress through Linux/networking, VMs, public hosting, private access, delivery automation, mail/state, traffic/capacity, resilient hardware and private cloud administration. The order recommends background; earlier whole tracks are not hard prerequisites. The default main-level gates use the prior milestone. Existing early-unlock lets a practitioner attempt a later independent milestone without doing every worked example.

## Start here

Download /training/io-private-cloud-platform.zip and extract it into a NEW folder you choose on your PC. Open a terminal in its io-private-cloud-platform directory; read README.md and bootstrap.md. Python 3.11+ runs the portable tools without extra Python packages. POSIX examples use Linux; Windows users can use a prepared Linux guest or WSL for the initial shell practice. Create work/ and notes/. Copy notes-template.md in your editor to notes/entry.md, or append a dated attempt if the note already exists. Input files are in inputs/NN/, portable starting cases in cases/, operational instructions in lessons/NN.md, and the shared synthetic service in shared/. All generated work remains in the local paths printed by the tools. Opening a challenge does not create or upload these files. Use Ascend's notebook/upload control only when you choose to copy evidence into Ascend. Run commands one at a time on the named HOST, GUEST or CLIENT. Replace explicit address/key placeholders after inspection, and keep each foreground service in its own terminal. Stop its process with Ctrl+C before reusing the same listener.

Read bootstrap.md, then check the local tools:

```sh
python3 --version
mkdir -p work notes
python3 shared/selfcheck.py
```

For the first persistent service, open Terminal A in this extracted folder:

```sh
python3 shared/relay.py --host 127.0.0.1 --port 8000 --data data/relay.sqlite --release v1
```

Terminal B, same machine and folder:

```sh
python3 shared/check_service.py --url http://127.0.0.1:8000 --expect-release v1 --write
```

Stop Terminal A with Ctrl+C before a lesson starts another listener on that port. The SQLite data remains at data/relay.sqlite. A teaching selfcheck and an actual learner operation are different results.

## Practical sequence

1. [Read an existing control plane](lessons/01.md) — Trace guest creation in one supported existing platform from UI/API to hypervisor and virtual network.
2. [Offer reproducible guest templates](lessons/02.md) — Publish a small internal catalog of reviewed templates in the owned lab platform.
3. [Separate learner and operator roles](lessons/03.md) — Use two sample learner identities and an operator in the local platform.
4. [Handle lifecycle and resizing jobs](lessons/04.md) — Create/start/stop/resize a guest and inspect the platform's job and inventory state.
5. [Publish a guest service](lessons/05.md) — Give a learner guest a website route and a separate administration path.
6. [Move and recover guests](lessons/06.md) — Restore or migrate between supported lab hypervisors; use a second physical host for physical-failure evidence.
7. [Compare orchestration layers](lessons/07.md) — Deploy Relay's stateless mode in a small separate cluster lab and compare its control loop with VM management.
8. [Run the college-style capstone](lessons/08.md) — Operate two learner guests through the selected existing control plane and hand over a reproducible runbook.

Each level has a worked operation, a distinct portable transfer fixture, an independent native application, named failure controls and recovery/cleanup. Optional recall tasks invite a later return. Estimated active time per level is 90 minutes worked practice plus 120 minutes independent work, excluding setup/downloads; split sessions as needed. Estimates are author judgments, not measured learner times.

## What completion means

Operational milestones use manual review of real observations. Portable configuration feedback checks only the stated data contract; it does not create VMs, measure physical hardware, verify learner identity, or establish public reachability. Required native operations remain incomplete until performed. Recipes are unreviewed drafts; tool-version and provider/hardware variants require native replay before a tested label.

The portable cases intentionally expose their rubric and reference; they teach diagnosis and planning. Setting a Boolean to true does not demonstrate that the event happened. Retain real observations for native milestones and record any help used. A local reference, checked fixture, manual completion, public observation and physical-device test must not be presented as interchangeable evidence.

For job preparation, retain a reproducible handover with source/config identities and a recovery demonstration. For curiosity, extend the same controls to another guest, device or owned route. Neither intention changes what the task actually proves.

This material keeps the shared server's two hosted lab slots unchanged. Use the learner PC for guests/builds/load generation; bootstrap.md covers the small-server, 16 GB PC and optional physical-device routes.

The supplied Relay is a synthetic-data teaching service, not a production internet application. Provider/native recipes have not been replayed on every host or account. Source is ai-draft and reviewed=false; record tool versions and untested boundaries.
