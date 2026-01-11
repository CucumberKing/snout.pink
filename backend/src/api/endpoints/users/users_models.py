import re

from pydantic import BaseModel, Field, field_validator


class UserResponse(BaseModel):
    """Response model for user data."""

    user_id: str
    display_name: str | None
    created_ts: float
    updated_ts: float


class UserUpdateRequest(BaseModel):
    """Request model for updating user data."""

    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="User display name",
    )

    @field_validator("display_name")
    @classmethod
    def sanitize_display_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Remove control characters and null bytes
        v = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", v)
        # Strip leading/trailing whitespace
        v = v.strip()
        if not v:
            return None
        return v


class UserUpdateResponse(BaseModel):
    """Response model for user update."""

    user_id: str
    display_name: str | None
    updated_ts: float
    message: str


class UserDeleteResponse(BaseModel):
    """Response model for user deletion."""

    message: str

