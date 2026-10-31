from datetime import datetime, timezone
from pathlib import Path
import re

from ascend.engine.packs import substitute
from ascend.engine.verifiers import VerifyResult


def verify(spec, vars):
    spec = substitute(spec, vars)
    path = Path(spec["path"]).expanduser()
    try:
        if not path.is_file(): return VerifyResult(False, "Evidence file does not exist")
        stat = path.stat()
        if stat.st_size < int(spec.get("min_bytes", 0)): return VerifyResult(False, "Evidence file is too small")
        if spec.get("contains"):
            if stat.st_size > 2_000_000: return VerifyResult(False, "Evidence file exceeds 2 MB content-check limit")
            if not re.search(spec["contains"], path.read_text(errors="replace")):
                return VerifyResult(False, "Evidence file does not match the required pattern")
        return VerifyResult(True, f"Evidence file exists ({stat.st_size} bytes)", datetime.fromtimestamp(stat.st_mtime, timezone.utc))
    except (OSError, ValueError, re.error):
        return VerifyResult(False, "Unable to read or validate the evidence file")
