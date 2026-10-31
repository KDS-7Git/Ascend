"""Record tracked and pending project files, respecting .gitignore."""

from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
output = root / "docs/testing/file-tree.txt"
output.touch()
paths = subprocess.check_output(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
    cwd=root,
    text=True,
).splitlines()
tree = {}
for path in sorted(set(paths)):
    node = tree
    for part in Path(path).parts:
        node = node.setdefault(part, {})
lines = ["ascend/"]


def render(node, prefix=""):
    items = sorted(node.items(), key=lambda item: (not bool(item[1]), item[0]))
    for index, (name, children) in enumerate(items):
        last = index == len(items) - 1
        lines.append(
            prefix + ("└── " if last else "├── ") + name + ("/" if children else "")
        )
        if children:
            render(children, prefix + ("    " if last else "│   "))


render(tree)
output.write_text("\n".join(lines) + "\n")
