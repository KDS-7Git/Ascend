"""Scoped SQLite persistence and transactional, numbered migrations."""

from contextlib import contextmanager
from pathlib import Path
import json
import os
import sqlite3

TABLES = {
    "practice_rewards",
    "external_lab_attempts",
    "node_checkpoints",
    "activity_feedback",
    "activity_events",
    "activity_selections",
    "activity_tour_history",
    "activity_runs",
    "activity_rewards",
    "activity_evidence",
    "activity_bookmarks",
    "permission_attempts",
    "case_attempts",
    "lab_runs",
    "task_sessions",
    "xp_awards",
    "missions",
    "entries",
    "parked",
    "settings",
    "audit",
    "packs",
    "node_state",
    "level_unlocks",
    "evidence_log",
    "node_splits",
    "push_subscriptions",
    "telegram_updates",
}

# A running server must use the schema shipped with its loaded Python code.
# New migration files become eligible on restart, along with the new routes.
MIGRATIONS = tuple(sorted((Path(__file__).parent / "migrations").glob("[0-9]*.sql")))


def default_home():
    return Path(os.environ.get("ASCEND_HOME", "~/.config/ascend")).expanduser()


class Database:
    def __init__(self, home=None, user_id=1):
        self.home = Path(home or default_home()).expanduser()
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.user_id = user_id
        self.connection = sqlite3.connect(
            self.home / "ascend.db",
            timeout=15,
            isolation_level=None,
            check_same_thread=False,
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=15000")
        self.migrate()

    def migrate(self):
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        )
        for path in MIGRATIONS:
            version = int(path.name.split("_")[0])
            with self.transaction():
                row = self.connection.execute(
                    "SELECT version FROM schema_version"
                ).fetchone()
                if row and row[0] >= version:
                    continue
                statement = ""
                for line in path.read_text().splitlines(True):
                    statement += line
                    if sqlite3.complete_statement(statement):
                        self.connection.execute(statement)
                        statement = ""
                if statement.strip():
                    raise ValueError(f"Incomplete migration: {path.name}")
                self.connection.execute("DELETE FROM schema_version")
                self.connection.execute(
                    "INSERT INTO schema_version VALUES (?)", (version,)
                )

    @contextmanager
    def transaction(self):
        if self.connection.in_transaction:
            yield
            return
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise

    def rows(self, table, where="", params=(), order=""):
        if table not in TABLES:
            raise ValueError("Unknown table")
        return [
            dict(r)
            for r in self.connection.execute(
                f"SELECT * FROM {table} WHERE user_id=?"
                + (f" AND {where}" if where else "")
                + (f" ORDER BY {order}" if order else ""),
                (self.user_id, *params),
            )
        ]

    def insert(self, table, **values):
        if table not in TABLES:
            raise ValueError("Unknown table")
        values["user_id"] = self.user_id
        cols = ",".join(values)
        return self.connection.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({','.join('?' for _ in values)})",
            tuple(values.values()),
        ).lastrowid

    def update(self, table, where, params=(), **values):
        if table not in TABLES:
            raise ValueError("Unknown table")
        self.connection.execute(
            f"UPDATE {table} SET {','.join(k + '=?' for k in values)} WHERE user_id=? AND {where}",
            (*values.values(), self.user_id, *params),
        )

    def setting(self, key, default=None):
        rows = self.rows("settings", "key=?", (key,))
        return json.loads(rows[0]["value"]) if rows else default

    def set_setting(self, key, value):
        self.connection.execute(
            "INSERT INTO settings(user_id,key,value) VALUES (?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
            (self.user_id, key, json.dumps(value)),
        )

    def close(self):
        self.connection.close()
