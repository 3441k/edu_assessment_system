"""Statistics and analytics routes."""

from flask import Blueprint, request, jsonify, session
from server.database import db_session
from server.models import User, Submission, Answer, Grade, Question, Topic, Test, TestQuestion, Group
from shared.constants import API_STATISTICS, SUBMISSION_STATUS_GRADED, GROUP_UNASSIGNED_ID, ROLE_STUDENT
from sqlalchemy import func

bp = Blueprint('statistics', __name__, url_prefix=API_STATISTICS)


def require_lecturer():
    """Check if user is a lecturer."""
    user_id = session.get('user_id')
    if not user_id:
        return None, jsonify({"error": "Not authenticated"}), 401

    user = db_session.query(User).filter_by(id=user_id).first()
    if not user or user.role != 'lecturer':
        return None, jsonify({"error": "Only lecturers can access statistics"}), 403

    return user, None, None


def _parse_group_id_param():
    raw = request.args.get('group_id')
    if raw is None or raw == '':
        return None
    if str(raw) in ('0', str(GROUP_UNASSIGNED_ID)):
        return GROUP_UNASSIGNED_ID
    return int(raw)


def _student_ids_for_group(group_id):
    if group_id is None:
        return None
    if group_id == GROUP_UNASSIGNED_ID:
        rows = db_session.query(User.id).filter_by(role=ROLE_STUDENT, group_id=None).all()
    else:
        rows = db_session.query(User.id).filter_by(role=ROLE_STUDENT, group_id=group_id).all()
    return [r[0] for r in rows]


def _grades_for_test(test_id, group_id=None):
    query = db_session.query(Grade).join(Submission).filter(Submission.test_id == test_id)
    student_ids = _student_ids_for_group(group_id)
    if student_ids is not None:
        if not student_ids:
            return []
        query = query.filter(Submission.user_id.in_(student_ids))
    return query.all()


def _submissions_for_test(test_id, group_id=None):
    query = db_session.query(Submission).filter_by(test_id=test_id)
    student_ids = _student_ids_for_group(group_id)
    if student_ids is not None:
        if not student_ids:
            return []
        query = query.filter(Submission.user_id.in_(student_ids))
    return query.all()


def _group_entries_for_compare():
    entries = []
    for group in db_session.query(Group).order_by(Group.name).all():
        count = db_session.query(User).filter_by(role=ROLE_STUDENT, group_id=group.id).count()
        entries.append({"group_id": group.id, "group_name": group.name, "student_count": count})
    unassigned = db_session.query(User).filter_by(role=ROLE_STUDENT, group_id=None).count()
    if unassigned:
        entries.append({
            "group_id": GROUP_UNASSIGNED_ID,
            "group_name": "Unassigned",
            "student_count": unassigned,
        })
    return entries


def _topic_statistics_list(group_id=None):
    """Build per-topic statistics."""
    topics = db_session.query(Topic).all()
    result = []

    for topic in topics:
        questions = db_session.query(Question).filter_by(topic_id=topic.id).all()
        question_ids = [q.id for q in questions]

        if not question_ids:
            result.append({
                "topic_id": topic.id,
                "topic_name": topic.name,
                "question_count": 0,
                "average_score": 0,
                "average_percentage": 0,
                "submission_count": 0,
            })
            continue

        answers = db_session.query(Answer).join(Submission).filter(
            Answer.question_id.in_(question_ids),
            Answer.score.isnot(None),
        )
        student_ids = _student_ids_for_group(group_id)
        if student_ids is not None:
            if not student_ids:
                answers = answers.filter(Submission.user_id == -1)
            else:
                answers = answers.filter(Submission.user_id.in_(student_ids))
        answers = answers.all()

        submission_count = len({a.submission_id for a in answers})
        if answers:
            avg_score = sum(a.score for a in answers) / len(answers)
            max_by_q = {q.id: q.points for q in questions}
            pct_values = []
            for a in answers:
                mx = max_by_q.get(a.question_id) or 1
                if mx > 0:
                    pct_values.append((a.score / mx) * 100)
            avg_pct = sum(pct_values) / len(pct_values) if pct_values else 0
        else:
            avg_score = 0
            avg_pct = 0

        result.append({
            "topic_id": topic.id,
            "topic_name": topic.name,
            "question_count": len(questions),
            "average_score": round(avg_score, 2),
            "average_percentage": round(avg_pct, 2),
            "submission_count": submission_count,
        })

    return result


def _test_summary(test, group_id=None):
    """Summary stats for one test."""
    submissions = _submissions_for_test(test.id, group_id)
    grades = _grades_for_test(test.id, group_id)

    avg_percentage = 0
    avg_score = 0
    max_score = 0
    if grades:
        avg_percentage = sum(g.percentage for g in grades) / len(grades)
        avg_score = sum(g.total_score for g in grades) / len(grades)
        max_score = grades[0].max_score

    submitted = [s for s in submissions if s.status in ('submitted', SUBMISSION_STATUS_GRADED)]
    pending_grade = len(submitted) - len(grades)

    return {
        "test_id": test.id,
        "test_name": test.name,
        "test_mode": getattr(test, 'test_mode', 'scheduled'),
        "created_at": test.created_at.isoformat() if test.created_at else None,
        "question_count": len(test.test_questions),
        "total_submissions": len(submissions),
        "submitted_count": len(submitted),
        "graded_submissions": len(grades),
        "pending_grade": max(0, pending_grade),
        "average_score": round(avg_score, 2),
        "average_percentage": round(avg_percentage, 2),
        "max_score": max_score,
    }


def _score_distribution(grades):
    """Bucket graded percentages for charts."""
    buckets = [
        ("0–49%", 0, 49),
        ("50–59%", 50, 59),
        ("60–69%", 60, 69),
        ("70–79%", 70, 79),
        ("80–89%", 80, 89),
        ("90–100%", 90, 100),
    ]
    counts = {label: 0 for label, _, _ in buckets}
    for g in grades:
        pct = g.percentage
        for label, lo, hi in buckets:
            if lo <= pct <= hi:
                counts[label] += 1
                break
    return [{"label": label, "count": counts[label]} for label, _, _ in buckets]


def _question_stats_for_test(test_id, group_id=None):
    """Per-question averages for a test."""
    test_questions = db_session.query(TestQuestion).filter_by(
        test_id=test_id
    ).order_by(TestQuestion.order).all()

    question_stats = []
    for tq in test_questions:
        question = tq.question
        max_points = tq.points if tq.points is not None else question.points
        answers = db_session.query(Answer).join(Submission).filter(
            Submission.test_id == test_id,
            Answer.question_id == question.id,
            Answer.score.isnot(None),
        )
        student_ids = _student_ids_for_group(group_id)
        if student_ids is not None:
            if not student_ids:
                answers = answers.filter(Submission.user_id == -1)
            else:
                answers = answers.filter(Submission.user_id.in_(student_ids))
        answers = answers.all()

        if answers:
            avg_score_q = sum(a.score for a in answers) / len(answers)
            avg_pct = (avg_score_q / max_points * 100) if max_points else 0
        else:
            avg_score_q = 0
            avg_pct = 0

        content = question.content or ''
        question_stats.append({
            "question_id": question.id,
            "order": tq.order,
            "type": question.type,
            "content": content[:100] + "..." if len(content) > 100 else content,
            "average_score": round(avg_score_q, 2),
            "average_percentage": round(avg_pct, 2),
            "max_points": max_points,
            "answer_count": len(answers),
        })

    return question_stats


@bp.route('/overview', methods=['GET'])
def get_overview():
    """Class overview with test summaries and weak topics."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    focus_test_id = request.args.get('test_id', type=int)
    group_id = _parse_group_id_param()

    student_query = db_session.query(User).filter_by(role=ROLE_STUDENT)
    student_ids = _student_ids_for_group(group_id)
    if student_ids is not None:
        total_students = len(student_ids)
    else:
        total_students = student_query.count()

    total_tests = db_session.query(func.count(Test.id)).scalar()
    total_questions = db_session.query(func.count(Question.id)).scalar()
    total_submissions = db_session.query(func.count(Submission.id))
    total_graded = db_session.query(func.count(Grade.id)).join(Submission)
    if student_ids is not None:
        if not student_ids:
            total_submissions = 0
            total_graded = 0
        else:
            total_submissions = total_submissions.filter(Submission.user_id.in_(student_ids)).scalar()
            total_graded = total_graded.filter(Submission.user_id.in_(student_ids)).scalar()
    else:
        total_submissions = total_submissions.scalar()
        total_graded = total_graded.scalar()

    tests = db_session.query(Test).order_by(Test.created_at.desc()).all()
    tests_summary = [_test_summary(t, group_id) for t in tests]

    latest_test_id = None
    for summary in tests_summary:
        if summary['graded_submissions'] > 0:
            latest_test_id = summary['test_id']
            break
    if latest_test_id is None and tests_summary:
        latest_test_id = tests_summary[0]['test_id']

    if focus_test_id is None:
        focus_test_id = latest_test_id

    focus_distribution = []
    focus_test_name = None
    if focus_test_id:
        test = db_session.query(Test).filter_by(id=focus_test_id).first()
        if test:
            focus_test_name = test.name
            grades = _grades_for_test(focus_test_id, group_id)
            focus_distribution = _score_distribution(grades)

    topics = _topic_statistics_list(group_id)
    weak_topics = sorted(
        [t for t in topics if t['submission_count'] > 0],
        key=lambda t: t['average_percentage'],
    )[:5]

    return jsonify({
        "total_students": total_students,
        "total_tests": total_tests,
        "total_questions": total_questions,
        "total_submissions": total_submissions,
        "total_graded": total_graded,
        "tests_summary": tests_summary,
        "latest_test_id": latest_test_id,
        "focus_test_id": focus_test_id,
        "focus_test_name": focus_test_name,
        "focus_distribution": focus_distribution,
        "weak_topics": weak_topics,
        "group_id": group_id,
    }), 200


@bp.route('/groups/compare', methods=['GET'])
def compare_groups():
    """Compare average scores across groups (includes Unassigned)."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    focus_test_id = request.args.get('test_id', type=int)
    group_entries = _group_entries_for_compare()
    tests = db_session.query(Test).order_by(Test.created_at.desc()).all()

    matrix = []
    chart_by_test = []
    all_pcts_by_group = {}

    for entry in group_entries:
        gid = entry["group_id"]
        row_tests = {}
        row_pcts = []
        for test in tests:
            grades = _grades_for_test(test.id, gid)
            if grades:
                avg = round(sum(g.percentage for g in grades) / len(grades), 2)
                row_tests[str(test.id)] = {
                    "test_id": test.id,
                    "test_name": test.name,
                    "average_percentage": avg,
                    "graded_count": len(grades),
                }
                row_pcts.extend(g.percentage for g in grades)
            else:
                row_tests[str(test.id)] = {
                    "test_id": test.id,
                    "test_name": test.name,
                    "average_percentage": None,
                    "graded_count": 0,
                }
        matrix.append({
            **entry,
            "tests": row_tests,
            "overall_average": round(sum(row_pcts) / len(row_pcts), 2) if row_pcts else None,
        })
        all_pcts_by_group[str(gid)] = row_pcts

    for test in tests:
        groups_data = []
        for entry in group_entries:
            gid = entry["group_id"]
            grades = _grades_for_test(test.id, gid)
            groups_data.append({
                "group_id": gid,
                "group_name": entry["group_name"],
                "average_percentage": round(sum(g.percentage for g in grades) / len(grades), 2) if grades else None,
                "graded_count": len(grades),
            })
        chart_by_test.append({
            "test_id": test.id,
            "test_name": test.name,
            "groups": groups_data,
        })

    distributions = []
    if focus_test_id:
        test = db_session.query(Test).filter_by(id=focus_test_id).first()
        if test:
            for entry in group_entries:
                gid = entry["group_id"]
                grades = _grades_for_test(focus_test_id, gid)
                distributions.append({
                    "group_id": gid,
                    "group_name": entry["group_name"],
                    "distribution": _score_distribution(grades),
                    "graded_count": len(grades),
                })

    return jsonify({
        "focus_test_id": focus_test_id,
        "tests": [{"test_id": t.id, "test_name": t.name} for t in tests],
        "groups": group_entries,
        "matrix": matrix,
        "chart_by_test": chart_by_test,
        "distributions": distributions,
    }), 200


@bp.route('/topics', methods=['GET'])
def get_topic_statistics():
    """Get statistics by topic."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    return jsonify(_topic_statistics_list(_parse_group_id_param())), 200


@bp.route('/tests', methods=['GET'])
def list_test_statistics():
    """List tests with summary stats; supports search and filters."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    q = (request.args.get('q') or '').strip().lower()
    mode = (request.args.get('mode') or '').strip()
    status_filter = (request.args.get('status') or 'all').strip()
    sort = (request.args.get('sort') or 'date').strip()
    group_id = _parse_group_id_param()

    tests = db_session.query(Test).all()
    result = []

    for test in tests:
        summary = _test_summary(test, group_id)

        if q and q not in test.name.lower():
            continue
        if mode and summary['test_mode'] != mode:
            continue
        if status_filter == 'has_submissions' and summary['total_submissions'] == 0:
            continue
        if status_filter == 'graded' and summary['graded_submissions'] == 0:
            continue
        if status_filter == 'pending' and summary['pending_grade'] == 0:
            continue

        result.append(summary)

    if sort == 'name':
        result.sort(key=lambda x: x['test_name'].lower())
    elif sort == 'avg_score':
        result.sort(key=lambda x: x['average_percentage'], reverse=True)
    else:
        result.sort(key=lambda x: x['created_at'] or '', reverse=True)

    return jsonify(result), 200


@bp.route('/students', methods=['GET'])
def get_student_statistics():
    """Get statistics by student; optional search query."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    q = (request.args.get('q') or '').strip().lower()
    group_id = _parse_group_id_param()
    students = db_session.query(User).filter_by(role='student').order_by(User.username).all()
    student_ids = _student_ids_for_group(group_id)

    result = []
    for student in students:
        if student_ids is not None and student.id not in student_ids:
            continue
        if q:
            haystack = f"{student.username} {student.student_id or ''}".lower()
            if q not in haystack:
                continue

        grades = db_session.query(Grade).join(Submission).filter(
            Submission.user_id == student.id
        ).all()

        submissions = db_session.query(Submission).filter_by(user_id=student.id).count()

        if grades:
            avg_percentage = sum(g.percentage for g in grades) / len(grades)
            total_tests_graded = len(grades)
        else:
            avg_percentage = 0
            total_tests_graded = 0

        result.append({
            "student_id": student.id,
            "username": student.username,
            "student_id_number": student.student_id,
            "group_id": student.group_id,
            "group_name": student.group.name if student.group else "Unassigned",
            "total_submissions": submissions,
            "total_tests_graded": total_tests_graded,
            "average_percentage": round(avg_percentage, 2),
        })

    return jsonify(result), 200


@bp.route('/students/<int:student_id>', methods=['GET'])
def get_student_detail(student_id):
    """Detailed statistics for one student."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    student = db_session.query(User).filter_by(id=student_id, role='student').first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    submissions = db_session.query(Submission).filter_by(user_id=student.id).order_by(
        Submission.submitted_at.desc(),
        Submission.started_at.desc(),
    ).all()

    tests_data = []
    grades = []
    for sub in submissions:
        grade = sub.grade
        tests_data.append({
            "test_id": sub.test_id,
            "test_name": sub.test.name if sub.test else None,
            "submission_id": sub.id,
            "status": sub.status,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
            "total_score": grade.total_score if grade else None,
            "max_score": grade.max_score if grade else None,
            "percentage": round(grade.percentage, 2) if grade else None,
            "is_graded": grade is not None,
        })
        if grade:
            grades.append(grade)

    avg_percentage = round(sum(g.percentage for g in grades) / len(grades), 2) if grades else 0

    # Per-test average for trend chart
    test_chart = [
        {"test_name": t['test_name'], "percentage": t['percentage']}
        for t in reversed(tests_data) if t['percentage'] is not None
    ]

    return jsonify({
        "student_id": student.id,
        "username": student.username,
        "student_id_number": student.student_id,
        "total_submissions": len(submissions),
        "total_graded": len(grades),
        "average_percentage": avg_percentage,
        "tests": tests_data,
        "test_chart": test_chart,
    }), 200


@bp.route('/students/<int:student_id>/tests/<int:test_id>', methods=['GET'])
def get_student_test_detail(student_id, test_id):
    """Per-question score summary for one student on one test."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    student = db_session.query(User).filter_by(id=student_id, role='student').first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    test = db_session.query(Test).filter_by(id=test_id).first()
    if not test:
        return jsonify({"error": "Test not found"}), 404

    submission = db_session.query(Submission).filter_by(
        test_id=test_id, user_id=student_id
    ).order_by(Submission.started_at.desc()).first()

    if not submission:
        return jsonify({"error": "No submission for this test"}), 404

    grade = submission.grade
    answers = {a.question_id: a for a in submission.answers}

    test_questions = db_session.query(TestQuestion).filter_by(
        test_id=test_id
    ).order_by(TestQuestion.order).all()

    questions = []
    for tq in test_questions:
        q = tq.question
        max_points = tq.points if tq.points is not None else q.points
        answer = answers.get(q.id)
        score = answer.score if answer and answer.score is not None else None
        pct = round((score / max_points) * 100, 2) if score is not None and max_points else None
        content = q.content or ''
        questions.append({
            "question_id": q.id,
            "order": tq.order,
            "type": q.type,
            "content": content[:120] + "..." if len(content) > 120 else content,
            "max_points": max_points,
            "score": score,
            "percentage": pct,
        })

    return jsonify({
        "student_id": student.id,
        "username": student.username,
        "test_id": test.id,
        "test_name": test.name,
        "submission_id": submission.id,
        "status": submission.status,
        "total_score": grade.total_score if grade else None,
        "max_score": grade.max_score if grade else None,
        "percentage": round(grade.percentage, 2) if grade else None,
        "questions": questions,
    }), 200


@bp.route('/tests/<int:test_id>', methods=['GET'])
def get_test_statistics(test_id):
    """Detailed statistics for one test including student results."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status

    test = db_session.query(Test).filter_by(id=test_id).first()
    if not test:
        return jsonify({"error": "Test not found"}), 404

    group_id = _parse_group_id_param()
    submissions = _submissions_for_test(test_id, group_id)
    grades = _grades_for_test(test_id, group_id)
    grade_by_sub = {g.submission_id: g for g in grades}

    if grades:
        avg_score = sum(g.total_score for g in grades) / len(grades)
        avg_percentage = sum(g.percentage for g in grades) / len(grades)
        max_score = grades[0].max_score
    else:
        avg_score = 0
        avg_percentage = 0
        max_score = 0

    student_results = []
    for sub in submissions:
        grade = grade_by_sub.get(sub.id)
        student_results.append({
            "submission_id": sub.id,
            "student_id": sub.user_id,
            "username": sub.user.username if sub.user else None,
            "student_id_number": sub.user.student_id if sub.user else None,
            "status": sub.status,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
            "total_score": grade.total_score if grade else None,
            "max_score": grade.max_score if grade else None,
            "percentage": round(grade.percentage, 2) if grade else None,
            "is_graded": grade is not None,
        })

    student_results.sort(
        key=lambda r: (r['percentage'] is None, -(r['percentage'] or 0))
    )

    return jsonify({
        "test_id": test_id,
        "test_name": test.name,
        "test_mode": getattr(test, 'test_mode', 'scheduled'),
        "total_submissions": len(submissions),
        "graded_submissions": len(grades),
        "pending_grade": max(0, len([s for s in submissions if s.status in ('submitted', SUBMISSION_STATUS_GRADED)]) - len(grades)),
        "average_score": round(avg_score, 2),
        "average_percentage": round(avg_percentage, 2),
        "max_score": max_score,
        "score_distribution": _score_distribution(grades),
        "question_statistics": _question_stats_for_test(test_id, group_id),
        "student_results": student_results,
        "group_id": group_id,
    }), 200
