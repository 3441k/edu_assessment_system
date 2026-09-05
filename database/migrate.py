"""Apply lightweight schema migrations for existing databases."""

import os
import sqlite3
from pathlib import Path

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

    # WAL mode: better concurrent reads/writes for multiple students (auto-save, submit)
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA synchronous=NORMAL")

    conn.commit()
    conn.close()

    # Create any new tables (live_sessions, etc.)
    sys_path = str(Path(__file__).parent.parent)
    if sys_path not in __import__("sys").path:
        __import__("sys").path.insert(0, sys_path)
    from server.models import Base
    engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)
    Base.metadata.create_all(engine)
