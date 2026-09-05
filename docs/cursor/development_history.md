# Development History & Key Fixes

## Development Timeline

### Initial Requirements Gathering
- User requested GUI tool for lecturers to check student knowledge
- Requirements for multiple question types
- Need for dual interfaces (student and lecturer)
- Local network deployment

### Architecture Decisions
- Chose Flask for backend (lightweight, Python-based)
- PyQt5 for desktop applications (cross-platform, native look)
- SQLite for database (simple, no server needed)
- Session-based authentication

### Implementation Phases

#### Phase 1: Core Backend
- Database models and schema
- Flask REST API structure
- Authentication system
- Basic CRUD operations

#### Phase 2: Lecturer Interface
- PyQt5 desktop application
- Question bank management
- Test creation
- Grading interface

#### Phase 3: Student Interfaces
- Web interface (Flask templates)
- Desktop application (PyQt5)
- Test taking functionality

#### Phase 4: Advanced Features
- Auto-grading for code questions
- Statistics and analytics
- Export functionality
- Topic management

#### Phase 5: Test Scheduling and Live Control
- Scheduled mode with availability windows and per-student deadlines
- Live mode with lecturer Go Live / Extend / End
- Auto-submit on deadline expiry
- Web UI for live controls and student locked/waiting states
- Database migration script for existing installations

#### Phase 6: Composite Questions and UX
- Combined answer types on single questions (web question bank)
- Student test wizard UI with Previous/Next and numbered navigation
- Auto-submit and grading reliability fixes

#### Phase 7: Student Results Access
- Student submission API returns grades and per-question results
- Results page and dashboard View Results for closed scheduled tests

#### Phase 8: Lecturer Web Statistics Redesign
- Class overview with Chart.js bar/line charts
- Focus test picker, weak topics, all-tests summary on one screen
- Searchable/filterable test and student browse lists
- Drill-down: test statistics (distribution, question breakdown, student table) and student statistics (trend, per-test/per-question scores)
- Heavy linking to grading page from statistics rows

#### Phase 9: Student Groups
- One group per student; Unassigned shown as separate row in comparisons
- Groups tab + group picker on Students tab
- CSV import with optional `group` column
- Statistics group filter and Compare groups view

## Critical Issues and Fixes

### Issue 1: Circular Import Error
**Date**: Early development
**Error**: `AttributeError: partially initialized module 'server.routes.auth' has no attribute 'bp'`
**Root Cause**: `server/app.py` imported routes, routes imported `db_session` from `server/app.py`
**Solution**: Created `server/database.py` to centralize database initialization
**Files Changed**:
- Created `server/database.py`
- Updated `server/app.py` to import from `server.database`
- Updated all route files to import from `server.database`

### Issue 2: Module Not Found Error
**Date**: Early development
**Error**: `ModuleNotFoundError: No module named 'server'`
**Root Cause**: Project root not in Python path when running scripts directly
**Solution**: 
- Added project root to `sys.path` in `server/app.py`
- Created run scripts (`run_server.py`, `run_lecturer.py`, `run_student.py`) that add project root to path
**Files Changed**:
- `server/app.py`
- Created `run_server.py`, `run_lecturer.py`, `run_student.py`

### Issue 3: Database Not Initialized
**Date**: Early development
**Error**: `sqlalchemy.exc.OperationalError: no such table: users`
**Root Cause**: Database file existed but was empty (no tables created)
**Solution**: Run `python database/init_db.py` to initialize schema
**Documentation**: Added to README.md setup instructions

### Issue 4: Firefox Redirect Loop
**Date**: Mid development
**Error**: `Firefox has detected that the server is redirecting the request in a way that will never complete`
**Root Cause**: Default admin user is lecturer, but web login redirected all users to student dashboard, which then redirected lecturers back to login
**Solution**:
- Modified `server/routes/web.py` to check role and show error for lecturers
- Updated `server/templates/login.html` JavaScript to check role and redirect lecturers to `/lecturer/login`
**Files Changed**:
- `server/routes/web.py`
- `server/templates/login.html`
**Note**: Later superseded by dedicated lecturer web interface at `/lecturer/login` (see Feature: Lecturer Web Interface below).

### Issue 5: Session Not Persisting (Web)
**Date**: Mid development
**Error**: `Failed to load tests: API request failed: 401 Client Error: UNAUTHORIZED`
**Root Cause**: Flask session cookie not being set or persisted
**Solution**:
- Configured `SESSION_COOKIE_PATH = '/'`
- Set `PERMANENT_SESSION_LIFETIME = 86400`
- Explicitly set `session.permanent = True` after login
- Simplified CORS configuration
**Files Changed**:
- `server/app.py`
- `server/routes/auth.py`

### Issue 6: Session Not Persisting (Desktop)
**Date**: Mid development
**Error**: `Failed to load tests: API request failed: 401 Client Error: UNAUTHORIZED` (lecturer desktop app)
**Root Cause**: `MainWindow` created new `LecturerAPIClient` instance, losing authenticated session
**Solution**: Pass authenticated `api_client` instance from `LecturerLoginWindow` to `MainWindow`
**Files Changed**:
- `lecturer_app/windows/login_window.py`
- `lecturer_app/windows/main_window.py`

### Issue 7: Multiple Choice Choices Not Saving
**Date**: Mid development
**Error**: Choices entered in lecturer app disappeared after saving, not visible when editing
**Root Cause**: Choices were not being saved to database, only `correct_answer` text was saved
**Solution**:
- Store choices as JSON in `correct_answer` field: `{"choices": [...], "correct": "..."}`
- Parse JSON when loading for editing
- Update web interface to parse new format
**Files Changed**:
- `lecturer_app/windows/question_bank.py`
- `server/templates/test_taking.html`
- `server/routes/tests.py` (added `correct_answer` to response)

### Issue 8: Missing manage_topics Method
**Date**: Mid development
**Error**: `'QuestionBankWindow' object has no attribute 'manage_topics'`
**Root Cause**: Button connected to method that didn't exist
**Solution**: Added `manage_topics()` method to `QuestionBankWindow`
**Files Changed**:
- `lecturer_app/windows/question_bank.py`

### Issue 9: Grading Window NoneType Error
**Date**: Mid development
**Error**: `setValue(self, val: float): argument 1 has unexpected type 'NoneType'`
**Root Cause**: Ungraded answers have `score = None`, but `QDoubleSpinBox.setValue()` expects float
**Solution**: Explicit None checking and defaulting to 0.0
**Files Changed**:
- `lecturer_app/windows/grading_window.py`

### Issue 10: Template Variable Error
**Date**: Late development
**Error**: `Property assignment expected` in JavaScript
**Root Cause**: `{{ test_id }}` might render as invalid JavaScript if None or wrong type
**Solution**: Use `{{ test_id|tojson }}` to safely convert to JavaScript
**Files Changed**:
- `server/templates/test_taking.html`

### Issue 11: Statistics Import Error
**Date**: Late development
**Error**: `NameError: name 'User' is not defined`
**Root Cause**: `User` model imported inside function but used at module level
**Solution**: Added `User` to module-level imports
**Files Changed**:
- `server/routes/statistics.py`

## Feature: Lecturer Web Interface

**Date**: September 2026
**Request**: Add web-based lecturer control alongside the existing PyQt5 desktop app

**Implementation**:
- Created `server/routes/lecturer_web.py` with routes under `/lecturer`
- Added templates in `server/templates/lecturer/` (login, dashboard, grading)
- Added `server/static/js/lecturer.js` for API-driven dashboard UI
- Registered blueprint in `server/app.py`
- Updated student login page with link to lecturer login

**Capabilities** (parity with desktop app):
- Question bank management (topics, CRUD for all question types)
- Test creation and editing
- Submission grading with score/feedback and finalize
- Statistics (overview, by topic, by student, by test)
- Student management (add, delete, CSV import)

**Design**:
- Both lecturer interfaces (web and desktop) use the same REST API
- Server-side `require_lecturer()` guards on API endpoints unchanged
- Web pages use Flask session cookies via `fetch(..., { credentials: 'include' })`

**Files Added/Changed**:
- Created `server/routes/lecturer_web.py`
- Created `server/templates/lecturer/login.html`, `dashboard.html`, `grading.html`
- Created `server/static/js/lecturer.js`
- Updated `server/app.py`, `server/templates/login.html`, `README.md`, `QUICKSTART.md`

## Feature: Lecturer Web Statistics Redesign

**Date**: September 2026
**Request**: Improve statistics UX — class overview with charts, search/filters for tests, drill-down into student and test statistics, links to grading

**Implementation**:
- Extended `server/routes/statistics.py` with overview enrichment, filtered test list, student/test drill-down endpoints
- Rewrote Statistics tab in `server/static/js/lecturer.js` with breadcrumb navigation and Chart.js charts
- Updated `server/templates/lecturer/dashboard.html` (Chart.js CDN, stats toolbar/breadcrumb)

**Capabilities**:
- Class overview: summary cards, average-by-test chart, focus-test distribution, weak topics
- Browse tests: search, mode/status filters, sort; click through to test statistics
- Browse students: search; click through to student statistics and per-test score summary
- Grade links from student rows in statistics views

**Files Changed**:
- `server/routes/statistics.py`
- `server/static/js/lecturer.js`
- `server/templates/lecturer/dashboard.html`
- `README.md`, `QUICKSTART.md`, `docs/cursor/*`

## Feature: Student Groups

**Date**: September 2026
**Request**: Students belong to groups; manage groups in UI; compare group results by test; Unassigned as separate comparison row

**Implementation**:
- Added `Group` model, `users.group_id`, migration in `database/migrate.py`
- Created `server/routes/groups.py`; extended students and statistics routes
- Groups tab, student group assignment/edit, CSV import with `group` column
- Statistics group filter and Compare groups view in `lecturer.js`
- Fixed stray braces in `lecturer.js` that broke dashboard initialization

**Files Changed**:
- `server/models.py`, `database/migrate.py`, `shared/constants.py`, `server/app.py`
- `server/routes/groups.py`, `server/routes/students.py`, `server/routes/statistics.py`
- `server/static/js/lecturer.js`, `server/templates/lecturer/dashboard.html`
- `README.md`, `QUICKSTART.md`, `docs/cursor/*`

## Feature: Production Server and SQLite WAL

**Date**: September 2026
**Request**: Support ~11 simultaneous users on a local classroom server

**Implementation**:
- Added `run_server_production.py` using Waitress (configurable `SERVER_THREADS`)
- Enabled SQLite WAL mode and `busy_timeout` in `database/migrate.py` and `server/database.py`
- Documented deployment, capacity, and troubleshooting in README and QUICKSTART

**Files Changed**:
- `run_server_production.py`, `requirements.txt`, `server/database.py`, `database/migrate.py`
- `README.md`, `QUICKSTART.md`, `docs/cursor/*`

## UI/UX Improvements

### Login Window Redesign
- Added gradient background
- Improved spacing between elements
- Better visual hierarchy
- Modern, professional appearance
- Increased window size for better spacing

### Question Bank Enhancements
- Added topic management dialog
- Improved question editing interface
- Better validation for multiple choice questions
- Clearer error messages

### Grading Interface
- Better handling of ungraded answers
- Improved question card layout
- Auto-grading button for code questions
- Clear feedback areas

## Code Quality Improvements

### Refactoring
- Extracted database initialization to separate module
- Created shared API client base class
- Centralized constants
- Improved error handling

### Documentation
- Added comprehensive README
- Created QUICKSTART guide
- Added inline code comments
- Created this documentation folder

## Testing and Validation

### Manual Testing Performed
- [x] Lecturer login and logout (web and desktop)
- [x] Student login (web and desktop)
- [x] Question creation (all types)
- [x] Test creation
- [x] Test taking (web and desktop)
- [x] Test submission
- [x] Grading workflow
- [x] Statistics viewing
- [x] Topic management
- [x] Student management
- [x] Lecturer web dashboard (all tabs)
- [x] Lecturer web grading workflow
- [x] Scheduled test availability and auto-submit
- [x] Live test Go Live / Extend / End workflow (web)
- [x] Composite question types and student test navigation UI
- [x] Auto-submit on timeout (idempotent submit endpoint)
- [x] Grading score validation with clear error messages
- [x] Student results viewing for graded scheduled and live tests
- [x] Lecturer web statistics redesign (overview charts, filters, drill-down, grading links)
- [x] Student groups (Groups tab, CSV import, compare groups in statistics)

### Known Limitations
- Code execution sandbox could be more secure
- Live session controls (Go Live / Extend / End) are web-only; desktop app supports scheduled fields only
- Limited diagram editing (web only)
- Statistics calculations could be optimized
- No automated test suite (manual testing only)

## Future Improvements

### Short Term
- Add more validation
- Improve error messages
- Add loading indicators
- Better mobile responsiveness for web interfaces
- PDF/CSV export from lecturer web statistics tab

### Medium Term
- Automated test suite
- Performance optimization
- Enhanced security
- Better code execution sandbox

### Long Term
- Mobile app
- Advanced analytics
- Integration with LMS systems
- Live controls in lecturer desktop app

## Lessons Learned

1. **Circular Imports**: Always centralize shared resources (like database session)
2. **Session Management**: Flask sessions need explicit configuration for persistence
3. **Desktop App Sessions**: Share authenticated client instances, don't create new ones
4. **Template Variables**: Always use `|tojson` filter for JavaScript variables
5. **None Handling**: Always check for None before using values in UI components
6. **User Experience**: Spacing and visual hierarchy are crucial for usability

## Development Environment

### Python Version
- Python 3.12.0 (specified by user)
- Path: `/home/hlnb/.pyenv/versions/3.12.0/bin/python3.12`

### Key Tools
- Flask for backend
- PyQt5 for desktop apps
- SQLAlchemy for ORM
- Jinja2 for templating

### Project Structure
- Modular design with clear separation of concerns
- Shared code in `shared/` directory
- Separate apps for lecturer and student
- Centralized server with REST API

