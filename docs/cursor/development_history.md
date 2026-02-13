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
- Updated `server/templates/login.html` JavaScript to check role and prevent lecturer login via web
**Files Changed**:
- `server/routes/web.py`
- `server/templates/login.html`

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
- [x] Lecturer login and logout
- [x] Student login (web and desktop)
- [x] Question creation (all types)
- [x] Test creation
- [x] Test taking (web and desktop)
- [x] Test submission
- [x] Grading workflow
- [x] Statistics viewing
- [x] Topic management
- [x] Student management

### Known Limitations
- Code execution sandbox could be more secure
- No real-time collaboration
- Limited diagram editing (web only)
- Statistics calculations could be optimized
- No automated test suite (manual testing only)

## Future Improvements

### Short Term
- Add more validation
- Improve error messages
- Add loading indicators
- Better mobile responsiveness for web interface

### Medium Term
- Automated test suite
- Performance optimization
- Enhanced security
- Better code execution sandbox

### Long Term
- Real-time features
- Mobile app
- Advanced analytics
- Integration with LMS systems

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

