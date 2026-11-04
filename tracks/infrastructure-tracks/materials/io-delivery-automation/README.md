# Delivery & Infrastructure Automation

Reproduce a service and its infrastructure, promote a tested release, and recover a bad change.

Recommended sequence position: 5 of 9 in Infrastructure & Internet Operations.

## Choose your starting point

New to this subject: start with the worked operation in level 1. Already practising: attempt an independent operation first and use Ascend early-unlock for a later level when appropriate. It records your choice, not an automatic proficiency pass. Job preparation emphasizes the reproducible handover; interest-led work can extend the same technical evidence with a different owned environment.

Use the earlier tracks or equivalent practical experience. The sequence recommends background and does not require completing another whole track.

The nine tracks progress through Linux/networking, VMs, public hosting, private access, delivery automation, mail/state, traffic/capacity, resilient hardware and private cloud administration. The order recommends background; earlier whole tracks are not hard prerequisites. The default main-level gates use the prior milestone. Existing early-unlock lets a practitioner attempt a later independent milestone without doing every worked example.

## Start here

Download /training/io-delivery-automation.zip and extract it into a NEW folder you choose on your PC. Open a terminal in its io-delivery-automation directory; read README.md and bootstrap.md. Python 3.11+ runs the portable tools without extra Python packages. POSIX examples use Linux; Windows users can use a prepared Linux guest or WSL for the initial shell practice. Create work/ and notes/. Copy notes-template.md in your editor to notes/entry.md, or append a dated attempt if the note already exists. Input files are in inputs/NN/, portable starting cases in cases/, operational instructions in lessons/NN.md, and the shared synthetic service in shared/. All generated work remains in the local paths printed by the tools. Opening a challenge does not create or upload these files. Use Ascend's notebook/upload control only when you choose to copy evidence into Ascend. Run commands one at a time on the named HOST, GUEST or CLIENT. Replace explicit address/key placeholders after inspection, and keep each foreground service in its own terminal. Stop its process with Ctrl+C before reusing the same listener.

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

1. [Build an identifiable release](lessons/01.md) — Build Relay from a known revision and retain a manifest.
2. [Package the runtime](lessons/02.md) — Run an immutable image locally and in the service VM.
3. [Compose a small service](lessons/03.md) — Run edge, application and state components with explicit data locations.
4. [Automate checks in CI](lessons/04.md) — Run a failing and passing change in a learner-owned CI project or equivalent local pipeline rehearsal.
5. [Promote and roll back](lessons/05.md) — Promote one tested artifact and recover a seeded stateless regression.
6. [Declare infrastructure](lessons/06.md) — Provision owned local VM resources with a reviewed provider and inspect its state.
7. [Configure a fleet](lessons/07.md) — Configure two owned guests and run the same playbook again.
8. [Recreate and recover the delivery path](lessons/08.md) — Rebuild a clean target and deploy the same release using the recorded procedure.

Each level has a worked operation, a distinct portable transfer fixture, an independent native application, named failure controls and recovery/cleanup. Optional recall tasks invite a later return. Estimated active time per level is 90 minutes worked practice plus 120 minutes independent work, excluding setup/downloads; split sessions as needed. Estimates are author judgments, not measured learner times.

## What completion means

Operational milestones use manual review of real observations. Portable configuration feedback checks only the stated data contract; it does not create VMs, measure physical hardware, verify learner identity, or establish public reachability. Required native operations remain incomplete until performed. Recipes are unreviewed drafts; tool-version and provider/hardware variants require native replay before a tested label.

The portable cases intentionally expose their rubric and reference; they teach diagnosis and planning. Setting a Boolean to true does not demonstrate that the event happened. Retain real observations for native milestones and record any help used. A local reference, checked fixture, manual completion, public observation and physical-device test must not be presented as interchangeable evidence.

For job preparation, retain a reproducible handover with source/config identities and a recovery demonstration. For curiosity, extend the same controls to another guest, device or owned route. Neither intention changes what the task actually proves.

This material keeps the shared server's two hosted lab slots unchanged. Use the learner PC for guests/builds/load generation; bootstrap.md covers the small-server, 16 GB PC and optional physical-device routes.

The supplied Relay is a synthetic-data teaching service, not a production internet application. Provider/native recipes have not been replayed on every host or account. Source is ai-draft and reviewed=false; record tool versions and untested boundaries.
