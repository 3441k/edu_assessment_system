"""Student group management routes."""

from flask import Blueprint, request, jsonify, session
from server.database import db_session
from server.models import User, Group, Grade, Submission
from shared.constants import API_GROUPS, GROUP_UNASSIGNED_ID, ROLE_STUDENT

bp = Blueprint('groups', __name__, url_prefix=API_GROUPS)


def require_lecturer():
    user_id = session.get('user_id')
    if not user_id:
        return None, jsonify({"error": "Not authenticated"}), 401

    user = db_session.query(User).filter_by(id=user_id).first()
    if not user or user.role != 'lecturer':
        return None, jsonify({"error": "Only lecturers can manage groups"}), 403

    return user, None, None


def _group_average_percentage(student_ids):
    if not student_ids:
        return None
    grades = db_session.query(Grade).join(Submission).filter(
        Submission.user_id.in_(student_ids)
    ).all()
    if not grades:
        return None
    return round(sum(g.percentage for g in grades) / len(grades), 2)


def _serialize_group(group, student_count=None, average_percentage=None):
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "student_count": student_count,
        "average_percentage": average_percentage,
        "is_virtual": False,
        "created_at": group.created_at.isoformat() if group.created_at else None,
    }


def _unassigned_summary():
    students = db_session.query(User).filter_by(role=ROLE_STUDENT, group_id=None).all()
    if not students:
        return None
    ids = [s.id for s in students]
    return {
        "id": GROUP_UNASSIGNED_ID,
        "name": "Unassigned",
        "description": None,
        "student_count": len(students),
        "average_percentage": _group_average_percentage(ids),
        "is_virtual": True,
        "created_at": None,
    }


@bp.route('', methods=['GET'])
def list_groups():
    """List groups with student counts and average graded percentage."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    include_unassigned = request.args.get('include_unassigned', '1') != '0'
    result = []

    for group in db_session.query(Group).order_by(Group.name).all():
        students = db_session.query(User).filter_by(role=ROLE_STUDENT, group_id=group.id).all()
        ids = [s.id for s in students]
        result.append(_serialize_group(
            group,
            student_count=len(students),
            average_percentage=_group_average_percentage(ids),
        ))

    if include_unassigned:
        unassigned = _unassigned_summary()
        if unassigned:
            result.append(unassigned)

    return jsonify(result), 200


@bp.route('', methods=['POST'])
def create_group():
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip() or None

    if not name:
        return jsonify({"error": "Group name is required"}), 400
    if name.lower() == 'unassigned':
        return jsonify({"error": "Reserved group name"}), 400

    existing = db_session.query(Group).filter_by(name=name).first()
    if existing:
        return jsonify({"error": "Group name already exists"}), 400

    group = Group(name=name, description=description)
    db_session.add(group)
    db_session.commit()

    return jsonify(_serialize_group(group, student_count=0, average_percentage=None)), 201


@bp.route('/<int:group_id>', methods=['GET'])
def get_group(group_id):
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    if group_id == GROUP_UNASSIGNED_ID:
        students = db_session.query(User).filter_by(role=ROLE_STUDENT, group_id=None).order_by(User.username).all()
        summary = _unassigned_summary()
        if not summary:
            return jsonify({"error": "No unassigned students"}), 404
        return jsonify({
            **summary,
            "students": [{
                "id": s.id,
                "username": s.username,
                "student_id": s.student_id,
            } for s in students],
        }), 200

    group = db_session.query(Group).filter_by(id=group_id).first()
    if not group:
        return jsonify({"error": "Group not found"}), 404

    students = db_session.query(User).filter_by(role=ROLE_STUDENT, group_id=group.id).order_by(User.username).all()
    ids = [s.id for s in students]

    return jsonify({
        **_serialize_group(group, student_count=len(students), average_percentage=_group_average_percentage(ids)),
        "students": [{
            "id": s.id,
            "username": s.username,
            "student_id": s.student_id,
        } for s in students],
    }), 200


@bp.route('/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    if group_id == GROUP_UNASSIGNED_ID:
        return jsonify({"error": "Cannot edit the Unassigned group"}), 400

    group = db_session.query(Group).filter_by(id=group_id).first()
    if not group:
        return jsonify({"error": "Group not found"}), 404

    data = request.get_json() or {}
    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name:
            return jsonify({"error": "Group name is required"}), 400
        if name.lower() == 'unassigned':
            return jsonify({"error": "Reserved group name"}), 400
        existing = db_session.query(Group).filter_by(name=name).first()
        if existing and existing.id != group.id:
            return jsonify({"error": "Group name already exists"}), 400
        group.name = name
    if 'description' in data:
        group.description = (data.get('description') or '').strip() or None

    db_session.commit()
    students = db_session.query(User).filter_by(role=ROLE_STUDENT, group_id=group.id).count()
    return jsonify(_serialize_group(group, student_count=students)), 200


@bp.route('/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    if group_id == GROUP_UNASSIGNED_ID:
        return jsonify({"error": "Cannot delete the Unassigned group"}), 400

    group = db_session.query(Group).filter_by(id=group_id).first()
    if not group:
        return jsonify({"error": "Group not found"}), 404

    students = db_session.query(User).filter_by(role=ROLE_STUDENT, group_id=group.id).all()
    for student in students:
        student.group_id = None

    db_session.delete(group)
    db_session.commit()

    return jsonify({"message": "Group deleted; students moved to Unassigned"}), 200
