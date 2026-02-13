"""Auto-grading service for code questions."""

from server.services.code_executor import grade_code_submission
from server.models import Answer, Question, TestQuestion, Submission
from typing import Optional


def auto_grade_code_answer(answer: Answer, submission: Submission) -> Optional[float]:
    """
    Auto-grade a code answer.
    
    Args:
        answer: Answer object to grade
        submission: Submission object
    
    Returns:
        Score if auto-graded, None if manual grading required
    """
    if not answer.code or not answer.question:
        return None
    
    question = answer.question
    
    # Only auto-grade code questions
    if question.type != 'code':
        return None
    
    # Get test cases
    test_cases = question.test_cases or []
    if not test_cases:
        return None  # No test cases, requires manual grading
    
    # Get points
    from server.database import db_session
    test_question = db_session.query(TestQuestion).filter_by(
        test_id=submission.test_id,
        question_id=question.id
    ).first()
    
    points = test_question.points if test_question and test_question.points is not None else question.points
    
    # Grade the submission
    grade_result = grade_code_submission(answer.code, test_cases, points)
    
    # Update answer
    answer.score = grade_result['score']
    answer.feedback = grade_result['feedback']
    
    return grade_result['score']

