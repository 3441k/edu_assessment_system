"""Student management routes."""

from flask import Blueprint, request, jsonify, session
from server.database import db_session
from server.models import User
from shared.constants import API_STUDENTS
import bcrypt
import csv
import io

bp = Blueprint('students', __name__, url_prefix=API_STUDENTS)


def require_lecturer():
    """Check if user is a lecturer."""
    user_id = session.get('user_id')
    if not user_id:
        return None, jsonify({"error": "Not authenticated"}), 401
    
    user = db_session.query(User).filter_by(id=user_id).first()
    if not user or user.role != 'lecturer':
        return None, jsonify({"error": "Only lecturers can perform this action"}), 403
    
    return user, None, None


@bp.route('', methods=['GET'])
def get_students():
    """Get all students."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    students = db_session.query(User).filter_by(role='student').order_by(User.username).all()
    
    return jsonify([{
        "id": s.id,
        "username": s.username,
        "student_id": s.student_id,
        "created_at": s.created_at.isoformat() if s.created_at else None
    } for s in students]), 200


@bp.route('', methods=['POST'])
def create_student():
    """Create a new student."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    student_id = data.get('student_id')
    
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    # Check if username exists
    existing = db_session.query(User).filter_by(username=username).first()
    if existing:
        return jsonify({"error": "Username already exists"}), 400
    
    # Check if student_id exists (if provided)
    if student_id:
        existing_id = db_session.query(User).filter_by(student_id=student_id).first()
        if existing_id:
            return jsonify({"error": "Student ID already exists"}), 400
    
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    student = User(
        username=username,
        password_hash=password_hash,
        role='student',
        student_id=student_id
    )
    
    db_session.add(student)
    db_session.commit()
    
    return jsonify({
        "id": student.id,
        "username": student.username,
        "student_id": student.student_id
    }), 201


@bp.route('/import', methods=['POST'])
def import_students():
    """Import students from CSV."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "File must be a CSV"}), 400
    
    # Read CSV
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.DictReader(stream)
    
    imported = []
    errors = []
    
    for idx, row in enumerate(csv_input, start=2):  # Start at 2 (row 1 is header)
        username = row.get('username', '').strip()
        password = row.get('password', '').strip()
        student_id = row.get('student_id', '').strip() or None
        
        if not username or not password:
            errors.append(f"Row {idx}: Username and password are required")
            continue
        
        # Check if username exists
        existing = db_session.query(User).filter_by(username=username).first()
        if existing:
            errors.append(f"Row {idx}: Username '{username}' already exists")
            continue
        
        # Check if student_id exists (if provided)
        if student_id:
            existing_id = db_session.query(User).filter_by(student_id=student_id).first()
            if existing_id:
                errors.append(f"Row {idx}: Student ID '{student_id}' already exists")
                continue
        
        try:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            student = User(
                username=username,
                password_hash=password_hash,
                role='student',
                student_id=student_id
            )
            db_session.add(student)
            imported.append(username)
        except Exception as e:
            errors.append(f"Row {idx}: Error creating student - {str(e)}")
    
    db_session.commit()
    
    return jsonify({
        "imported": len(imported),
        "errors": len(errors),
        "imported_users": imported,
        "error_messages": errors
    }), 200


@bp.route('/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """Get a specific student."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    student = db_session.query(User).filter_by(id=student_id, role='student').first()
    if not student:
        return jsonify({"error": "Student not found"}), 404
    
    return jsonify({
        "id": student.id,
        "username": student.username,
        "student_id": student.student_id,
        "created_at": student.created_at.isoformat() if student.created_at else None
    }), 200


@bp.route('/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    """Update a student."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    student = db_session.query(User).filter_by(id=student_id, role='student').first()
    if not student:
        return jsonify({"error": "Student not found"}), 404
    
    data = request.get_json()
    if 'username' in data:
        # Check if new username exists
        existing = db_session.query(User).filter_by(username=data['username']).first()
        if existing and existing.id != student_id:
            return jsonify({"error": "Username already exists"}), 400
        student.username = data['username']
    
    if 'password' in data and data['password']:
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        student.password_hash = password_hash
    
    if 'student_id' in data:
        new_student_id = data['student_id'] or None
        if new_student_id:
            existing_id = db_session.query(User).filter_by(student_id=new_student_id).first()
            if existing_id and existing_id.id != student_id:
                return jsonify({"error": "Student ID already exists"}), 400
        student.student_id = new_student_id
    
    db_session.commit()
    
    return jsonify({
        "id": student.id,
        "username": student.username,
        "student_id": student.student_id
    }), 200


@bp.route('/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Delete a student."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    student = db_session.query(User).filter_by(id=student_id, role='student').first()
    if not student:
        return jsonify({"error": "Student not found"}), 404
    
    db_session.delete(student)
    db_session.commit()
    
    return jsonify({"message": "Student deleted successfully"}), 200

