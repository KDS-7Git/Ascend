"""Save your own observations; this program does not solve or grade a lab."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Report path shown in the challenge")
    args = parser.parse_args()
    path = Path(args.path).expanduser()
    if path.exists():
        parser.exit(1, "Report already exists. Open it in a text editor to update your notes.\n")
    prompts = {
        "scope": "Which local fixture, app or dataset did you use? ",
        "setup": "OS, tool versions and setup you actually used: ",
        "prediction": "What did you expect before testing? ",
        "actions": "Exact commands, queries or steps you performed: ",
        "observed": "Actual output and evidence file/row references: ",
        "comparison": "Changed input/control and its actual result: ",
        "explanation": "Why do those observations differ? ",
        "limitations": "What remains untested or uncertain? ",
        "assistance": "References or help used (or none): ",
    }
    try:
        report = {key: input(prompt).strip() for key, prompt in prompts.items()}
    except (EOFError, KeyboardInterrupt):
        parser.exit(1, "\nCancelled; no report saved.\n")
    if not all(report.values()):
        parser.exit(1, "An answer was empty; no report saved. Run again when ready.\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2, ensure_ascii=False)
            output.write("\n")
    except FileExistsError:
        parser.exit(1, "Report already exists; your existing notes were preserved.\n")
    print("Saved:", path)
    print("Review your observations against the finish line. This is not a skill grade.")


if __name__ == "__main__":
    main()
