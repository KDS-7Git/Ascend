"""Render reviewed authoring data into draft packs, cases and catalog metadata."""

import argparse
import json
from pathlib import Path

from ascend.engine.packs import dump_toml, parse_pack

ROOT = Path(__file__).resolve().parents[1]


def evidence_step(path):
    return (
        "Save your own observations from the extracted lab folder. The included report.py asks for scope, setup, prediction, exact actions, actual results, a comparison, explanation, limitations and help used. It does not supply answers or overwrite an existing report.\n"
        f'```sh\npython3 report.py "{path}"\n```\n'
        "On Windows use py -3 instead of python3. Review the saved JSON in a text editor. Ascend checks files on the SERVER computer: for a hosted/container deployment, place your report at the server’s configured lab path. A file saved only on your laptop is not visible to that checker. Use Challenge options → Check evidence, then Log progress → Mark as done only after reviewing the finish line. File presence does not grade reasoning or earn automatic skill XP."
    )


def apply_lab_guide(pack, track, guide):
    levels = {level["id"]: level for level in track["levels"]}
    material = {
        "label": "Download this track’s lab files (ZIP)",
        "url": "/training/" + track["id"] + ".zip",
    }
    for node in pack["node"]:
        node.update(
            resource=guide["resource"],
            resource_label="Free reference (optional)",
            resource_note="The challenge and its named lab files define the task. This reference explains the topic; buying or completing a course is not required.",
        )
        if node["verify"]["type"] == "lab":
            node["preview"] = (
                "Check the integrity of a small evidence sample by calculating its content hash."
                if node["verify"].get("exercise") == "integrity"
                else "Apply your understanding to a short scenario and choose the best response."
            )
            node["requirements"] = "A browser. No external tools or account are needed."
            node["setup"] = (
                "This is an in-browser decision or micro-exercise. Its inputs appear when you start; no course, VM or external lab setup is required for this check."
            )
            if node["id"] == "lab-readiness":
                node["resource"] = "https://docs.python.org/3/library/hashlib.html"
            if node["verify"].get("exercise") == "case":
                lid = node["verify"]["case_id"].split(":", 1)[1]
                node["steps"] = [
                    "Read the scenario shown in the exercise. Select one final decision, then read the explanation after submitting.",
                    "This checks the stated decision only. The separate practice task contains the environment, materials and hands-on work.",
                ]
                if node["id"].startswith("recall-"):
                    node["steps"].insert(0, levels[lid]["recall"])
            continue
        lid = node["level"]
        level = levels[lid]
        node["preview"] = guide["previews"][lid]
        node["requirements"] = guide.get("level_requirements", {}).get(
            lid, guide["requirements"]
        )
        node["setup"] = guide["setup"]
        node["materials"] = [material]
        path = (
            "{lab_dir}/"
            + lid
            + ("-assessment.json" if node.get("milestone") else "-experiment.json")
        )
        if lid == "foundations":
            steps = guide["foundation"]["steps"]
        elif lid == "independent-transfer":
            steps = guide["transfer"]["steps"]
        else:
            steps = guide["topics"][lid]
        node["brief"] = level["experiment"]
        if node.get("milestone"):
            node["title"] = "Apply it: " + level["title"]
            node["steps"] = [
                "Use the same named files and environment as the practice task. This is an independent assessment: record your prediction before opening your earlier solution.",
                "Starting point: " + steps[0],
                "Change to test: " + level["variant"],
                "Comparison to retain: " + level["control"],
                "Perform the changed test and preserve exact input changes, actual output and an explanation. Record any help. If the change needs an unavailable environment, save preparation as progress and leave the operational test incomplete.",
                evidence_step(path),
            ]
            node["done_when"] = (
                "Your report at "
                + path
                + " includes the stated changed case, comparison, prediction versus actual result and explanation. A reviewer or honest self-review must assess the reasoning; the file check does not grade it."
            )
        else:
            node["title"] = "Practice: " + level["title"]
            node["steps"] = list(steps) + [evidence_step(path)]
            node["done_when"] = (
                "Save the named inputs, your exact actions, observed results and the explanation requested in the final step in "
                + path
                + ". Compare against the checks below before marking done; leave any required live-system test incomplete until actually performed."
            )
        # Individually authored walkthroughs remain authoritative, including the HTTP lab.
        apply_guidance(node, level.get("reference", {}))
        apply_guidance(
            node,
            level.get(
                "milestone_guidance"
                if node.get("milestone")
                else "experiment_guidance",
                {},
            ),
        )


def apply_guidance(node, guidance):
    allowed = {
        "title",
        "brief",
        "steps",
        "hints",
        "done_when",
        "minutes",
        "resource",
        "resource_label",
        "resource_note",
        "setup",
        "materials",
        "preview",
        "requirements",
    }
    if set(guidance) - allowed:
        raise ValueError(
            "Guidance may only override learner-facing content and duration"
        )
    node.update(guidance)


def outputs():
    source = json.loads((ROOT / "docs/curriculum/specialist-paths.json").read_text())
    guides = json.loads((ROOT / "docs/curriculum/lab-guides.json").read_text())[
        "tracks"
    ]
    sources = {
        r["id"]: r
        for r in json.loads((ROOT / "docs/curriculum/sources.json").read_text())[
            "sources"
        ]
    }
    cases = {}
    catalog = []
    assessments = []
    files = {}
    for track in source["tracks"]:
        pid = track["id"]
        first = track["levels"][0]["id"]
        resource = sources[track["sources"][0]]["url"]
        pack = {
            "pack": {
                "id": pid,
                "title": track["title"],
                "kind": "proficiency",
                "version": track.get("version", 1),
                "source": "ai-draft",
                "reviewed": False,
            },
            "vars": {"lab_dir": "~/cyber/" + pid},
            "level": [
                {"id": lv["id"], "title": lv["title"], "lane": "main"}
                for lv in track["levels"]
            ]
            + [
                {
                    "id": "recall-lane",
                    "title": "Return later: reasoning checks",
                    "lane": "side",
                },
                {"id": "quick", "title": "Small verified exercises", "lane": "side"},
            ],
            "node": [],
        }
        pack["node"].append(
            {
                "id": "lab-readiness",
                "level": first,
                "title": "Start with a verifiable evidence exercise",
                "size": "S",
                "minutes": 10,
                "needs": [],
                "done_when": "Compute the exact content hash of a fresh server-generated evidence fixture and pass its check.",
                "brief": "This small exercise tests evidence integrity. Track entry background: "
                + track["entry"],
                "resource": resource,
                "verify": {"type": "lab", "exercise": "integrity"},
            }
        )
        apply_guidance(pack["node"][-1], track.get("readiness_guidance", {}))
        for i, lv in enumerate(track["levels"]):
            lid = lv["id"]
            case_id = pid + ":" + lid
            cases[case_id] = lv["case"]
            model = lid + "-reasoning"
            exercise = lid + "-experiment"
            milestone = lid + "-milestone"
            needs = ["lab-readiness"] if i == 0 else []
            pack["node"].append(
                {
                    "id": model,
                    "level": lid,
                    "title": "Reason it through: " + lv["title"],
                    "size": "S",
                    "minutes": 10,
                    "needs": needs,
                    "done_when": "Pass the server-graded scenario decision for this concept. This checks conceptual judgment, not completion of the later hands-on exercise.",
                    "brief": lv["primer"],
                    "steps": [
                        "Work through this preparation: " + lv["primer"],
                        "Open the server exercise, make your decision and check its result. Explain to yourself why the alternative fails.",
                    ],
                    "resource": resource,
                    "verify": {"type": "lab", "exercise": "case", "case_id": case_id},
                }
            )
            path = "{lab_dir}/" + lid + "-experiment.json"
            pack["node"].append(
                {
                    "id": exercise,
                    "level": lid,
                    "title": "Investigate: " + lv["title"],
                    "size": "M",
                    "minutes": 60,
                    "needs": [model],
                    "done_when": lv["experiment"]
                    + " Save scope, setup, commands or query, observed result and limitations in "
                    + path
                    + ".",
                    "brief": lv["experiment"],
                    "steps": [
                        lv["primer"],
                        lv["experiment"],
                        "Save the actual evidence; file presence is not a skill grade. If required hardware or a tenant is unavailable, record preparation and leave the hands-on task incomplete.",
                    ],
                    "resource": resource,
                    "verify": {"type": "file", "path": path, "min_bytes": 200},
                }
            )
            path = "{lab_dir}/" + lid + "-assessment.json"
            pack["node"].append(
                {
                    "id": milestone,
                    "level": lid,
                    "title": "Apply it to a changed case: " + lv["title"],
                    "size": "M",
                    "minutes": 120,
                    "needs": [model, exercise] + needs,
                    "milestone": True,
                    "done_when": "Independently demonstrate the changed case and contrasting control, explain the mechanism, record assistance and save reproducible evidence in "
                    + path
                    + ". A reviewer or honest self-assessment must evaluate the reasoning; this file check does not grade it.",
                    "brief": lv["experiment"],
                    "steps": [
                        lv["experiment"],
                        "Transfer: " + lv["variant"],
                        "Control: " + lv["control"],
                        "Explain why the result supports the mechanism. Record untested assumptions and help used. Save the evidence packet.",
                    ],
                    "hints": [
                        "Predict the outcome before testing. If a walkthrough reveals the answer, practice and try a fresh variation before claiming independent transfer."
                    ],
                    "resource": resource,
                    "verify": {"type": "file", "path": path, "min_bytes": 300},
                }
            )
            pack["node"].append(
                {
                    "id": "recall-" + lid,
                    "level": "recall-lane",
                    "title": "Return later: " + lv["title"],
                    "size": "S",
                    "minutes": 10,
                    "needs": [milestone],
                    "done_when": "After a suggested 2–7 day delay, reconstruct the reasoning, then pass the server scenario check. The app grades the decision, not your free-form explanation or elapsed spacing.",
                    "brief": lv["recall"],
                    "steps": [
                        lv["recall"],
                        "Try without opening your notes first, then check the scenario. Correct your explanation using the source.",
                    ],
                    "resource": resource,
                    "verify": {"type": "lab", "exercise": "case", "case_id": case_id},
                }
            )
            for node in pack["node"]:
                if (node["level"] == lid and node["id"] != "lab-readiness") or node[
                    "id"
                ] == "recall-" + lid:
                    apply_guidance(node, lv.get("reference", {}))
                if node["id"] == exercise:
                    apply_guidance(node, lv.get("experiment_guidance", {}))
                if node["id"] == milestone:
                    apply_guidance(node, lv.get("milestone_guidance", {}))
            assessments.append(
                {
                    "pack": pid,
                    "level": lid,
                    "milestone": milestone,
                    "skill": lv["title"],
                    "experiment": lv["experiment"],
                    "variant": lv["variant"],
                    "control": lv["control"],
                    "recall": lv["recall"],
                    "sources": track["sources"],
                }
            )
        pack["node"].append(
            {
                "id": "quick-access-check",
                "level": "quick",
                "title": "A ten-minute permission puzzle",
                "size": "S",
                "minutes": 10,
                "needs": [],
                "done_when": "Correctly evaluate every allow/deny decision for a fresh server-generated policy fixture.",
                "resource": resource,
                "verify": {"type": "lab", "exercise": "access-policy"},
            }
        )
        apply_lab_guide(pack, track, guides[pid])
        text = (
            "# Generated from docs/curriculum/specialist-paths.json; unreviewed draft.\n"
            + dump_toml(pack)
        )
        parse_pack(text)
        relative = f"packs/community/{track['category'].lower()}/{pid}.toml"
        files[relative] = text
        files["tracks/cyber-tracks/" + relative] = text
        catalog.append(
            {
                k: track[k]
                for k in (
                    "id",
                    "title",
                    "category",
                    "aliases",
                    "entry",
                    "background",
                    "labs",
                    "limits",
                )
            }
            | {
                "main_levels": len(track["levels"]),
                "nodes": len(pack["node"]),
                "verification": "18 server-graded concept/micro-exercise checks; 16 hands-on artifact checks requiring evidence review.",
            }
        )
    # Existing deeper technical tracks retain their IDs and assessment definitions.
    for pid, category, aliases in [
        ("networking-for-security", "Foundations", ["networking", "tcp ip"]),
        ("web-application-security", "Offensive", ["web", "owasp"]),
        ("network-penetration-testing", "Offensive", ["pentest", "offensive security"]),
        (
            "reverse-engineering-and-binary-exploitation",
            "Specialist",
            ["reversing", "binary exploitation", "pwn"],
        ),
        (
            "defensive-security-and-detection",
            "Defensive",
            ["defense", "detection engineering", "blue team"],
        ),
    ]:
        p = parse_pack(
            (ROOT / "packs/community" / category.lower() / f"{pid}.toml").read_text()
        )
        catalog.append(
            {
                "id": pid,
                "title": p.title,
                "category": category,
                "aliases": aliases,
                "entry": "Use the entry demonstration in the track to check your background.",
                "background": [],
                "labs": [],
                "limits": "Established v3 assessment rubric; file checks do not grade reasoning.",
                "main_levels": 8,
                "nodes": len(p.nodes),
                "verification": "See each task: automated evidence, artifact checks and human assessment have different scope.",
            }
        )
    practice = parse_pack(
        (ROOT / "packs/community/practice/verified-security-lab.toml").read_text()
    )
    catalog.append(
        {
            "id": practice.id,
            "title": practice.title,
            "category": "Practice",
            "aliases": ["verified labs", "ctf", "logging lab"],
            "entry": "No prior track completion needed for the built-in exercises.",
            "background": [],
            "labs": ["juice-shop"],
            "limits": "Five built-in graded exercises and three signed Juice Shop checks. External tasks need the proof bridge and an individually assigned instance.",
            "main_levels": 8,
            "nodes": len(practice.nodes),
            "verification": "All eight tasks require verified results.",
        }
    )
    files["ascend/labs/cases.json"] = json.dumps(cases, indent=2) + "\n"
    files["packs/community/catalog.json"] = (
        json.dumps({"version": 1, "tracks": catalog}, indent=2) + "\n"
    )
    files["docs/curriculum/specialist-assessments.json"] = (
        json.dumps({"version": 1, "assessments": assessments}, indent=2) + "\n"
    )
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for relative, content in outputs().items():
        path = ROOT / relative
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise SystemExit("Generated content is stale: " + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print("Specialist packs, cases, assessments and catalog are consistent.")


if __name__ == "__main__":
    main()
