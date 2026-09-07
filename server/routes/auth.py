"""Authentication routes."""

import bcrypt
from flask import Blueprint, jsonify, request, session

from server.auth_helpers import get_session_user, is_staff, require_admin_api
from server.database import db_session
from server.models import User
from shared.constants import API_AUTH, ROLE_STUDENT

bp = Blueprint('auth', __name__, url_prefix=API_AUTH)


@bp.route('/login', methods=['POST'])
def login():
    """Login endpoint."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    student_id = data.get('student_id')  # Optional for students

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = db_session.query(User).filter_by(username=username).first()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({"error": "Invalid credentials"}), 401

    if user.role == ROLE_STUDENT and student_id and user.student_id != student_id:
        return jsonify({"error": "Invalid student ID"}), 401

    session.permanent = True
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session.modified = True

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "student_id": user.student_id
        }
    }), 200


@bp.route('/logout', methods=['POST'])
def logout():
    """Logout endpoint."""
    session.clear()
    return jsonify({"message": "Logout successful"}), 200


@bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user information."""
    user = get_session_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    return jsonify({
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "student_id": user.student_id
    }), 200


@bp.route('/change-password', methods=['POST'])
def change_password():
    """Change the logged-in administrator's password."""
    user, error_response, status = require_admin_api()
    if error_response:
        return error_response, status

    data = request.get_json() or {}
    current_password = data.get('current_password') or ''
    new_password = data.get('new_password') or ''

    if not current_password or not new_password:
        return jsonify({"error": "Current and new password are required"}), 400
    if len(new_password) < 4:
        return jsonify({"error": "New password must be at least 4 characters"}), 400

    if not bcrypt.checkpw(current_password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({"error": "Current password is incorrect"}), 400

    user.password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db_session.commit()

    return jsonify({"message": "Password changed successfully"}), 200


@bp.route('/register', methods=['POST'])
def register():
    """Register new student (staff only)."""
    current_user = get_session_user()
    if not current_user:
        return jsonify({"error": "Not authenticated"}), 401
    if not is_staff(current_user):
        return jsonify({"error": "Only lecturers can register students"}), 403

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    student_id = data.get('student_id')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    existing = db_session.query(User).filter_by(username=username).first()
    if existing:
        return jsonify({"error": "Username already exists"}), 400

    if student_id:
        existing_id = db_session.query(User).filter_by(student_id=student_id).first()
        if existing_id:
            return jsonify({"error": "Student ID already exists"}), 400

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(
        username=username,
        password_hash=password_hash,
        role=ROLE_STUDENT,
        student_id=student_id
    )

    db_session.add(new_user)
    db_session.commit()

    return jsonify({
        "message": "Student registered successfully",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "student_id": new_user.student_id
        }
    }), 201
