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

### 2. Access Lecturer Interface

**Option A — Web (browser):**

Open a web browser and navigate to:
```
http://localhost:5000/lecturer/login
```

Or from another device on the local network:
```
http://<server-ip>:5000/lecturer/login
```

Login with the default credentials (admin/admin) or your lecturer account.

**Option B — Desktop app (optional):**

In a new terminal:

```bash
python lecturer_app/main.py
```

Login with the same credentials.

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

Use either the **web interface** (`/lecturer/login`) or the **desktop app** (`lecturer_app/main.py`). Both connect to the same API.

1. **Manage Topics**: Create topics to organize questions
2. **Question Bank**: Add questions; select one or more answer types per question (multiple choice, text, code, diagram)
3. **Create Tests**: Combine questions from the question bank into tests
4. **Student Management**: Add students manually or import from CSV; assign each student to one **group** (or leave Unassigned)
5. **Groups**: Create and manage student groups on the **Groups** tab; view group members and average grades
6. **Grading**: Open a submission, score each answer (0 to the question maximum), add feedback, then finalize
7. **Statistics**: Class overview charts, filter by group, **Compare groups** view, drill-down to test/student score summaries

When creating questions on the web **Question Bank** tab, check one or more **answer types** to combine components on a single question (e.g. written answer + diagram).

#### Test modes

Each test uses one of two modes (set when creating or editing a test on the **Tests** tab):

| Mode | How it works |
|------|--------------|
| **Scheduled** | Set `available_from` / `available_until` and an optional per-student `time_limit`. Students can start during the window; submissions auto-submit when their deadline passes. |
| **Live** | Students see the test as locked until the lecturer starts a session. Use **Go Live** to set a global duration; all students share the same end time. **Extend** adds time; **End** closes the session early. In-progress submissions are auto-submitted when the session ends. |

Live controls (Go Live / Extend / End) are available in the **lecturer web dashboard**. The desktop test editor supports scheduled availability fields; live session controls are web-only for now.

#### Statistics (lecturer web)

The **Statistics** tab provides a class overview first, then drill-down views:

| View | What you see |
|------|----------------|
| **Class overview** | Summary cards, average score by test (bar chart), score distribution for a focused test, weak topics, quick test list |
| **Browse tests** | Search by name; filter by mode (scheduled/live), grading status, and sort order; click a test for full test statistics |
| **Test statistics** | Score distribution, per-question averages, student score table with **Grade** links |
| **Browse students** | Search by username or student ID; click a student for their statistics |
| **Student statistics** | Score trend across tests, per-test scores; click a test for per-question score summary |
| **Student + test** | Total score and per-question breakdown (scores only); **Open grading** for full answers |

Use the **Focus test** dropdown on the overview to change which test drives the distribution chart. Use the **Group** filter to limit charts and tables to one group (including **Unassigned**). Click **Compare groups** for side-by-side group averages, a summary matrix, and per-group score distributions. Breadcrumb links at the top help navigate back. Grading stays on its own tab but is linked from statistics rows.

#### Groups

- **Groups tab**: create, edit, delete groups; view members and group average grade
- **Students tab**: assign a group when adding/editing a student; filter the list by group
- **Unassigned** appears as its own group wherever groups are compared (students with no group assigned)
- **Statistics**: filter any stats view by group, or open **Compare groups** for a full cross-group summary

### For Students:

1. **Login**: Use username, password, and optionally student ID
2. **View Tests**: See available tests and their status (open, upcoming, waiting for lecturer, live, closed)
3. **Take Test**: One question is shown at a time; use **Previous** / **Next** or the numbered sidebar to navigate; progress auto-saves
4. **Submit**: Use **Submit Test** on the last question, or the test auto-submits when time expires
5. **View Results**: After grading is finalized, open **View Results** from the dashboard (available even after a scheduled test window closes)

For **live** tests, the dashboard shows "Waiting for lecturer" until the session starts, then displays a shared countdown timer during the session.

## CSV Import Format

For importing students, use a CSV file with the following columns:
- `username` (required)
- `password` (required)
- `student_id` (optional)
- `group` (optional — group name; created automatically if it does not exist)

Example:
```csv
username,password,student_id,group
student1,password123,STU001,CS-2024-A
student2,password456,STU002,CS-2024-B
```

## Troubleshooting

- **Connection errors**: Ensure the Flask server is running before starting desktop applications or using web interfaces
- **Database errors**: Run `python database/init_db.py` to reinitialize. For existing databases, schema updates run automatically on server startup via `database/migrate.py`.
- **Port already in use**: Change `SERVER_PORT` in `.env` file
- **Import errors**: Ensure all dependencies are installed: `pip install -r requirements.txt`
- **Grading save error**: Each score must be between 0 and the question's maximum points (shown next to the score field)

