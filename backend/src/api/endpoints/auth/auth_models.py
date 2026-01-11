from typing import Any

from pydantic import BaseModel


class RegisterBeginResponse(BaseModel):
    """Response for registration begin."""

    challenge_id: str
    options: dict[str, Any]


class RegisterCompleteRequest(BaseModel):
    """Request for registration complete."""

    challenge_id: str
    credential: dict[str, Any]


class RegisterCompleteResponse(BaseModel):
    """Response for registration complete."""

    user_id: str
    message: str


class LoginBeginResponse(BaseModel):
    """Response for login begin."""

    challenge_id: str
    options: dict[str, Any]


class LoginCompleteRequest(BaseModel):
    """Request for login complete."""

    challenge_id: str
    credential: dict[str, Any]


class LoginCompleteResponse(BaseModel):
    """Response for login complete."""

    user_id: str
    message: str


class MeResponse(BaseModel):
    """Response for current user."""

    user_id: str
    display_name: str | None
    created_ts: float


class LogoutResponse(BaseModel):
    """Response for logout."""

    message: str

