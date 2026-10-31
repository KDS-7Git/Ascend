"""Optional encrypted Web Push delivery via pywebpush; no crypto in the CLI core."""
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import urlparse


def _crypto():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        return serialization, ec
    except ImportError: raise ValueError("Install ascend-tracker[push] for Web Push support") from None


def generate_keys(path):
    serialization, ec = _crypto()
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    private = ec.generate_private_key(ec.SECP256R1())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return _public(private)


def _public(private):
    serialization, _ = _crypto()
    raw = private.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def public_key():
    serialization, _ = _crypto()
    path = os.environ.get("VAPID_PRIVATE_KEY")
    if not path: raise ValueError("Set VAPID_PRIVATE_KEY to your private key file")
    try:
        private = serialization.load_pem_private_key(Path(path).expanduser().read_bytes(), password=None)
        return _public(private)
    except (OSError, ValueError): raise ValueError("Cannot read the configured VAPID key") from None


def subscribe(db, subscription):
    endpoint = subscription.get("endpoint", "")
    if not isinstance(endpoint, str): raise ValueError("Push endpoint must be a URL string")
    parsed = urlparse(endpoint)
    allowed = {"fcm.googleapis.com", "updates.push.services.mozilla.com", "web.push.apple.com"}
    allowed.update(filter(None, os.environ.get("PUSH_ALLOWED_HOSTS", "").split(",")))
    if parsed.scheme != "https" or parsed.hostname not in allowed or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError("Unapproved push endpoint; only HTTPS push providers are accepted")
    keys = subscription.get("keys", {})
    if not isinstance(keys, dict): raise ValueError("Invalid push subscription keys")
    try:
        decode = lambda value: base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        p256dh, auth = decode(keys["p256dh"]), decode(keys["auth"])
        if len(p256dh) != 65 or p256dh[0] != 4 or len(auth) != 16: raise ValueError("Invalid push keys")
        _, ec = _crypto()
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), p256dh)
    except (KeyError, TypeError, ValueError): raise ValueError("Invalid push subscription keys") from None
    subscriptions = db.rows("push_subscriptions")
    if len(subscriptions) >= 20 and not any(s["endpoint"] == endpoint for s in subscriptions): raise ValueError("At most 20 browser subscriptions are allowed")
    db.connection.execute("INSERT INTO push_subscriptions VALUES (?,?,?,?) ON CONFLICT(user_id,endpoint) DO UPDATE SET subscription=excluded.subscription",
                          (db.user_id, endpoint, json.dumps(subscription), datetime.now(timezone.utc).isoformat()))
    return {"subscribed": True}


def unsubscribe(db, endpoint):
    db.connection.execute("DELETE FROM push_subscriptions WHERE user_id=? AND endpoint=?", (db.user_id, endpoint))
    return {"unsubscribed": True}


def send_to_user(db, message):
    try: from pywebpush import WebPushException, webpush
    except ImportError: raise ValueError("Install ascend-tracker[push] for Web Push support") from None
    private = os.environ.get("VAPID_PRIVATE_KEY")
    subject = os.environ.get("VAPID_SUBJECT")
    if not private or not subject: raise ValueError("Configure VAPID_PRIVATE_KEY and VAPID_SUBJECT")
    rows = db.rows("push_subscriptions")
    if not rows: raise ValueError("No browser has subscribed to notifications")
    sent, failed, expired = 0, 0, 0
    for row in rows:
        try:
            webpush(subscription_info=json.loads(row["subscription"]), data=json.dumps({"title": "Ascend", "body": message, "url": "/"}),
                    vapid_private_key=str(Path(private).expanduser()), vapid_claims={"sub": subject}, timeout=10)
            sent += 1
        except WebPushException as error:
            status = error.response.status_code if error.response is not None else None
            if status in {404, 410}:
                unsubscribe(db, row["endpoint"])
                expired += 1
            else: failed += 1
        except (OSError, ValueError): failed += 1
    if not sent and failed: raise ValueError("Web Push delivery failed")
    return {"sent": sent, "failed": failed, "expired": expired}
