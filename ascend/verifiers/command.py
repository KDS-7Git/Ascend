import os
from pathlib import Path
import shlex
import subprocess
import tempfile

from ascend.engine.packs import substitute
from ascend.engine.verifiers import VerifyResult


def verify(spec, vars):
    # Split the trusted template first: substituted values remain single arguments.
    argv = [os.path.expanduser(substitute(arg, vars)) for arg in shlex.split(spec["cmd"])]
    if not argv or any(Path(arg).name == "sudo" for arg in argv):
        return VerifyResult(False, "Empty commands and sudo are not allowed")
    try:
        # Temporary output files bound memory even if a command prints a great deal.
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            result = subprocess.run(argv, shell=False, timeout=10, stdout=out, stderr=err)
            # Do not persist arbitrary command output: it may contain credentials.
        return VerifyResult(result.returncode == 0, f"Command exited with status {result.returncode}")
    except subprocess.TimeoutExpired:
        return VerifyResult(False, "Command timed out after 10 seconds")
    except (OSError, ValueError):
        return VerifyResult(False, "Command could not be executed")
