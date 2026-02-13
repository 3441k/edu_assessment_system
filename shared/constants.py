"""Shared constants and configuration for the assessment system."""

# Question Types
QUESTION_TYPE_MULTIPLE_CHOICE = "multiple_choice"
QUESTION_TYPE_CODE = "code"
QUESTION_TYPE_DIAGRAM = "diagram"
QUESTION_TYPE_TEXT = "text"

QUESTION_TYPES = [
    QUESTION_TYPE_MULTIPLE_CHOICE,
    QUESTION_TYPE_CODE,
    QUESTION_TYPE_DIAGRAM,
    QUESTION_TYPE_TEXT,
]

# User Roles
ROLE_LECTURER = "lecturer"
ROLE_STUDENT = "student"

# Submission Status
SUBMISSION_STATUS_NOT_STARTED = "not_started"
SUBMISSION_STATUS_IN_PROGRESS = "in_progress"
SUBMISSION_STATUS_SUBMITTED = "submitted"
SUBMISSION_STATUS_GRADED = "graded"

# API Endpoints
API_BASE = "/api/v1"
API_AUTH = f"{API_BASE}/auth"
API_TESTS = f"{API_BASE}/tests"
API_QUESTIONS = f"{API_BASE}/questions"
API_SUBMISSIONS = f"{API_BASE}/submissions"
API_GRADING = f"{API_BASE}/grading"
API_STATISTICS = f"{API_BASE}/statistics"
API_STUDENTS = f"{API_BASE}/students"
API_TOPICS = f"{API_BASE}/topics"

# Default Configuration
DEFAULT_SERVER_HOST = "0.0.0.0"
DEFAULT_SERVER_PORT = 5000
DEFAULT_DB_PATH = "database/assessment.db"
DEFAULT_CODE_TIMEOUT = 5
DEFAULT_CODE_MEMORY_LIMIT = 128  # MB
DEFAULT_SESSION_TIMEOUT = 3600  # seconds

