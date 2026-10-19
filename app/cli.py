import argparse
import getpass
import sys

from app.db.session import SessionLocal
from app.services.owner import (
    OwnerExistsError,
    WeakPasswordError,
    create_owner,
    reset_password,
)


def _ask_password() -> str:
    first = getpass.getpass("Password: ")
    second = getpass.getpass("Repeat password: ")
    if first != second:
        sys.exit("Passwords do not match.")
    return first


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-owner", help="Create the one owner.")
    create.add_argument("--username", required=True)

    reset = sub.add_parser("reset-password", help="Set a new owner password.")
    reset.add_argument("--username", required=True)

    args = parser.parse_args()
    password = _ask_password()

    try:
        with SessionLocal() as db:
            if args.command == "create-owner":
                create_owner(db, args.username, password)
                print("Owner created.")
            else:
                reset_password(db, args.username, password)
                print("Password changed. All sessions signed out.")
    except (OwnerExistsError, WeakPasswordError, LookupError, ValueError) as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()