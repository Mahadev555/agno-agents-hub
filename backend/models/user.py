"""
User accounts.

Everything created in the hub belongs to a user. Before this, every endpoint was
unauthenticated: anyone reachable on the network could read, edit, or delete any
agent, and spend the deployment's LLM budget.
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from models.base import Base, utcnow


class User(Base):
    """A registered account."""

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(320), nullable=False, unique=True, index=True)

    # Argon2id hash. Never the password itself, and never returned by the API.
    password_hash = Column(String(255), nullable=False)

    display_name = Column(String(120), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Reserved for future admin-only operations; not yet used for elevation.
    is_admin = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    last_login_at = Column(DateTime, nullable=True)

    def to_dict(self):
        """Public representation. Deliberately excludes password_hash."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }

    def __repr__(self):
        return f"<User(id={self.user_id}, email='{self.email}')>"
