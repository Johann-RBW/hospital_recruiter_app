# ─────────────────────────────────────────────────────────────
# auth.py  —  CandidateIQ Authentication Layer
# SQLite-backed invite tokens + bcrypt hashed passwords
# No external auth service required.
# ─────────────────────────────────────────────────────────────

import sqlite3
import secrets
import hashlib
import os
from datetime import datetime, timedelta, timezone

DB_PATH = os.environ.get("AUTH_DB_PATH", "candidateiq_auth.db")
TOKEN_EXPIRY_HOURS = 48


# ─────────────────────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist. Safe to call on every startup."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT    UNIQUE NOT NULL,
                username      TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL,
                is_active     INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS invite_tokens (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT    NOT NULL,
                token      TEXT    UNIQUE NOT NULL,
                created_at TEXT    NOT NULL,
                expires_at TEXT    NOT NULL,
                used       INTEGER NOT NULL DEFAULT 0
            );
        """)


# ─────────────────────────────────────────────────────────────
# PASSWORD HELPERS  (SHA-256 + salt — no bcrypt dependency)
# ─────────────────────────────────────────────────────────────

def _hash_password(password: str, salt: str = None) -> str:
    """Return 'salt$hash' string. Generates salt if not provided."""
    if salt is None:
        salt = secrets.token_hex(32)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${hashed}"


def _verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored 'salt$hash' string."""
    try:
        salt, _ = stored.split("$", 1)
        return _hash_password(password, salt) == stored
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────
# INVITE TOKEN LOGIC
# ─────────────────────────────────────────────────────────────

def create_invite_token(email: str) -> str:
    """
    Generate a single-use invite token for the given email.
    Invalidates any prior unused tokens for the same email.
    Returns the raw token string.
    """
    email = email.strip().lower()
    token = secrets.token_urlsafe(48)
    now   = datetime.now(timezone.utc)
    exp   = now + timedelta(hours=TOKEN_EXPIRY_HOURS)

    with get_db() as conn:
        # Invalidate old unused tokens for this email
        conn.execute(
            "UPDATE invite_tokens SET used = 1 WHERE email = ? AND used = 0",
            (email,)
        )
        conn.execute(
            """INSERT INTO invite_tokens (email, token, created_at, expires_at, used)
               VALUES (?, ?, ?, ?, 0)""",
            (email, token, now.isoformat(), exp.isoformat())
        )
    return token


def validate_invite_token(token: str) -> dict | None:
    """
    Validate a token. Returns the invite row dict if valid, None otherwise.
    Does NOT mark the token as used — call consume_invite_token() after account creation.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM invite_tokens WHERE token = ? AND used = 0",
            (token,)
        ).fetchone()

    if not row:
        return None

    exp = datetime.fromisoformat(row["expires_at"])
    # Make exp timezone-aware if naive
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > exp:
        return None  # Expired

    return dict(row)


def consume_invite_token(token: str):
    """Mark a token as used. Call this after successful account creation."""
    with get_db() as conn:
        conn.execute(
            "UPDATE invite_tokens SET used = 1 WHERE token = ?",
            (token,)
        )


# ─────────────────────────────────────────────────────────────
# USER MANAGEMENT
# ─────────────────────────────────────────────────────────────

def username_exists(username: str) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE username = ?", (username.strip().lower(),)
        ).fetchone()
    return row is not None


def email_already_registered(email: str) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    return row is not None


def create_user(email: str, username: str, password: str) -> bool:
    """
    Create a new user. Returns True on success, False if username/email conflict.
    """
    email    = email.strip().lower()
    username = username.strip().lower()
    pw_hash  = _hash_password(password)
    now      = datetime.now(timezone.utc).isoformat()

    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO users (email, username, password_hash, created_at)
                   VALUES (?, ?, ?, ?)""",
                (email, username, pw_hash, now)
            )
        return True
    except sqlite3.IntegrityError:
        return False


def authenticate_user(username: str, password: str) -> dict | None:
    """
    Verify credentials. Returns user dict on success, None on failure.
    """
    username = username.strip().lower()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,)
        ).fetchone()

    if not row:
        return None

    if _verify_password(password, row["password_hash"]):
        return {"id": row["id"], "email": row["email"], "username": row["username"]}

    return None


# ─────────────────────────────────────────────────────────────
# STREAMLIT SESSION HELPERS
# ─────────────────────────────────────────────────────────────

def is_logged_in(session_state) -> bool:
    return session_state.get("authenticated", False) and session_state.get("user") is not None


def login_user(session_state, user: dict):
    session_state["authenticated"] = True
    session_state["user"] = user


def logout_user(session_state):
    session_state["authenticated"] = False
    session_state["user"] = None


# ─────────────────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────────────────
init_db()