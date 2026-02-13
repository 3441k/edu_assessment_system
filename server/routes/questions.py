"""Question management routes."""

from flask import Blueprint, request, jsonify, session
from server.database import db_session
from server.models import Question, Topic
from shared.constants import API_QUESTIONS, QUESTION_TYPES
from datetime import datetime

bp = Blueprint('questions', __name__, url_prefix=API_QUESTIONS)


def require_lecturer():
    """Check if user is a lecturer."""
    user_id = session.get('user_id')
    if not user_id:
        return None, jsonify({"error": "Not authenticated"}), 401
    
    from server.models import User
    user = db_session.query(User).filter_by(id=user_id).first()
    if not user or user.role != 'lecturer':
        return None, jsonify({"error": "Only lecturers can perform this action"}), 403
    
    return user, None, None


@bp.route('', methods=['GET'])
def get_questions():
    """Get all questions, optionally filtered by topic."""
    topic_id = request.args.get('topic_id', type=int)
    
    query = db_session.query(Question)
    if topic_id:
        query = query.filter_by(topic_id=topic_id)
    
    questions = query.order_by(Question.created_at.desc()).all()
    
    return jsonify([{
        "id": q.id,
        "topic_id": q.topic_id,
        "type": q.type,
        "content": q.content,
        "correct_answer": q.correct_answer,
        "test_cases": q.test_cases,
        "points": q.points,
        "created_at": q.created_at.isoformat() if q.created_at else None
    } for q in questions]), 200


@bp.route('/<int:question_id>', methods=['GET'])
def get_question(question_id):
    """Get a specific question."""
    question = db_session.query(Question).filter_by(id=question_id).first()
    if not question:
        return jsonify({"error": "Question not found"}), 404
    
    return jsonify({
        "id": question.id,
        "topic_id": question.topic_id,
        "type": question.type,
        "content": question.content,
        "correct_answer": question.correct_answer,
        "test_cases": question.test_cases,
        "points": question.points,
        "created_at": question.created_at.isoformat() if question.created_at else None
    }), 200


@bp.route('', methods=['POST'])
def create_question():
    """Create a new question."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    data = request.get_json()
    topic_id = data.get('topic_id')
    question_type = data.get('type')
    content = data.get('content')
    correct_answer = data.get('correct_answer')
    test_cases = data.get('test_cases')
    points = data.get('points', 1.0)
    
    if not topic_id or not question_type or not content:
        return jsonify({"error": "topic_id, type, and content are required"}), 400
    
    if question_type not in QUESTION_TYPES:
        return jsonify({"error": f"Invalid question type. Must be one of: {QUESTION_TYPES}"}), 400
    
    # Verify topic exists
    topic = db_session.query(Topic).filter_by(id=topic_id).first()
    if not topic:
        return jsonify({"error": "Topic not found"}), 404
    
    question = Question(
        topic_id=topic_id,
        type=question_type,
        content=content,
        correct_answer=correct_answer,
        test_cases=test_cases,
        points=points
    )
    
    db_session.add(question)
    db_session.commit()
    
    return jsonify({
        "id": question.id,
        "topic_id": question.topic_id,
        "type": question.type,
        "content": question.content,
        "correct_answer": question.correct_answer,
        "test_cases": question.test_cases,
        "points": question.points,
        "created_at": question.created_at.isoformat() if question.created_at else None
    }), 201


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
    if 'type' in data:
        if data['type'] not in QUESTION_TYPES:
            return jsonify({"error": f"Invalid question type"}), 400
        question.type = data['type']
    if 'content' in data:
        question.content = data['content']
    if 'correct_answer' in data:
        question.correct_answer = data['correct_answer']
    if 'test_cases' in data:
        question.test_cases = data['test_cases']
    if 'points' in data:
        question.points = data['points']
    
    db_session.commit()
    
    return jsonify({
        "id": question.id,
        "topic_id": question.topic_id,
        "type": question.type,
        "content": question.content,
        "correct_answer": question.correct_answer,
        "test_cases": question.test_cases,
        "points": question.points,
        "created_at": question.created_at.isoformat() if question.created_at else None
    }), 200


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

