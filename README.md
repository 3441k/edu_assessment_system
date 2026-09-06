# Educational Assessment System

A comprehensive tool for lecturers to create, manage, and grade student assessments with support for multiple question types including multiple choice, code, diagrams, and long text answers.

## Features

- **Question Types**: Multiple choice, code, diagram, and text — combinable on a single question (e.g. text + diagram, choices + code)
- **Dual Student Interfaces**: Web-based (browser) and desktop application (PyQt5)
- **Dual Lecturer Interfaces**: Web-based (browser) and desktop application (PyQt5)
- **Student Test UX**: One question at a time with Previous/Next, numbered jump navigation, and auto-save
- **Test Management**: Create tests from question bank, configure time limits, attempts, and availability
- **Scheduled Tests**: Set availability windows and optional per-student duration; auto-submit when time expires
- **Live Tests**: Lecturer-controlled sessions with Go Live, Extend, and End; global deadline and auto-submit for all students
- **Auto & Manual Grading**: Automatic code execution with test cases, manual grading for all question types
- **Student Results**: Graded submissions show scores and feedback on the dashboard; available after the test window closes for scheduled tests
- **Statistics & Analytics** (lecturer web): Class overview with Chart.js charts, test focus picker, weak-topic highlights, searchable test/student lists with filters, drill-down score summaries, **student groups** with cross-group comparison, and one-click links to grading
- **Export**: CSV grades export and PDF report generation

## Architecture

- **Lecturer Interfaces**: Web (Flask templates) and Desktop (PyQt5)
- **Student Interfaces**: Web (Flask templates) and Desktop (PyQt5)
- **Backend**: Flask REST API server
- **Database**: SQLite

## Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

On some Linux systems the built-in `sqlite3` module is too old for SQLAlchemy. This project includes **`pysqlite3-binary`** in `requirements.txt` and loads it automatically via `shared/sqlite_compat.py` in the run scripts and database entry points.

If you start the app with a **custom Python script** (not `run_server.py` / `run_server_production.py`), add these lines **before** any import that uses SQLite or SQLAlchemy:

```python
import sys
import pysqlite3
sys.modules['sqlite3'] = pysqlite3
```

Alternatively, after adding the project root to `sys.path`:

```python
import shared.sqlite_compat  # noqa: F401
```

### Offline installation

On a machine with internet, download wheels for transfer to an offline classroom PC:

```bash
mkdir offline_packages
pip download -r requirements.txt -d offline_packages
# Optional: Python 3.13-specific pins
pip download -r requirements_local_313.txt -d offline_packages
```

Copy the project folder and `offline_packages/` to the offline machine, then:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --no-index --find-links=offline_packages -r requirements.txt
```

3. Initialize the database:
```bash
python database/init_db.py
```

Existing databases are migrated automatically on server startup (`database/migrate.py`).

4. Start the Flask server:

**Development** (auto-reload, debug messages):
```bash
./run_server.py
# or: python -m server.app
```

**Classroom / local network** (~10–15 simultaneous users — recommended for live tests):
```bash
pip install -r requirements.txt   # includes waitress
./run_server_production.py
```

Use `SERVER_HOST=0.0.0.0` in `.env` so students on the same Wi‑Fi can connect via `http://<your-ip>:5000/login`. SQLite WAL mode is enabled automatically for smoother concurrent saves.

5. Access lecturer web interface (recommended for browser use):
Open browser and navigate to `http://localhost:5000/lecturer/login`

6. Run the lecturer desktop application (optional):
```bash
# Using the run script (recommended)
./run_lecturer.py
# Or directly
/home/hlnb/.pyenv/versions/3.12.0/bin/python3.12 run_lecturer.py
```

7. Access student web interface:
Open browser and navigate to `http://localhost:5000/login`

8. Run student desktop application:
```bash
# Using the run script (recommended)
./run_student.py
# Or directly
/home/hlnb/.pyenv/versions/3.12.0/bin/python3.12 run_student.py
```

## Configuration

Create a `.env` file in the root directory:
```
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
DATABASE_PATH=database/assessment.db
CODE_EXECUTION_TIMEOUT=5
CODE_EXECUTION_MEMORY_LIMIT=128
# Optional — production server (run_server_production.py)
SERVER_THREADS=8
SQLITE_BUSY_TIMEOUT_MS=30000
```

## Capacity (local network)

Typical classroom use (**~10–15 simultaneous users**) works on a modern laptop (4 GB+ RAM) when you run `./run_server_production.py` instead of the debug server. The heaviest load is auto-grading **code** questions for many students at once. See `QUICKSTART.md` for deployment details.

## Browser support

The web UI targets **Firefox 64+**, Chrome, and recent Edge. Older Firefox versions do not support `?.` and `??` in JavaScript; the project avoids that syntax and uses **Chart.js 3.9** (not v4) for statistics charts.

If pages stay blank on an old browser, hard-refresh (Ctrl+Shift+R) after updating. Ensure the **server** is started with `run_server.py` or `run_server_production.py` (includes the SQLite compatibility shim via `shared/sqlite_compat.py`).

## Default Credentials

After initialization, a default lecturer account is created:
- Username: `admin`
- Password: `admin`
- **Change this password after first login!**

## License

Private project for educational use.

