import secrets
import time

from beanie import Document, Indexed
from pydantic import Field


def generate_user_id() -> str:
    """Generate a random user ID (16 bytes hex = 32 chars)."""
    return secrets.token_hex(16)


class User(Document):
    """User document stored in MongoDB."""

    user_id: Indexed(str, unique=True) = Field(default_factory=generate_user_id)  # type: ignore[valid-type]
    display_name: str | None = Field(default=None)
    default_currency: str = Field(default="EUR")
    created_ts: float = Field(default_factory=time.time)
    updated_ts: float = Field(default_factory=time.time)

    class Settings:
        name = "users"
        use_state_management = True

    def update_timestamp(self) -> None:
        """Update the updated_ts field to current time."""
        self.updated_ts = time.time()
