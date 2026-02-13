# Quick Start Guide

## Initial Setup

1. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Initialize database:**
```bash
python database/init_db.py
```

This creates the database with a default lecturer account:
- Username: `admin`
- Password: `admin`
- **Change this password after first login!**

## Running the System

### 1. Start the Flask Server

The server must be running for all applications to work:

```bash
python server/app.py
```

The server will start on `http://0.0.0.0:5000` (accessible from all network interfaces).

### 2. Run Lecturer Application

In a new terminal:

```bash
python lecturer_app/main.py
```

Login with the default credentials (admin/admin) or your lecturer account.

### 3. Access Student Web Interface

Open a web browser and navigate to:
```
http://localhost:5000/login
```

Or if accessing from another device on the local network:
```
http://<server-ip>:5000/login
```

### 4. Run Student Desktop Application (Optional)

In a new terminal:

```bash
python student_app/main.py
```

## Configuration

Create a `.env` file in the root directory to customize settings:

```env
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
DATABASE_PATH=database/assessment.db
CODE_EXECUTION_TIMEOUT=5
CODE_EXECUTION_MEMORY_LIMIT=128
```

## Usage Workflow

### For Lecturers:

1. **Manage Topics**: Create topics to organize questions
2. **Question Bank**: Add questions of different types (multiple choice, code, diagram, text)
3. **Create Tests**: Combine questions from the question bank into tests
4. **Student Management**: Add students manually or import from CSV
5. **Grading**: Grade submitted tests, use auto-grading for code questions
6. **Statistics**: View analytics and export reports

### For Students:

1. **Login**: Use username, password, and optionally student ID
2. **View Tests**: See available tests and their status
3. **Take Test**: Answer questions, save progress, submit when done
4. **View Results**: See grades and feedback after grading

## CSV Import Format

For importing students, use a CSV file with the following columns:
- `username` (required)
- `password` (required)
- `student_id` (optional)

Example:
```csv
username,password,student_id
student1,password123,STU001
student2,password456,STU002
```

## Troubleshooting

- **Connection errors**: Ensure the Flask server is running before starting desktop applications
- **Database errors**: Run `python database/init_db.py` to reinitialize
- **Port already in use**: Change `SERVER_PORT` in `.env` file
- **Import errors**: Ensure all dependencies are installed: `pip install -r requirements.txt`

