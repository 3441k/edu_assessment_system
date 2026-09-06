#!/usr/bin/env python
"""Run the Flask server with Waitress for classroom / local-network use.

Uses a single process with a thread pool (recommended with SQLite).
Debug mode is off. For development, use run_server.py instead.
"""

import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import shared.sqlite_compat  # noqa: F401, E402 — before SQLAlchemy/sqlite3

from dotenv import load_dotenv

load_dotenv()

from server.app import app, SERVER_HOST, SERVER_PORT

if __name__ == "__main__":
    try:
        from waitress import serve
    except ImportError:
        print("Waitress is not installed. Run: pip install -r requirements.txt")
        sys.exit(1)

    threads = int(os.getenv("SERVER_THREADS", "8"))
    db_path = os.getenv("DATABASE_PATH", "database/assessment.db")

    print(f"Starting production server on {SERVER_HOST}:{SERVER_PORT}")
    print(f"Database: {db_path} (SQLite WAL enabled on startup)")
    print(f"Threads: {threads}")
    print("Students on the same network: http://<this-machine-ip>:5000/login")
    print("Press Ctrl+C to stop.")

    serve(app, host=SERVER_HOST, port=SERVER_PORT, threads=threads)
