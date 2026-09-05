"""Student management routes."""

from flask import Blueprint, request, jsonify, session
from server.database import db_session
from server.models import User, Group
from shared.constants import API_STUDENTS, GROUP_UNASSIGNED_ID, ROLE_STUDENT
import bcrypt
import csv
import io

bp = Blueprint('students', __name__, url_prefix=API_STUDENTS)


def require_lecturer():
    user_id = session.get('user_id')
    if not user_id:
        return None, jsonify({"error": "Not authenticated"}), 401

    user = db_session.query(User).filter_by(id=user_id).first()
    if not user or user.role != 'lecturer':
        return None, jsonify({"error": "Only lecturers can perform this action"}), 403

    return user, None, None


def _resolve_group_id(raw):
    if raw is None or raw == '':
        return None
    if raw == GROUP_UNASSIGNED_ID or raw == '0':
        return None
    group = db_session.query(Group).filter_by(id=int(raw)).first()
    if not group:
        raise ValueError("Group not found")
    return group.id


def _get_or_create_group_by_name(name):
    name = (name or '').strip()
    if not name:
        return None
    if name.lower() == 'unassigned':
        return None
    group = db_session.query(Group).filter_by(name=name).first()
    if not group:
        group = Group(name=name)
        db_session.add(group)
        db_session.flush()
    return group.id


def _serialize_student(student):
    return {
        "id": student.id,
        "username": student.username,
        "student_id": student.student_id,
        "group_id": student.group_id,
        "group_name": student.group.name if student.group else "Unassigned",
        "created_at": student.created_at.isoformat() if student.created_at else None,
    }


@bp.route('', methods=['GET'])
def get_students():
    """Get all students; optional group_id filter (0 = unassigned)."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    group_filter = request.args.get('group_id')
    q = db_session.query(User).filter_by(role=ROLE_STUDENT)

    if group_filter is not None and group_filter != '':
        if str(group_filter) in ('0', str(GROUP_UNASSIGNED_ID)):
            q = q.filter(User.group_id.is_(None))
        else:
            q = q.filter_by(group_id=int(group_filter))

    students = q.order_by(User.username).all()
    return jsonify([_serialize_student(s) for s in students]), 200


@bp.route('', methods=['POST'])
def create_student():
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    student_id = data.get('student_id')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    existing = db_session.query(User).filter_by(username=username).first()
    if existing:
        return jsonify({"error": "Username already exists"}), 400

    if student_id:
        existing_id = db_session.query(User).filter_by(student_id=student_id).first()
        if existing_id:
            return jsonify({"error": "Student ID already exists"}), 400

    group_id = None
    if 'group_id' in data and data.get('group_id') not in (None, '', GROUP_UNASSIGNED_ID, '0'):
        try:
            group_id = _resolve_group_id(data.get('group_id'))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    student = User(
        username=username,
        password_hash=password_hash,
        role=ROLE_STUDENT,
        student_id=student_id,
        group_id=group_id,
    )

    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    return jsonify(_serialize_student(student)), 201


@bp.route('/import', methods=['POST'])
def import_students():
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

    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.DictReader(stream)

    imported = []
    errors = []

    for idx, row in enumerate(csv_input, start=2):
        username = row.get('username', '').strip()
        password = row.get('password', '').strip()
        student_id = row.get('student_id', '').strip() or None
        group_name = row.get('group', '').strip()

        if not username or not password:
            errors.append(f"Row {idx}: Username and password are required")
            continue

        existing = db_session.query(User).filter_by(username=username).first()
        if existing:
            errors.append(f"Row {idx}: Username '{username}' already exists")
            continue

        if student_id:
            existing_id = db_session.query(User).filter_by(student_id=student_id).first()
            if existing_id:
                errors.append(f"Row {idx}: Student ID '{student_id}' already exists")
                continue

        try:
            group_id = _get_or_create_group_by_name(group_name) if group_name else None
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            student = User(
                username=username,
                password_hash=password_hash,
                role=ROLE_STUDENT,
                student_id=student_id,
                group_id=group_id,
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
        "error_messages": errors,
    }), 200


@bp.route('/<int:student_id>', methods=['GET'])
def get_student(student_id):
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    student = db_session.query(User).filter_by(id=student_id, role=ROLE_STUDENT).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    return jsonify(_serialize_student(student)), 200


@bp.route('/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    student = db_session.query(User).filter_by(id=student_id, role=ROLE_STUDENT).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    data = request.get_json() or {}
    if 'username' in data:
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

    if 'group_id' in data:
        raw = data.get('group_id')
        if raw in (None, '', GROUP_UNASSIGNED_ID, '0'):
            student.group_id = None
        else:
            try:
                student.group_id = _resolve_group_id(raw)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400

    db_session.commit()
    db_session.refresh(student)

    return jsonify(_serialize_student(student)), 200


@bp.route('/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    student = db_session.query(User).filter_by(id=student_id, role=ROLE_STUDENT).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    db_session.delete(student)
    db_session.commit()

    return jsonify({"message": "Student deleted successfully"}), 200
