"""Grading routes."""

from flask import Blueprint, request, jsonify, session
from server.app import db_session
from server.models import Submission, Answer, Grade, Question
from shared.constants import API_GRADING, SUBMISSION_STATUS_SUBMITTED, SUBMISSION_STATUS_GRADED
from datetime import datetime

bp = Blueprint('grading', __name__, url_prefix=API_GRADING)


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


@bp.route('/submissions/<int:submission_id>', methods=['GET'])
def get_submission_for_grading(submission_id):
    """Get submission details for grading."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    submission = db_session.query(Submission).filter_by(id=submission_id).first()
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    
    # Get test questions in order
    from server.models import TestQuestion
    test_questions = db_session.query(TestQuestion).filter_by(
        test_id=submission.test_id
    ).order_by(TestQuestion.order).all()
    
    # Get answers
    answers = {a.question_id: a for a in submission.answers}
    
    questions_data = []
    for tq in test_questions:
        q = tq.question
        answer = answers.get(q.id)
        questions_data.append({
            "question_id": q.id,
            "order": tq.order,
            "type": q.type,
            "content": q.content,
            "points": tq.points if tq.points is not None else q.points,
            "correct_answer": q.correct_answer,
            "test_cases": q.test_cases,
            "answer": {
                "id": answer.id if answer else None,
                "answer_text": answer.answer_text if answer else None,
                "code": answer.code if answer else None,
                "diagram_data": answer.diagram_data if answer else None,
                "score": answer.score,
                "feedback": answer.feedback
            } if answer else None
        })
    
    return jsonify({
        "submission_id": submission.id,
        "test_id": submission.test_id,
        "test_name": submission.test.name if submission.test else None,
        "user_id": submission.user_id,
        "username": submission.user.username if submission.user else None,
        "student_id": submission.user.student_id if submission.user else None,
        "started_at": submission.started_at.isoformat() if submission.started_at else None,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "status": submission.status,
        "questions": questions_data
    }), 200


@bp.route('/answers/<int:answer_id>', methods=['PUT'])
def grade_answer(answer_id):
    """Grade an individual answer."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    answer = db_session.query(Answer).filter_by(id=answer_id).first()
    if not answer:
        return jsonify({"error": "Answer not found"}), 404
    
    data = request.get_json()
    score = data.get('score')
    feedback = data.get('feedback')
    
    if score is not None:
        # Validate score doesn't exceed max points
        question = answer.question
        max_points = question.points
        # Check if test question has custom points
        from server.models import TestQuestion, Submission
        submission = answer.submission
        test_question = db_session.query(TestQuestion).filter_by(
            test_id=submission.test_id, question_id=question.id
        ).first()
        if test_question and test_question.points is not None:
            max_points = test_question.points
        
        if score < 0 or score > max_points:
            return jsonify({"error": f"Score must be between 0 and {max_points}"}), 400
        
        answer.score = score
    
    if feedback is not None:
        answer.feedback = feedback
    
    answer.updated_at = datetime.utcnow()
    db_session.commit()
    
    return jsonify({
        "id": answer.id,
        "score": answer.score,
        "feedback": answer.feedback
    }), 200


@bp.route('/submissions/<int:submission_id>/finalize', methods=['POST'])
def finalize_grading(submission_id):
    """Finalize grading for a submission and calculate final grade."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    submission = db_session.query(Submission).filter_by(id=submission_id).first()
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    
    # Calculate total score
    total_score = 0.0
    max_score = 0.0
    
    from server.models import TestQuestion
    test_questions = db_session.query(TestQuestion).filter_by(
        test_id=submission.test_id
    ).all()
    
    answers = {a.question_id: a for a in submission.answers}
    
    for tq in test_questions:
        question = tq.question
        points = tq.points if tq.points is not None else question.points
        max_score += points
        
        answer = answers.get(question.id)
        if answer and answer.score is not None:
            total_score += answer.score
    
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    # Create or update grade
    grade = db_session.query(Grade).filter_by(submission_id=submission_id).first()
    if grade:
        grade.total_score = total_score
        grade.max_score = max_score
        grade.percentage = percentage
        grade.graded_by = user.id
        grade.graded_at = datetime.utcnow()
    else:
        grade = Grade(
            submission_id=submission_id,
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            graded_by=user.id
        )
        db_session.add(grade)
    
    submission.status = SUBMISSION_STATUS_GRADED
    db_session.commit()
    
    return jsonify({
        "submission_id": submission_id,
        "total_score": total_score,
        "max_score": max_score,
        "percentage": percentage,
        "grade_id": grade.id
    }), 200

