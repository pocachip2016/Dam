#!/usr/bin/env python3
import sys
import argparse
import getpass
import psycopg
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.auth import hash_password, issue_token

DSN = "postgresql://dam:dam@localhost:15432/dam"


def main():
    parser = argparse.ArgumentParser(description="Create a Dam user")
    parser.add_argument("--username", required=True, help="Username")
    parser.add_argument("--role", required=True, choices=["admin", "editor", "viewer"], help="User role")
    parser.add_argument("--password-stdin", action="store_true", help="Read password from stdin")
    parser.add_argument("--issue-token", action="store_true", help="Issue and print API token")

    args = parser.parse_args()

    if args.password_stdin:
        password = sys.stdin.readline().strip()
    else:
        password = getpass.getpass("Password: ")

    if not password:
        print("Error: password cannot be empty", file=sys.stderr)
        sys.exit(1)

    password_hash = hash_password(password)

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO users(username, password_hash, role) VALUES(%s, %s, %s) RETURNING id",
                    (args.username, password_hash, args.role)
                )
                user_id = cur.fetchone()[0]
            except psycopg.IntegrityError:
                print(f"Error: user '{args.username}' already exists", file=sys.stderr)
                sys.exit(1)
        conn.commit()

    print(f"Created user: {args.username} (id={user_id}, role={args.role})")

    if args.issue_token:
        raw_token, _ = issue_token(user_id, name="cli-issued")
        print(f"Token: {raw_token}")


if __name__ == "__main__":
    main()
