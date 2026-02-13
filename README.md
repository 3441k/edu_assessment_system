# Educational Assessment System

A comprehensive tool for lecturers to create, manage, and grade student assessments with support for multiple question types including multiple choice, code, diagrams, and long text answers.

## Features

- **Question Types**: Multiple choice, code writing, diagram drawing, and long text answers
- **Dual Student Interfaces**: Web-based (browser) and desktop application (PyQt5)
- **Test Management**: Create tests from question bank, configure time limits, attempts, and availability
- **Auto & Manual Grading**: Automatic code execution with test cases, manual grading for all question types
- **Statistics & Analytics**: Topic-wise performance tracking, student progress, class-wide statistics
- **Export**: CSV grades export and PDF report generation

## Architecture

- **Lecturer Interface**: PyQt5 desktop application
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

4. Start the Flask server:
```bash
python server/app.py
```

5. Run the lecturer application:
```bash
python lecturer_app/main.py
```

6. Access student web interface:
Open browser and navigate to `http://localhost:5000`

7. Run student desktop application:
```bash
python student_app/main.py
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

After initialization, create a lecturer account through the application or database.

## License

Private project for educational use.

