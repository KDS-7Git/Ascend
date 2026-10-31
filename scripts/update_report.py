"""Refresh the LaTeX status section from retained pytest output and Git history."""
from pathlib import Path
import re
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parents[1]


def escape(value):
    return str(value).replace("\\", r"\textbackslash{}").replace("_", r"\_").replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")


rows = []
for phase in ("1", "1b", "2", "3", "4"):
    path = ROOT / f"docs/testing/phase-{phase}.txt"
    status = "Not yet validated"
    if path.exists():
        matches = re.findall(r"=+\s+([^\n]*\b(?:passed|failed|error)[^\n]*)\s+=+", path.read_text())
        if matches: status = matches[-1].strip(" =")
    rows.append(f"Phase {phase} & {escape(status)} \\\\")
history = subprocess.check_output(["git", "log", "--format=%h %s", "-12"], cwd=ROOT, text=True)
history = "\n".join(textwrap.fill(line, width=76, subsequent_indent="  ") for line in history.splitlines()) + "\n"
content = "\\begin{longtable}{p{0.18\\textwidth}p{0.75\\textwidth}}\n\\textbf{Milestone} & \\textbf{Cumulative test result} \\\\\n\\hline\n"
content += "\n".join(rows) + "\n\\end{longtable}\n"
content += "\\subsection*{Recent recorded commits}\n\\begin{verbatim}\n" + history + "\\end{verbatim}\n"
content += "\\noindent Full transcripts: \\texttt{docs/testing/phase-*.txt}. The implementation may have uncommitted work beyond the last validated milestone.\n"
(ROOT / "docs/report-status.tex").write_text(content)
