import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

SESSION_LIFETIME = timedelta(days=30)
MAX_SESSIONS = 20


def validate_password(password):
    if not 12 <= len(password) <= 1024:
        raise ValueError("Password must have between 12 and 1024 characters")


def password_matches(password, encoded):
    if encoded.startswith("scrypt$"):
        try:
            salt = encoded.split("$")[1]
            return hmac.compare_digest(password_hash(password, salt), encoded)
        except (ValueError, IndexError):
            pass
    password_hash(password, "00" * 16)
    return False


def session_expiry(created_at):
    try:
        created = datetime.fromisoformat(created_at)
        return created.astimezone(UTC) + SESSION_LIFETIME if created.tzinfo else None
    except (ValueError, TypeError):
        return None


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
    ).hex()
    return f"scrypt${salt}${digest}"


def create_user(db, username, password, timezone_name):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", username):
        raise ValueError("Username must use letters, numbers, _ or -")
    validate_password(password)
    try:
        ZoneInfo(timezone_name)
    except (KeyError, ValueError):
        raise ValueError("An IANA timezone is required") from None
    with db.transaction():
        cursor = db.connection.execute(
            "INSERT INTO users(username,password_hash,timezone,created_at) VALUES (?,?,?,?)",
            (
                username,
                password_hash(password),
                timezone_name,
                datetime.now(UTC).isoformat(),
            ),
        )
        return cursor.lastrowid


def issue_token(db, user_id, label="CLI or browser"):
    now = datetime.now(UTC)
    if not isinstance(label, str) or not 1 <= len(label.strip()) <= 80:
        raise ValueError("Session label must have between 1 and 80 characters")
    token = secrets.token_urlsafe(32)
    with db.transaction():
        db.connection.execute(
            "DELETE FROM api_tokens WHERE user_id=? AND created_at<?",
            (user_id, (now - SESSION_LIFETIME).isoformat()),
        )
        db.connection.execute(
            "INSERT INTO api_tokens(token,user_id,created_at,label) VALUES (?,?,?,?)",
            (
                hashlib.sha256(token.encode()).hexdigest(),
                user_id,
                now.isoformat(),
                label.strip(),
            ),
        )
        db.connection.execute(
            "DELETE FROM api_tokens WHERE user_id=? AND token NOT IN "
            "(SELECT token FROM api_tokens WHERE user_id=? ORDER BY created_at DESC,token DESC LIMIT ?)",
            (user_id, user_id, MAX_SESSIONS),
        )
    return token


def login(db, username, password, label="CLI or browser"):
    row = db.connection.execute(
        "SELECT * FROM users WHERE username=?", (username,)
    ).fetchone()
    if not password_matches(password, row["password_hash"] if row else ""):
        raise ValueError("Invalid username or password")
    with db.transaction():
        current = db.connection.execute(
            "SELECT password_hash FROM users WHERE id=?", (row["id"],)
        ).fetchone()
        if not current or not hmac.compare_digest(
            current["password_hash"], row["password_hash"]
        ):
            raise ValueError("Invalid username or password")
        return issue_token(db, row["id"], label)


def authenticate(db, token):
    if not token:
        return None
    row = db.connection.execute(
        "SELECT users.*,api_tokens.created_at AS session_created_at FROM api_tokens "
        "JOIN users ON users.id=api_tokens.user_id WHERE token=?",
        (hashlib.sha256(token.encode()).hexdigest(),),
    ).fetchone()
    if not row or not row["password_hash"].startswith("scrypt$"):
        return None
    expires = session_expiry(row["session_created_at"])
    return row if expires and expires > datetime.now(UTC) else None


def session_id(token_hash):
    # A display/revocation identifier cannot be used as the bearer token or its hash.
    return hashlib.sha256(("session:" + token_hash).encode()).hexdigest()[:24]


def sessions(db, user_id, current_token=None):
    current_hash = (
        hashlib.sha256(current_token.encode()).hexdigest() if current_token else None
    )
    now = datetime.now(UTC)
    result = []
    for row in db.connection.execute(
        "SELECT token,created_at,label FROM api_tokens WHERE user_id=? ORDER BY created_at DESC",
        (user_id,),
    ):
        expires = session_expiry(row["created_at"])
        if expires and expires > now:
            result.append(
                {
                    "id": session_id(row["token"]),
                    "label": row["label"] or "CLI or browser",
                    "created_at": row["created_at"],
                    "expires_at": expires.isoformat(),
                    "current": row["token"] == current_hash,
                }
            )
    return result


def revoke_session(db, user_id, target_id):
    if not re.fullmatch(r"[a-f0-9]{24}", target_id):
        return False
    with db.transaction():
        for row in db.connection.execute(
            "SELECT token FROM api_tokens WHERE user_id=?", (user_id,)
        ):
            if hmac.compare_digest(session_id(row["token"]), target_id):
                db.connection.execute(
                    "DELETE FROM api_tokens WHERE user_id=? AND token=?",
                    (user_id, row["token"]),
                )
                return True
    return False


def revoke_other_sessions(db, user_id, current_token):
    current_hash = hashlib.sha256(current_token.encode()).hexdigest()
    return db.connection.execute(
        "DELETE FROM api_tokens WHERE user_id=? AND token<>?", (user_id, current_hash)
    ).rowcount


def change_password(db, user_id, current_password, new_password):
    validate_password(new_password)
    row = db.connection.execute(
        "SELECT password_hash FROM users WHERE id=?", (user_id,)
    ).fetchone()
    if (
        user_id == 1
        or not row
        or not password_matches(current_password, row["password_hash"])
    ):
        raise ValueError("Current password is incorrect")
    replacement = password_hash(new_password)
    with db.transaction():
        current = db.connection.execute(
            "SELECT password_hash FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if not current or not hmac.compare_digest(
            current["password_hash"], row["password_hash"]
        ):
            raise ValueError("Current password is incorrect")
        db.connection.execute(
            "UPDATE users SET password_hash=? WHERE id=?", (replacement, user_id)
        )
        db.connection.execute("DELETE FROM api_tokens WHERE user_id=?", (user_id,))
        return issue_token(db, user_id, "Browser after password change")


def managed_user(db, username):
    row = db.connection.execute(
        "SELECT * FROM users WHERE username=?", (username,)
    ).fetchone()
    if not row or row["id"] == 1:
        raise ValueError(
            "Choose an existing named account; the local testing account cannot be managed"
        )
    return row


def reset_password(db, username, new_password):
    validate_password(new_password)
    with db.transaction():
        row = managed_user(db, username)
        db.connection.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (password_hash(new_password), row["id"]),
        )
        db.connection.execute("DELETE FROM api_tokens WHERE user_id=?", (row["id"],))


def set_enabled(db, username, enabled):
    with db.transaction():
        row = managed_user(db, username)
        encoded = row["password_hash"]
        if enabled and encoded.startswith("disabled$scrypt$"):
            encoded = encoded.removeprefix("disabled$")
        elif not enabled and encoded.startswith("scrypt$"):
            encoded = "disabled$" + encoded
        db.connection.execute(
            "UPDATE users SET password_hash=? WHERE id=?", (encoded, row["id"])
        )
        db.connection.execute("DELETE FROM api_tokens WHERE user_id=?", (row["id"],))


def list_users(db):
    return [
        {
            "id": row["id"],
            "username": row["username"],
            "timezone": row["timezone"],
            "created_at": row["created_at"],
            "enabled": row["password_hash"].startswith("scrypt$"),
            "sessions": len(sessions(db, row["id"])),
        }
        for row in db.connection.execute(
            "SELECT * FROM users WHERE id<>1 ORDER BY username"
        )
    ]
