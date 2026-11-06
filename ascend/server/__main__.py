import argparse
import getpass
import json
import os
import sqlite3


def main():
    parser = argparse.ArgumentParser(prog="ascend-server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8420)
    parser.add_argument("--home")
    parser.add_argument(
        "--auth-mode",
        choices=["single", "multi"],
        default=os.environ.get("AUTH_MODE", "single"),
    )
    parser.add_argument(
        "--account-management",
        action="store_true",
        default=os.environ.get("ASCEND_ACCOUNT_MANAGEMENT") == "1",
        help="Enable account security controls with --auth-mode multi; off for single-user testing",
    )
    parser.add_argument(
        "--registration",
        action="store_true",
        default=os.environ.get("ASCEND_REGISTRATION") == "1",
        help="Allow self-service signup with --auth-mode multi",
    )
    sub = parser.add_subparsers(dest="command")
    add = sub.add_parser("user-add")
    add.add_argument("username")
    add.add_argument("--timezone", required=True)
    sub.add_parser("user-list")
    for name in ("user-password", "user-disable", "user-enable", "user-revoke"):
        sub.add_parser(name).add_argument("username")
    keys = sub.add_parser("push-keys")
    keys.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.command == "push-keys":
        from ascend.nudge.channels.webpush import generate_keys

        try:
            print("Public VAPID key:", generate_keys(args.out))
            print(
                "Private key saved with mode 0600. Set VAPID_PRIVATE_KEY to that path."
            )
        except (ValueError, OSError) as error:
            parser.exit(2, f"{error}\n")
        return
    if args.command == "user-add":
        from ascend.server.auth import create_user
        from ascend.storage import Database

        db = Database(args.home)
        try:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Confirm password: "):
                raise ValueError("Passwords do not match")
            create_user(db, args.username, password, args.timezone)
            print(f"Created user {args.username}")
        except (ValueError, sqlite3.IntegrityError) as error:
            parser.exit(2, f"{error}\n")
        finally:
            db.close()
        return
    if args.command in {
        "user-list",
        "user-password",
        "user-disable",
        "user-enable",
        "user-revoke",
    }:
        from ascend.server import auth
        from ascend.storage import Database

        db = Database(args.home)
        try:
            if args.command == "user-list":
                print(json.dumps(auth.list_users(db), indent=2))
            elif args.command == "user-password":
                password = getpass.getpass("New password: ")
                if password != getpass.getpass("Confirm new password: "):
                    raise ValueError("Passwords do not match")
                auth.reset_password(db, args.username, password)
                print(
                    f"Password reset for {args.username}. Account enabled; all existing sessions signed out."
                )
            elif args.command == "user-revoke":
                row = auth.managed_user(db, args.username)
                db.connection.execute(
                    "DELETE FROM api_tokens WHERE user_id=?", (row["id"],)
                )
                print(f"Signed out all sessions for {args.username}.")
            else:
                auth.set_enabled(db, args.username, args.command == "user-enable")
                print(
                    f"Account {args.username} {'enabled' if args.command == 'user-enable' else 'disabled'}; existing sessions signed out. Learning data is retained."
                )
        except (ValueError, sqlite3.IntegrityError) as error:
            parser.exit(2, f"{error}\n")
        finally:
            db.close()
        return
    import uvicorn

    from ascend.server.app import create_app

    if args.host == "0.0.0.0":
        print(
            "Listening on all interfaces. Use a TLS reverse proxy beyond your trusted LAN."
        )
    uvicorn.run(
        create_app(
            args.home,
            args.auth_mode,
            account_management=args.account_management,
            registration=args.registration,
        ),
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
