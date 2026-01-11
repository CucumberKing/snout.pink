from fastapi import Cookie, Depends, HTTPException, Request, status

from config.config import settings
from config.logging import get_logger
from models import Session, User

log = get_logger(__name__)


async def get_session_token(
    request: Request,
    session_token: str | None = Cookie(default=None, alias=None),
) -> str | None:
    """Extract session token from cookie."""
    # Try to get from the configured cookie name
    return request.cookies.get(settings.session_cookie_name)


async def get_current_session(
    session_token: str | None = Depends(get_session_token),
) -> Session:
    """
    Get the current session from the session token.

    Raises:
        HTTPException: If no valid session is found
    """
    if not session_token:
        log.debug("no_session_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    session = await Session.find_one(
        Session.session_token == session_token,
    )

    if not session:
        log.debug("session_not_found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )

    if session.is_expired():
        log.debug("session_expired", session_id=str(session.id))
        await session.delete()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    return session


async def get_current_user(
    session: Session = Depends(get_current_session),
) -> User:
    """
    Get the current authenticated user.

    Raises:
        HTTPException: If not authenticated or user not found
    """
    # Always fetch the user via the Link reference
    user = await session.user.fetch()
    if not user:
        log.warning("user_not_found_for_session", session_id=str(session.id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_optional_user(
    session_token: str | None = Depends(get_session_token),
) -> User | None:
    """
    Get the current user if authenticated, None otherwise.

    Useful for endpoints that work with or without authentication.
    """
    if not session_token:
        return None

    session = await Session.find_one(
        Session.session_token == session_token,
    )

    if not session or session.is_expired():
        return None

    return await session.user.fetch()
