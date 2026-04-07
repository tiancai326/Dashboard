import argparse
import getpass
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.services.auth_service import AuthService


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update admin account")
    parser.add_argument("--email", required=True, help="admin email")
    parser.add_argument("--username", default="admin", help="admin display name")
    parser.add_argument("--password", default="", help="admin password")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Admin password: ")
    if len(password) < 6:
        raise SystemExit("Password must be at least 6 characters")

    service = AuthService()
    service.create_admin(args.email.strip().lower(), args.username.strip(), password)
    print(f"Admin account ready: {args.email.strip().lower()}")


if __name__ == "__main__":
    main()
