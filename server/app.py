"""Main Flask application."""

import os
import sys
from pathlib import Path

# Add project root to Python path if running directly
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from flask import Flask, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
from server.database import db_session, DATABASE_PATH

load_dotenv()

# Configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 5000))

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow cookies for localhost
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours in seconds

# Enable CORS for local network access
# For same-origin requests (web interface from same server), CORS isn't needed
# But we enable it for API access from desktop apps or other origins
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000", "http://0.0.0.0:5000", "*"],
        "supports_credentials": True,
        "allow_headers": ["Content-Type"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    }
}, supports_credentials=True, expose_headers=["Content-Type"])


@app.teardown_appcontext
def shutdown_session(exception=None):
    """Remove database session after request."""
    db_session.remove()


# Import and register routes
from server.routes import auth, tests, questions, submissions, grading, statistics, students, topics, web

app.register_blueprint(auth.bp)
app.register_blueprint(tests.bp)
app.register_blueprint(questions.bp)
app.register_blueprint(submissions.bp)
app.register_blueprint(grading.bp)
app.register_blueprint(statistics.bp)
app.register_blueprint(students.bp)
app.register_blueprint(topics.bp)
app.register_blueprint(web.bp)


@app.route('/')
def index():
    """Root endpoint - redirect to student login."""
    return redirect(url_for('web.login'))


@app.route('/api')
def api_info():
    """API information endpoint."""
    return {
        "message": "Educational Assessment System API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/v1/auth",
            "tests": "/api/v1/tests",
            "questions": "/api/v1/questions",
            "submissions": "/api/v1/submissions",
            "grading": "/api/v1/grading",
            "statistics": "/api/v1/statistics",
            "students": "/api/v1/students",
            "topics": "/api/v1/topics"
        }
    }


if __name__ == "__main__":
    print(f"Starting server on {SERVER_HOST}:{SERVER_PORT}")
    print(f"Database: {DATABASE_PATH}")
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=True)

