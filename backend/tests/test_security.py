"""
Security tests: authentication, authorization, SSRF egress, and rate limits.

These cost no API quota. They cover the things that, if they regress, expose
other people's data or let a stranger spend the deployment's LLM budget.
"""

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dependencies import can_read, require_owner  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from runtime.mcp_guard import MCPEndpointBlocked, validate_mcp_url  # noqa: E402
from services import rate_limit  # noqa: E402
from services.auth_service import (  # noqa: E402
    AuthError,
    AuthService,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# --------------------------- passwords ---------------------------


def test_password_hash_is_not_the_password():
    hashed = hash_password("a-sufficiently-long-passphrase")
    assert "a-sufficiently-long-passphrase" not in hashed
    assert hashed.startswith("$argon2")


def test_password_verification():
    hashed = hash_password("a-sufficiently-long-passphrase")
    assert verify_password("a-sufficiently-long-passphrase", hashed)
    assert not verify_password("wrong-passphrase-here", hashed)


def test_hashes_are_salted():
    """Two identical passwords must not produce the same hash."""
    assert hash_password("same-password-value") != hash_password("same-password-value")


def test_short_password_rejected():
    with pytest.raises(AuthError, match="at least"):
        hash_password("short")


def test_long_passwords_are_not_truncated():
    """
    bcrypt silently ignores anything past 72 bytes, which would make these two
    passphrases interchangeable. Argon2 has no such limit.
    """
    base = "x" * 80
    hashed = hash_password(base + "AAAA")
    assert not verify_password(base + "BBBB", hashed)


# ---------------------------- tokens -----------------------------


def test_token_round_trip():
    token = create_access_token(42, "user@example.com")["access_token"]
    claims = decode_access_token(token)
    assert claims["sub"] == "42"
    assert claims["email"] == "user@example.com"
    assert claims["exp"] > claims["iat"]


def test_tampered_token_rejected():
    token = create_access_token(42, "user@example.com")["access_token"]
    with pytest.raises(AuthError):
        decode_access_token(token[:-4] + "AAAA")


def test_garbage_token_rejected():
    with pytest.raises(AuthError):
        decode_access_token("not-a-real-token")


def test_alg_none_token_rejected():
    """
    A token asking to be verified with alg=none must not be accepted; the
    decoder pins the algorithm.
    """
    import jwt

    forged = jwt.encode({"sub": "1"}, key="", algorithm="none")
    with pytest.raises(AuthError):
        decode_access_token(forged)


# ------------------------- authorization -------------------------

OWNER = {"user_id": 1, "is_admin": False}
STRANGER = {"user_id": 2, "is_admin": False}
ADMIN = {"user_id": 3, "is_admin": True}


def test_owner_can_read_and_write_own_private_resource():
    resource = {"owner_id": 1, "is_public": False}
    assert can_read(resource, OWNER)
    require_owner(resource, OWNER, "agent")  # no raise


def test_stranger_cannot_read_private_resource():
    assert not can_read({"owner_id": 1, "is_public": False}, STRANGER)


def test_public_resource_is_readable_but_not_writable():
    """Sharing an agent must not let a stranger edit or delete it."""
    resource = {"owner_id": 1, "is_public": True}
    assert can_read(resource, STRANGER)
    with pytest.raises(HTTPException) as exc:
        require_owner(resource, STRANGER, "agent")
    assert exc.value.status_code == 403


def test_admin_can_read_and_write_anything():
    resource = {"owner_id": 1, "is_public": False}
    assert can_read(resource, ADMIN)
    require_owner(resource, ADMIN, "agent")


def test_unowned_resource_is_admin_only_for_writes():
    """Pre-auth rows must not become writable by everyone."""
    resource = {"owner_id": None, "is_public": False}
    assert can_read(resource, STRANGER)
    with pytest.raises(HTTPException) as exc:
        require_owner(resource, STRANGER, "agent")
    assert exc.value.status_code == 403
    require_owner(resource, ADMIN, "agent")  # admin may


# ---------------------------- SSRF -------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data/",  # cloud instance metadata
        "http://127.0.0.1:3001/sse",
        "http://10.0.0.5/sse",
        "http://192.168.1.10/sse",
        "http://172.16.5.4/sse",
        "http://[::1]:3001/sse",
    ],
)
def test_internal_addresses_are_blocked(url):
    with pytest.raises(MCPEndpointBlocked):
        validate_mcp_url(url)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "gopher://evil/", "ftp://host/x"])
def test_non_http_schemes_blocked(url):
    with pytest.raises(MCPEndpointBlocked, match="scheme"):
        validate_mcp_url(url)


def test_empty_url_blocked():
    with pytest.raises(MCPEndpointBlocked):
        validate_mcp_url("")


def test_public_host_allowed():
    assert validate_mcp_url("https://example.com/sse")


def test_allowlist_permits_a_named_host(monkeypatch):
    """Local development needs an explicit opt-in for localhost."""
    from config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "localhost:3001")
    try:
        assert validate_mcp_url("http://localhost:3001/sse")
        # A different internal host is still refused.
        with pytest.raises(MCPEndpointBlocked):
            validate_mcp_url("http://169.254.169.254/")
    finally:
        get_settings.cache_clear()


# -------------------------- rate limits --------------------------


def test_concurrency_limit_blocks_then_recovers():
    user_id = 10_000_000 + int(uuid.uuid4().int % 1000)

    for _ in range(3):
        rate_limit.check_concurrency(user_id)
        rate_limit.acquire(user_id)

    assert rate_limit.in_flight_count(user_id) == 3
    with pytest.raises(rate_limit.RateLimitExceeded):
        rate_limit.check_concurrency(user_id)

    rate_limit.release(user_id)
    rate_limit.check_concurrency(user_id)  # a slot freed up

    rate_limit.release(user_id)
    rate_limit.release(user_id)
    assert rate_limit.in_flight_count(user_id) == 0


def test_release_never_goes_negative():
    """A double release must not leave a phantom free slot."""
    user_id = 10_000_999
    rate_limit.release(user_id)
    rate_limit.release(user_id)
    assert rate_limit.in_flight_count(user_id) == 0


def test_rate_limit_error_carries_retry_hint():
    error = rate_limit.RateLimitExceeded("slow down", retry_after=42)
    assert error.retry_after == 42


# --------------------------- accounts ----------------------------


def test_registration_rejects_duplicate_email():
    email = f"__test_{uuid.uuid4().hex[:10]}@example.com"
    AuthService.register(email, "a-long-enough-passphrase")
    try:
        with pytest.raises(AuthError, match="already exists"):
            AuthService.register(email, "a-long-enough-passphrase")
    finally:
        _delete_user(email)


def test_authenticate_gives_identical_error_for_unknown_and_wrong():
    """The endpoint must not reveal whether an email is registered."""
    email = f"__test_{uuid.uuid4().hex[:10]}@example.com"
    AuthService.register(email, "a-long-enough-passphrase")
    try:
        with pytest.raises(AuthError) as wrong:
            AuthService.authenticate(email, "definitely-not-it")
        with pytest.raises(AuthError) as unknown:
            AuthService.authenticate("nobody@example.com", "definitely-not-it")
        assert str(wrong.value) == str(unknown.value)
    finally:
        _delete_user(email)


def test_user_dict_never_exposes_the_hash():
    email = f"__test_{uuid.uuid4().hex[:10]}@example.com"
    record = AuthService.register(email, "a-long-enough-passphrase")
    try:
        assert "password_hash" not in record
    finally:
        _delete_user(email)


def _delete_user(email: str) -> None:
    from connection import session_scope
    from models.user import User

    with session_scope() as session:
        session.query(User).filter(User.email == email).delete(synchronize_session=False)
