from datetime import datetime
from typing import NamedTuple


class VerifyResult(NamedTuple):
    ok: bool
    summary: str
    evidence_time: datetime | None = None
