"""Test management routes."""

from flask import Blueprint, request, jsonify, session
from server.database import db_session
from server.models import Test, TestQuestion, Question
from server.services.test_schedule import (
    auto_submit_if_expired, can_access_test, can_start_test,
    get_availability_status, submission_timing_info
)
from server.services.live_session import (
    get_active_live_session, live_session_info, finalize_expired_live_sessions
)
from shared.constants import API_TESTS, TEST_MODE_LIVE, TEST_MODE_SCHEDULED
from datetime import datetime


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


def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, str) and value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.fromisoformat(value)


def _validate_availability(available_from, available_until):
    if available_from and available_until and available_until <= available_from:
        return "Available until must be after available from"
    return None


bp = Blueprint('tests', __name__, url_prefix=API_TESTS)


def _student_test_extras(test, user):
    """Build student-specific fields including live session state."""
    from server.models import Submission

    finalize_expired_live_sessions(test.id, db_session)
    live_session = get_active_live_session(test, db_session)

    submission = db_session.query(Submission).filter_by(
        test_id=test.id, user_id=user.id
    ).order_by(Submission.started_at.desc()).first()

    if submission:
        auto_submit_if_expired(submission, db_session, live_session)
        db_session.refresh(submission)
        submission_status = submission.status
        submission_id = submission.id
    else:
        submission_status = "not_started"
        submission_id = None

    in_progress = submission and submission.status == 'in_progress'
    if in_progress and live_session and submission.live_session_id != live_session.id:
        in_progress = False

    can_access = can_access_test(test, submission if in_progress else None, live_session)
    extras = {
        "submission_status": submission_status,
        "submission_id": submission_id,
        "test_mode": getattr(test, 'test_mode', TEST_MODE_SCHEDULED),
        "can_access": can_access,
        **live_session_info(live_session),
    }
    extras["availability_status"] = get_availability_status(test, live_session)

    if in_progress:
        extras.update(submission_timing_info(test, submission, live_session))
    elif test.test_mode == TEST_MODE_LIVE and live_session:
        extras.update(submission_timing_info(test, None, live_session))

    return extras


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
            "test_mode": getattr(test, 'test_mode', TEST_MODE_SCHEDULED),
            "created_at": test.created_at.isoformat() if test.created_at else None,
            "question_count": len(test.test_questions)
        }
        
        if user and user.role == 'student':
            test_data.update(_student_test_extras(test, user))
        elif user and user.role == 'lecturer' and test.test_mode == TEST_MODE_LIVE:
            live_session = get_active_live_session(test, db_session)
            test_data.update(live_session_info(live_session))
        
        result.append(test_data)
    
    return jsonify(result), 200


@bp.route('/<int:test_id>', methods=['GET'])
def get_test(test_id):
    """Get a specific test with questions."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    from server.models import User, Submission
    user = db_session.query(User).filter_by(id=user_id).first()

    test = db_session.query(Test).filter_by(id=test_id).first()
    if not test:
        return jsonify({"error": "Test not found"}), 404

    submission = None
    live_session = get_active_live_session(test, db_session)

    if user.role == 'student':
        submission = db_session.query(Submission).filter_by(
            test_id=test_id, user_id=user.id
        ).order_by(Submission.started_at.desc()).first()
        if submission:
            auto_submit_if_expired(submission, db_session, live_session)
            db_session.refresh(submission)
        if not can_access_test(test, submission, live_session):
            avail = get_availability_status(test, live_session)
            if avail == 'waiting':
                return jsonify({"error": "Waiting for lecturer to start the test"}), 403
            if avail == 'upcoming':
                return jsonify({"error": "Test not yet available"}), 403
            return jsonify({"error": "Test is no longer available"}), 403
    
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
            "correct_answer": q.correct_answer,
            "test_cases": q.test_cases if q.type == 'code' else None
        })
    
    response = {
        "id": test.id,
        "name": test.name,
        "description": test.description,
        "time_limit": test.time_limit,
        "attempts_allowed": test.attempts_allowed,
        "available_from": test.available_from.isoformat() if test.available_from else None,
        "available_until": test.available_until.isoformat() if test.available_until else None,
        "test_mode": getattr(test, 'test_mode', TEST_MODE_SCHEDULED),
        "created_at": test.created_at.isoformat() if test.created_at else None,
        "questions": questions,
        "availability_status": get_availability_status(test, live_session),
        **live_session_info(live_session),
    }
    if submission:
        response.update(submission_timing_info(test, submission, live_session))
        response["submission_id"] = submission.id
        response["submission_status"] = submission.status

    return jsonify(response), 200


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
    test_mode = data.get('test_mode', TEST_MODE_SCHEDULED)
    question_ids = data.get('question_ids', [])
    
    if not name:
        return jsonify({"error": "Test name is required"}), 400
    if test_mode not in (TEST_MODE_SCHEDULED, TEST_MODE_LIVE):
        return jsonify({"error": "Invalid test mode"}), 400

    parsed_from = _parse_datetime(available_from) if test_mode == TEST_MODE_SCHEDULED else None
    parsed_until = _parse_datetime(available_until) if test_mode == TEST_MODE_SCHEDULED else None
    avail_error = _validate_availability(parsed_from, parsed_until)
    if avail_error:
        return jsonify({"error": avail_error}), 400
    
    test = Test(
        name=name,
        description=description,
        time_limit=time_limit if test_mode == TEST_MODE_SCHEDULED else None,
        attempts_allowed=attempts_allowed,
        available_from=parsed_from,
        available_until=parsed_until,
        test_mode=test_mode,
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
        test.available_from = _parse_datetime(data['available_from'])
    if 'available_until' in data and test.test_mode == TEST_MODE_SCHEDULED:
        test.available_until = _parse_datetime(data['available_until'])
    if 'test_mode' in data:
        if data['test_mode'] not in (TEST_MODE_SCHEDULED, TEST_MODE_LIVE):
            return jsonify({"error": "Invalid test mode"}), 400
        test.test_mode = data['test_mode']
        if test.test_mode == TEST_MODE_LIVE:
            test.available_from = None
            test.available_until = None
            test.time_limit = None

    avail_error = _validate_availability(test.available_from, test.available_until)
    if avail_error:
        return jsonify({"error": avail_error}), 400
    
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

