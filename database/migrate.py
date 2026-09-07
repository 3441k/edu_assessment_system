"""Apply lightweight schema migrations for existing databases."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import shared.sqlite_compat  # noqa: F401, E402 — before sqlite3

import sqlite3

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "database/assessment.db")


def _column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _table_exists(cursor, table):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cursor.fetchone() is not None


def _apply_sqlite_pragmas(db_path):
    """PRAGMA journal_mode/synchronous must run outside an explicit transaction."""
    conn = sqlite3.connect(db_path)
    try:
        conn.isolation_level = None
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
    finally:
        conn.close()


def run_migrations():
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    if _table_exists(cursor, "tests") and not _column_exists(cursor, "tests", "test_mode"):
        cursor.execute(
            "ALTER TABLE tests ADD COLUMN test_mode VARCHAR(20) NOT NULL DEFAULT 'scheduled'"
        )

    if _table_exists(cursor, "submissions") and not _column_exists(cursor, "submissions", "live_session_id"):
        cursor.execute(
            "ALTER TABLE submissions ADD COLUMN live_session_id INTEGER REFERENCES live_sessions(id)"
        )

    if _table_exists(cursor, "questions") and not _column_exists(cursor, "questions", "answer_types"):
        cursor.execute("ALTER TABLE questions ADD COLUMN answer_types JSON")

    if _table_exists(cursor, "users") and not _column_exists(cursor, "users", "group_id"):
        cursor.execute("ALTER TABLE users ADD COLUMN group_id INTEGER REFERENCES groups(id)")

    if _table_exists(cursor, "questions") and not _column_exists(cursor, "questions", "image_data"):
        cursor.execute("ALTER TABLE questions ADD COLUMN image_data TEXT")

    # Promote legacy default admin user from lecturer to admin role
    if _table_exists(cursor, "users"):
        cursor.execute(
            "UPDATE users SET role = 'admin' WHERE username = 'admin' AND role = 'lecturer'"
        )

    conn.commit()
    conn.close()

    _apply_sqlite_pragmas(DATABASE_PATH)

    # Create any new tables (live_sessions, etc.)
    sys_path = str(Path(__file__).parent.parent)
    if sys_path not in __import__("sys").path:
        __import__("sys").path.insert(0, sys_path)
    from server.models import Base
    engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)
    Base.metadata.create_all(engine)
