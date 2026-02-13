"""Submission management routes."""

from flask import Blueprint, request, jsonify, session
from server.database import db_session
from server.models import Submission, Answer, Test, Question, TestQuestion
from shared.constants import API_SUBMISSIONS, SUBMISSION_STATUS_NOT_STARTED, SUBMISSION_STATUS_IN_PROGRESS, SUBMISSION_STATUS_SUBMITTED
from datetime import datetime

bp = Blueprint('submissions', __name__, url_prefix=API_SUBMISSIONS)


@bp.route('', methods=['GET'])
def get_submissions():
    """Get submissions (filtered by user role)."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    from server.models import User
    user = db_session.query(User).filter_by(id=user_id).first()
    
    test_id = request.args.get('test_id', type=int)
    
    query = db_session.query(Submission)
    
    # Students can only see their own submissions
    if user.role == 'student':
        query = query.filter_by(user_id=user_id)
    
    if test_id:
        query = query.filter_by(test_id=test_id)
    
    submissions = query.order_by(Submission.started_at.desc()).all()
    
    return jsonify([{
        "id": s.id,
        "test_id": s.test_id,
        "test_name": s.test.name if s.test else None,
        "user_id": s.user_id,
        "username": s.user.username if s.user else None,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
        "status": s.status
    } for s in submissions]), 200


@bp.route('/<int:submission_id>', methods=['GET'])
def get_submission(submission_id):
    """Get a specific submission with answers."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    from server.models import User
    user = db_session.query(User).filter_by(id=user_id).first()
    
    submission = db_session.query(Submission).filter_by(id=submission_id).first()
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    
    # Students can only see their own submissions
    if user.role == 'student' and submission.user_id != user_id:
        return jsonify({"error": "Access denied"}), 403
    
    # Get answers
    answers = db_session.query(Answer).filter_by(submission_id=submission_id).all()
    
    answers_data = []
    for answer in answers:
        answers_data.append({
            "id": answer.id,
            "question_id": answer.question_id,
            "answer_text": answer.answer_text,
            "code": answer.code,
            "diagram_data": answer.diagram_data,
            "score": answer.score,
            "feedback": answer.feedback
        })
    
    return jsonify({
        "id": submission.id,
        "test_id": submission.test_id,
        "test_name": submission.test.name if submission.test else None,
        "user_id": submission.user_id,
        "username": submission.user.username if submission.user else None,
        "started_at": submission.started_at.isoformat() if submission.started_at else None,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "status": submission.status,
        "answers": answers_data
    }), 200


@bp.route('', methods=['POST'])
def create_submission():
    """Start a new test submission."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    from server.models import User
    user = db_session.query(User).filter_by(id=user_id).first()
    if user.role != 'student':
        return jsonify({"error": "Only students can create submissions"}), 403
    
    data = request.get_json()
    test_id = data.get('test_id')
    
    if not test_id:
        return jsonify({"error": "test_id is required"}), 400
    
    test = db_session.query(Test).filter_by(id=test_id).first()
    if not test:
        return jsonify({"error": "Test not found"}), 404
    
    # Check attempts
    existing_submissions = db_session.query(Submission).filter_by(
        test_id=test_id, user_id=user_id
    ).count()
    
    if existing_submissions >= test.attempts_allowed:
        return jsonify({"error": "Maximum attempts reached"}), 400
    
    # Check availability
    now = datetime.utcnow()
    if test.available_from and now < test.available_from:
        return jsonify({"error": "Test not yet available"}), 400
    if test.available_until and now > test.available_until:
        return jsonify({"error": "Test no longer available"}), 400
    
    submission = Submission(
        test_id=test_id,
        user_id=user_id,
        status=SUBMISSION_STATUS_IN_PROGRESS
    )
    
    db_session.add(submission)
    db_session.commit()
    
    return jsonify({
        "id": submission.id,
        "test_id": submission.test_id,
        "started_at": submission.started_at.isoformat() if submission.started_at else None,
        "status": submission.status
    }), 201


@bp.route('/<int:submission_id>/answers', methods=['POST'])
def save_answer(submission_id):
    """Save or update an answer."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    submission = db_session.query(Submission).filter_by(id=submission_id).first()
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    
    if submission.user_id != user_id:
        return jsonify({"error": "Access denied"}), 403
    
    if submission.status == SUBMISSION_STATUS_SUBMITTED:
        return jsonify({"error": "Cannot modify submitted answers"}), 400
    
    data = request.get_json()
    question_id = data.get('question_id')
    answer_text = data.get('answer_text')
    code = data.get('code')
    diagram_data = data.get('diagram_data')
    
    if not question_id:
        return jsonify({"error": "question_id is required"}), 400
    
    # Verify question is in the test
    test_question = db_session.query(TestQuestion).filter_by(
        test_id=submission.test_id, question_id=question_id
    ).first()
    if not test_question:
        return jsonify({"error": "Question not found in test"}), 404
    
    # Find or create answer
    answer = db_session.query(Answer).filter_by(
        submission_id=submission_id, question_id=question_id
    ).first()
    
    if answer:
        answer.answer_text = answer_text
        answer.code = code
        answer.diagram_data = diagram_data
        answer.updated_at = datetime.utcnow()
    else:
        answer = Answer(
            submission_id=submission_id,
            question_id=question_id,
            answer_text=answer_text,
            code=code,
            diagram_data=diagram_data
        )
        db_session.add(answer)
    
    submission.status = SUBMISSION_STATUS_IN_PROGRESS
    db_session.commit()
    
    return jsonify({
        "id": answer.id,
        "question_id": answer.question_id,
        "answer_text": answer.answer_text,
        "code": answer.code,
        "diagram_data": answer.diagram_data
    }), 200


@bp.route('/<int:submission_id>/submit', methods=['POST'])
def submit_submission(submission_id):
    """Submit a test."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    submission = db_session.query(Submission).filter_by(id=submission_id).first()
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    
    if submission.user_id != user_id:
        return jsonify({"error": "Access denied"}), 403
    
    if submission.status == SUBMISSION_STATUS_SUBMITTED:
        return jsonify({"error": "Submission already submitted"}), 400
    
    submission.status = SUBMISSION_STATUS_SUBMITTED
    submission.submitted_at = datetime.utcnow()
    db_session.commit()
    
    return jsonify({
        "id": submission.id,
        "status": submission.status,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None
    }), 200

