"""Database configuration and session management."""

import shared.sqlite_compat  # noqa: F401 — before sqlite3/SQLAlchemy

import os
import sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv

load_dotenv()

# Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "database/assessment.db")
SQLITE_BUSY_TIMEOUT_MS = int(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "30000"))

# Database setup — timeout helps concurrent writes; WAL is set in migrate + connect hook
engine = create_engine(
    f"sqlite:///{DATABASE_PATH}",
    echo=False,
    connect_args={"check_same_thread": False, "timeout": SQLITE_BUSY_TIMEOUT_MS / 1000},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


db_session = scoped_session(sessionmaker(bind=engine))

# Apply migrations for existing databases
try:
    from database.migrate import run_migrations
    run_migrations()
except Exception:
    pass

