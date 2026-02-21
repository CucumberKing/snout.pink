from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    dev: bool = Field(default=False, description="Development mode")
    log_level: str = Field(
        default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)"
    )
    standby_mode: bool = Field(default=False, description="Standby mode: retry DB init instead of crashing (for failover replicas)")

    # MongoDB
    mongo_uri: str = Field(
        ...,
        description="MongoDB connection string",
    )
    mongo_uri_testing: str | None = Field(
        default=None,
        description="MongoDB connection string for testing",
    )

    # WebAuthn / Passkey
    rp_id: str = Field(
        default="localhost",
        description="Relying Party ID (domain)",
    )
    rp_name: str = Field(
        default="Snout Pink",
        description="Relying Party display name",
    )
    rp_origin: str = Field(
        default="http://localhost:4200",
        description="Allowed origin for WebAuthn",
    )

    # Session
    session_cookie_name: str = Field(
        default="session",
        description="Name of the session cookie",
    )
    session_ttl_seconds: int = Field(
        default=31536000,  # 365 days
        description="Session lifetime in seconds",
    )
    session_cookie_secure: bool = Field(
        default=True,
        description="Set Secure flag on session cookie (set False for local HTTP dev)",
    )

    # Logo.dev API
    logo_dev_token: str | None = Field(
        default=None,
        description="API token for logo.dev service",
    )

    # Legal / About URLs (optional)
    imprint_url: str | None = Field(
        default=None,
        description="URL to imprint/impressum page",
    )
    privacy_url: str | None = Field(
        default=None,
        description="URL to privacy policy page",
    )
    github_url: str | None = Field(
        default=None,
        description="URL to GitHub repository",
    )

    # Umami Analytics (optional)
    umami_website_id: str | None = Field(
        default=None,
        description="Umami Analytics website ID",
    )
    umami_host_url: str | None = Field(
        default=None,
        description="Umami Analytics host URL",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
