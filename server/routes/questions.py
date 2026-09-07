"""Question management routes."""

from flask import Blueprint, request, jsonify, session
from server.database import db_session
from server.models import Question, Topic
from shared.constants import API_QUESTIONS, QUESTION_TYPES
from shared.question_utils import get_answer_types, normalize_answer_types, format_type_label

from server.auth_helpers import require_staff_api as require_lecturer

bp = Blueprint('questions', __name__, url_prefix=API_QUESTIONS)

MAX_IMAGE_DATA_LEN = 4_000_000  # ~3 MB as base64 data URL


def _validate_image_data(image_data):
    if image_data is None or image_data == '':
        return None
    if not isinstance(image_data, str):
        return 'image_data must be a string'
    if not image_data.startswith('data:image/'):
        return 'Invalid image format (expected PNG, JPEG, GIF, or WebP)'
    if len(image_data) > MAX_IMAGE_DATA_LEN:
        return 'Image too large (max 3 MB)'
    return None


def _serialize_question(question, include_image=False):
    data = {
        "id": question.id,
        "topic_id": question.topic_id,
        "type": question.type,
        "type_label": format_type_label(question),
        "answer_types": get_answer_types(question),
        "content": question.content,
        "has_image": bool(question.image_data),
        "correct_answer": question.correct_answer,
        "test_cases": question.test_cases,
        "points": question.points,
        "created_at": question.created_at.isoformat() if question.created_at else None,
    }
    if include_image:
        data["image_data"] = question.image_data
    return data


def _apply_question_types(question, data):
    if 'answer_types' in data:
        try:
            answer_types, question_type = normalize_answer_types(
                data.get('answer_types'),
                data.get('type'),
            )
        except ValueError as exc:
            return str(exc)
        question.answer_types = answer_types
        question.type = question_type
    elif 'type' in data:
        if data['type'] not in QUESTION_TYPES and data['type'] != 'composite':
            return "Invalid question type"
        if data['type'] == 'composite':
            return "Use answer_types for composite questions"
        question.type = data['type']
        question.answer_types = [data['type']]
    return None


@bp.route('', methods=['GET'])
def get_questions():
    """Get all questions, optionally filtered by topic."""
    topic_id = request.args.get('topic_id', type=int)

    query = db_session.query(Question)
    if topic_id:
        query = query.filter_by(topic_id=topic_id)

    questions = query.order_by(Question.created_at.desc()).all()
    return jsonify([_serialize_question(q, include_image=False) for q in questions]), 200


@bp.route('/<int:question_id>', methods=['GET'])
def get_question(question_id):
    """Get a specific question."""
    question = db_session.query(Question).filter_by(id=question_id).first()
    if not question:
        return jsonify({"error": "Question not found"}), 404

    return jsonify(_serialize_question(question, include_image=True)), 200


def _apply_image_data(question, data):
    if 'image_data' not in data:
        return None
    raw = data.get('image_data')
    if raw is None or raw == '':
        question.image_data = None
        return None
    err = _validate_image_data(raw)
    if err:
        return err
    question.image_data = raw
    return None


@bp.route('', methods=['POST'])
def create_question():
    """Create a new question."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    data = request.get_json()
    topic_id = data.get('topic_id')
    content = data.get('content')
    correct_answer = data.get('correct_answer')
    test_cases = data.get('test_cases')
    points = data.get('points', 1.0)

    if not topic_id or not content:
        return jsonify({"error": "topic_id and content are required"}), 400

    if 'answer_types' not in data and not data.get('type'):
        return jsonify({"error": "type or answer_types is required"}), 400

    topic = db_session.query(Topic).filter_by(id=topic_id).first()
    if not topic:
        return jsonify({"error": "Topic not found"}), 404

    try:
        answer_types, question_type = normalize_answer_types(
            data.get('answer_types'),
            data.get('type'),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    image_data = data.get('image_data')
    if image_data:
        img_err = _validate_image_data(image_data)
        if img_err:
            return jsonify({"error": img_err}), 400

    question = Question(
        topic_id=topic_id,
        type=question_type,
        answer_types=answer_types,
        content=content,
        image_data=image_data or None,
        correct_answer=correct_answer,
        test_cases=test_cases,
        points=points,
    )

    db_session.add(question)
    db_session.commit()

    return jsonify(_serialize_question(question, include_image=True)), 201


@bp.route('/<int:question_id>', methods=['PUT'])
def update_question(question_id):
    """Update a question."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    question = db_session.query(Question).filter_by(id=question_id).first()
    if not question:
        return jsonify({"error": "Question not found"}), 404

    data = request.get_json()
    if 'topic_id' in data:
        topic = db_session.query(Topic).filter_by(id=data['topic_id']).first()
        if not topic:
            return jsonify({"error": "Topic not found"}), 404
        question.topic_id = data['topic_id']

    type_error = _apply_question_types(question, data)
    if type_error:
        return jsonify({"error": type_error}), 400

    if 'content' in data:
        question.content = data['content']
    if 'correct_answer' in data:
        question.correct_answer = data['correct_answer']
    if 'test_cases' in data:
        question.test_cases = data['test_cases']
    if 'points' in data:
        question.points = data['points']

    img_err = _apply_image_data(question, data)
    if img_err:
        return jsonify({"error": img_err}), 400

    db_session.commit()

    return jsonify(_serialize_question(question, include_image=True)), 200


@bp.route('/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """Delete a question."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    question = db_session.query(Question).filter_by(id=question_id).first()
    if not question:
        return jsonify({"error": "Question not found"}), 404

    db_session.delete(question)
    db_session.commit()

    return jsonify({"message": "Question deleted successfully"}), 200
