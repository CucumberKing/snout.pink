import time

from beanie import Document, Indexed, Link
from pydantic import Field

from models.user import User


class PasskeyCredential(Document):
    """WebAuthn credential stored in MongoDB."""

    credential_id: Indexed(str, unique=True) = Field(...)  # type: ignore[valid-type]
    public_key: bytes = Field(...)
    sign_count: int = Field(default=0)
    user: Link[User] = Field(...)
    created_ts: float = Field(default_factory=time.time)

    # Optional metadata
    aaguid: str | None = Field(default=None)
    device_name: str | None = Field(default=None)

    class Settings:
        name = "passkey_credentials"
        use_state_management = True

