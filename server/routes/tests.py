"""Test management routes."""

from flask import Blueprint, request, jsonify, session
from server.app import db_session
from server.models import Test, TestQuestion, Question
from shared.constants import API_TESTS
from datetime import datetime

bp = Blueprint('tests', __name__, url_prefix=API_TESTS)


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
def get_tests():
    """Get all tests."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    from server.models import User
    user = db_session.query(User).filter_by(id=user_id).first()
    
    tests = db_session.query(Test).order_by(Test.created_at.desc()).all()
    
    result = []
    for test in tests:
        test_data = {
            "id": test.id,
            "name": test.name,
            "description": test.description,
            "time_limit": test.time_limit,
            "attempts_allowed": test.attempts_allowed,
            "available_from": test.available_from.isoformat() if test.available_from else None,
            "available_until": test.available_until.isoformat() if test.available_until else None,
            "created_at": test.created_at.isoformat() if test.created_at else None,
            "question_count": len(test.test_questions)
        }
        
        # For students, include submission status
        if user and user.role == 'student':
            from server.models import Submission
            submission = db_session.query(Submission).filter_by(
                test_id=test.id, user_id=user.id
            ).order_by(Submission.started_at.desc()).first()
            
            if submission:
                test_data["submission_status"] = submission.status
                test_data["submission_id"] = submission.id
            else:
                test_data["submission_status"] = "not_started"
        
        result.append(test_data)
    
    return jsonify(result), 200


@bp.route('/<int:test_id>', methods=['GET'])
def get_test(test_id):
    """Get a specific test with questions."""
    test = db_session.query(Test).filter_by(id=test_id).first()
    if not test:
        return jsonify({"error": "Test not found"}), 404
    
    # Get questions in order
    test_questions = db_session.query(TestQuestion).filter_by(
        test_id=test_id
    ).order_by(TestQuestion.order).all()
    
    questions = []
    for tq in test_questions:
        q = tq.question
        questions.append({
            "id": q.id,
            "order": tq.order,
            "points": tq.points if tq.points is not None else q.points,
            "type": q.type,
            "content": q.content,
            "test_cases": q.test_cases if q.type == 'code' else None
        })
    
    return jsonify({
        "id": test.id,
        "name": test.name,
        "description": test.description,
        "time_limit": test.time_limit,
        "attempts_allowed": test.attempts_allowed,
        "available_from": test.available_from.isoformat() if test.available_from else None,
        "available_until": test.available_until.isoformat() if test.available_until else None,
        "created_at": test.created_at.isoformat() if test.created_at else None,
        "questions": questions
    }), 200


@bp.route('', methods=['POST'])
def create_test():
    """Create a new test."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    time_limit = data.get('time_limit')
    attempts_allowed = data.get('attempts_allowed', 1)
    available_from = data.get('available_from')
    available_until = data.get('available_until')
    question_ids = data.get('question_ids', [])  # List of question IDs with optional order/points
    
    if not name:
        return jsonify({"error": "Test name is required"}), 400
    
    test = Test(
        name=name,
        description=description,
        time_limit=time_limit,
        attempts_allowed=attempts_allowed,
        available_from=datetime.fromisoformat(available_from) if available_from else None,
        available_until=datetime.fromisoformat(available_until) if available_until else None
    )
    
    db_session.add(test)
    db_session.flush()  # Get test.id
    
    # Add questions
    for idx, q_data in enumerate(question_ids):
        if isinstance(q_data, dict):
            question_id = q_data.get('question_id') or q_data.get('id')
            order = q_data.get('order', idx + 1)
            points = q_data.get('points')
        else:
            question_id = q_data
            order = idx + 1
            points = None
        
        question = db_session.query(Question).filter_by(id=question_id).first()
        if not question:
            continue
        
        test_question = TestQuestion(
            test_id=test.id,
            question_id=question_id,
            order=order,
            points=points
        )
        db_session.add(test_question)
    
    db_session.commit()
    
    return jsonify({
        "id": test.id,
        "name": test.name,
        "description": test.description,
        "time_limit": test.time_limit,
        "attempts_allowed": test.attempts_allowed,
        "created_at": test.created_at.isoformat() if test.created_at else None
    }), 201


@bp.route('/<int:test_id>', methods=['PUT'])
def update_test(test_id):
    """Update a test."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    test = db_session.query(Test).filter_by(id=test_id).first()
    if not test:
        return jsonify({"error": "Test not found"}), 404
    
    data = request.get_json()
    if 'name' in data:
        test.name = data['name']
    if 'description' in data:
        test.description = data.get('description', '')
    if 'time_limit' in data:
        test.time_limit = data['time_limit']
    if 'attempts_allowed' in data:
        test.attempts_allowed = data['attempts_allowed']
    if 'available_from' in data:
        test.available_from = datetime.fromisoformat(data['available_from']) if data['available_from'] else None
    if 'available_until' in data:
        test.available_until = datetime.fromisoformat(data['available_until']) if data['available_until'] else None
    
    # Update questions if provided
    if 'question_ids' in data:
        # Delete existing test questions
        db_session.query(TestQuestion).filter_by(test_id=test_id).delete()
        
        # Add new questions
        for idx, q_data in enumerate(data['question_ids']):
            if isinstance(q_data, dict):
                question_id = q_data.get('question_id') or q_data.get('id')
                order = q_data.get('order', idx + 1)
                points = q_data.get('points')
            else:
                question_id = q_data
                order = idx + 1
                points = None
            
            question = db_session.query(Question).filter_by(id=question_id).first()
            if question:
                test_question = TestQuestion(
                    test_id=test_id,
                    question_id=question_id,
                    order=order,
                    points=points
                )
                db_session.add(test_question)
    
    db_session.commit()
    
    return jsonify({
        "id": test.id,
        "name": test.name,
        "description": test.description,
        "time_limit": test.time_limit,
        "attempts_allowed": test.attempts_allowed,
        "created_at": test.created_at.isoformat() if test.created_at else None
    }), 200


@bp.route('/<int:test_id>', methods=['DELETE'])
def delete_test(test_id):
    """Delete a test."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    test = db_session.query(Test).filter_by(id=test_id).first()
    if not test:
        return jsonify({"error": "Test not found"}), 404
    
    db_session.delete(test)
    db_session.commit()
    
    return jsonify({"message": "Test deleted successfully"}), 200

