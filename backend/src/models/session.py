import secrets
import time

from beanie import Document, Indexed, Link
from pydantic import Field

from config.config import settings as app_settings
from models.user import User


def generate_session_token() -> str:
    """Generate a secure random session token (32 bytes hex = 64 chars)."""
    return secrets.token_hex(32)


class Session(Document):
    """Session document stored in MongoDB."""

    session_token: Indexed(str, unique=True) = Field(
        default_factory=generate_session_token
    )  # type: ignore[valid-type]
    user: Link[User] = Field(...)
    created_ts: float = Field(default_factory=time.time)
    expires_ts: float = Field(
        default_factory=lambda: time.time() + app_settings.session_ttl_seconds
    )

    # Optional metadata
    user_agent: str | None = Field(default=None)
    ip_address: str | None = Field(default=None)

    class Settings:
        name = "sessions"
        use_state_management = True

    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return time.time() > self.expires_ts

    def refresh(self) -> None:
        """Refresh the session expiration time."""
        self.expires_ts = time.time() + app_settings.session_ttl_seconds

