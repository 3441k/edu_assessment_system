"""Live test session control for lecturer-managed tests."""

from datetime import datetime, timedelta

from server.models import LiveSession, Submission
from shared.constants import (
    LIVE_SESSION_LIVE, LIVE_SESSION_ENDED,
    SUBMISSION_STATUS_IN_PROGRESS, SUBMISSION_STATUS_SUBMITTED,
    TEST_MODE_LIVE,
)


def get_active_live_session(test, db_session):
    """Return the current live session for a test, finalizing expired ones."""
    if test.test_mode != TEST_MODE_LIVE:
        return None
    finalize_expired_live_sessions(test.id, db_session)
    return db_session.query(LiveSession).filter_by(
        test_id=test.id, status=LIVE_SESSION_LIVE
    ).order_by(LiveSession.started_at.desc()).first()


def live_session_info(live_session, now=None):
    """Serialize live session state for API responses."""
    if not live_session:
        return {
            "live_status": "waiting",
            "live_session_id": None,
            "live_started_at": None,
            "live_ends_at": None,
            "live_seconds_remaining": None,
        }
    now = now or datetime.utcnow()
    remaining = max(0, int((live_session.ends_at - now).total_seconds()))
    if live_session.status == LIVE_SESSION_ENDED or remaining <= 0:
        status = "ended"
    else:
        status = "live"
    return {
        "live_status": status,
        "live_session_id": live_session.id,
        "live_started_at": live_session.started_at.isoformat() if live_session.started_at else None,
        "live_ends_at": live_session.ends_at.isoformat() if live_session.ends_at else None,
        "live_seconds_remaining": remaining if status == "live" else 0,
        "live_duration_minutes": live_session.duration_minutes,
    }


def auto_submit_session_submissions(live_session_id, db_session):
    """Auto-submit all in-progress submissions for a live session."""
    submissions = db_session.query(Submission).filter_by(
        live_session_id=live_session_id,
        status=SUBMISSION_STATUS_IN_PROGRESS,
    ).all()
    now = datetime.utcnow()
    for submission in submissions:
        submission.status = SUBMISSION_STATUS_SUBMITTED
        submission.submitted_at = now
    if submissions:
        db_session.commit()
    return len(submissions)


def finalize_expired_live_sessions(test_id=None, db_session=None):
    """End live sessions past their deadline and auto-submit submissions."""
    now = datetime.utcnow()
    query = db_session.query(LiveSession).filter(
        LiveSession.status == LIVE_SESSION_LIVE,
        LiveSession.ends_at <= now,
    )
    if test_id:
        query = query.filter_by(test_id=test_id)
    expired = query.all()
    for live_session in expired:
        live_session.status = LIVE_SESSION_ENDED
        live_session.ended_at = now
        auto_submit_session_submissions(live_session.id, db_session)
    if expired:
        db_session.commit()
    return len(expired)


def start_live_session(test, duration_minutes, lecturer_id, db_session):
    """Start a new live session (ends any active session first)."""
    if test.test_mode != TEST_MODE_LIVE:
        raise ValueError("Test is not in live mode")
    if duration_minutes <= 0:
        raise ValueError("Duration must be positive")

    active = db_session.query(LiveSession).filter_by(
        test_id=test.id, status=LIVE_SESSION_LIVE
    ).first()
    if active:
        end_live_session(test, db_session)

    now = datetime.utcnow()
    live_session = LiveSession(
        test_id=test.id,
        started_at=now,
        ends_at=now + timedelta(minutes=duration_minutes),
        status=LIVE_SESSION_LIVE,
        started_by=lecturer_id,
        duration_minutes=duration_minutes,
    )
    db_session.add(live_session)
    db_session.commit()
    db_session.refresh(live_session)
    return live_session


def extend_live_session(test, minutes, db_session):
    """Extend the active live session."""
    live_session = get_active_live_session(test, db_session)
    if not live_session:
        raise ValueError("No active live session")
    if minutes <= 0:
        raise ValueError("Extension must be positive")
    live_session.ends_at += timedelta(minutes=minutes)
    live_session.duration_minutes += minutes
    db_session.commit()
    db_session.refresh(live_session)
    return live_session


def end_live_session(test, db_session):
    """End the active live session early and auto-submit."""
    live_session = db_session.query(LiveSession).filter_by(
        test_id=test.id, status=LIVE_SESSION_LIVE
    ).first()
    if not live_session:
        raise ValueError("No active live session")
    now = datetime.utcnow()
    live_session.status = LIVE_SESSION_ENDED
    live_session.ended_at = now
    live_session.ends_at = min(live_session.ends_at, now)
    db_session.commit()
    auto_submit_session_submissions(live_session.id, db_session)
    db_session.refresh(live_session)
    return live_session
