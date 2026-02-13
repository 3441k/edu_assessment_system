"""Main Flask application."""

import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

load_dotenv()

# Configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 5000))
DATABASE_PATH = os.getenv("DATABASE_PATH", "database/assessment.db")

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Enable CORS for local network access
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Database setup
engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)
db_session = scoped_session(sessionmaker(bind=engine))


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
    """Root endpoint."""
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

