"""Create/restore an independent SQLite snapshot using SQLite's backup API."""

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def inspect(path):
    source = Path(path).resolve()
    if not source.is_file():
        raise ValueError("Source database does not exist")
    with closing(
        sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=2)
    ) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError("Database integrity check failed: " + integrity)
        rows = db.execute(
            "SELECT id,message,created_at,idempotency_key FROM updates ORDER BY id"
        ).fetchall()
    return {
        "path": str(source),
        "integrity": integrity,
        "records": len(rows),
        "records_sha256": hashlib.sha256(
            json.dumps(rows, ensure_ascii=False).encode()
        ).hexdigest(),
    }


def copy_database(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    inspect(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Reserve the destination exclusively: never overwrite live data or a prior backup.
    with destination.open("xb"):
        pass
    try:
        with (
            closing(
                sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=2)
            ) as src,
            closing(sqlite3.connect(destination, timeout=2)) as dst,
        ):
            src.backup(dst, pages=128, sleep=0.01)
        return inspect(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("operation", choices=["create", "restore", "inspect"])
    cli.add_argument("--source", required=True)
    cli.add_argument("--destination")
    args = cli.parse_args()
    if args.operation != "inspect" and not args.destination:
        cli.error("create/restore require a new --destination path")
    try:
        result = (
            inspect(args.source)
            if args.operation == "inspect"
            else copy_database(args.source, args.destination)
        )
    except (OSError, ValueError, sqlite3.Error) as error:
        cli.exit(1, "Database operation failed: " + str(error) + "\n")
    print(json.dumps({"operation": args.operation, **result}, indent=2))


if __name__ == "__main__":
    main()
