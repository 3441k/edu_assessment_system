"""Web routes for lecturer interface."""

from flask import Blueprint, render_template, redirect, url_for, session
from server.database import db_session
from server.models import User

bp = Blueprint('lecturer_web', __name__, url_prefix='/lecturer')


def require_lecturer():
    """Check if user is a lecturer."""
    user_id = session.get('user_id')
    if not user_id:
        return None, redirect(url_for('lecturer_web.login'))

    user = db_session.query(User).filter_by(id=user_id).first()
    if not user or user.role != 'lecturer':
        return None, redirect(url_for('lecturer_web.login'))

    return user, None


@bp.route('/login')
def login():
    """Lecturer login page."""
    user_id = session.get('user_id')
    if user_id:
        user = db_session.query(User).filter_by(id=user_id).first()
        if user and user.role == 'lecturer':
            return redirect(url_for('lecturer_web.dashboard'))
        session.clear()
    return render_template('lecturer/login.html')


@bp.route('/logout')
def logout():
    """Logout and redirect to lecturer login."""
    session.clear()
    return redirect(url_for('lecturer_web.login'))


@bp.route('/dashboard')
def dashboard():
    """Lecturer dashboard."""
    user, redirect_response = require_lecturer()
    if redirect_response:
        return redirect_response
    return render_template('lecturer/dashboard.html')


@bp.route('/grading/<int:submission_id>')
def grading(submission_id):
    """Grading page for a submission."""
    user, redirect_response = require_lecturer()
    if redirect_response:
        return redirect_response
    return render_template('lecturer/grading.html', submission_id=submission_id)
