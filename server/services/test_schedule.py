"""Test availability window, live sessions, and deadline helpers."""

from datetime import datetime, timedelta

from shared.constants import (
    SUBMISSION_STATUS_IN_PROGRESS, TEST_MODE_LIVE,
    LIVE_SESSION_LIVE,
)


def _is_live_mode(test):
    return getattr(test, 'test_mode', 'scheduled') == TEST_MODE_LIVE


def get_availability_status(test, live_session=None, now=None):
    """Return availability: scheduled uses upcoming/open/closed; live uses waiting/live/ended."""
    now = now or datetime.utcnow()
    if _is_live_mode(test):
        if not live_session or live_session.status != LIVE_SESSION_LIVE:
            return 'ended' if live_session else 'waiting'
        if now >= live_session.ends_at:
            return 'ended'
        return 'live'
    if test.available_from and now < test.available_from:
        return 'upcoming'
    if test.available_until and now > test.available_until:
        return 'closed'
    return 'open'


def get_submission_deadline(test, submission, live_session=None):
    """Return the earliest applicable deadline for an in-progress submission."""
    if _is_live_mode(test):
        if live_session and live_session.status == LIVE_SESSION_LIVE:
            return live_session.ends_at
        if submission and submission.live_session:
            return submission.live_session.ends_at
        return None
    deadlines = []
    if submission and submission.started_at and test.time_limit:
        deadlines.append(submission.started_at + timedelta(minutes=test.time_limit))
    if test.available_until:
        deadlines.append(test.available_until)
    if not deadlines:
        return None
    return min(deadlines)


def get_seconds_remaining(test, submission, live_session=None, now=None):
    now = now or datetime.utcnow()
    deadline = get_submission_deadline(test, submission, live_session)
    if not deadline:
        return None
    return max(0, int((deadline - now).total_seconds()))


def is_submission_time_expired(test, submission, live_session=None, now=None):
    now = now or datetime.utcnow()
    deadline = get_submission_deadline(test, submission, live_session)
    if not deadline:
        return False
    return now >= deadline


def can_start_test(test, live_session=None, now=None):
    now = now or datetime.utcnow()
    if _is_live_mode(test):
        return (
            live_session is not None
            and live_session.status == LIVE_SESSION_LIVE
            and now < live_session.ends_at
        )
    return get_availability_status(test, None, now) == 'open'


def can_access_test(test, submission, live_session=None, now=None):
    now = now or datetime.utcnow()
    if submission and submission.status == SUBMISSION_STATUS_IN_PROGRESS:
        if _is_live_mode(test) and live_session:
            if submission.live_session_id != live_session.id:
                return False
        return not is_submission_time_expired(test, submission, live_session, now)
    return can_start_test(test, live_session, now)


def submission_timing_info(test, submission, live_session=None, now=None):
    now = now or datetime.utcnow()
    deadline = get_submission_deadline(test, submission, live_session) if submission else (
        live_session.ends_at if live_session and _is_live_mode(test) else None
    )
    seconds_remaining = None
    if _is_live_mode(test) and live_session and live_session.status == LIVE_SESSION_LIVE:
        seconds_remaining = max(0, int((live_session.ends_at - now).total_seconds()))
    elif submission:
        seconds_remaining = get_seconds_remaining(test, submission, live_session, now)

    info = {
        'started_at': submission.started_at.isoformat() if submission and submission.started_at else None,
        'deadline_at': deadline.isoformat() if deadline else None,
        'seconds_remaining': seconds_remaining,
        'time_expired': is_submission_time_expired(test, submission, live_session, now) if submission else False,
        'availability_status': get_availability_status(test, live_session, now),
        'available_from': test.available_from.isoformat() if test.available_from else None,
        'available_until': test.available_until.isoformat() if test.available_until else None,
        'time_limit': test.time_limit,
        'test_mode': getattr(test, 'test_mode', 'scheduled'),
    }
    if _is_live_mode(test) and live_session:
        info['live_session_id'] = live_session.id
    return info


def auto_submit_if_expired(submission, db_session, live_session=None):
    from shared.constants import SUBMISSION_STATUS_SUBMITTED
    if submission.status != SUBMISSION_STATUS_IN_PROGRESS:
        return False
    test = submission.test
    if is_submission_time_expired(test, submission, live_session):
        submission.status = SUBMISSION_STATUS_SUBMITTED
        submission.submitted_at = datetime.utcnow()
        db_session.commit()
        return True
    return False
