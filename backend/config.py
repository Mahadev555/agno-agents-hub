"""
Application settings.

One typed object instead of os.getenv scattered across modules, so a missing or
malformed value fails at boot with a clear message rather than at the moment the
value is first needed.
"""

import secrets
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration read from the environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---- core ----
    database_url: str = Field(..., alias="DATABASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # ---- auth ----
    # Generated per-process when unset, which is fine for local development but
    # invalidates every token on restart. Production must set it explicitly;
    # see _require_production_secrets below.
    jwt_secret: Optional[str] = Field(default=None, alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_ttl_minutes: int = Field(
        default=60 * 12, alias="ACCESS_TOKEN_TTL_MINUTES", gt=0
    )

    # Registration is open by default so a fresh install can bootstrap itself.
    allow_registration: bool = Field(default=True, alias="ALLOW_REGISTRATION")

    # ---- CORS ----
    cors_allow_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000", alias="CORS_ALLOW_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")

    # ---- database pool ----
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE", ge=1)
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW", ge=0)
    db_pool_recycle: int = Field(default=280, alias="DB_POOL_RECYCLE", gt=0)

    # ---- MCP egress ----
    # Comma-separated host[:port] entries an agent's mcp_config may point at.
    # Empty means "any public address"; loopback and private ranges are always
    # refused unless explicitly listed here. See runtime/mcp_guard.py.
    mcp_allowed_hosts: str = Field(default="", alias="MCP_ALLOWED_HOSTS")
    mcp_allow_private_network: bool = Field(
        default=False, alias="MCP_ALLOW_PRIVATE_NETWORK"
    )

    # ---- rate limits ----
    # Runs are the expensive endpoint: each one spends real tokens.
    run_rate_limit_per_hour: int = Field(default=60, alias="RUN_RATE_LIMIT_PER_HOUR", ge=1)
    run_concurrency_per_user: int = Field(
        default=3, alias="RUN_CONCURRENCY_PER_USER", ge=1
    )

    @field_validator("environment")
    @classmethod
    def _known_environment(cls, value: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if value not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {sorted(allowed)}")
        return value

    @property
    def is_production(self) -> bool:
        return self.environment in ("production", "staging")

    @property
    def cors_origins(self) -> List[str]:
        """Parsed origin list. A wildcard disables credentials (CORS spec)."""
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def allow_credentials(self) -> bool:
        return self.cors_allow_credentials and "*" not in self.cors_origins

    @property
    def mcp_allowlist(self) -> List[str]:
        return [h.strip().lower() for h in self.mcp_allowed_hosts.split(",") if h.strip()]

    def resolved_jwt_secret(self) -> str:
        """
        The signing key.

        Refuses to invent one in production: an ephemeral secret would silently
        log every user out on each deploy and differ between replicas.
        """
        if self.jwt_secret:
            return self.jwt_secret
        if self.is_production:
            raise RuntimeError(
                "JWT_SECRET must be set when ENVIRONMENT is production or staging"
            )
        return _dev_secret()


@lru_cache(maxsize=1)
def _dev_secret() -> str:
    """A stable-per-process secret for local development only."""
    return secrets.token_urlsafe(48)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once."""
    return Settings()
