"""
Shared SQLAlchemy declarative base.

Every model must inherit from this single Base so that create_all() (and later,
Alembic autogenerate) sees one consistent metadata registry.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utcnow() -> datetime:
    """
    Current UTC time as a naive datetime.

    datetime.utcnow() is deprecated in 3.12 and scheduled for removal, but the
    timestamp columns are naive DateTime, so strip the tzinfo rather than mixing
    aware and naive values in the same column.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
