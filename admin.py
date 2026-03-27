#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# admin.py  —  CandidateIQ Admin CLI
#
# Usage (run locally from your project root):
#
#   python admin.py invite user@company.com
#   python admin.py list-users
#   python admin.py list-tokens
#   python admin.py deactivate <username>
#
# The invite command prints a signup URL you copy/paste to the
# client. No email service required.
# ─────────────────────────────────────────────────────────────

import sys
import sqlite3
from auth import create_invite_token, get_db, init_db

# ── CONFIGURE THIS ──────────────────────────────────────────
# Your app's public URL (no trailing slash)
APP_URL = "https://your-app.streamlit.app"   # <-- update this
# ────────────────────────────────────────────────────────────


def cmd_invite(email: str):
    email = email.strip().lower()
    if not email or "@" not in email:
        print(f"  ✗  '{email}' doesn't look like a valid email.")
        sys.exit(1)

    token = create_invite_token(email)
    link  = f"{APP_URL}/?invite={token}"

    print()
    print("─" * 60)
    print(f"  ✓  Invite token generated for: {email}")
    print(f"  ⏳  Expires in 48 hours")
    print()
    print("  Signup link (copy and send to the user):")
    print()
    print(f"  {link}")
    print()
    print("─" * 60)
    print()


def cmd_list_users():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, username, email, created_at, is_active FROM users ORDER BY id"
        ).fetchall()

    if not rows:
        print("\n  No users registered yet.\n")
        return

    print()
    print(f"  {'ID':<4}  {'Username':<20}  {'Email':<30}  {'Active':<6}  Created")
    print("  " + "─" * 80)
    for r in rows:
        active = "Yes" if r["is_active"] else "No"
        print(f"  {r['id']:<4}  {r['username']:<20}  {r['email']:<30}  {active:<6}  {r['created_at'][:10]}")
    print()


def cmd_list_tokens():
    with get_db() as conn:
        rows = conn.execute(
            """SELECT email, token, expires_at, used
               FROM invite_tokens
               ORDER BY id DESC LIMIT 20"""
        ).fetchall()

    if not rows:
        print("\n  No tokens issued yet.\n")
        return

    print()
    print(f"  {'Email':<30}  {'Status':<8}  {'Expires':<20}  Token (truncated)")
    print("  " + "─" * 85)
    for r in rows:
        status = "Used" if r["used"] else "Active"
        short  = r["token"][:16] + "..."
        print(f"  {r['email']:<30}  {status:<8}  {r['expires_at'][:16]:<20}  {short}")
    print()


def cmd_deactivate(username: str):
    username = username.strip().lower()
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE users SET is_active = 0 WHERE username = ?", (username,)
        )
    if cursor.rowcount:
        print(f"\n  ✓  User '{username}' deactivated.\n")
    else:
        print(f"\n  ✗  User '{username}' not found.\n")


def cmd_reactivate(username: str):
    username = username.strip().lower()
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE users SET is_active = 1 WHERE username = ?", (username,)
        )
    if cursor.rowcount:
        print(f"\n  ✓  User '{username}' reactivated.\n")
    else:
        print(f"\n  ✗  User '{username}' not found.\n")


def print_help():
    print("""
CandidateIQ Admin CLI
─────────────────────
  python admin.py invite <email>           Generate a signup link for a user
  python admin.py list-users               Show all registered users
  python admin.py list-tokens              Show recent invite tokens
  python admin.py deactivate <username>    Disable a user's access
  python admin.py reactivate <username>    Re-enable a user's access
""")


if __name__ == "__main__":
    init_db()
    args = sys.argv[1:]

    if not args:
        print_help()
        sys.exit(0)

    command = args[0].lower()

    if command == "invite":
        if len(args) < 2:
            print("  Usage: python admin.py invite <email>")
            sys.exit(1)
        cmd_invite(args[1])

    elif command == "list-users":
        cmd_list_users()

    elif command == "list-tokens":
        cmd_list_tokens()

    elif command == "deactivate":
        if len(args) < 2:
            print("  Usage: python admin.py deactivate <username>")
            sys.exit(1)
        cmd_deactivate(args[1])

    elif command == "reactivate":
        if len(args) < 2:
            print("  Usage: python admin.py reactivate <username>")
            sys.exit(1)
        cmd_reactivate(args[1])

    else:
        print(f"  Unknown command: '{command}'")
        print_help()
        sys.exit(1)