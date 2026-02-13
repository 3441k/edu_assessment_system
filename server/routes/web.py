"""Web routes for student interface."""

from flask import Blueprint, render_template, redirect, url_for, session, request
from server.app import db_session
from server.models import User, Test, Submission

bp = Blueprint('web', __name__)


def require_student():
    """Check if user is a student."""
    user_id = session.get('user_id')
    if not user_id:
        return None, redirect(url_for('web.login'))
    
    user = db_session.query(User).filter_by(id=user_id).first()
    if not user or user.role != 'student':
        return None, redirect(url_for('web.login'))
    
    return user, None


@bp.route('/login')
def login():
    """Student login page."""
    if session.get('user_id'):
        return redirect(url_for('web.dashboard'))
    return render_template('login.html')


@bp.route('/logout')
def logout():
    """Logout and redirect to login."""
    session.clear()
    return redirect(url_for('web.login'))


@bp.route('/dashboard')
def dashboard():
    """Student dashboard."""
    user, redirect_response = require_student()
    if redirect_response:
        return redirect_response
    return render_template('dashboard.html')


@bp.route('/test/<int:test_id>')
def take_test(test_id):
    """Test taking page."""
    user, redirect_response = require_student()
    if redirect_response:
        return redirect_response
    
    test = db_session.query(Test).filter_by(id=test_id).first()
    if not test:
        return redirect(url_for('web.dashboard'))
    
    return render_template('test_taking.html', test_id=test_id)


@bp.route('/results/<int:submission_id>')
def view_results(submission_id):
    """View test results."""
    user, redirect_response = require_student()
    if redirect_response:
        return redirect_response
    
    submission = db_session.query(Submission).filter_by(id=submission_id).first()
    if not submission or submission.user_id != user.id:
        return redirect(url_for('web.dashboard'))
    
    return render_template('results.html', submission_id=submission_id)

