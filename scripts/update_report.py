"""Refresh the LaTeX status section from retained pytest output and Git history."""

from pathlib import Path
import re
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parents[1]


def escape(value):
    return (
        str(value)
        .replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("#", r"\#")
    )


rows = []
milestones = [
    (f"Phase {phase}", f"phase-{phase}.txt") for phase in ("1", "1b", "2", "3", "4")
]
milestones += [
    ("Engagement refresh", "engagement-refresh.txt"),
    ("Curriculum assurance", "curriculum-assurance.txt"),
    ("LaTeX handbooks", "docs-build.txt"),
    ("Installed v3 tracks", "curriculum-install.txt"),
    ("Container restore", "restore-smoke.txt"),
    ("Compose settings", "compose-config.txt"),
    ("Verified learning", "verified-learning.txt"),
    ("Lab integration", "docker-labs.txt"),
    ("Expanded release", "expanded-release.txt"),
    ("Pi compatibility", "arm64-compatibility.txt"),
    ("Hardened deployment", "deployment-integration-final.txt"),
    ("Expanded installation", "expanded-install.txt"),
    ("Public archive", "public-archive.txt"),
]
for milestone, filename in milestones:
    path = ROOT / "docs/testing" / filename
    status = "Not yet validated"
    if path.exists():
        matches = re.findall(
            r"^(?:RESULT: ([^\n]+)|([^\n]*\d+ passed[^\n]*))$",
            path.read_text(),
            re.MULTILINE,
        )
        if matches:
            status = next(value for value in matches[-1] if value).strip(" =")
    rows.append(f"{escape(milestone)} & {escape(status)} \\\\")
history = subprocess.check_output(
    ["git", "log", "--format=%h %s", "-12"], cwd=ROOT, text=True
)
history = (
    "\n".join(
        textwrap.fill(line, width=76, subsequent_indent="  ")
        for line in history.splitlines()
    )
    + "\n"
)
content = "\\begin{longtable}{p{0.18\\textwidth}p{0.75\\textwidth}}\n\\textbf{Milestone} & \\textbf{Recorded validation} \\\\\n\\hline\n"
content += "\n".join(rows) + "\n\\end{longtable}\n"
content += (
    "\\subsection*{Recent recorded commits}\n\\begin{verbatim}\n"
    + history
    + "\\end{verbatim}\n"
)
content += "\\noindent Full transcripts: \\texttt{docs/testing/phase-*.txt}. The implementation may have uncommitted work beyond the last validated milestone.\n"
(ROOT / "docs/report-status.tex").write_text(content)
