from fastapi import APIRouter, Depends, Response

from config.config import settings
from config.logging import get_logger
from interfaces.api.dependencies import get_current_session, get_current_user
from interfaces.api.endpoints.users.users_models import (
    UserDeleteResponse,
    UserResponse,
    UserUpdateRequest,
    UserUpdateResponse,
)
from models import PasskeyCredential, Session, User
from services.mcp_tokens.mcp_token_service import delete_mcp_tokens_for_user

log = get_logger(__name__)
router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get the current user's profile.
    """
    return UserResponse(
        user_id=user.user_id,
        display_name=user.display_name,
        created_ts=user.created_ts,
        updated_ts=user.updated_ts,
    )


@router.patch("/me", response_model=UserUpdateResponse)
async def update_current_user(
    request: UserUpdateRequest,
    user: User = Depends(get_current_user),
) -> UserUpdateResponse:
    """
    Update the current user's profile.
    """
    if request.display_name is not None:
        user.display_name = request.display_name

    user.update_timestamp()
    await user.save()

    log.info("user_updated", user_id=user.user_id)

    return UserUpdateResponse(
        user_id=user.user_id,
        display_name=user.display_name,
        updated_ts=user.updated_ts,
        message="Profile updated successfully",
    )


@router.delete("/me", response_model=UserDeleteResponse)
async def delete_current_user(
    response: Response,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_current_session),
) -> UserDeleteResponse:
    """
    Delete the current user's account.

    This will:
    - Delete all passkey credentials
    - Delete all sessions
    - Delete the user
    """
    user_id = user.user_id

    # Delete all credentials for this user
    await PasskeyCredential.find(
        PasskeyCredential.user.id == user.id,  # type: ignore[attr-defined]
    ).delete()

    # Delete all sessions for this user
    await Session.find(
        Session.user.id == user.id,  # type: ignore[attr-defined]
    ).delete()

    await delete_mcp_tokens_for_user(user_id)

    # Delete the user
    await user.delete()

    # Clear session cookie
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )

    log.info("user_deleted", user_id=user_id)

    return UserDeleteResponse(message="Account deleted successfully")

