"""Statistics and analytics routes."""

from flask import Blueprint, request, jsonify, session
from server.app import db_session
from server.models import Submission, Answer, Grade, Question, Topic, Test
from shared.constants import API_STATISTICS
from sqlalchemy import func

bp = Blueprint('statistics', __name__, url_prefix=API_STATISTICS)


def require_lecturer():
    """Check if user is a lecturer."""
    user_id = session.get('user_id')
    if not user_id:
        return None, jsonify({"error": "Not authenticated"}), 401
    
    from server.models import User
    user = db_session.query(User).filter_by(id=user_id).first()
    if not user or user.role != 'lecturer':
        return None, jsonify({"error": "Only lecturers can access statistics"}), 403
    
    return user, None, None


@bp.route('/overview', methods=['GET'])
def get_overview():
    """Get overall statistics."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    # Count totals
    total_students = db_session.query(func.count()).select_from(
        db_session.query(User).filter_by(role='student').subquery()
    ).scalar()
    
    total_tests = db_session.query(func.count(Test.id)).scalar()
    total_questions = db_session.query(func.count(Question.id)).scalar()
    total_submissions = db_session.query(func.count(Submission.id)).scalar()
    total_graded = db_session.query(func.count(Grade.id)).scalar()
    
    return jsonify({
        "total_students": total_students,
        "total_tests": total_tests,
        "total_questions": total_questions,
        "total_submissions": total_submissions,
        "total_graded": total_graded
    }), 200


@bp.route('/topics', methods=['GET'])
def get_topic_statistics():
    """Get statistics by topic."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    topics = db_session.query(Topic).all()
    result = []
    
    for topic in topics:
        # Get questions in this topic
        questions = db_session.query(Question).filter_by(topic_id=topic.id).all()
        question_ids = [q.id for q in questions]
        
        if not question_ids:
            result.append({
                "topic_id": topic.id,
                "topic_name": topic.name,
                "question_count": 0,
                "average_score": 0,
                "submission_count": 0
            })
            continue
        
        # Get answers for questions in this topic
        answers = db_session.query(Answer).filter(
            Answer.question_id.in_(question_ids),
            Answer.score.isnot(None)
        ).all()
        
        submission_count = len(set(a.submission_id for a in answers))
        
        if answers:
            avg_score = sum(a.score for a in answers) / len(answers)
        else:
            avg_score = 0
        
        result.append({
            "topic_id": topic.id,
            "topic_name": topic.name,
            "question_count": len(questions),
            "average_score": round(avg_score, 2),
            "submission_count": submission_count
        })
    
    return jsonify(result), 200


@bp.route('/students', methods=['GET'])
def get_student_statistics():
    """Get statistics by student."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    from server.models import User
    students = db_session.query(User).filter_by(role='student').all()
    
    result = []
    for student in students:
        # Get all grades for this student
        grades = db_session.query(Grade).join(Submission).filter(
            Submission.user_id == student.id
        ).all()
        
        if grades:
            avg_percentage = sum(g.percentage for g in grades) / len(grades)
            total_tests = len(grades)
        else:
            avg_percentage = 0
            total_tests = 0
        
        result.append({
            "student_id": student.id,
            "username": student.username,
            "student_id_number": student.student_id,
            "total_tests": total_tests,
            "average_percentage": round(avg_percentage, 2)
        })
    
    return jsonify(result), 200


@bp.route('/tests/<int:test_id>', methods=['GET'])
def get_test_statistics(test_id):
    """Get statistics for a specific test."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    test = db_session.query(Test).filter_by(id=test_id).first()
    if not test:
        return jsonify({"error": "Test not found"}), 404
    
    # Get all submissions for this test
    submissions = db_session.query(Submission).filter_by(test_id=test_id).all()
    
    # Get grades
    grades = db_session.query(Grade).join(Submission).filter(
        Submission.test_id == test_id
    ).all()
    
    if grades:
        avg_score = sum(g.total_score for g in grades) / len(grades)
        avg_percentage = sum(g.percentage for g in grades) / len(grades)
        max_score = max(g.max_score for g in grades) if grades else 0
    else:
        avg_score = 0
        avg_percentage = 0
        max_score = 0
    
    # Question-level statistics
    from server.models import TestQuestion
    test_questions = db_session.query(TestQuestion).filter_by(
        test_id=test_id
    ).order_by(TestQuestion.order).all()
    
    question_stats = []
    for tq in test_questions:
        question = tq.question
        answers = db_session.query(Answer).join(Submission).filter(
            Submission.test_id == test_id,
            Answer.question_id == question.id,
            Answer.score.isnot(None)
        ).all()
        
        if answers:
            avg_score_q = sum(a.score for a in answers) / len(answers)
            max_points = tq.points if tq.points is not None else question.points
        else:
            avg_score_q = 0
            max_points = tq.points if tq.points is not None else question.points
        
        question_stats.append({
            "question_id": question.id,
            "order": tq.order,
            "type": question.type,
            "content": question.content[:100] + "..." if len(question.content) > 100 else question.content,
            "average_score": round(avg_score_q, 2),
            "max_points": max_points,
            "answer_count": len(answers)
        })
    
    return jsonify({
        "test_id": test_id,
        "test_name": test.name,
        "total_submissions": len(submissions),
        "graded_submissions": len(grades),
        "average_score": round(avg_score, 2),
        "average_percentage": round(avg_percentage, 2),
        "max_score": max_score,
        "question_statistics": question_stats
    }), 200

