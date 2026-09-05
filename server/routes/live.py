"""Live test session control routes."""

from flask import Blueprint, request, jsonify, session
from server.database import db_session
from server.models import Test
from server.services.live_session import (
    get_active_live_session, live_session_info,
    start_live_session, extend_live_session, end_live_session,
    finalize_expired_live_sessions,
)
from shared.constants import API_TESTS, TEST_MODE_LIVE

bp = Blueprint('live', __name__, url_prefix=API_TESTS)


def _require_lecturer():
    user_id = session.get('user_id')
    if not user_id:
        return None, jsonify({"error": "Not authenticated"}), 401
    from server.models import User
    user = db_session.query(User).filter_by(id=user_id).first()
    if not user or user.role != 'lecturer':
        return None, jsonify({"error": "Only lecturers can perform this action"}), 403
    return user, None, None


def _get_live_test(test_id):
    test = db_session.query(Test).filter_by(id=test_id).first()
    if not test:
        return None, jsonify({"error": "Test not found"}), 404
    if test.test_mode != TEST_MODE_LIVE:
        return None, jsonify({"error": "Test is not in live mode"}), 400
    return test, None, None


@bp.route('/<int:test_id>/live/status', methods=['GET'])
def live_status(test_id):
    """Get current live session status."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    test, err, code = _get_live_test(test_id)
    if err:
        return err, code

    finalize_expired_live_sessions(test_id, db_session)
    live_session = get_active_live_session(test, db_session)
    return jsonify({
        "test_id": test.id,
        "test_mode": test.test_mode,
        **live_session_info(live_session),
    }), 200


@bp.route('/<int:test_id>/live/start', methods=['POST'])
def live_start(test_id):
    """Start a live session with a duration in minutes."""
    user, err, code = _require_lecturer()
    if err:
        return err, code

    test, err, code = _get_live_test(test_id)
    if err:
        return err, code

    data = request.get_json() or {}
    duration = data.get('duration_minutes', 0)
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        return jsonify({"error": "duration_minutes must be a number"}), 400

    try:
        live_session = start_live_session(test, duration, user.id, db_session)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "message": "Live session started",
        **live_session_info(live_session),
    }), 201


@bp.route('/<int:test_id>/live/extend', methods=['POST'])
def live_extend(test_id):
    """Extend the active live session."""
    user, err, code = _require_lecturer()
    if err:
        return err, code

    test, err, code = _get_live_test(test_id)
    if err:
        return err, code

    data = request.get_json() or {}
    minutes = data.get('minutes', 0)
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return jsonify({"error": "minutes must be a number"}), 400

    try:
        live_session = extend_live_session(test, minutes, db_session)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "message": "Live session extended",
        **live_session_info(live_session),
    }), 200


@bp.route('/<int:test_id>/live/end', methods=['POST'])
def live_end(test_id):
    """End the active live session early."""
    user, err, code = _require_lecturer()
    if err:
        return err, code

    test, err, code = _get_live_test(test_id)
    if err:
        return err, code

    try:
        live_session = end_live_session(test, db_session)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "message": "Live session ended",
        **live_session_info(live_session),
    }), 200
