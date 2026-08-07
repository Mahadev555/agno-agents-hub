"""
Per-user limits on run creation.

Runs are the only endpoint that spends real money, so the limits are counted
there rather than as a blanket request-per-second cap. Two separate concerns:

  * hourly volume  - stops a script from burning the token budget overnight
  * concurrency    - stops one user from occupying every worker at once

Hourly volume is counted from the runs table so it survives a restart and is
consistent across processes. Concurrency is tracked in memory, because it is
about what this process is currently executing.
"""

import logging
from datetime import timedelta
from typing import Dict

from sqlalchemy import func

from config import get_settings
from connection import session_scope
from models.base import utcnow
from models.run import Run

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when a user is over a limit. Carries a retry hint in seconds."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


# user_id -> number of runs this process is currently executing.
_in_flight: Dict[int, int] = {}


def check_hourly_quota(user_id: int) -> None:
    """Refuse if the user started too many runs in the last hour."""
    settings = get_settings()
    limit = settings.run_rate_limit_per_hour
    since = utcnow() - timedelta(hours=1)

    with session_scope() as session:
        used = (
            session.query(func.count(Run.run_id))
            .filter(Run.owner_id == user_id, Run.created_at >= since)
            .scalar()
        ) or 0

    if used >= limit:
        logger.warning(f"User {user_id} hit the hourly run quota ({used}/{limit})")
        raise RateLimitExceeded(
            f"Run limit reached: {limit} runs per hour. Try again later.",
            retry_after=3600,
        )


def check_concurrency(user_id: int) -> None:
    """Refuse if the user already has the maximum number of runs in flight."""
    settings = get_settings()
    limit = settings.run_concurrency_per_user
    current = _in_flight.get(user_id, 0)

    if current >= limit:
        raise RateLimitExceeded(
            f"You already have {current} runs in progress (limit {limit}). "
            "Wait for one to finish.",
            retry_after=30,
        )


def acquire(user_id: int) -> None:
    """Record that a run has started. Pair with release() in a finally block."""
    _in_flight[user_id] = _in_flight.get(user_id, 0) + 1


def release(user_id: int) -> None:
    """Record that a run has finished."""
    remaining = _in_flight.get(user_id, 0) - 1
    if remaining > 0:
        _in_flight[user_id] = remaining
    else:
        _in_flight.pop(user_id, None)


def enforce(user_id: int) -> None:
    """Run every check before a run is accepted."""
    check_concurrency(user_id)
    check_hourly_quota(user_id)


def in_flight_count(user_id: int) -> int:
    """Current in-flight runs for a user, for diagnostics and tests."""
    return _in_flight.get(user_id, 0)
