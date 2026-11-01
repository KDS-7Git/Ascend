from datetime import datetime
from pathlib import Path
import re
import subprocess

from ascend.engine.packs import substitute
from ascend.engine.verifiers import VerifyResult


def verify(spec, vars):
    spec = substitute(spec, vars)
    path = Path(spec.get("path", ".")).expanduser()
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(path),
                "log",
                "-100",
                "--format=%cI%x09%s",
                # An epoch-date default can parse before epoch in local time.
                # With no requested cutoff, let Git include all recent commits.
                *(["--since=" + spec["since"]] if spec.get("since") else []),
                "--",
            ],
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode:
            return VerifyResult(False, "Git repository could not be read")
        for line in result.stdout.splitlines():
            stamp, _, subject = line.partition("\t")
            if re.search(spec.get("pattern", ".*"), subject):
                return VerifyResult(
                    True,
                    "A matching repository commit was found",
                    datetime.fromisoformat(stamp),
                )
        return VerifyResult(False, "No matching repository commit was found")
    except (OSError, ValueError, re.error, subprocess.SubprocessError):
        return VerifyResult(False, "Git verifier could not complete")
