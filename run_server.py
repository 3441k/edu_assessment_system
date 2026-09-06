#!/usr/bin/env python
"""Run the Flask server."""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import shared.sqlite_compat  # noqa: F401, E402 — before SQLAlchemy/sqlite3

# Now import and run the app
from server.app import app, SERVER_HOST, SERVER_PORT

if __name__ == "__main__":
    print(f"Starting server on {SERVER_HOST}:{SERVER_PORT}")
    print(f"Database: {os.getenv('DATABASE_PATH', 'database/assessment.db')}")
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=True)

