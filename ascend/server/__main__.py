import argparse
import getpass
import os
import sqlite3


def main():
    parser = argparse.ArgumentParser(prog="ascend-server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8420)
    parser.add_argument("--home")
    parser.add_argument("--auth-mode", choices=["single", "multi"], default=os.environ.get("AUTH_MODE", "single"))
    sub = parser.add_subparsers(dest="command")
    add = sub.add_parser("user-add"); add.add_argument("username"); add.add_argument("--timezone", required=True)
    args = parser.parse_args()
    if args.command == "user-add":
        from ascend.storage import Database
        from ascend.server.auth import create_user
        db = Database(args.home)
        try:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Confirm password: "): raise ValueError("Passwords do not match")
            create_user(db, args.username, password, args.timezone)
            print(f"Created user {args.username}")
        except (ValueError, sqlite3.IntegrityError) as error:
            parser.exit(2, f"{error}\n")
        finally: db.close()
        return
    from ascend.server.app import create_app
    import uvicorn
    if args.host == "0.0.0.0":
        print("Listening on all interfaces. Use a TLS reverse proxy beyond your trusted LAN.")
    uvicorn.run(create_app(args.home, args.auth_mode), host=args.host, port=args.port)


if __name__ == "__main__": main()
