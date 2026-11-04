"""Generate code-derived LaTeX references and compile the complete documentation."""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from ascend.cli import parser as cli_parser
from ascend.server.app import create_app

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
GENERATED = DOCS / "latex/generated"
DOCUMENTS = (
    "report",
    "handbook",
    "user-guide",
    "deployment-guide",
    "developer-handbook",
    "command-reference",
    "design-history",
)


def escape(value):
    table = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "^": r"\textasciicircum{}",
        "~": r"\textasciitilde{}",
    }
    return "".join(table.get(c, c) for c in str(value))


def verbatim(value):
    # Inputs are parser help, repository schemas and migration source, not user logs.
    return "\\begin{verbatim}\n" + value.rstrip() + "\n\\end{verbatim}\n"


def curriculum_prose(value):
    """Allow long reference URLs and underscored training literals to wrap."""
    result, cursor = [], 0
    for match in re.finditer(
        r"https?://[^\s{}]+|\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b", str(value)
    ):
        result.append(escape(value[cursor : match.start()]))
        token = match[0].rstrip(".,;")
        command = "url" if token.startswith(("http://", "https://")) else "path"
        result.append("\\" + command + "{" + token + "}")
        result.append(escape(match[0][len(token) :]))
        cursor = match.end()
    result.append(escape(value[cursor:]))
    return "".join(result)


def walk(parser):
    yield parser
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                yield from walk(child)


def generate():
    GENERATED.mkdir(parents=True, exist_ok=True)
    guide = json.loads((ROOT / "web/guide.json").read_text())
    titles = {topic["id"]: topic["title"] for topic in guide["topics"]}
    site_guide = [
        "% Generated from web/guide.json; do not edit.\n",
        "\\section{In-app documentation reference}\n",
        "The following topics match the searchable Docs screen in the application.\n",
    ]
    for topic in guide["topics"]:
        site_guide.append("\\subsection{" + escape(topic["title"]) + "}\n")
        site_guide.append(escape(topic["summary"]) + "\\par\n")
        for block in topic["blocks"]:
            kind = block["type"]
            if kind == "paragraph":
                site_guide.append(escape(block["text"]) + "\\par\n")
            elif kind == "heading":
                site_guide.append("\\subsubsection{" + escape(block["text"]) + "}\n")
            elif kind in {"steps", "list"}:
                environment = "enumerate" if kind == "steps" else "itemize"
                site_guide.append("\\begin{" + environment + "}\n")
                site_guide.extend(
                    "\\item " + escape(item) + "\n" for item in block["items"]
                )
                site_guide.append("\\end{" + environment + "}\n")
            elif kind == "code":
                site_guide.append(verbatim(block["text"]))
            else:
                raise ValueError(f"Unsupported guide block: {kind}")
        site_guide.append(
            "\\noindent\\textbf{Related guides:} "
            + escape(", ".join(titles[key] for key in topic.get("related", [])))
            + "\\par\n"
        )
    (GENERATED / "site-guide.tex").write_text("".join(site_guide))
    help_text = ["% Generated from the actual CLI parsers; do not edit.\n"]
    for parser in walk(cli_parser()):
        help_text.append(
            "\\subsubsection{"
            + escape(parser.prog)
            + "}\n"
            + verbatim(parser.format_help())
        )
    for args in [
        [],
        ["user-add"],
        ["user-list"],
        ["user-password"],
        ["user-disable"],
        ["user-enable"],
        ["user-revoke"],
        ["push-keys"],
    ]:
        result = subprocess.run(
            [sys.executable, "-m", "ascend.server", *args, "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        help_text.append(
            "\\subsubsection{"
            + escape("ascend-server " + " ".join(args))
            + "}\n"
            + verbatim(result.stdout)
        )
    (GENERATED / "cli-help.tex").write_text("".join(help_text))
    with tempfile.TemporaryDirectory(prefix="ascend-doc-schema-") as home:
        schema = create_app(
            home, auth_mode="multi", scheduler=False, account_management=True
        ).openapi()
    models = [
        "\\subsection{Generated HTTP request and validation schemas}\nThese schemas come from the current OpenAPI model definitions. Business rules and additional status codes are documented in the endpoint reference.\n"
    ]
    for name, definition in sorted(
        schema.get("components", {}).get("schemas", {}).items()
    ):
        models.append(
            "\\subsubsection{"
            + escape(name)
            + "}\n"
            + verbatim(json.dumps(definition, indent=2))
        )
    (GENERATED / "api-models.tex").write_text("".join(models))
    migrations = [
        "\\section{Storage migration reference}\nGenerated from the numbered SQL migrations. These are schema sources, not commands to rerun manually against an initialized profile.\n"
    ]
    for path in sorted((ROOT / "ascend/storage/migrations").glob("*.sql")):
        migrations.append(
            "\\subsection{" + escape(path.name) + "}\n" + verbatim(path.read_text())
        )
    (GENERATED / "storage.tex").write_text("".join(migrations))
    rows = json.loads((DOCS / "curriculum/assessment-map.json").read_text())[
        "assessments"
    ]
    rows += json.loads((DOCS / "curriculum/specialist-assessments.json").read_text())[
        "assessments"
    ]
    matrix = [
        "\\subsection{Level-by-level assessment crosswalk}\nEach entry corresponds to a named milestone in the original five or nineteen specialist tracks. Source IDs refer to the evidence register. The task text and prerequisites remain in the runtime TOML packs.\n"
    ]
    for row in rows:
        matrix.append(
            "\\subsubsection{" + escape(row["pack"] + ": " + row["level"]) + "}\n"
        )
        for label, key in [
            ("Milestone", "milestone"),
            ("Skill", "skill"),
            ("Experiment", "experiment"),
            ("Transfer", "variant"),
            ("Control", "control"),
            ("Later retrieval", "recall"),
        ]:
            matrix.append(
                "\\noindent\\textbf{"
                + label
                + ":} "
                + curriculum_prose(row[key])
                + "\\par\n"
            )
        matrix.append(
            "\\noindent\\textbf{Alignment references:} "
            + escape(", ".join(row["sources"]))
            + "\\par\n"
        )
    (GENERATED / "curriculum-map.tex").write_text("".join(matrix))
    catalog = ["\\section{Public learning catalog}\\label{public-catalog}\n"]
    community = ROOT / "packs/community"
    catalog_rows = [
        row
        for path in [
            community / "catalog.json",
            *sorted(community.glob("*/catalog.json")),
        ]
        for row in json.loads(path.read_text())["tracks"]
    ]
    for row in catalog_rows:
        catalog.append("\\subsection{" + escape(row["title"]) + "}\n")
        for label, key in [
            ("Pack ID", "id"),
            ("Category", "category"),
            ("Entry", "entry"),
            ("Limits", "limits"),
            ("Verification", "verification"),
        ]:
            catalog.append(
                "\\noindent\\textbf{" + label + ":} " + escape(row[key]) + "\\par\n"
            )
    (GENERATED / "catalog.tex").write_text("".join(catalog))
    register = json.loads((DOCS / "curriculum/sources.json").read_text())
    sources = [
        "\\subsection{Research evidence register}\nReviewed 2026-11-01. Titles identify sources; findings below are original paraphrases. Public pages and abstracts are distinguished from full-course or experimental validation.\n"
    ]
    for row in register["sources"]:
        sources.append("\\subsubsection{" + escape(row["id"]) + "}\n")
        for label, key in [
            ("Title", "title"),
            ("Evidence", "evidence_kind"),
            ("Supported inference", "finding"),
            ("Limits", "limits"),
        ]:
            sources.append(
                "\\noindent\\textbf{" + label + ":} " + escape(row[key]) + "\\par\n"
            )
        sources.append(
            "\\noindent Access: "
            + escape(f"{row['accessed']}, HTTP {row['status']}")
            + ". \\url{"
            + row["url"]
            + "}\n"
        )
    sources.append("\\subsubsection{Discovery limits}\n")
    for row in register["discovery_limits"]:
        sources.append(escape(row["result"]) + " \\url{" + row["url"] + "}\\par\n")
    (GENERATED / "research-sources.tex").write_text("".join(sources))


def compile_doc(name, records):
    for pass_number in (1, 2):
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", name + ".tex"],
            check=False,
            cwd=DOCS,
            text=True,
            capture_output=True,
            timeout=180,
        )
        records.append(f"{name}, pass {pass_number}: exit {result.returncode}\n")
        if result.returncode:
            records.append(result.stdout[-8000:])
            (DOCS / "testing/docs-build.txt").write_text("".join(records))
            raise RuntimeError(result.stdout[-4000:])
    log = (DOCS / (name + ".log")).read_text(errors="replace")
    issues = [
        line
        for line in log.splitlines()
        if any(
            x in line
            for x in [
                "Missing character:",
                "undefined references",
                "multiply defined",
            ]
        )
        or (
            (overflow := re.search(r"Overfull .*\((\d+\.\d+)pt too", line))
            and float(overflow[1]) > 1
        )
    ]
    if issues:
        records.append(f"{name}: layout/reference check failed\n" + "\n".join(issues))
        (DOCS / "testing/docs-build.txt").write_text("".join(records))
        raise RuntimeError(name + ": " + "\n".join(issues[:30]))
    print("Compiled " + str(DOCS / (name + ".pdf")), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--documents", nargs="+", choices=DOCUMENTS, default=list(DOCUMENTS)
    )
    args = parser.parse_args()
    generate()
    subprocess.run([sys.executable, "scripts/update_report.py"], cwd=ROOT, check=True)
    records = ["LaTeX compilation; generated references use temporary profiles only.\n"]
    for name in args.documents:
        compile_doc(name, records)
    summary = f"RESULT: {len(args.documents)} LaTeX documents compiled successfully; no missing glyphs, unresolved references or overflow above 1 pt.\n"
    records.append(summary)
    (DOCS / "testing/docs-build.txt").write_text("".join(records))
    subprocess.run([sys.executable, "scripts/update_report.py"], cwd=ROOT, check=True)
    if "report" in args.documents:
        compile_doc("report", records)
        (DOCS / "testing/docs-build.txt").write_text("".join(records))
    print(summary.strip())


if __name__ == "__main__":
    main()
