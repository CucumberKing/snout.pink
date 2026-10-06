from fastapi import APIRouter, Depends, HTTPException, Response, status

from config.config import settings
from config.logging import get_logger
from interfaces.api.dependencies import get_current_session, get_current_user
from interfaces.api.endpoints.auth.auth_models import (
    LoginBeginResponse,
    LoginCompleteRequest,
    LoginCompleteResponse,
    LogoutResponse,
    MeResponse,
    RegisterBeginResponse,
    RegisterCompleteRequest,
    RegisterCompleteResponse,
)
from models import PasskeyCredential, Session, User
from services.auth.passkey_service import passkey_service
from services.auth.session_service import (
    begin_login,
    begin_registration,
    clear_session_cookie,
    create_credential_for_user,
    create_session_with_cookie,
    find_credential_by_id,
    get_user_from_credential,
)

log = get_logger(__name__)
router = APIRouter()


# ============================================================================
# Registration Endpoints
# ============================================================================


@router.post("/register/begin", response_model=RegisterBeginResponse)
async def register_begin() -> RegisterBeginResponse:
    """
    Begin passkey registration.

    This creates a new user and returns WebAuthn options for the client.
    """
    _user, options = await begin_registration()
    return RegisterBeginResponse(**options)


@router.post("/register/complete", response_model=RegisterCompleteResponse)
async def register_complete(
    request: RegisterCompleteRequest,
    response: Response,
) -> RegisterCompleteResponse:
    """
    Complete passkey registration.

    Verifies the credential and creates a session.
    """
    log.debug(
        "register_complete_request",
        challenge_id=request.challenge_id,
        has_credential=bool(request.credential),
    )

    try:
        verified = await passkey_service.verify_registration(
            challenge_id=request.challenge_id,
            credential_response=request.credential,
        )
    except ValueError as e:
        log.error("registration_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        log.exception("registration_unexpected_error", error=str(e))
        detail = f"Registration failed: {e}" if settings.dev else "Registration failed"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from e

    # Find the user (created in begin step) using user_id from verification
    user = await User.find_one(User.user_id == verified.user_id)
    if not user:
        log.error("registration_user_not_found", user_id=verified.user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    # Store credential and create session
    await create_credential_for_user(verified, user)
    await create_session_with_cookie(user, response)

    log.info("registration_completed", user_id=user.user_id)

    return RegisterCompleteResponse(
        user_id=user.user_id,
        message="Registration successful",
    )


# ============================================================================
# Login Endpoints
# ============================================================================


@router.post("/login/begin", response_model=LoginBeginResponse)
async def login_begin() -> LoginBeginResponse:
    """
    Begin passkey login.

    Returns WebAuthn options for discoverable credentials.
    """
    options = await begin_login()
    return LoginBeginResponse(**options)


@router.post("/login/complete", response_model=LoginCompleteResponse)
async def login_complete(
    request: LoginCompleteRequest,
    response: Response,
) -> LoginCompleteResponse:
    """
    Complete passkey login.

    Verifies the credential and creates a session.
    """
    raw_id = request.credential.get("rawId", "")

    credential = await find_credential_by_id(raw_id)
    if not credential:
        log.warning("login_failed_credential_not_found", credential_id=raw_id[:16])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credential not found",
        )

    # Verify authentication
    try:
        verified = await passkey_service.verify_authentication(
            challenge_id=request.challenge_id,
            credential_response=request.credential,
            credential_public_key=credential.public_key,
            credential_current_sign_count=credential.sign_count,
        )
    except ValueError as e:
        log.warning("login_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e

    # WebAuthn replay attack protection:
    # new_sign_count must be > stored sign_count (authenticators can increment by >1)
    # If new_sign_count <= stored, it could be a cloned authenticator replay attack
    if verified.new_sign_count <= credential.sign_count and credential.sign_count > 0:
        log.warning(
            "sign_count_replay_detected",
            credential_id=credential.credential_id[:16],
            stored_count=credential.sign_count,
            received_count=verified.new_sign_count,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Possible replay attack detected",
        )

    # Update sign count (no strict optimistic lock - just update to new value)
    await PasskeyCredential.find(
        PasskeyCredential.credential_id == credential.credential_id,
    ).update({"$set": {"sign_count": verified.new_sign_count}})

    # Get user and create session
    user = await get_user_from_credential(credential)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    await create_session_with_cookie(user, response)
    log.info("login_completed", user_id=user.user_id)

    return LoginCompleteResponse(
        user_id=user.user_id,
        message="Login successful",
    )


# ============================================================================
# Session Endpoints
# ============================================================================


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    session: Session = Depends(get_current_session),
) -> LogoutResponse:
    """
    Log out the current user.

    Deletes the session and clears the cookie.
    """
    await session.delete()
    clear_session_cookie(response)
    log.info("logout_completed")

    return LogoutResponse(message="Logged out successfully")


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(get_current_user),
) -> MeResponse:
    """
    Get the current authenticated user.
    """
    return MeResponse(
        user_id=user.user_id,
        display_name=user.display_name,
        created_ts=user.created_ts,
    )
