import base64
import binascii
import json
import secrets
import time
from dataclasses import dataclass

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import bytes_to_base64url, options_to_json
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from config.config import settings
from config.logging import get_logger
from models import AuthChallenge

log = get_logger(__name__)

CHALLENGE_TTL_SECONDS = 300  # 5 minutes


@dataclass
class RegistrationChallenge:
    """Data for a registration challenge."""

    challenge: str  # challenge_id
    user_id: str
    options_json: dict


@dataclass
class AuthenticationChallenge:
    """Data for an authentication challenge."""

    challenge: str  # challenge_id
    options_json: dict


@dataclass
class VerifiedRegistration:
    """Result of a verified registration."""

    credential_id: str  # base64url encoded
    public_key: bytes
    sign_count: int
    aaguid: str
    user_id: str  # The user_id from registration begin


@dataclass
class VerifiedAuthentication:
    """Result of a verified authentication."""

    credential_id: str
    new_sign_count: int


class PasskeyService:
    """Service for WebAuthn/Passkey operations."""

    async def generate_registration_options(
        self,
        user_id: str,
        user_name: str | None = None,
        exclude_credentials: list[bytes] | None = None,
    ) -> RegistrationChallenge:
        """
        Generate WebAuthn registration options.

        Args:
            user_id: Unique user identifier
            user_name: Display name for the user (defaults to user_id)
            exclude_credentials: List of existing credential IDs to exclude

        Returns:
            RegistrationChallenge with options for the client
        """
        display_name = user_name or f"User {user_id[:8]}"

        exclude_descriptors = None
        if exclude_credentials:
            exclude_descriptors = [
                PublicKeyCredentialDescriptor(id=cred_id)
                for cred_id in exclude_credentials
            ]

        options = generate_registration_options(
            rp_id=settings.rp_id,
            rp_name=settings.rp_name,
            user_id=user_id.encode(),
            user_name=display_name,
            user_display_name=display_name,
            exclude_credentials=exclude_descriptors,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )

        # Store challenge in DB
        challenge_id = secrets.token_hex(16)
        now = time.time()
        challenge_doc = AuthChallenge(
            challenge_id=challenge_id,
            challenge_bytes=options.challenge,
            user_id=user_id,
            challenge_type="registration",
            created_ts=now,
            expires_ts=now + CHALLENGE_TTL_SECONDS,
        )
        await challenge_doc.insert()

        log.debug(
            "generated_registration_options",
            user_id=user_id,
            challenge_id=challenge_id,
        )

        return RegistrationChallenge(
            challenge=challenge_id,
            user_id=user_id,
            options_json=json.loads(options_to_json(options)),
        )

    async def verify_registration(
        self,
        challenge_id: str,
        credential_response: dict,
    ) -> VerifiedRegistration:
        """
        Verify a WebAuthn registration response.

        Args:
            challenge_id: The challenge ID from registration options
            credential_response: The credential response from the client

        Returns:
            VerifiedRegistration with credential details

        Raises:
            ValueError: If verification fails
        """
        # Find and delete challenge atomically
        challenge_doc = await AuthChallenge.find_one(
            AuthChallenge.challenge_id == challenge_id,
            AuthChallenge.challenge_type == "registration",
        )

        if challenge_doc is None:
            raise ValueError("Invalid or expired challenge")

        # Check expiry
        if time.time() > challenge_doc.expires_ts:
            await challenge_doc.delete()
            raise ValueError("Challenge expired")

        # Delete challenge (one-time use)
        await challenge_doc.delete()

        challenge = challenge_doc.challenge_bytes
        user_id = challenge_doc.user_id

        try:
            verification = verify_registration_response(
                credential=credential_response,
                expected_challenge=challenge,
                expected_rp_id=settings.rp_id,
                expected_origin=settings.rp_origin,
            )
        except Exception as e:
            log.warning("registration_verification_failed", error=str(e))
            raise ValueError(f"Registration verification failed: {e}") from e

        credential_id = bytes_to_base64url(verification.credential_id)

        log.info(
            "registration_verified",
            credential_id=credential_id[:16] + "...",
            user_id=user_id,
        )

        return VerifiedRegistration(
            credential_id=credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            aaguid=str(verification.aaguid) if verification.aaguid else None,
            user_id=user_id,
        )

    async def generate_authentication_options(
        self,
        allowed_credentials: list[bytes] | None = None,
    ) -> AuthenticationChallenge:
        """
        Generate WebAuthn authentication options.

        Args:
            allowed_credentials: List of credential IDs that can authenticate
                                (None for discoverable credentials)

        Returns:
            AuthenticationChallenge with options for the client
        """
        allow_descriptors = None
        if allowed_credentials:
            allow_descriptors = [
                PublicKeyCredentialDescriptor(id=cred_id)
                for cred_id in allowed_credentials
            ]

        options = generate_authentication_options(
            rp_id=settings.rp_id,
            allow_credentials=allow_descriptors,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        # Store challenge in DB
        challenge_id = secrets.token_hex(16)
        now = time.time()
        challenge_doc = AuthChallenge(
            challenge_id=challenge_id,
            challenge_bytes=options.challenge,
            user_id=None,
            challenge_type="authentication",
            created_ts=now,
            expires_ts=now + CHALLENGE_TTL_SECONDS,
        )
        await challenge_doc.insert()

        log.debug("generated_authentication_options", challenge_id=challenge_id)

        return AuthenticationChallenge(
            challenge=challenge_id,
            options_json=json.loads(options_to_json(options)),
        )

    async def verify_authentication(
        self,
        challenge_id: str,
        credential_response: dict,
        credential_public_key: bytes,
        credential_current_sign_count: int,
    ) -> VerifiedAuthentication:
        """
        Verify a WebAuthn authentication response.

        Args:
            challenge_id: The challenge ID from authentication options
            credential_response: The credential response from the client
            credential_public_key: The stored public key for this credential
            credential_current_sign_count: The current sign count for replay protection

        Returns:
            VerifiedAuthentication with updated sign count

        Raises:
            ValueError: If verification fails
        """
        # Find and delete challenge
        challenge_doc = await AuthChallenge.find_one(
            AuthChallenge.challenge_id == challenge_id,
            AuthChallenge.challenge_type == "authentication",
        )

        if challenge_doc is None:
            raise ValueError("Invalid or expired challenge")

        # Check expiry
        if time.time() > challenge_doc.expires_ts:
            await challenge_doc.delete()
            raise ValueError("Challenge expired")

        # Delete challenge (one-time use)
        await challenge_doc.delete()

        challenge = challenge_doc.challenge_bytes

        # Extract credential ID from response with proper error handling
        raw_id = credential_response.get("rawId", "")
        try:
            if isinstance(raw_id, str):
                # Add padding if needed for base64url
                padding = 4 - len(raw_id) % 4
                if padding != 4:
                    raw_id += "=" * padding
                credential_id_bytes = base64.urlsafe_b64decode(raw_id)
            else:
                credential_id_bytes = raw_id
        except (binascii.Error, ValueError) as e:
            log.warning("invalid_credential_id_format", error=str(e))
            raise ValueError("Invalid credential ID format") from e

        try:
            verification = verify_authentication_response(
                credential=credential_response,
                expected_challenge=challenge,
                expected_rp_id=settings.rp_id,
                expected_origin=settings.rp_origin,
                credential_public_key=credential_public_key,
                credential_current_sign_count=credential_current_sign_count,
            )
        except Exception as e:
            log.warning("authentication_verification_failed", error=str(e))
            raise ValueError(f"Authentication verification failed: {e}") from e

        log.info("authentication_verified")

        return VerifiedAuthentication(
            credential_id=bytes_to_base64url(credential_id_bytes),
            new_sign_count=verification.new_sign_count,
        )

    async def cleanup_expired_challenges(self) -> int:
        """
        Clean up expired challenges.

        Returns:
            Number of deleted challenges
        """
        result = await AuthChallenge.find(
            AuthChallenge.expires_ts < time.time()
        ).delete()
        deleted = result.deleted_count if result else 0
        if deleted > 0:
            log.info("cleaned_up_expired_challenges", count=deleted)
        return deleted


# Global instance
passkey_service = PasskeyService()
