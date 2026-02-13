# Implementation Details

## API Endpoints

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

### Tests (`/api/v1/tests`)
- `GET /` - Get all tests
- `GET /<id>` - Get test with questions
- `POST /` - Create test (lecturer only)
- `PUT /<id>` - Update test (lecturer only)
- `DELETE /<id>` - Delete test (lecturer only)

### Submissions (`/api/v1/submissions`)
- `GET /` - Get user's submissions (optionally filtered by test_id)
- `GET /<id>` - Get submission details
- `POST /` - Create new submission
- `POST /<id>/answers` - Save answer for a question
- `POST /<id>/submit` - Submit test

### Grading (`/api/v1/grading`)
- `GET /submissions/<id>` - Get submission for grading (lecturer only)
- `PUT /answers/<id>` - Grade an answer (lecturer only)
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
    type VARCHAR(50) NOT NULL,  -- 'multiple_choice', 'code', 'diagram', 'text'
    content TEXT NOT NULL,
    correct_answer TEXT,  -- JSON for multiple choice, expected output for code
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
    time_limit INTEGER,  -- Minutes, NULL = no limit
    attempts_allowed INTEGER DEFAULT 1,
    available_from DATETIME,
    available_until DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    submitted_at DATETIME,
    status VARCHAR(50) DEFAULT 'not_started',  -- 'not_started', 'in_progress', 'submitted', 'graded'
    FOREIGN KEY (test_id) REFERENCES tests(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
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
- [ ] Login/logout for both roles
- [ ] Create and edit questions
- [ ] Create tests
- [ ] Take test (web and desktop)
- [ ] Submit test
- [ ] Grade submissions
- [ ] View statistics
- [ ] Export reports

## Deployment Notes

### Local Network Setup
1. Ensure Flask server is accessible on network interface (0.0.0.0)
2. Configure firewall to allow port 5000
3. Students access via `http://<server-ip>:5000`
4. Desktop apps configured with server URL

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

