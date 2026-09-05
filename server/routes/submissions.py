"""Submission management routes."""

from flask import Blueprint, request, jsonify, session
from server.database import db_session
from server.models import Submission, Answer, Test, Question, TestQuestion, Grade
from shared.question_utils import get_answer_types, format_type_label
from server.services.test_schedule import (
    auto_submit_if_expired, can_start_test, submission_timing_info
)
from server.services.live_session import get_active_live_session
from shared.constants import API_SUBMISSIONS, SUBMISSION_STATUS_IN_PROGRESS, SUBMISSION_STATUS_SUBMITTED, SUBMISSION_STATUS_GRADED, TEST_MODE_LIVE
from datetime import datetime

bp = Blueprint('submissions', __name__, url_prefix=API_SUBMISSIONS)


def _student_results_detail(submission):
    """Build question-level results for a student submission."""
    test_questions = db_session.query(TestQuestion).filter_by(
        test_id=submission.test_id
    ).order_by(TestQuestion.order).all()
    answers_by_q = {a.question_id: a for a in submission.answers}

    questions = []
    for tq in test_questions:
        q = tq.question
        answer = answers_by_q.get(q.id)
        entry = {
            "question_id": q.id,
            "order": tq.order,
            "content": q.content,
            "type": q.type,
            "type_label": format_type_label(q),
            "answer_types": get_answer_types(q),
            "max_points": tq.points if tq.points is not None else q.points,
            "answer": None,
        }
        if answer:
            entry["answer"] = {
                "id": answer.id,
                "answer_text": answer.answer_text,
                "code": answer.code,
                "diagram_data": answer.diagram_data,
                "score": answer.score,
                "feedback": answer.feedback,
            }
        questions.append(entry)

    grade = submission.grade
    grade_data = None
    if grade:
        grade_data = {
            "total_score": grade.total_score,
            "max_score": grade.max_score,
            "percentage": grade.percentage,
            "graded_at": grade.graded_at.isoformat() if grade.graded_at else None,
        }

    return {
        "questions": questions,
        "grade": grade_data,
        "can_view_results": submission.status in (SUBMISSION_STATUS_SUBMITTED, SUBMISSION_STATUS_GRADED),
        "results_ready": submission.status == SUBMISSION_STATUS_GRADED or grade is not None,
    }


def _submission_response(submission, include_answers=False, include_results=False):
    """Build submission JSON with timing info."""
    live_session = get_active_live_session(submission.test, db_session)
    auto_submit_if_expired(submission, db_session, live_session)
    db_session.refresh(submission)

    data = {
        "id": submission.id,
        "test_id": submission.test_id,
        "test_name": submission.test.name if submission.test else None,
        "user_id": submission.user_id,
        "username": submission.user.username if submission.user else None,
        "started_at": submission.started_at.isoformat() if submission.started_at else None,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "status": submission.status,
        "live_session_id": submission.live_session_id,
    }
    data.update(submission_timing_info(submission.test, submission, live_session))

    if include_answers:
        answers = db_session.query(Answer).filter_by(submission_id=submission.id).all()
        data["answers"] = [{
            "id": a.id,
            "question_id": a.question_id,
            "answer_text": a.answer_text,
            "code": a.code,
            "diagram_data": a.diagram_data,
            "score": a.score,
            "feedback": a.feedback
        } for a in answers]

    if include_results:
        data.update(_student_results_detail(submission))

    return data


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

    result = []
    for s in submissions:
        live_session = get_active_live_session(s.test, db_session)
        auto_submit_if_expired(s, db_session, live_session)
        result.append(_submission_response(s))

    return jsonify(result), 200


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

    include_results = (
        user.role == 'student'
        and submission.status in (SUBMISSION_STATUS_SUBMITTED, SUBMISSION_STATUS_GRADED)
    )

    return jsonify(_submission_response(
        submission,
        include_answers=not include_results,
        include_results=include_results,
    )), 200


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

    live_session = get_active_live_session(test, db_session)

    # Check attempts (per live session for live mode)
    attempt_query = db_session.query(Submission).filter_by(test_id=test_id, user_id=user_id)
    if test.test_mode == TEST_MODE_LIVE and live_session:
        attempt_query = attempt_query.filter_by(live_session_id=live_session.id)
    existing_submissions = attempt_query.count()

    if existing_submissions >= test.attempts_allowed:
        return jsonify({"error": "Maximum attempts reached"}), 400

    if not can_start_test(test, live_session):
        status = submission_timing_info(test, None, live_session)['availability_status']
        if status == 'waiting':
            return jsonify({"error": "Waiting for lecturer to start the test"}), 400
        if status == 'upcoming':
            return jsonify({"error": "Test not yet available"}), 400
        return jsonify({"error": "Test is no longer available"}), 400

    submission = Submission(
        test_id=test_id,
        user_id=user_id,
        live_session_id=live_session.id if live_session else None,
        status=SUBMISSION_STATUS_IN_PROGRESS
    )
    
    db_session.add(submission)
    db_session.commit()
    db_session.refresh(submission)

    return jsonify(_submission_response(submission)), 201


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

    live_session = get_active_live_session(submission.test, db_session)
    if auto_submit_if_expired(submission, db_session, live_session):
        return jsonify({"error": "Time expired. Test has been auto-submitted.", "auto_submitted": True}), 400
    
    if submission.status == SUBMISSION_STATUS_SUBMITTED:
        return jsonify({
            "error": "Cannot modify submitted answers",
            "already_submitted": True,
            "auto_submitted": True,
        }), 400
    
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

    live_session = get_active_live_session(submission.test, db_session)
    if auto_submit_if_expired(submission, db_session, live_session):
        db_session.refresh(submission)
        return jsonify({
            "id": submission.id,
            "status": submission.status,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "auto_submitted": True
        }), 200

    if submission.status == SUBMISSION_STATUS_SUBMITTED:
        return jsonify({
            "id": submission.id,
            "status": submission.status,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "already_submitted": True
        }), 200
    
    submission.status = SUBMISSION_STATUS_SUBMITTED
    submission.submitted_at = datetime.utcnow()
    db_session.commit()
    
    return jsonify({
        "id": submission.id,
        "status": submission.status,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None
    }), 200

