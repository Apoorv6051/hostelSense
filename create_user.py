"""Create a HostelSense user account.

Usage:
    python create_user.py --role warden --email warden@example.com --name "Warden Name"
    python create_user.py --role student --roll 1234567890123 --name "Student Name"
"""

import argparse
import getpass

from app import User, app, db
from werkzeug.security import generate_password_hash


def main():
    parser = argparse.ArgumentParser(description="Create a HostelSense account")
    parser.add_argument("--role", required=True, choices=("student", "parent", "warden"))
    parser.add_argument("--name", required=True)
    parser.add_argument("--email")
    parser.add_argument("--roll")
    args = parser.parse_args()

    if args.role == "student" and not args.roll:
        parser.error("--roll is required for student accounts")
    if args.role != "student" and not args.email:
        parser.error("--email is required for parent and warden accounts")

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if not password or password != confirmation:
        parser.error("Passwords must be non-empty and match")
    if len(password) < 12:
        parser.error("Password must contain at least 12 characters")

    with app.app_context():
        duplicate = User.query.filter(
            (User.email == args.email) | (User.roll == args.roll)
        ).first()
        if duplicate:
            parser.error("An account with that email or roll number already exists")

        user = User(
            name=args.name.strip(),
            email=args.email.strip().lower() if args.email else None,
            roll=args.roll.strip() if args.roll else None,
            password_hash=generate_password_hash(password),
            role=args.role,
        )
        db.session.add(user)
        db.session.commit()
        print(f"Created {user.role} account for {user.name}.")


if __name__ == "__main__":
    main()
