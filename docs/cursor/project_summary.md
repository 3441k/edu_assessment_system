# Educational Assessment System - Project Summary

## Original Request

Create a GUI-based tool to help lecturers check student knowledge. The system should:

- Allow students to take tests based on previous lectures before each lesson
- Support multiple question types:
  - Multiple choice (choosing from a list)
  - Code writing
  - Diagram drawing
  - Long text answers
- Enable lecturers to:
  - Mark/grade tests
  - View statistics on topics where students perform poorly
  - Get overall progress summaries
  - Combine questions from different topics into tests
  - View all topics and tasks
- Provide two distinct interfaces:
  - **Student interface**: For taking tests
  - **Lecturer interface**: For creating tests, grading, and analytics

## Architecture & Technology Stack

### Client-Server Architecture

- **Backend**: Flask REST API server (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Lecturer Interface**: PyQt5 desktop application
- **Student Interfaces**: 
  - Web interface (Flask templates with Bootstrap)
  - Desktop application (PyQt5) - optional

### Key Design Decisions

1. **Dual Student Interfaces**: Students can use either web browser or desktop app, both connecting to the same backend
2. **Local Network Deployment**: Designed for local network use in shared areas
3. **Session-Based Authentication**: Flask sessions with bcrypt password hashing
4. **Code Execution**: Isolated Python subprocess with resource limits for safe code evaluation
5. **Question Storage**: Multiple choice questions store choices as JSON in `correct_answer` field: `{"choices": [...], "correct": "..."}`

## Implementation Plan

### Phase 1: Core Infrastructure
- [x] Database models (User, Topic, Question, Test, Submission, Answer, Grade)
- [x] Flask REST API with authentication
- [x] Database initialization script
- [x] Shared constants and API client base classes

### Phase 2: Lecturer Interface
- [x] PyQt5 desktop application
- [x] Login window with authentication
- [x] Main window with tabs:
  - Question Bank (create/edit/delete questions)
  - Test Editor (create tests from question bank)
  - Grading (grade submissions)
  - Statistics (view analytics)
  - Student Management (add/import students)

### Phase 3: Student Interfaces
- [x] Web interface (Flask templates)
  - Login page
  - Dashboard (view available tests)
  - Test taking interface
  - Results viewing
- [x] Desktop application (PyQt5)
  - Login window
  - Dashboard
  - Test taking interface

### Phase 4: Features
- [x] Multiple question types support
- [x] Auto-grading for code questions
- [x] Manual grading interface
- [x] Statistics and analytics
- [x] Topic management
- [x] Student management (manual and CSV import)
- [x] Export functionality (CSV, PDF)

## File Structure

```
edu_assessment_system/
├── database/
│   ├── assessment.db          # SQLite database
│   └── init_db.py             # Database initialization
├── server/
│   ├── app.py                 # Flask application entry point
│   ├── database.py            # Database engine and session
│   ├── models.py              # SQLAlchemy ORM models
│   ├── routes/                # API route handlers
│   │   ├── auth.py
│   │   ├── questions.py
│   │   ├── tests.py
│   │   ├── submissions.py
│   │   ├── grading.py
│   │   ├── statistics.py
│   │   ├── students.py
│   │   ├── topics.py
│   │   └── web.py             # Web interface routes
│   ├── services/              # Business logic
│   │   ├── code_executor.py   # Code execution with isolation
│   │   ├── grader.py          # Auto-grading logic
│   │   └── report_generator.py
│   └── templates/             # HTML templates
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── test_taking.html
│       └── results.html
├── lecturer_app/
│   ├── main.py                # Entry point
│   ├── api_client.py          # API client for lecturer app
│   └── windows/               # PyQt5 windows
│       ├── login_window.py
│       ├── main_window.py
│       ├── question_bank.py
│       ├── test_editor.py
│       ├── grading_window.py
│       ├── statistics.py
│       └── student_management.py
├── student_app/
│   ├── main.py                # Entry point
│   ├── api_client.py          # API client for student app
│   └── windows/               # PyQt5 windows
│       ├── login_window.py
│       ├── dashboard.py
│       └── test_taking.py
├── shared/
│   ├── constants.py            # Shared constants
│   └── api_client.py          # Base API client class
├── run_server.py              # Server startup script
├── run_lecturer.py            # Lecturer app startup script
├── run_student.py             # Student app startup script
├── requirements.txt           # Python dependencies
└── README.md                  # Setup and usage instructions
```

## Key Technical Details

### Database Models

- **User**: Students and lecturers with role-based access
- **Topic**: Organizes questions by subject/topic
- **Question**: Stores question content, type, correct answer, test cases
- **Test**: Collection of questions with time limits
- **TestQuestion**: Many-to-many relationship (test + question + order + points override)
- **Submission**: Student's test attempt
- **Answer**: Individual question answer with score and feedback
- **Grade**: Final grade for a submission

### Authentication

- Session-based authentication using Flask sessions
- Bcrypt for password hashing
- Role-based access control (lecturer vs student)
- CORS enabled for desktop applications

### Code Execution

- Isolated Python subprocess execution
- Resource limits (timeout, memory)
- Test case validation
- Automatic grading based on test cases

### Multiple Choice Questions

- Choices stored as JSON in `correct_answer` field:
  ```json
  {
    "choices": ["Option A", "Option B", "Option C", "Option D"],
    "correct": "Option A"
  }
  ```
- Backward compatible with legacy format

## Important Issues Resolved

### 1. Circular Import Issue
**Problem**: `server/app.py` and route files had circular imports
**Solution**: Created `server/database.py` to centralize database initialization

### 2. Module Not Found Error
**Problem**: Running scripts directly caused `ModuleNotFoundError`
**Solution**: Added project root to `sys.path` in run scripts and `server/app.py`

### 3. Session Management
**Problem**: Flask session cookies not persisting across requests
**Solution**: 
- Configured `SESSION_COOKIE_PATH`, `PERMANENT_SESSION_LIFETIME`
- Set `session.permanent = True` after login
- Simplified CORS configuration

### 4. Desktop App Session Sharing
**Problem**: Lecturer app created new API client instances, losing authentication
**Solution**: Pass authenticated `api_client` instance from login window to main window

### 5. Multiple Choice Choices Not Saving
**Problem**: Choices entered in lecturer app weren't saved or displayed
**Solution**: 
- Store choices as JSON in `correct_answer` field
- Parse JSON when loading for editing
- Update web interface to parse new format

### 6. Grading Window NoneType Error
**Problem**: `setValue(None)` error when score is None
**Solution**: Explicit None checking and defaulting to 0.0 for ungraded answers

### 7. Template Variable Error
**Problem**: `{{ test_id }}` causing JavaScript syntax error
**Solution**: Use `{{ test_id|tojson }}` to safely convert to JavaScript

## Configuration

### Environment Variables (.env)
```
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
DATABASE_PATH=database/assessment.db
CODE_EXECUTION_TIMEOUT=5
CODE_EXECUTION_MEMORY_LIMIT=128
```

### Default Credentials
After database initialization:
- Username: `admin`
- Password: `admin`
- **Important**: Change password after first login!

## Dependencies

### Backend
- Flask 3.0.0
- Flask-CORS 4.0.0
- SQLAlchemy 2.0.23
- bcrypt 4.1.1
- python-dotenv 1.0.0

### Desktop Applications
- PyQt5 5.15.10
- QScintilla 2.13.3
- requests 2.31.0

### Code Execution
- psutil 5.9.6

### Reporting
- reportlab 4.0.7
- pandas 2.1.4

## Usage Workflow

### For Lecturers:
1. Login to lecturer desktop app
2. Manage Topics: Create topics to organize questions
3. Question Bank: Add questions of different types
4. Create Tests: Combine questions from question bank
5. Student Management: Add students manually or import CSV
6. Grading: Grade submitted tests (auto-grade code questions)
7. Statistics: View analytics and export reports

### For Students:
1. Login via web interface or desktop app
2. View available tests on dashboard
3. Start test and answer questions
4. Save progress (auto-saves every 30 seconds)
5. Submit test when complete
6. View results and grades

## Future Enhancements (Not Implemented)

- Real-time collaboration features
- Advanced diagram editing tools
- Mobile app support
- Integration with learning management systems
- Advanced analytics and machine learning insights
- Multi-language support

## Notes

- System designed for local network deployment
- All applications connect to shared Flask backend
- Database is SQLite (single file, easy backup)
- Code execution is isolated but should be further hardened for production
- Session management configured for local network use

