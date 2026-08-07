"""
Authentication: password hashing, token issuance, and user lookup.

Argon2id is used rather than bcrypt because bcrypt silently truncates passwords
at 72 bytes, which turns a long passphrase into a weaker secret than the user
believes they chose.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from config import get_settings
from connection import session_scope
from models.base import utcnow
from models.user import User

logger = logging.getLogger(__name__)

_hasher = PasswordHasher()

# Minimum viable length. Long passphrases beat short complex strings, and argon2
# has no upper bound to work around.
MIN_PASSWORD_LENGTH = 10


class AuthError(Exception):
    """Raised for any credential or token problem."""


def hash_password(password: str) -> str:
    """Hash a password with Argon2id."""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against its hash."""
    try:
        _hasher.verify(password_hash, password)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(user_id: int, email: str) -> Dict[str, Any]:
    """Issue a signed access token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_ttl_minutes)

    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    token = jwt.encode(
        payload, settings.resolved_jwt_secret(), algorithm=settings.jwt_algorithm
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.access_token_ttl_minutes * 60,
    }


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Verify a token and return its claims.

    The algorithm is pinned so a token cannot ask to be verified with `none`.
    """
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.resolved_jwt_secret(),
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid token") from exc


class AuthService:
    """User registration and sign-in."""

    @staticmethod
    def register(email: str, password: str, display_name: str = None) -> Dict[str, Any]:
        """
        Create an account.

        The first account created becomes an admin so a fresh deployment has
        someone who can manage it.
        """
        email = (email or "").strip().lower()
        if not email:
            raise AuthError("Email is required")

        password_hash = hash_password(password)

        with session_scope() as session:
            if session.query(User).filter(User.email == email).first():
                raise AuthError("An account with that email already exists")

            is_first = session.query(User).count() == 0

            user = User(
                email=email,
                password_hash=password_hash,
                display_name=display_name or email.split("@")[0],
                is_active=True,
                is_admin=is_first,
            )
            session.add(user)
            session.flush()
            record = user.to_dict()

        logger.info(f"Registered user {email} (id={record['user_id']}, admin={record['is_admin']})")
        return record

    @staticmethod
    def authenticate(email: str, password: str) -> Dict[str, Any]:
        """
        Verify credentials and return the user.

        The same message is returned for an unknown email and a wrong password,
        so the endpoint cannot be used to enumerate registered accounts.
        """
        email = (email or "").strip().lower()

        with session_scope() as session:
            user = session.query(User).filter(User.email == email).first()

            if not user or not verify_password(password, user.password_hash):
                logger.warning(f"Failed sign-in attempt for {email!r}")
                raise AuthError("Incorrect email or password")

            if not user.is_active:
                raise AuthError("This account is disabled")

            user.last_login_at = utcnow()
            session.flush()
            return user.to_dict()

    @staticmethod
    def get_user(user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a user by id."""
        with session_scope() as session:
            user = session.query(User).filter(User.user_id == user_id).first()
            return user.to_dict() if user else None
