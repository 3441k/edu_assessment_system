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
- **Statistics & Analytics** (lecturer web): Class overview with Chart.js charts, test focus picker, weak-topic highlights, searchable test/student lists with filters, and drill-down to per-test and per-student score summaries with one-click links to grading
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

3. Initialize the database:
```bash
python database/init_db.py
```

Existing databases are migrated automatically on server startup (`database/migrate.py`).

4. Start the Flask server:
```bash
# Using the run script (recommended)
./run_server.py
# Or directly with Python 3.12
/home/hlnb/.pyenv/versions/3.12.0/bin/python3.12 run_server.py
# Or using python module
python -m server.app
```

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
```

## Default Credentials

After initialization, a default lecturer account is created:
- Username: `admin`
- Password: `admin`
- **Change this password after first login!**

## License

Private project for educational use.

