from datetime import datetime, timezone
import hashlib
import hmac
import re
import secrets
from zoneinfo import ZoneInfo


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
    ).hex()
    return f"scrypt${salt}${digest}"


def create_user(db, username, password, timezone_name):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", username):
        raise ValueError("Username must use letters, numbers, _ or -")
    if len(password) < 12:
        raise ValueError("Password must have at least 12 characters")
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
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return cursor.lastrowid


def login(db, username, password):
    row = db.connection.execute(
        "SELECT * FROM users WHERE username=?", (username,)
    ).fetchone()
    valid = False
    if row and row["password_hash"].startswith("scrypt$"):
        salt = row["password_hash"].split("$")[1]
        valid = hmac.compare_digest(password_hash(password, salt), row["password_hash"])
    else:
        password_hash(password, "00" * 16)  # Keep absent-user timing comparable.
    if not valid:
        raise ValueError("Invalid username or password")
    token = secrets.token_urlsafe(32)
    db.connection.execute(
        "INSERT INTO api_tokens VALUES (?,?,?,?)",
        (
            hashlib.sha256(token.encode()).hexdigest(),
            row["id"],
            datetime.now(timezone.utc).isoformat(),
            "CLI or browser",
        ),
    )
    return token


def authenticate(db, token):
    if not token:
        return None
    return db.connection.execute(
        "SELECT users.* FROM api_tokens JOIN users ON users.id=api_tokens.user_id WHERE token=?",
        (hashlib.sha256(token.encode()).hexdigest(),),
    ).fetchone()
