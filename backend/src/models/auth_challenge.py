import time

from beanie import Document, Indexed
from pydantic import Field


class AuthChallenge(Document):
    """WebAuthn challenge stored in MongoDB with TTL."""

    challenge_id: Indexed(str, unique=True) = Field(...)  # type: ignore[valid-type]
    challenge_bytes: bytes = Field(...)
    user_id: str | None = Field(default=None)  # Only set for registration
    challenge_type: str = Field(...)  # "registration" or "authentication"
    created_ts: float = Field(default_factory=time.time)
    expires_ts: float = Field(...)  # TTL timestamp

    class Settings:
        name = "auth_challenges"
