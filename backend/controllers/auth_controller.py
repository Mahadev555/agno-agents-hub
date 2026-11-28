"""
Auth Controller

Registration, sign-in, and the current-user endpoint.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, Field, TypeAdapter, ValidationError

from config import get_settings
from services.auth_service import (
    MIN_PASSWORD_LENGTH,
    AdminBootstrapError,
    AuthError,
    AuthService,
    create_access_token,
)

logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    """New account details."""

    email: EmailStr
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=1024)
    display_name: Optional[str] = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    """Sign-in credentials."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    """An issued access token and the account it belongs to."""

    access_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]


class BootstrapAdminResponse(BaseModel):
    """Non-sensitive result of the one-time admin bootstrap."""

    created: bool
    message: str


class AuthController:
    """Handles authentication endpoints."""

    @staticmethod
    async def register(payload: RegisterRequest) -> TokenResponse:
        """
        Create an account and sign in immediately.

        Registration can be closed off with ALLOW_REGISTRATION=false once the
        intended users exist.
        """
        settings = get_settings()
        if not settings.allow_registration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration is closed on this deployment",
            )

        try:
            user = AuthService.register(
                email=payload.email,
                password=payload.password,
                display_name=payload.display_name,
            )
        except AuthError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        token = create_access_token(
            user["user_id"], user["email"], is_admin=user.get("is_admin", False)
        )
        return TokenResponse(**token, user=user)

    @staticmethod
    async def login(payload: LoginRequest) -> TokenResponse:
        """Exchange credentials for an access token."""
        try:
            user = AuthService.authenticate(payload.email, payload.password)
        except AuthError as exc:
            # 401 for any credential failure, with no hint about which part
            # was wrong.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(
            user["user_id"], user["email"], is_admin=user.get("is_admin", False)
        )
        return TokenResponse(**token, user=user)

    @staticmethod
    async def bootstrap_admin() -> BootstrapAdminResponse:
        """Create the first administrator using credentials from environment."""
        settings = get_settings()
        email = settings.bootstrap_admin_email
        password = settings.bootstrap_admin_password
        if not email:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Admin bootstrap email is not configured",
            )

        try:
            email = str(TypeAdapter(EmailStr).validate_python(email))
            if AuthService.is_admin_account(email):
                return BootstrapAdminResponse(
                    created=False, message="Admin account is already present"
                )
            if not password:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Admin bootstrap password is not configured",
                )
            AuthService.create_initial_admin(
                email=email,
                password=password,
                display_name="Administrator",
            )
        except AdminBootstrapError:
            return BootstrapAdminResponse(
                created=False, message="Admin account is already present"
            )
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Configured admin email is invalid",
            ) from exc
        except AuthError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        return BootstrapAdminResponse(created=True, message="Admin account created")

    @staticmethod
    async def me(user: Dict[str, Any]) -> Dict[str, Any]:
        """Return the signed-in account."""
        return user
