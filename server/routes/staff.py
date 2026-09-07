"""Staff (lecturer/admin) account management — admin only."""

import bcrypt
from flask import Blueprint, jsonify, request

from server.auth_helpers import require_admin_api
from server.database import db_session
from server.models import User
from shared.constants import API_STAFF, ROLE_ADMIN, ROLE_LECTURER, STAFF_ROLES

bp = Blueprint('staff', __name__, url_prefix=API_STAFF)


def _serialize_staff(user):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _admin_count():
    return db_session.query(User).filter_by(role=ROLE_ADMIN).count()


@bp.route('', methods=['GET'])
def list_staff():
    user, error_response, status = require_admin_api()
    if error_response:
        return error_response, status

    staff = (
        db_session.query(User)
        .filter(User.role.in_(STAFF_ROLES))
        .order_by(User.username)
        .all()
    )
    return jsonify([_serialize_staff(s) for s in staff]), 200


@bp.route('', methods=['POST'])
def create_staff():
    user, error_response, status = require_admin_api()
    if error_response:
        return error_response, status

    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    role = data.get('role') or ROLE_LECTURER

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    if role not in (ROLE_LECTURER, ROLE_ADMIN):
        return jsonify({"error": "Role must be lecturer or admin"}), 400

    existing = db_session.query(User).filter_by(username=username).first()
    if existing:
        return jsonify({"error": "Username already exists"}), 400

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(username=username, password_hash=password_hash, role=role)
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)

    return jsonify(_serialize_staff(new_user)), 201


@bp.route('/<int:staff_id>', methods=['PUT'])
def update_staff(staff_id):
    user, error_response, status = require_admin_api()
    if error_response:
        return error_response, status

    staff = db_session.query(User).filter(User.id == staff_id, User.role.in_(STAFF_ROLES)).first()
    if not staff:
        return jsonify({"error": "Staff member not found"}), 404

    data = request.get_json() or {}

    if 'username' in data:
        username = (data.get('username') or '').strip()
        if not username:
            return jsonify({"error": "Username is required"}), 400
        existing = db_session.query(User).filter_by(username=username).first()
        if existing and existing.id != staff_id:
            return jsonify({"error": "Username already exists"}), 400
        staff.username = username

    if 'password' in data and data['password']:
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        staff.password_hash = password_hash

    if 'role' in data:
        new_role = data.get('role')
        if new_role not in (ROLE_LECTURER, ROLE_ADMIN):
            return jsonify({"error": "Role must be lecturer or admin"}), 400
        if staff.role == ROLE_ADMIN and new_role == ROLE_LECTURER and _admin_count() <= 1:
            return jsonify({"error": "Cannot demote the last administrator"}), 400
        staff.role = new_role

    db_session.commit()
    db_session.refresh(staff)

    if staff.id == user.id:
        from flask import session
        session['username'] = staff.username
        session['role'] = staff.role
        session.modified = True

    return jsonify(_serialize_staff(staff)), 200


@bp.route('/<int:staff_id>', methods=['DELETE'])
def delete_staff(staff_id):
    user, error_response, status = require_admin_api()
    if error_response:
        return error_response, status

    if staff_id == user.id:
        return jsonify({"error": "You cannot delete your own account"}), 400

    staff = db_session.query(User).filter(User.id == staff_id, User.role.in_(STAFF_ROLES)).first()
    if not staff:
        return jsonify({"error": "Staff member not found"}), 404

    if staff.role == ROLE_ADMIN and _admin_count() <= 1:
        return jsonify({"error": "Cannot delete the last administrator"}), 400

    db_session.delete(staff)
    db_session.commit()

    return jsonify({"message": "Staff member deleted successfully"}), 200
