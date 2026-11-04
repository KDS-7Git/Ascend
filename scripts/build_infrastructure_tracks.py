"""Render authored infrastructure lessons into installable packs and lab files.

Run from the repository with its Python environment. --check never writes files.
Native VM, networking, provider and hardware operations are teaching recipes;
generation only validates the pack schema and creates text/material inputs.
"""

import argparse
import json
from pathlib import Path, PurePosixPath

from ascend.engine.packs import dump_toml, parse_pack

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "docs/curriculum/infrastructure-paths.json"
MATERIALS = "tracks/infrastructure-tracks/materials"
RUNTIME = f"{MATERIALS}/shared/lab.py"


def workspace(track, number=None):
    note = f"{number:02d}" if number else "entry"
    return (
        f"Download /training/{track['id']}.zip and extract it into a NEW folder you choose on your PC. "
        f"Open a terminal in its {track['id']} directory; read README.md and bootstrap.md. "
        "Python 3.11+ runs the portable tools without extra Python packages. POSIX examples use Linux; "
        "Windows users can use a prepared Linux guest or WSL for the initial shell practice. "
        "Create work/ and notes/. Copy notes-template.md in your editor to "
        f"notes/{note}.md, or append a dated attempt if the note already exists. "
        "Input files are in inputs/NN/, portable starting cases in cases/, operational instructions in lessons/NN.md, "
        "and the shared synthetic service in shared/. All generated work remains in the local paths printed by the tools. "
        "Opening a challenge does not create or upload these files. Use Ascend's notebook/upload control only when "
        "you choose to copy evidence into Ascend. Run commands one at a time on the named HOST, GUEST or CLIENT. "
        "Replace explicit address/key placeholders after inspection, and keep each foreground service in its own terminal. "
        "Stop its process with Ctrl+C before reusing the same listener."
    )


def completion(level):
    return (
        level["lesson"]["native_control"]
        + " Retain your prediction, commands, positive and negative results, recovery and help used in your local note. "
        "Complete a required native operation in the stated environment before marking it done. "
        "Manual completion records your assessment; a saved file or passing portable case is not automatic verified skill."
    )


def common(track, level, number):
    return {
        "level": level["id"],
        "preview": level["guided_lab"],
        "requirements": level["lesson"]["requirements"],
        "setup": workspace(track, number),
        "resource": level["lesson"]["resource"],
        "resource_label": "Free technical reference",
        "resource_note": "The bundled lesson defines the practical task. This optional official/open reference explains its mechanism; no paid course is needed.",
        "materials": [
            {
                "label": "Download this track's practical lab files",
                "url": f"/training/{track['id']}.zip",
            }
        ],
        "verify": {"type": "manual"},
        "auto_complete": False,
    }


def case_steps(number, variant):
    destination = f"work/{number:02d}-{variant}"
    return (
        "First predict the failed control from the assignment. This short portable exercise checks a configuration model, "
        "not a running machine. Create a fresh workspace (the tool refuses to overwrite an existing one):\n"
        f"```sh\npython3 lab.py prepare {number:02d} --variant {variant} --out {destination}\n"
        f"python3 lab.py check {destination}\n```\n"
        "The initial check intentionally fails. Read assignment.json, edit candidate.json, then repeat the same check. "
        f"Your files stay in {destination}. If repeating the exercise, choose a new --out directory. "
        "A green result checks only this data contract. The native operation and its finish line below remain required."
    )


def contract_lines(lesson):
    result = []
    for rule in lesson["rules"]:
        fields = ", ".join(rule.get("fields", [rule["field"]]))
        result.append(
            f"- `{fields}`: {rule['op']} `{json.dumps(rule.get('value'), ensure_ascii=False)}` — {rule['why']}."
        )
    return result


def lesson_markdown(track, level, number):
    lesson = level["lesson"]
    lines = [
        f"# {number:02d}. {level['title']}",
        "",
        level["guided_lab"],
        "",
        f"Author estimate: {level['practice_minutes']} minutes guided practice and {level['milestone_minutes']} minutes independent work; split into sessions as needed. The portable preparation alone is usually 5–15 minutes. Setup, downloads and provider approval are separate.",
        "",
        "## Before starting",
        "",
        lesson["requirements"],
        "",
        workspace(track, number),
        "",
        "Use only the named learner-owned environment. Commands that install packages or change services, networks, storage or VMs belong on that specified guest/host. A college-provided guest account is not permission to administer the physical host.",
        "",
        "## How it works",
        "",
        level["concepts"],
        "",
        lesson["explanation"],
        "",
        "## Portable diagnosis",
        "",
        case_steps(number, "guided"),
        "",
        "This case has the following declared contract. Predict how each requirement affects the actual system before editing its model:",
        "",
        *contract_lines(lesson),
        "",
        "Rules are data-only comparisons. `eq` means equal value and JSON type; `near` allows the stated rounding tolerance; `min`/`max` set bounds; `sum_max` constrains the combined allocation. This checker does not inspect whether an asserted observation actually occurred.",
        "",
        "If you need help, create a separate reference workspace. Treat this as help used, not an independent pass:",
        "",
        f"```sh\npython3 lab.py reference {number:02d} --out work/{number:02d}-reference\n```",
        "",
        "## Perform the operation",
        "",
        "Predict the outcome, then run one block at a time on the named machine. A foreground server keeps running until you stop it; open the specified second terminal for its client checks. Shell comments describing a different terminal are instructions, not already executed commands.",
        "",
    ]
    for index, command in enumerate(lesson["native_commands"], 1):
        lines.extend([f"### Operation {index}", "", f"```sh\n{command}\n```", ""])
    lines.extend(
        [
            "## Independent application",
            "",
            "If you already know this level, start here and use the worked operation only when a gap appears. This is a real demonstration; prior experience does not auto-complete it.",
            "",
            level["independent_failure_or_transfer"],
            "",
            case_steps(number, "transfer"),
            "",
            "Carry the changed condition into the specified owned environment, perform the repair, and repeat the positive and negative controls. If a provider or physical device is unavailable, retain the portable work as preparation and leave that native outcome incomplete.",
            "",
            "## Finish line",
            "",
            completion(level),
            "",
            "## Recovery and cleanup",
            "",
            lesson["cleanup"],
            "",
            "## Return later",
            "",
            "After a suggested 2–7 days, reconstruct the mechanism and one failure from memory. Compare it with retained evidence or a fresh owned experiment and write down the correction. Spacing is optional; Ascend does not verify elapsed days.",
            "",
            f"[Free technical reference]({lesson['resource']})",
            "",
            "Content status: ai-draft, unreviewed. Local tool/fixture checks do not imply native VM, provider, physical-device or public-mail replay.",
            "",
        ]
    )
    return "\n".join(lines)


def bootstrap(track):
    return f"""# Environment bootstrap

{track["environment"]}

Start with your own PC, Python 3.11+, an editor and a few hundred MiB of free space. The portable exercises, Relay service and local HTTP checks need no account, domain, paid service or Raspberry Pi. The ZIP is a set of readable files: nothing launches merely because it is downloaded. Keep work/ and notes/ in the extracted directory so outputs are easy to find.

```sh
python3 --version
mkdir -p work notes
python3 shared/selfcheck.py
```

The selfcheck uses temporary loopback endpoints and synthetic data, then cleans its own resources. It checks the supplied teaching tools, not your knowledge. Stop the persistent practice service before another exercise reuses its port.

## A Linux environment before full VM administration

An existing owned Linux PC or an assigned Linux guest is sufficient to start. Record its hostname, OS and account rights. Use the assigned guest console/SSH instructions; guest sudo does not grant rights to the host hypervisor. Linux networking and systemd lessons require a disposable guest/host with the named tools, not just an online code editor.

For a new learner PC, an optional bootstrap is [Multipass](https://documentation.ubuntu.com/multipass/latest/how-to-guides/install-multipass/), after installing the supported host application from its official instructions and checking virtualization support. On your PC, this creates only a specifically named starter guest:

```sh
multipass version
multipass launch 24.04 --name ascend-linux --cpus 1 --memory 1G --disk 12G
multipass info ascend-linux
multipass shell ascend-linux
```

Inside the guest run `hostname`, `cat /etc/os-release` and `id`. Transfer this extracted folder using the documented Multipass transfer/mount workflow, then open a guest terminal in it. The VM track teaches the underlying host, guest, image, network and administration mechanics explicitly. An Ubuntu/WSL shell is another route for early shell practice; it does not substitute for demonstrating a separate VM kernel/control plane. If the host cannot expose virtualization, use an eligible existing guest or another host and record the limitation.

At teardown preserve evidence and stop only `ascend-linux`. Remove it only when no longer needed; avoid a global purge that might remove unrelated deleted guests. Never format physical storage or change your main network while following a guest recipe.

## Resource choices

- Learner PC baseline: 16 GB RAM and about 200 GB free SSD. Begin with one 1–2 GiB guest, then run multi-guest exercises sequentially with a starting total lab allowance near 8 GiB. Inspect actual CPU topology, free RAM, image growth and host reserve. A sparse disk's declared capacity is not current storage use.
- Ascend server baseline: approximately 4 cores, 4–8 GB RAM and 100–120 GB microSD storage. These downloads do not run guests, Docker builds or load generators on it. Its separately authorized hosted-runner limit remains two simultaneous labs.
- Hardware route: a Raspberry Pi, spare laptop, mini-PC or eligible VPS can be a later owned target. Check architecture, firmware/virtualization support, power, cooling, storage and tool compatibility. Build/load-test on the PC and deploy measured artifacts to the smaller machine. The VM/software route remains available without buying a device.
- Advanced route: run additional physical hosts or larger guests when available. Keep the same backup, identity, workload and recovery evidence. Multiple guests on one PC share its power, disk and network failures; they do not prove physical high availability.
- Public DNS, mail, free hosting, tunnels and provider accounts have current eligibility/usage conditions. Start with the local variant, inspect the provider's current official terms, and initiate public actions only in your own chosen account. Public access needs an actual external client observation. Mail capture is not internet delivery.

## Machine and file boundaries

HOST means the machine administering guest definitions/disks. GUEST means the particular disposable Linux instance. CLIENT means the machine issuing a request; its 127.0.0.1 is its own loopback. EDGE means the intended reverse proxy. An address inside a sample file is a placeholder until verified against your actual environment. Keep tokens, private keys, real messages, cloud state and private inventories out of public reports.

Read `shared/README.md` for the synthetic service and portable helper interfaces. Native tools such as Caddy, QEMU/libvirt, Incus, WireGuard, Postfix, Dovecot, OpenTofu, Ansible, Docker and k6 are separate installations named by their lessons. Their recipes are authored drafts; record versions and keep untested variants explicit.
"""


def track_readme(track):
    lines = [
        f"# {track['title']}",
        "",
        track["description"],
        "",
        f"Recommended sequence position: {track['order']} of 9 in Infrastructure & Internet Operations.",
        "",
        "## Choose your starting point",
        "",
        track["entry"],
        "",
        track["background"],
        "",
        "The nine tracks progress through Linux/networking, VMs, public hosting, private access, delivery automation, mail/state, traffic/capacity, resilient hardware and private cloud administration. The order recommends background; earlier whole tracks are not hard prerequisites. The default main-level gates use the prior milestone. Existing early-unlock lets a practitioner attempt a later independent milestone without doing every worked example.",
        "",
        "## Start here",
        "",
        workspace(track),
        "",
        "Read bootstrap.md, then check the local tools:",
        "",
        "```sh\npython3 --version\nmkdir -p work notes\npython3 shared/selfcheck.py\n```",
        "",
        "For the first persistent service, open Terminal A in this extracted folder:",
        "",
        "```sh\npython3 shared/relay.py --host 127.0.0.1 --port 8000 --data data/relay.sqlite --release v1\n```",
        "",
        "Terminal B, same machine and folder:",
        "",
        "```sh\npython3 shared/check_service.py --url http://127.0.0.1:8000 --expect-release v1 --write\n```",
        "",
        "Stop Terminal A with Ctrl+C before a lesson starts another listener on that port. The SQLite data remains at data/relay.sqlite. A teaching selfcheck and an actual learner operation are different results.",
        "",
        "## Practical sequence",
        "",
    ]
    for number, level in enumerate(track["levels"], 1):
        lines.append(
            f"{number}. [{level['title']}](lessons/{number:02d}.md) — {level['guided_lab']}"
        )
    lines.extend(
        [
            "",
            "Each level has a worked operation, a distinct portable transfer fixture, an independent native application, named failure controls and recovery/cleanup. Optional recall tasks invite a later return. Estimated active time per level is 90 minutes worked practice plus 120 minutes independent work, excluding setup/downloads; split sessions as needed. Estimates are author judgments, not measured learner times.",
            "",
            "## What completion means",
            "",
            track["limits"],
            "",
            "The portable cases intentionally expose their rubric and reference; they teach diagnosis and planning. Setting a Boolean to true does not demonstrate that the event happened. Retain real observations for native milestones and record any help used. A local reference, checked fixture, manual completion, public observation and physical-device test must not be presented as interchangeable evidence.",
            "",
            "For job preparation, retain a reproducible handover with source/config identities and a recovery demonstration. For curiosity, extend the same controls to another guest, device or owned route. Neither intention changes what the task actually proves.",
            "",
            "This material keeps the shared server's two hosted lab slots unchanged. Use the learner PC for guests/builds/load generation; bootstrap.md covers the small-server, 16 GB PC and optional physical-device routes.",
            "",
            "The supplied Relay is a synthetic-data teaching service, not a production internet application. Provider/native recipes have not been replayed on every host or account. Source is ai-draft and reviewed=false; record tool versions and untested boundaries.",
            "",
        ]
    )
    return "\n".join(lines)


def outputs():
    source = json.loads((ROOT / SOURCE).read_text())
    files, catalog = {}, []
    runtime = (ROOT / RUNTIME).read_text()
    if len(source["tracks"]) != 9:
        raise ValueError(
            "The authored infrastructure sequence must contain nine tracks"
        )
    for track in source["tracks"]:
        levels = track["levels"]
        if len(levels) != 8:
            raise ValueError(f"Expected eight levels: {track['id']}")
        pack = {
            "pack": {
                "id": track["id"],
                "title": track["title"],
                "kind": "proficiency",
                "version": 1,
                "source": "ai-draft",
                "reviewed": False,
            },
            "level": [
                {"id": level["id"], "title": level["title"], "lane": "main"}
                for level in levels
            ]
            + [
                {"id": "entry", "title": "Choose your entry point", "lane": "side"},
                {"id": "recall", "title": "Return later", "lane": "side"},
            ],
            "node": [],
        }
        entry = common(track, levels[0], 1)
        entry.update(
            {
                "id": "entry-demonstration",
                "level": "entry",
                "title": "Choose an entry point through a short demonstration",
                "size": "S",
                "minutes": 20,
                "needs": [],
                "requirements": "Python 3.11+, a text editor and your own PC. No account or device purchase is required for this entry check.",
                "preview": "Match a concrete practical outcome to what you can already demonstrate.",
                "brief": track["entry"],
                "setup": workspace(track),
                "steps": [
                    "Read bootstrap.md, record your machine/OS and confirm the tools work.\n```sh\npython3 shared/selfcheck.py\n```\nThis checks the teaching tools, not proficiency.",
                    "Read the eight independent finish lines in README.md and lessons/NN.md. Choose the first operation you cannot demonstrate on a fresh target without the worked steps.",
                    "Begin that independent milestone if you already have the background, using existing early-unlock when needed. Otherwise start level 1 worked practice. Your own demonstration remains required; an entry choice does not complete other nodes.",
                    "Record the chosen level, supporting prior observation and next concrete action in notes/entry.md. Return to guided material whenever a gap appears.",
                ],
                "done_when": "Your local tool checks run, a practical observation supports the chosen starting level, and notes/entry.md names the next operation. This is manual self-assessment and does not certify or complete other levels.",
            }
        )
        pack["node"].append(entry)
        base = f"{MATERIALS}/{track['id']}"
        for number, level in enumerate(levels, 1):
            lesson, lid = level["lesson"], level["id"]
            practice = common(track, level, number)
            practice.update(
                {
                    "id": lid + "-practice",
                    "title": "Operate: " + level["title"],
                    "size": "M",
                    "minutes": level["practice_minutes"],
                    "needs": [],
                    "brief": lesson["explanation"],
                    "steps": [
                        case_steps(number, "guided"),
                        "Read the mechanism and environment boundaries in lessons/"
                        + f"{number:02d}.md. Predict a successful response and a failure before running the following native operations.",
                    ]
                    + [
                        f"```sh\n{command}\n```"
                        for command in lesson["native_commands"]
                    ]
                    + [
                        "Observe these controls and retain actual output: "
                        + lesson["native_control"],
                        "Recover and clean up only the named resources: "
                        + lesson["cleanup"],
                    ],
                    "hints": [
                        "Check which machine owns the listener, address, file and identity. The same loopback address names a different endpoint on each machine.",
                        f"For the portable model only, create a separate help workspace: python3 lab.py reference {number:02d} --out work/{number:02d}-reference. Record that help was used.",
                    ],
                    "done_when": completion(level),
                    "checkpoints": [
                        {
                            "id": "diagnosis",
                            "title": "Explain the failed control",
                            "minutes": 15,
                            "done_when": "A prediction and the portable check identify the failing control and state what real observation is still needed.",
                            "next_step": "Run the named native operation on the owned machine and collect its actual success/failure controls.",
                        },
                        {
                            "id": "observation",
                            "title": "Retain the native observation",
                            "minutes": 30,
                            "done_when": "The intended native positive and negative observations are retained with their environment and file paths.",
                            "next_step": "Recover the changed condition, check retained state/access, and complete the named cleanup.",
                        },
                    ],
                }
            )
            milestone = common(track, level, number)
            milestone.update(
                {
                    "id": lid + "-milestone",
                    "title": "Apply independently: " + level["title"],
                    "size": "M",
                    "minutes": level["milestone_minutes"],
                    "milestone": True,
                    "needs": [],
                    "preview": level["independent_failure_or_transfer"],
                    "brief": "Demonstrate the mechanism under a changed condition. "
                    + level["concepts"],
                    "steps": [
                        "Choose the native environment in lessons/"
                        + f"{number:02d}.md. Prior experience may replace the worked operation; it does not replace the following evidence.",
                        case_steps(number, "transfer"),
                        "Perform this change on the specified owned target: "
                        + level["independent_failure_or_transfer"],
                        "Collect the actual controls: " + lesson["native_control"],
                        "Retain your commands, changed input, cause, recovery and help used in "
                        + f"notes/{number:02d}.md. "
                        + lesson["cleanup"],
                    ],
                    "hints": [
                        "Compare one changed condition with a known working control; use the guided operation only when needed and record that help."
                    ],
                    "done_when": completion(level),
                }
            )
            recall = common(track, level, number)
            recall.update(
                {
                    "id": "recall-" + lid,
                    "level": "recall",
                    "title": "Return later: " + level["title"],
                    "size": "S",
                    "minutes": 15,
                    "needs": [lid + "-milestone"],
                    "requirements": "Your retained local notes; original tools only if you choose a fresh observation.",
                    "preview": "Reconstruct this operation and one failure after a break.",
                    "brief": "A suggested 2–7 day return is optional; the application does not verify how long you waited.",
                    "steps": [
                        "Explain from memory: " + level["concepts"],
                        "Predict a changed-condition result: "
                        + level["independent_failure_or_transfer"],
                        "Compare with retained or fresh observations and record one correction plus the experiment that would test it.",
                    ],
                    "done_when": "Your note reconstructs the mechanism and a concrete failure/recovery path, compares it with evidence and records a correction. This recall does not certify an unperformed native operation.",
                }
            )
            pack["node"].extend([practice, milestone, recall])
            files[f"{base}/lessons/{number:02d}.md"] = lesson_markdown(
                track, level, number
            )
            input_names = []
            for name, content in lesson["files"].items():
                if (
                    PurePosixPath(name).is_absolute()
                    or ".." in PurePosixPath(name).parts
                ):
                    raise ValueError("Input path must stay inside its level: " + name)
                input_names.append(name)
                files[f"{base}/inputs/{number:02d}/{name}"] = content
            files[f"{base}/inputs/{number:02d}/README.md"] = (
                f"# Inputs for {level['title']}\n\n"
                + (
                    "\n".join(f"- {name}" for name in input_names)
                    if input_names
                    else "This operation uses the shared Relay/tools and commands in the lesson; no extra native input is required."
                )
                + f"\n\nRead ../../lessons/{number:02d}.md for the target machine, placeholders, controls and cleanup.\n"
            )
            for variant, field in [
                ("guided", "guided_start"),
                ("transfer", "transfer_start"),
            ]:
                case = {
                    "scope": lesson["scope"],
                    "brief": level["guided_lab"]
                    if variant == "guided"
                    else level["independent_failure_or_transfer"],
                    "contract": lesson["rules"],
                    "starting": lesson[field],
                    "reference": lesson["reference_config"],
                    "rules": lesson["rules"],
                }
                files[f"{base}/cases/{number:02d}-{variant}.json"] = (
                    json.dumps(case, indent=2, ensure_ascii=False) + "\n"
                )
        content = (
            "# Generated from "
            + SOURCE
            + "; unreviewed draft teaching content.\n"
            + dump_toml(pack)
        )
        parsed = parse_pack(content)
        files[f"packs/community/infrastructure/{track['id']}.toml"] = content
        files[f"{base}/README.md"] = track_readme(track)
        files[f"{base}/bootstrap.md"] = bootstrap(track)
        files[f"{base}/lab.py"] = runtime
        files[f"{base}/notes-template.md"] = (
            "# Practical evidence\n\n- Date and level:\n- Machine roles, OS/tool versions and permitted scope:\n- Prediction and mechanism:\n- Commands and explicit local save paths:\n- Actual successful control:\n- Changed input and failed control:\n- Cause, repair and retained state/access:\n- Recovery and selective cleanup:\n- Help used:\n- Untested native/provider/physical outcomes:\n- Next concrete operation:\n"
        )
        files[f"{base}/gitignore.example"] = (
            "work/\ndata/\nnotes/\nbackups/\n*.key\n*.pem\n*.sqlite*\n*.tfstate*\n*.plan\n.terraform/\n"
        )
        catalog.append(
            {
                "id": track["id"],
                "title": track["title"],
                "domain": "infrastructure",
                "category": "Infrastructure",
                "track_order": track["order"],
                "recommended_after": track["recommended_after"],
                "description": track["description"],
                "entry": track["entry"],
                "background": [track["background"]],
                "limits": track["limits"],
                "aliases": track["aliases"],
                "labs": [],
                "main_levels": len(levels),
                "nodes": len(parsed.nodes),
                "verification": "Manual operational review. Portable cases validate an editable configuration contract only; native VM/provider/device/public outcomes require actual observations.",
            }
        )
    files["packs/community/infrastructure/catalog.json"] = (
        json.dumps({"version": 1, "tracks": catalog}, indent=2) + "\n"
    )
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated = outputs()
    stale = []
    for relative, content in generated.items():
        path = ROOT / relative
        if args.check:
            if not path.is_file() or path.read_text() != content:
                stale.append(relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if stale:
        raise SystemExit("Generated content is stale:\n" + "\n".join(stale))
    print(
        f"Infrastructure: nine packs, 72 lessons and 144 portable cases are consistent ({len(generated)} generated files)."
    )


if __name__ == "__main__":
    main()
