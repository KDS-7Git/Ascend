"""Verify administrator-signed observations; never trust a browser's solved flag."""

from datetime import datetime, timedelta
import hashlib
import hmac
import json
import os
from pathlib import Path

from ascend.engine.verifiers import VerifyResult


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def verify(t, pack, node):
    key = os.environ.get("ASCEND_LAB_SIGNING_KEY", "")
    root = os.environ.get("ASCEND_LAB_RECEIPTS_DIR", "")
    provider = node.verify.get("provider")
    if not key or not root:
        return VerifyResult(
            False, "The administrator must configure the lab proof bridge first."
        )
    try:
        path = Path(root) / (f"{provider}-{t.db.user_id}.json")
        if path.stat().st_size > 256000:
            raise ValueError("oversized")
        envelope = json.loads(path.read_text())
        payload = envelope["payload"]
        if (
            not isinstance(payload, dict)
            or not isinstance(envelope.get("signature"), str)
            or not isinstance(payload.get("solved"), list)
            or any(not isinstance(item, str) for item in payload["solved"])
        ):
            raise ValueError("schema")
        signature = hmac.new(
            bytes.fromhex(key), canonical(payload), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, envelope["signature"]):
            raise ValueError("signature")
        if (
            payload["provider"] != provider
            or type(payload["owner"]) is not int
            or payload["owner"] != t.db.user_id
        ):
            raise ValueError("owner")
        stamp = datetime.fromisoformat(payload["observed_at"])
        if stamp.tzinfo is None or not timedelta(
            seconds=-5
        ) <= t.now() - stamp <= timedelta(minutes=5):
            raise ValueError("stale")
        if not all(
            challenge in payload["solved"]
            for challenge in [node.verify["challenge"], *node.verify.get("all_of", [])]
        ):
            return VerifyResult(
                False, "This challenge is not solved in the assigned lab observation."
            )
    except (OSError, ValueError, KeyError, TypeError):
        return VerifyResult(
            False,
            "No current, valid lab receipt for this account. Refresh the proof bridge.",
        )
    # Observation time is not necessarily the time of solving the external lab.
    return VerifyResult(
        True,
        f"Confirmed {provider} challenge {node.verify['challenge']} in the assigned lab.",
    )
