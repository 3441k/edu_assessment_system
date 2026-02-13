"""Authentication routes."""

from flask import Blueprint, request, jsonify, session
from server.database import db_session
from server.models import User
from shared.constants import API_AUTH
import bcrypt

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
    
    # Check password
    if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({"error": "Invalid credentials"}), 401
    
    # For students, optionally verify student_id
    if user.role == 'student' and student_id and user.student_id != student_id:
        return jsonify({"error": "Invalid student ID"}), 401
    
    # Create session - Flask will automatically save it at the end of the request
    session.permanent = True
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    # Explicitly mark session as modified to ensure it's saved
    session.modified = True
    
    # Create response and ensure session is saved
    response = jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "student_id": user.student_id
        }
    })
    
    # Ensure session cookie is included in response
    return response, 200


@bp.route('/logout', methods=['POST'])
def logout():
    """Logout endpoint."""
    session.clear()
    return jsonify({"message": "Logout successful"}), 200


@bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user information."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    user = db_session.query(User).filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "student_id": user.student_id
    }), 200


@bp.route('/register', methods=['POST'])
def register():
    """Register new student (lecturer only)."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    current_user = db_session.query(User).filter_by(id=user_id).first()
    if not current_user or current_user.role != 'lecturer':
        return jsonify({"error": "Only lecturers can register students"}), 403
    
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    student_id = data.get('student_id')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    # Check if username already exists
    existing = db_session.query(User).filter_by(username=username).first()
    if existing:
        return jsonify({"error": "Username already exists"}), 400
    
    # Check if student_id already exists (if provided)
    if student_id:
        existing_id = db_session.query(User).filter_by(student_id=student_id).first()
        if existing_id:
            return jsonify({"error": "Student ID already exists"}), 400
    
    # Create new student
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(
        username=username,
        password_hash=password_hash,
        role='student',
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

