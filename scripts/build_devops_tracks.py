"""Render the sequential DevOps curriculum into packs and standalone lab guides."""

import argparse
import json
from pathlib import Path

from ascend.engine.packs import dump_toml, parse_pack

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "docs/curriculum/devops-paths.json"
MATERIALS = "tracks/devops-tracks/materials"


def workspace(track, level=None):
    note = (level["id"] if level else "entry") + ".md"
    return (
        f"Download /training/{track['id']}.zip and extract it into a new folder you choose on your own PC. "
        f"Open a terminal in the extracted {track['id']} folder; commands use that folder unless a step explicitly changes it. "
        "Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. "
        "Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. "
        "Keep foreground services in separate terminals and stop earlier listeners before reusing a port. "
        f"Create notes/{note} from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. "
        "If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. "
        "These files stay on your computer; opening a challenge does not create or upload them. "
        "Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend."
    )


def completion(level):
    return (
        level["evidence"]
        + " Review the observations and explanation in your local notes before marking done. "
        "A required live operation remains incomplete until you perform it in the stated environment. "
        "Manual completion records your assessment; local tool output or a saved file does not automatically verify skill."
    )


def common(track, level):
    return {
        "level": level["id"],
        "resource": level["resource"],
        "resource_label": "Free technical reference",
        "resource_note": "The bundled lesson defines the practical task. This optional official reference explains the underlying tool or mechanism; a paid course is not required.",
        "preview": level["preview"],
        "requirements": level["requirements"],
        "setup": workspace(track, level),
        "materials": [
            {
                "label": "Download this track's runnable lab files",
                "url": f"/training/{track['id']}.zip",
            }
        ],
        "verify": {"type": "manual"},
        "auto_complete": False,
    }


def duration(minutes):
    return "S" if minutes <= 30 else "M" if minutes <= 120 else "L"


def lesson_markdown(track, level):
    lines = [
        f"# {level['title']}",
        "",
        level["preview"],
        "",
        f"Guided practice: about {level['practice_minutes']} minutes. Independent application: about {level['milestone_minutes']} minutes, split over sessions when needed.",
        "",
        "## Before you start",
        "",
        level["requirements"],
        "",
        workspace(track, level),
        "",
        "## How it works",
        "",
        level["concepts"],
        "",
        "## Guided practice",
        "",
    ]
    for index, step in enumerate(level["steps"], 1):
        lines.extend([f"### Step {index}", "", step, ""])
    lines.extend(
        [
            "## Independent application",
            "",
            "Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.",
            "",
        ]
    )
    for index, step in enumerate(level["independent"], 1):
        lines.extend([f"{index}. {step}", ""])
    lines.extend(
        [
            "## Finish line",
            "",
            completion(level),
            "",
            "## Return later",
            "",
            "After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.",
            "",
            f"[Free technical reference]({level['resource']})",
            "",
        ]
    )
    return "\n".join(lines)


def track_readme(track):
    lines = [
        f"# {track['title']}",
        "",
        track["description"],
        "",
        "## Choose your starting point",
        "",
        track["entry"],
        "",
        track["background"],
        "",
        "The three tracks form a recommended sequence: Service Foundations → Delivery Automation → Reliability and Orchestration. Prior experience can satisfy the background. Earlier whole tracks are not locked prerequisites. Inside Ascend, use an independent application first when you know a level; use the existing early-unlock action for a later level. A successful local selfcheck checks the supplied tools, not your proficiency.",
        "",
        "## Your workspace and first real check",
        "",
        workspace(track),
        "",
        "Run these from the extracted folder:",
        "",
        "```sh\npython3 --version\npython3 shared/selfcheck.py\n```",
        "",
        "The checks use temporary loopback services and temporary data. They report both success and intentional failure controls. They do not start a persistent server, provision VMs, change system configuration, or contact a cloud account.",
        "",
        "For a persistent exercise, start Relay in Terminal A:",
        "",
        "```sh\npython3 shared/relay.py --host 127.0.0.1 --port 8000 --data work/relay.sqlite --release v1\n```",
        "",
        "In Terminal B, create and verify one synthetic update:",
        "",
        "```sh\npython3 shared/check_service.py --url http://127.0.0.1:8000 --expect-release v1 --write\n```",
        "",
        "Stop that foreground service with Ctrl+C before a lesson starts another service on port 8000. Use a fresh output path for repeated backup, artifact and load experiments; the helpers preserve existing outputs instead of silently overwriting evidence.",
        "",
        "## Practical sequence",
        "",
        "Each level has guided practice and an independent changed-condition application. Return-later tasks are optional. The finish line names the actual behaviour to demonstrate.",
        "",
    ]
    for number, level in enumerate(track["levels"], 1):
        lines.append(
            f"{number}. [{level['title']}](lessons/{level['id']}.md) — {level['preview']}"
        )
    lines.extend(
        [
            "",
            "## Choose the environment that fits",
            "",
            "- Core Python practice runs on the learner PC without Docker, hardware purchases or a paid cloud account. Keep a few hundred MiB free for small lab data; measure actual use before adding tools.",
            "- Linux/systemd/SSH/Ansible practice uses an owned disposable Linux VM or spare PC. Begin with one guest and preserve host memory/disk reserve. The Infrastructure VM tracks cover guest creation and host administration.",
            "- Container practice needs a learner-owned Docker environment and room for images. A single Relay container is capped in the example configuration; this does not include Docker/VM overhead.",
            "- The local kind Kubernetes variant needs its own roughly 4–6 GiB planning allowance. Stop unused labs and inspect actual usage. A 16 GB PC can run this sequential exercise with reserve; do not pile every VM, monitor and cluster together.",
            "- A Pi or spare always-on host is an optional deployment target, with a Linux VM route available for the same software concepts. Physical power, cooling, flash wear and independent-host failures need actual hardware observations.",
            "- Real hosted CI, registry publication and provider identity variants require the learner's chosen accounts and current free allowance. Local rehearsal does not count as an external run. Choose free local routes first; no paid resource is provisioned by these files.",
            "",
            "Ascend's two hosted lab slots are a separate service budget. These engineering bundles execute on the learner's PC or explicitly chosen guest; they do not consume hosted slots or enlarge the server's 4-core, 4–8 GB, microSD-based envelope.",
            "",
            "## Evidence and limits",
            "",
            track["limits"],
            "",
            "All operational tasks use manual review. Retain the intended success, the changed failure, recovery, environment identity, help used and untested assumptions. A local report is an observation, not a signed server grade. Do not mark an unavailable required VM/CI/cluster operation complete as a reading exercise.",
            "",
            "The included Relay is a readable synthetic-data teaching service. Use a suitable production server, authentication, edge and state architecture for a real application. Run the operating-system and cleanup recipes only against the particular learner-owned guest/project named in your notes.",
            "",
            "Read [shared/README.md](shared/README.md) for tool interfaces. Keep credentials, databases and private inventories out of Git; review gitignore.example before the first commit.",
            "",
        ]
    )
    return "\n".join(lines)


def outputs():
    source = json.loads((ROOT / SOURCE).read_text())
    files, catalog = {}, []
    for track in source["tracks"]:
        levels = track["levels"]
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
        entry = common(track, levels[0])
        entry.update(
            {
                "id": "entry-demonstration",
                "level": "entry",
                "title": "Choose an entry point through a short demonstration",
                "size": "S",
                "minutes": 20,
                "needs": [],
                "preview": "Match the track's practical outcomes to what you can already demonstrate.",
                "requirements": "Python 3.11+ and a text editor on your own PC; no account required.",
                "brief": track["entry"],
                "setup": workspace(track),
                "steps": [
                    "Run the bundled checks to confirm your Python environment and the local reference tools work. These checks inspect the teaching code, not your knowledge.\n```sh\npython3 shared/selfcheck.py\n```",
                    "Read the eight independent applications in README.md and the linked lessons. Choose the first one you cannot yet demonstrate from a fresh target without its worked instructions.",
                    "If you already have the background, open the independent application for that level. Existing level early-unlock is available; it records your choice, not an automatic pass. Otherwise start the guided practice in level 1.",
                    "Write the chosen starting level, the observation supporting that choice and the next concrete operation in notes/entry.md. Use the guided lesson whenever a gap appears.",
                ],
                "done_when": "Your local tools run, you name a starting level based on demonstrated prior work, and your notes identify one concrete next operation. This self-assessment neither grades nor completes other levels.",
            }
        )
        pack["node"].append(entry)
        for level in levels:
            lid = level["id"]
            practice = common(track, level)
            practice.update(
                {
                    "id": lid + "-practice",
                    "title": "Practice: " + level["title"],
                    "size": duration(level["practice_minutes"]),
                    "minutes": level["practice_minutes"],
                    "needs": [],
                    "brief": level["concepts"],
                    "steps": level["steps"]
                    + [
                        "Compare the observed result with your prediction and retain the commands/output in notes/"
                        + lid
                        + ".md. "
                        + level["evidence"]
                    ],
                    "hints": [
                        "Use the actual listener, release identity and state path printed by your process; a healthy service at another address may be the wrong deployment.",
                        "If a required environment is unavailable, keep preparation as partial progress and return for the live operation.",
                    ],
                    "done_when": completion(level),
                }
            )
            milestone = common(track, level)
            milestone.update(
                {
                    "id": lid + "-milestone",
                    "title": "Apply independently: " + level["title"],
                    "size": duration(level["milestone_minutes"]),
                    "minutes": level["milestone_minutes"],
                    "milestone": True,
                    "needs": [],
                    "brief": "Apply the mechanism to a changed condition and recover the intended behaviour. "
                    + level["concepts"],
                    "steps": [
                        "Use the named environment and files in lessons/"
                        + lid
                        + ".md. Predict the changed result before opening the guided solution. Prior experience can replace guided practice; the demonstration below remains required."
                    ]
                    + level["independent"]
                    + [
                        "Retain the failing case, successful control, recovery, explanation and any help used in notes/"
                        + lid
                        + ".md. "
                        + level["evidence"]
                    ],
                    "hints": [
                        "Compare one changed condition against the earlier successful control. Recover that control before trying another change."
                    ],
                    "done_when": completion(level),
                }
            )
            recall = common(track, level)
            recall.update(
                {
                    "id": "recall-" + lid,
                    "level": "recall",
                    "title": "Return later: " + level["title"],
                    "size": "S",
                    "minutes": 15,
                    "needs": [lid + "-milestone"],
                    "preview": "Reconstruct a previous operational decision and check what you remember.",
                    "requirements": "Your retained local notes; the original tools only if you choose a fresh observation.",
                    "brief": "After a suggested 2–7 days, reconstruct the mechanism without your walkthrough. Spacing is optional and is not automatically verified.",
                    "steps": [
                        "From memory, explain the mechanism: " + level["concepts"],
                        "Predict one changed-condition result from this lesson: "
                        + level["independent"][0],
                        "Compare your reasoning with a fresh observation or your retained evidence. Record the specific correction and the next experiment you would use to test it.",
                    ],
                    "done_when": "You reconstruct a concrete failure/recovery path, compare it with retained or fresh evidence, and correct the explanation in your notes. This manual recall task does not certify an unperformed live operation.",
                }
            )
            pack["node"].extend([practice, milestone, recall])
            files[f"{MATERIALS}/{track['id']}/lessons/{lid}.md"] = lesson_markdown(
                track, level
            )
        content = (
            "# Generated from "
            + SOURCE
            + "; unreviewed draft teaching content.\n"
            + dump_toml(pack)
        )
        parsed = parse_pack(content)
        files[f"packs/community/devops/{track['id']}.toml"] = content
        files[f"{MATERIALS}/{track['id']}/README.md"] = track_readme(track)
        catalog.append(
            {
                "id": track["id"],
                "title": track["title"],
                "domain": "devops",
                "category": "DevOps",
                "track_order": track["order"],
                "recommended_after": track["recommended_after"],
                "description": track["description"],
                "entry": track["entry"],
                "background": [track["background"]],
                "limits": track["limits"],
                "aliases": track["aliases"],
                "labs": [],
                "capabilities": sorted(
                    {
                        capability
                        for level in levels
                        for capability in level["capabilities"]
                    }
                ),
                "main_levels": len(levels),
                "nodes": len(parsed.nodes),
                "verification": "Manual operational review; runnable local controls for service, state, release and failure/recovery. Local reports are not automatic verified skill results.",
            }
        )
    files["packs/community/devops/catalog.json"] = (
        json.dumps({"version": 1, "tracks": catalog}, indent=2) + "\n"
    )
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for relative, content in outputs().items():
        path = ROOT / relative
        if args.check:
            if not path.is_file() or path.read_text() != content:
                raise SystemExit("Generated content is stale: " + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print("DevOps packs, catalog and lab guides are consistent.")


if __name__ == "__main__":
    main()
