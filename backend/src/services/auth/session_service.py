"""Session management service for authentication."""

import base64

from fastapi import Response

from config.config import settings
from config.logging import get_logger
from models import PasskeyCredential, Session, User
from services.auth.passkey_service import VerifiedRegistration, passkey_service

log = get_logger(__name__)


def decode_user_handle(user_handle: str) -> str:
    """Decode base64url user handle to user_id string."""
    try:
        return base64.urlsafe_b64decode(user_handle + "==").decode()
    except Exception:
        return user_handle  # Already decoded


async def create_credential_for_user(
    verified: VerifiedRegistration,
    user: User,
) -> PasskeyCredential:
    """Store a verified credential for a user."""
    credential = PasskeyCredential(
        credential_id=verified.credential_id,
        public_key=verified.public_key,
        sign_count=verified.sign_count,
        user=user,
        aaguid=verified.aaguid,
    )
    await credential.insert()
    log.info("credential_created", user_id=user.user_id)
    return credential


async def create_session_with_cookie(
    user: User,
    response: Response,
) -> Session:
    """Create a session and set the session cookie."""
    session = Session(user=user)
    await session.insert()

    response.set_cookie(
        key=settings.session_cookie_name,
        value=session.session_token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )

    log.debug("session_created", user_id=user.user_id)
    return session


def clear_session_cookie(response: Response) -> None:
    """Clear the session cookie."""
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


async def find_credential_by_id(credential_id: str) -> PasskeyCredential | None:
    """Find a passkey credential by its ID."""
    # Beanie 2.x bug: find_one(fetch_links=True), fetch_all_links(), and even
    # Link.fetch(fetch_links=True) use aggregation pipelines that return cursors.
    # Workaround: fetch credential first, then manually fetch the linked user.
    credential = await PasskeyCredential.find_one(
        PasskeyCredential.credential_id == credential_id,
    )
    if credential:
        # Manually fetch the linked user
        credential.user = await _fetch_user_link(credential.user)
    return credential


async def _fetch_user_link(user_link) -> User | None:
    """
    Manually fetch a User from a Link without using Beanie's broken fetch_links.

    Beanie 2.x has a bug where aggregation pipelines return cursors instead of
    documents. This affects find_one(fetch_links=True), fetch_all_links(), and
    Link.fetch(fetch_links=True).
    """
    if isinstance(user_link, User):
        return user_link
    # It's a Link - extract the document ID and fetch directly
    if hasattr(user_link, "ref") and user_link.ref:
        return await User.get(user_link.ref.id)
    return None


async def get_user_from_credential(credential: PasskeyCredential) -> User | None:
    """Get the user associated with a credential."""
    return await _fetch_user_link(credential.user)


async def begin_registration() -> tuple[User, dict]:
    """
    Begin the registration process.

    Returns:
        Tuple of (new user, registration options dict with challenge_id)
    """
    user = User()
    await user.insert()

    log.info("registration_started", user_id=user.user_id)

    challenge = await passkey_service.generate_registration_options(
        user_id=user.user_id,
        user_name=user.display_name,
    )

    return user, {
        "challenge_id": challenge.challenge,
        "options": challenge.options_json,
    }


async def begin_login() -> dict:
    """
    Begin the login process.

    Returns:
        Authentication options dict with challenge_id
    """
    challenge = await passkey_service.generate_authentication_options()
    log.debug("login_started")

    return {
        "challenge_id": challenge.challenge,
        "options": challenge.options_json,
    }

