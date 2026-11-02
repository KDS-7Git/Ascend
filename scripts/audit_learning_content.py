"""Locate known instruction defects; this is not a pedagogical quality score."""

import argparse
import json
import re
from pathlib import Path

from ascend.engine.packs import parse_pack

ROOT = Path(__file__).resolve().parents[1]


def audit():
    sources = json.loads((ROOT / "docs/curriculum/sources.json").read_text())["sources"]
    curriculum_urls = {
        source["url"].rstrip("/")
        for source in sources
        if "curriculum" in source["evidence_kind"] or "/courses/" in source["url"]
    }
    records = []
    for file in sorted((ROOT / "packs/community").rglob("*.toml")):
        pack = parse_pack(file.read_text())
        for node in pack.nodes:
            text = "\n".join([node.brief, node.done_when, *node.steps])
            issues = []
            if "Demonstrate each entry skill with a small owned fixture" in text:
                issues.append("generic-entry-demonstration")
            if "After a delay, attempt the fresh task" in text:
                issues.append("unspecified-fresh-task")
            if node.brief and node.done_when.startswith(node.brief):
                issues.append("repeated-introduction-and-finish-line")
            if node.resource.rstrip("/") in curriculum_urls and not node.resource_note:
                issues.append("curriculum-reference-presented-as-task-resource")
            if re.search(
                r"\b(supplied|provided)\b.*\b(dataset|image|graph|bundle|capture|fixture|trace|timeline)\b",
                text,
                re.I,
            ):
                if (
                    not node.materials
                    and "```" not in text
                    and not re.search(r"https?://|fixtures/|materials/", text)
                ):
                    issues.append("material-location-needs-review")
            for material in node.materials:
                if (
                    material["url"].startswith("/training/")
                    and not (ROOT / "web" / material["url"].lstrip("/")).is_file()
                ):
                    issues.append("missing-bundled-material")
            if node.verify.get("type") == "file" and node.verify.get(
                "path", ""
            ).endswith(".json"):
                if "```" not in text and "JSON object" not in text:
                    issues.append("json-evidence-without-save-instructions")
            records.append(
                {
                    "pack": pack.id,
                    "node": node.id,
                    "title": node.title,
                    "file": str(file.relative_to(ROOT)),
                    "issues": issues,
                }
            )
    return {
        "scope": "All bundled community nodes; checks flag known text patterns for review, not readiness, learning effectiveness or execution success.",
        "packs": len({row["pack"] for row in records}),
        "nodes": len(records),
        "flagged_nodes": sum(bool(row["issues"]) for row in records),
        "issue_counts": {
            issue: sum(issue in row["issues"] for row in records)
            for issue in sorted({issue for row in records for issue in row["issues"]})
        },
        "findings": [row for row in records if row["issues"]],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check the saved diagnostic without rewriting it",
    )
    args = parser.parse_args()
    result = audit()
    path = ROOT / "docs/curriculum/usability-audit.json"
    content = json.dumps(result, indent=2) + "\n"
    if args.check:
        if not path.exists() or path.read_text() != content:
            raise SystemExit("Curriculum diagnostic is stale; rerun the audit.")
    else:
        path.write_text(content)
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "findings"}, indent=2
        )
    )
