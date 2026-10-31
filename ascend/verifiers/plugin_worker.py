"""Private subprocess protocol; never imports a plugin before checking its hash."""
from contextlib import redirect_stdout
import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    path, digest = sys.argv[1:]
    source = Path(path).read_bytes()
    if hashlib.sha256(source).hexdigest() != digest: raise ValueError("Plugin changed after trust check")
    inputs = json.load(sys.stdin)
    namespace = {"__name__": "ascend_user_plugin", "__file__": path}
    with open(os.devnull, "w") as sink, redirect_stdout(sink):
        exec(compile(source, path, "exec"), namespace)
        result = namespace["verify"](inputs["spec"], inputs["vars"])
    print(json.dumps({"ok": result.ok, "summary": result.summary,
                      "evidence_time": result.evidence_time.isoformat() if result.evidence_time else None}))


if __name__ == "__main__": main()
