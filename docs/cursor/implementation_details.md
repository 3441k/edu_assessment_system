# Implementation Details

## API Endpoints

All lecturer web and desktop interfaces consume the same REST API. Web pages use JavaScript `fetch()` with session cookies; desktop apps use `requests.Session()`.

### Authentication (`/api/v1/auth`)
- `POST /login` - Login with username and password
- `POST /logout` - Logout current user
- `GET /me` - Get current user info
- `GET /debug_session` - Debug session info (development)

### Topics (`/api/v1/topics`)
- `GET /` - Get all topics
- `GET /<id>` - Get topic by ID
- `POST /` - Create topic (lecturer only)
- `PUT /<id>` - Update topic (lecturer only)
- `DELETE /<id>` - Delete topic (lecturer only)

### Questions (`/api/v1/questions`)
- `GET /` - Get all questions (optionally filtered by topic_id)
- `GET /<id>` - Get question by ID
- `POST /` - Create question (lecturer only)
- `PUT /<id>` - Update question (lecturer only)
- `DELETE /<id>` - Delete question (lecturer only)

Question payloads include `answer_types`: an ordered array of one or more of `multiple_choice`, `text`, `code`, `diagram`. When multiple types are selected, `type` is stored as `composite`. Helpers live in `shared/question_utils.py`.

For combined multiple choice + text on one question, the student's `answer_text` is stored as JSON: `{"multiple_choice": "...", "text": "..."}`.

### Tests (`/api/v1/tests`)
- `GET /` - Get all tests
- `GET /<id>` - Get test with questions
- `POST /` - Create test (lecturer only)
- `PUT /<id>` - Update test (lecturer only)
- `DELETE /<id>` - Delete test (lecturer only)

Test payloads include `test_mode` (`scheduled` or `live`), `time_limit`, `attempts_allowed`, `available_from`, and `available_until`. List/detail responses also include timing fields (`availability_status`, `live_status`, `seconds_remaining`, etc.) computed by `server/services/test_schedule.py`. Student list responses add `can_view_results` and `results_ready` so graded results stay accessible after scheduled windows close.

### Live Sessions (`/api/v1/tests/<id>/live`)
Implemented in `server/routes/live.py`. Only applies to tests with `test_mode=live`.

- `GET /status` - Get current live session status (authenticated users)
- `POST /start` - Start a live session (lecturer only). Body: `{"duration_minutes": 60}`
- `POST /extend` - Extend active session (lecturer only). Body: `{"minutes": 10}`
- `POST /end` - End active session early (lecturer only)

When a live session ends (naturally, by extend/end, or on expiry), all in-progress submissions for that session are auto-submitted.

### Submissions (`/api/v1/submissions`)
- `GET /` - Get user's submissions (optionally filtered by test_id)
- `GET /<id>` - Get submission details
- `POST /` - Create new submission (blocked if test unavailable or live session not active)
- `POST /<id>/answers` - Save answer for a question
- `POST /<id>/submit` - Submit test

For students, `GET /<id>` on a submitted or graded submission returns a results payload: `grade`, `questions` (with content, answers, scores, feedback), `results_ready`, and `can_view_results`. Students do not use the lecturer grading API to view their own results.

Submission endpoints call `auto_submit_if_expired()` from `test_schedule.py` to finalize timed-out in-progress submissions before serving or mutating data. The submit endpoint is idempotent: if a submission was already auto-submitted, it returns 200 instead of an error.

### Grading (`/api/v1/grading`)
- `GET /submissions/<id>` - Get submission for grading (lecturer only). Creates placeholder `Answer` rows for unanswered questions.
- `PUT /answers/<id>` - Grade an answer (lecturer only). Score must be a number from 0 to the question maximum.
- `POST /submissions/<id>/finalize` - Finalize grading (lecturer only)

### Statistics (`/api/v1/statistics`)
- `GET /overview` - Get overview statistics (lecturer only)
- `GET /student/<id>` - Get student statistics (lecturer only)
- `GET /test/<id>` - Get test statistics (lecturer only)

### Students (`/api/v1/students`)
- `GET /` - Get all students (lecturer only)
- `POST /` - Create student (lecturer only)
- `POST /import` - Import students from CSV (lecturer only)
- `PUT /<id>` - Update student (lecturer only)
- `DELETE /<id>` - Delete student (lecturer only)

## Web Interface Routes

### Student Web (`/`)

| Route | Description |
|-------|-------------|
| `GET /login` | Student login page |
| `GET /logout` | Logout and redirect to student login |
| `GET /dashboard` | Student test dashboard (student role required) |
| `GET /test/<test_id>` | Test taking page (student role required) |
| `GET /results/<submission_id>` | View graded results (student role required) — loads from `/api/v1/submissions/<id>` |

Implemented in `server/routes/web.py`. Uses `require_student()` to block lecturers.

**Test taking UI** (`server/templates/test_taking.html`): one question at a time, Previous/Next buttons, numbered sidebar, progress bar, auto-save, Submit only on the last question. Code editor lazy-inits when shown; diagram canvas is full-width with correct drawing coordinates.

**Results UI** (`server/templates/results.html`): shows final grade and per-question scores/feedback after lecturer finalizes grading. The student dashboard always offers **View Results** for graded submissions, including scheduled tests whose availability window has closed (`can_view_results` / `results_ready` from the tests list API).

### Lecturer Web (`/lecturer`)

| Route | Description |
|-------|-------------|
| `GET /lecturer/login` | Lecturer login page |
| `GET /lecturer/logout` | Logout and redirect to lecturer login |
| `GET /lecturer/dashboard` | Main control panel with tabs (lecturer role required) |
| `GET /lecturer/grading/<submission_id>` | Grade a specific submission (lecturer role required) |

Implemented in `server/routes/lecturer_web.py`. Uses `require_lecturer()` for protected pages.

### Lecturer Dashboard Tabs

The dashboard (`server/templates/lecturer/dashboard.html`) provides five tabs, each calling the REST API via `server/static/js/lecturer.js`:

1. **Question Bank** — list/filter questions, manage topics, add/edit/delete questions with one or more answer types
2. **Tests** — list tests, create/edit tests with question selection, set test mode (scheduled vs live), availability window, and time limit; for live tests, use Go Live / Extend / End controls
3. **Grading** — list submitted/graded submissions, link to grading page
4. **Statistics** — overview, by topic, by student, by test
5. **Students** — list students, add manually, import CSV, delete

### Role Separation

- Student login (`/login`) rejects users with `role=lecturer` and links to `/lecturer/login`
- Lecturer login (`/lecturer/login`) rejects users with `role=student` and links to `/login`
- Both share the same `/api/v1/auth/login` endpoint; role is checked client-side and in route guards

## Test Scheduling and Live Control

Each test has a `test_mode`: `scheduled` (default) or `live`. Logic lives in `server/services/test_schedule.py` and `server/services/live_session.py`.

### Scheduled mode

- **Availability**: `available_from` / `available_until` define when students may start (`upcoming` → `open` → `closed`).
- **Per-student deadline**: If `time_limit` is set, deadline is `min(started_at + time_limit, available_until)`.
- **Auto-submit**: In-progress submissions are submitted automatically when the deadline passes.

### Live mode

- **Before session**: Test is visible but locked (`waiting`); students cannot start.
- **During session**: Lecturer starts a `LiveSession` with a global `ends_at`. All students share the same deadline.
- **After session**: Status is `ended`; new attempts require a new live session (lecturer can Go Live again).
- **Auto-submit**: When the session ends, all in-progress submissions linked to that `live_session_id` are submitted.

### Availability status values

| Mode | Status | Meaning |
|------|--------|---------|
| Scheduled | `upcoming` | Before `available_from` |
| Scheduled | `open` | Students can start |
| Scheduled | `closed` | After `available_until` |
| Live | `waiting` | No active session |
| Live | `live` | Session in progress |
| Live | `ended` | Session finished |

### Database migrations

`database/migrate.py` adds columns to existing databases and creates new tables. Migrations run automatically when the server starts (`server/database.py`):

| Migration | Purpose |
|-----------|---------|
| `tests.test_mode` | Scheduled vs live test mode |
| `submissions.live_session_id` | Link attempts to live sessions |
| `questions.answer_types` | JSON array of combined answer components |
| `live_sessions` table | Lecturer-controlled live windows |

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'lecturer' or 'student'
    student_id VARCHAR(50) UNIQUE,  -- Only for students
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Topics Table
```sql
CREATE TABLE topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Questions Table
```sql
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,  -- single type or 'composite'
    answer_types JSON,  -- ordered list: multiple_choice, text, code, diagram
    content TEXT NOT NULL,
    correct_answer TEXT,  -- JSON for multiple choice
    test_cases JSON,  -- For code questions: [{"input": "...", "output": "..."}]
    points FLOAT DEFAULT 1.0 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);
```

### Tests Table
```sql
CREATE TABLE tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    time_limit INTEGER,  -- Minutes per student (scheduled mode); NULL = no limit
    attempts_allowed INTEGER DEFAULT 1,
    available_from DATETIME,  -- Scheduled mode: window start
    available_until DATETIME,  -- Scheduled mode: window end
    test_mode VARCHAR(20) NOT NULL DEFAULT 'scheduled',  -- 'scheduled' or 'live'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### LiveSessions Table
```sql
CREATE TABLE live_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL,
    started_at DATETIME NOT NULL,
    ends_at DATETIME NOT NULL,
    ended_at DATETIME,
    status VARCHAR(20) NOT NULL DEFAULT 'live',  -- 'live' or 'ended'
    started_by INTEGER,  -- Lecturer user id
    duration_minutes INTEGER NOT NULL,
    FOREIGN KEY (test_id) REFERENCES tests(id),
    FOREIGN KEY (started_by) REFERENCES users(id)
);
```

### TestQuestions Table (Many-to-Many)
```sql
CREATE TABLE test_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    order INTEGER NOT NULL,
    points FLOAT,  -- Override question points if specified
    FOREIGN KEY (test_id) REFERENCES tests(id),
    FOREIGN KEY (question_id) REFERENCES questions(id)
);
```

### Submissions Table
```sql
CREATE TABLE submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    live_session_id INTEGER,  -- Set for live-mode attempts
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    submitted_at DATETIME,
    status VARCHAR(50) DEFAULT 'not_started',  -- 'not_started', 'in_progress', 'submitted', 'graded'
    FOREIGN KEY (test_id) REFERENCES tests(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (live_session_id) REFERENCES live_sessions(id)
);
```

### Answers Table
```sql
CREATE TABLE answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    answer_text TEXT,  -- For multiple choice and text questions
    code TEXT,  -- For code questions
    diagram_data TEXT,  -- Base64 or JSON for diagram questions
    score FLOAT,  -- Points awarded
    feedback TEXT,  -- Feedback from lecturer
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submission_id) REFERENCES submissions(id),
    FOREIGN KEY (question_id) REFERENCES questions(id)
);
```

### Grades Table
```sql
CREATE TABLE grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER UNIQUE NOT NULL,
    total_score FLOAT NOT NULL,
    max_score FLOAT NOT NULL,
    percentage FLOAT NOT NULL,
    graded_by INTEGER,  -- Lecturer user ID
    graded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submission_id) REFERENCES submissions(id),
    FOREIGN KEY (graded_by) REFERENCES users(id)
);
```

## Question Type Formats

### Multiple Choice
```json
{
  "type": "multiple_choice",
  "content": "What is 2 + 2?",
  "correct_answer": "{\"choices\": [\"3\", \"4\", \"5\", \"6\"], \"correct\": \"4\"}",
  "points": 1.0
}
```

### Code
```json
{
  "type": "code",
  "content": "Write a function to calculate the square of a number",
  "test_cases": [
    {"input": "5", "output": "25"},
    {"input": "10", "output": "100"}
  ],
  "points": 5.0
}
```

### Diagram
```json
{
  "type": "diagram",
  "content": "Draw a flowchart for a login process",
  "points": 10.0
}
```

### Text
```json
{
  "type": "text",
  "content": "Explain the concept of recursion",
  "points": 5.0
}
```

## Code Execution Details

### Safety Measures
- Subprocess execution with resource limits
- Timeout: 5 seconds (configurable)
- Memory limit: 128 MB (configurable)
- Process isolation

### Test Case Format
```python
test_cases = [
    {
        "input": "5",  # Input as string
        "output": "25"  # Expected output as string
    }
]
```

### Execution Flow
1. Student submits code
2. Code is executed with each test case
3. Output is compared with expected output
4. Score calculated: (passed_tests / total_tests) * points
5. Feedback includes which test cases passed/failed

## Session Management

### Flask Session Configuration
```python
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
app.config['SESSION_COOKIE_NAME'] = 'assessment_session'
```

### Session Data
- `user_id`: Current user's ID
- `role`: User's role ('lecturer' or 'student')
- `username`: Username for display

### Desktop App Session Handling
- Uses `requests.Session()` to maintain cookies
- Cookies automatically sent with each request
- Session persists across API calls

## Error Handling

### Common Errors and Solutions

1. **401 Unauthorized**
   - Cause: Session expired or not authenticated
   - Solution: Re-login

2. **403 Forbidden**
   - Cause: Insufficient permissions (e.g., student trying lecturer action)
   - Solution: Check user role

3. **404 Not Found**
   - Cause: Resource doesn't exist
   - Solution: Verify ID exists

4. **500 Internal Server Error**
   - Cause: Server-side error
   - Solution: Check server logs, database connection

## Security Considerations

### Current Implementation
- Password hashing with bcrypt
- Session-based authentication
- Role-based access control
- SQL injection prevention (SQLAlchemy ORM)
- CORS configuration for desktop apps

### Production Recommendations
- Use HTTPS for web interface
- Implement rate limiting
- Add input validation and sanitization
- Implement audit logging
- Regular security updates
- Database encryption at rest
- Stronger code execution sandboxing

## Performance Considerations

### Database
- SQLite suitable for small to medium deployments
- Indexes on foreign keys and frequently queried fields
- Consider PostgreSQL for larger deployments

### Code Execution
- Timeout prevents infinite loops
- Memory limits prevent resource exhaustion
- Subprocess isolation prevents system crashes

### Caching Opportunities
- Test questions (rarely change)
- Statistics calculations
- User session data

## Testing Recommendations

### Unit Tests
- API endpoint handlers
- Code execution service
- Auto-grading logic
- Database models

### Integration Tests
- Authentication flow
- Test creation and submission
- Grading workflow
- Statistics calculation

### Manual Testing Checklist
- [ ] Login/logout for both roles (web and desktop)
- [ ] Lecturer web dashboard (all tabs)
- [ ] Create and edit questions
- [ ] Create tests (scheduled and live modes)
- [ ] Composite questions (multiple answer types on one question)
- [ ] Student test navigation (Previous/Next, numbered sidebar)
- [ ] Scheduled test: availability window and per-student time limit
- [ ] Live test: Go Live, Extend, End; student locked/waiting states
- [ ] Auto-submit on deadline expiry
- [ ] Take test (web and desktop)
- [ ] Submit test
- [ ] Grade submissions
- [ ] View statistics
- [ ] Export reports

## Deployment Notes

### Local Network Setup
1. Ensure Flask server is accessible on network interface (0.0.0.0)
2. Configure firewall to allow port 5000
3. Students access via `http://<server-ip>:5000/login`
4. Lecturers access via `http://<server-ip>:5000/lecturer/login`
5. Desktop apps configured with server URL

### Database Backup
- SQLite database is single file: `database/assessment.db`
- Regular backups recommended
- Can be copied while server is running (SQLite handles concurrent reads)

### Scaling Considerations
- Current design: Single server, single database
- For larger deployments:
  - Use PostgreSQL instead of SQLite
  - Add load balancer for multiple Flask instances
  - Implement Redis for session storage
  - Use message queue for code execution

