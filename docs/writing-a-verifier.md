# Writing a verifier

A plugin is a Python file with this interface:

```python
from datetime import datetime, timezone
from ascend.engine.verifiers import VerifyResult

def verify(spec: dict, vars: dict) -> VerifyResult:
    return VerifyResult(True, "A concrete checkable result was found", None)
```

The result is `(ok: bool, summary: str, evidence_time: datetime | None)`. A known
timestamp must be timezone-aware and describe when the real-world work happened,
not when a poll happened. Use `None` when unknown. Keep summaries under 1,000
characters and exclude credentials, flags, file contents, and arbitrary output.

Save `my_checker.py` under `$ASCEND_HOME/verifiers/` (default
`~/.config/ascend/verifiers/`) and reference
`verify = {type = "plugin:my_checker"}` in a pack. Install lists plugin names.
Nothing is imported until `ascend plugin trust my_checker`. Editing the Python
file invalidates trust. On a multi-user server, plugin files live under
`$ASCEND_HOME/users/<id>/verifiers/` and require administrator permission as well.

Plugins run in an isolated Python process with a 10-second timeout and a bounded
result. **This is process isolation, not a security sandbox.** Trusted Python can
read files, access the network, or launch programs as its owner. Trust only code
you have reviewed. Imported dependencies are not included in the file fingerprint;
review their provenance and updates too.

Two built-in templates:

- [`file.py`](../ascend/verifiers/file.py) expands paths, checks size and optional
  text patterns, and returns the file's modification timestamp.
- [`command.py`](../ascend/verifiers/command.py) splits the template before
  substitution, executes with `shell=False`, and times out after ten seconds.
  It reports exit status without retaining arbitrary process output.

Local checks have an effect only when invoked by `check`, `done --complete`, or
`sync`. Lint, install, review, and trust do not execute plugin code.
