"""Shared authentication helpers for API and web routes."""

from flask import jsonify, redirect, session, url_for

from server.database import db_session
from server.models import User
from shared.constants import ROLE_ADMIN, STAFF_ROLES


def get_session_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db_session.query(User).filter_by(id=user_id).first()


def is_staff(user):
    return user is not None and user.role in STAFF_ROLES


def is_admin(user):
    return user is not None and user.role == ROLE_ADMIN


def require_staff_api():
    """Require lecturer or admin (teaching / management operations)."""
    user = get_session_user()
    if not user:
        return None, jsonify({"error": "Not authenticated"}), 401
    if not is_staff(user):
        return None, jsonify({"error": "Only lecturers can perform this action"}), 403
    return user, None, None


def require_admin_api():
    """Require administrator (staff account management)."""
    user = get_session_user()
    if not user:
        return None, jsonify({"error": "Not authenticated"}), 401
    if not is_admin(user):
        return None, jsonify({"error": "Only administrators can perform this action"}), 403
    return user, None, None


def require_staff_web():
    user = get_session_user()
    if not user:
        return None, redirect(url_for('lecturer_web.login'))
    if not is_staff(user):
        return None, redirect(url_for('lecturer_web.login'))
    return user, None
