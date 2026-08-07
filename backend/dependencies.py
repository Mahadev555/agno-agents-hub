"""
Shared FastAPI dependencies.

`get_current_user` is the single gate every protected route passes through, so
authentication cannot be forgotten on one endpoint while present on its
neighbours.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth_service import AuthError, AuthService, decode_access_token

logger = logging.getLogger(__name__)

# auto_error=False so a missing header produces our own 401 with a WWW-
# Authenticate hint rather than Starlette's bare 403.
_bearer = HTTPBearer(auto_error=False)

UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Dict[str, Any]:
    """
    Resolve the signed-in user, or reject the request.

    The user is re-read from the database on every request so a disabled or
    deleted account stops working immediately instead of surviving until its
    token expires.
    """
    if credentials is None or not credentials.credentials:
        raise UNAUTHENTICATED

    try:
        claims = decode_access_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        user_id = int(claims.get("sub", ""))
    except (TypeError, ValueError):
        raise UNAUTHENTICATED

    user = AuthService.get_user(user_id)
    if not user:
        raise UNAUTHENTICATED
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled"
        )

    return user


async def get_current_user_sse(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    access_token: Optional[str] = Query(
        None, description="Token for EventSource, which cannot send headers"
    ),
) -> Dict[str, Any]:
    """
    Authenticate an EventSource subscriber.

    The browser EventSource API cannot set an Authorization header, so this
    endpoint also accepts the token as a query parameter.

    Caveat: query strings commonly appear in web-server access logs and proxy
    logs, so this token is more exposed than one sent in a header. A short-lived
    single-use stream ticket would avoid that; until then, keep token TTLs
    modest and avoid logging full URLs.
    """
    token = credentials.credentials if credentials else access_token
    if not token:
        raise UNAUTHENTICATED

    try:
        claims = decode_access_token(token)
        user_id = int(claims.get("sub", ""))
    except (AuthError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = AuthService.get_user(user_id)
    if not user or not user.get("is_active"):
        raise UNAUTHENTICATED
    return user


async def get_current_admin(
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Require an admin account."""
    if not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required"
        )
    return user


def require_owner(resource: Dict[str, Any], user: Dict[str, Any], label: str) -> None:
    """
    Authorize a write against a resource the caller must own.

    Public resources are readable by anyone signed in but never writable, so
    sharing an agent cannot let a stranger edit or delete it.

    Rows predating auth have owner_id = None and are treated as unowned: only an
    admin may modify them, rather than silently granting everyone access.
    """
    owner_id = resource.get("owner_id")

    if owner_id is None:
        if user.get("is_admin"):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This {label} has no owner and can only be modified by an administrator",
        )

    if owner_id != user["user_id"] and not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to modify this {label}",
        )


def can_read(resource: Dict[str, Any], user: Dict[str, Any]) -> bool:
    """Whether the caller may read a resource: owned, public, unowned, or admin."""
    if user.get("is_admin"):
        return True
    if resource.get("is_public"):
        return True
    owner_id = resource.get("owner_id")
    return owner_id is None or owner_id == user["user_id"]
