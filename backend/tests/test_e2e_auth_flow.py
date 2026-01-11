"""
End-to-end test for the complete authentication flow.

This test verifies:
1. User registration with passkey
2. Creating subscriptions as authenticated user
3. Logout
4. Login with passkey
5. Verifying subscriptions are still accessible
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from models import PasskeyCredential, Session, Subscription, User
from services.auth.passkey_service import VerifiedAuthentication, VerifiedRegistration


@pytest.mark.asyncio
async def test_full_auth_flow_register_create_logout_login(
    client: AsyncClient, test_db
):
    """
    Complete E2E test: register -> create data -> logout -> login -> verify data.

    This test catches issues like:
    - Beanie 2.x find_one().update() not working
    - Beanie 2.x find_one(fetch_links=True) returning cursor
    - Session/credential linking issues
    """
    # =========================================================================
    # STEP 1: Begin registration
    # =========================================================================
    response = await client.post("/auth/register/begin")
    assert response.status_code == 200, f"Register begin failed: {response.text}"

    register_data = response.json()
    challenge_id = register_data["challenge_id"]
    assert challenge_id, "No challenge_id returned"

    # Get the user that was created
    users = await User.find_all().to_list()
    assert len(users) == 1, "User should be created in register/begin"
    user = users[0]
    user_id = user.user_id

    # =========================================================================
    # STEP 2: Complete registration (mock WebAuthn verification)
    # =========================================================================
    mock_credential_id = "test-credential-id-abc123"
    mock_public_key = b"mock-public-key-bytes-for-testing"

    mock_verified_registration = VerifiedRegistration(
        credential_id=mock_credential_id,
        public_key=mock_public_key,
        sign_count=0,
        aaguid="00000000-0000-0000-0000-000000000000",
        user_id=user_id,
    )

    with patch(
        "services.auth.passkey_service.passkey_service.verify_registration",
        new_callable=AsyncMock,
        return_value=mock_verified_registration,
    ):
        response = await client.post(
            "/auth/register/complete",
            json={
                "challenge_id": challenge_id,
                "credential": {
                    "id": mock_credential_id,
                    "rawId": mock_credential_id,
                    "type": "public-key",
                    "response": {
                        "clientDataJSON": "mock",
                        "attestationObject": "mock",
                    },
                },
            },
        )

    assert response.status_code == 200, f"Register complete failed: {response.text}"
    register_result = response.json()
    assert register_result["user_id"] == user_id

    # Verify credential was stored
    credentials = await PasskeyCredential.find_all().to_list()
    assert len(credentials) == 1, "Credential should be stored"
    credential = credentials[0]
    assert credential.credential_id == mock_credential_id

    # Verify session was created and cookie set
    sessions = await Session.find_all().to_list()
    assert len(sessions) == 1, "Session should be created"

    # Extract session cookie for subsequent requests
    session_cookie = response.cookies.get("session")
    assert session_cookie, "Session cookie should be set"

    # =========================================================================
    # STEP 3: Verify authenticated access works
    # =========================================================================
    client.cookies.set("session", session_cookie)

    response = await client.get("/auth/me")
    assert response.status_code == 200, f"Get me failed: {response.text}"
    me_data = response.json()
    assert me_data["user_id"] == user_id

    # =========================================================================
    # STEP 4: Create subscriptions as authenticated user
    # =========================================================================
    subscription_data = {
        "name": "Netflix",
        "price": 15.99,
        "currency": "EUR",
        "cycle": "Monthly",
        "url": "https://netflix.com",
        "color": "rose",
    }

    response = await client.post("/subscriptions", json=subscription_data)
    assert response.status_code == 201, f"Create subscription failed: {response.text}"
    subscription = response.json()
    subscription_id = subscription["subscription_id"]

    # Create a second subscription
    subscription_data_2 = {
        "name": "Spotify",
        "price": 9.99,
        "currency": "EUR",
        "cycle": "Monthly",
        "url": "https://spotify.com",
        "color": "green",
    }

    response = await client.post("/subscriptions", json=subscription_data_2)
    assert response.status_code == 201

    # Verify subscriptions are in database
    subs = await Subscription.find_all().to_list()
    assert len(subs) == 2, "Both subscriptions should be stored"

    # =========================================================================
    # STEP 5: Logout
    # =========================================================================
    response = await client.post("/auth/logout")
    assert response.status_code == 200, f"Logout failed: {response.text}"

    # Verify session was deleted
    sessions = await Session.find_all().to_list()
    assert len(sessions) == 0, "Session should be deleted after logout"

    # Clear the cookie
    client.cookies.clear()

    # Verify we're logged out
    response = await client.get("/auth/me")
    assert response.status_code == 401, "Should be unauthorized after logout"

    # =========================================================================
    # STEP 6: Begin login
    # =========================================================================
    response = await client.post("/auth/login/begin")
    assert response.status_code == 200, f"Login begin failed: {response.text}"

    login_data = response.json()
    login_challenge_id = login_data["challenge_id"]
    assert login_challenge_id, "No challenge_id for login"

    # =========================================================================
    # STEP 7: Complete login (mock WebAuthn verification)
    # =========================================================================
    mock_verified_auth = VerifiedAuthentication(
        credential_id=mock_credential_id,
        new_sign_count=1,
    )

    with patch(
        "services.auth.passkey_service.passkey_service.verify_authentication",
        new_callable=AsyncMock,
        return_value=mock_verified_auth,
    ):
        response = await client.post(
            "/auth/login/complete",
            json={
                "challenge_id": login_challenge_id,
                "credential": {
                    "id": mock_credential_id,
                    "rawId": mock_credential_id,
                    "type": "public-key",
                    "response": {
                        "clientDataJSON": "mock",
                        "authenticatorData": "mock",
                        "signature": "mock",
                    },
                },
            },
        )

    assert response.status_code == 200, f"Login complete failed: {response.text}"
    login_result = response.json()
    assert login_result["user_id"] == user_id, "Should login as same user"

    # Get new session cookie
    new_session_cookie = response.cookies.get("session")
    assert new_session_cookie, "New session cookie should be set after login"
    client.cookies.set("session", new_session_cookie)

    # =========================================================================
    # STEP 8: Verify we can access our data after re-login
    # =========================================================================
    response = await client.get("/auth/me")
    assert response.status_code == 200, f"Get me after login failed: {response.text}"
    assert response.json()["user_id"] == user_id

    # Verify subscriptions are still accessible
    response = await client.get("/subscriptions")
    assert response.status_code == 200, f"Get subscriptions failed: {response.text}"
    subs_response = response.json()
    assert len(subs_response["subscriptions"]) == 2, "Should have 2 subscriptions"

    # Verify specific subscription
    response = await client.get(f"/subscriptions/{subscription_id}")
    assert response.status_code == 200
    sub = response.json()
    assert sub["name"] == "Netflix"
    assert sub["price"] == 15.99

    # =========================================================================
    # STEP 9: Verify credential sign_count was updated
    # =========================================================================
    updated_credential = await PasskeyCredential.find_one(
        PasskeyCredential.credential_id == mock_credential_id
    )
    assert updated_credential is not None
    assert updated_credential.sign_count == 1, (
        "Sign count should be updated after login"
    )


@pytest.mark.asyncio
async def test_login_with_linked_user_fetches_correctly(client: AsyncClient, test_db):
    """
    Test that login correctly fetches the linked user from credential.

    This specifically tests the Beanie 2.x issue with fetch_links=True
    returning a cursor instead of a document.
    """
    # Create user and credential manually
    user = User(display_name="Link Test User")
    await user.insert()

    credential = PasskeyCredential(
        credential_id="link-test-credential",
        public_key=b"test-public-key",
        sign_count=5,
        user=user,
    )
    await credential.insert()

    # Begin login
    response = await client.post("/auth/login/begin")
    assert response.status_code == 200
    challenge_id = response.json()["challenge_id"]

    # Complete login with mocked verification
    mock_verified_auth = VerifiedAuthentication(
        credential_id="link-test-credential",
        new_sign_count=6,
    )

    with patch(
        "services.auth.passkey_service.passkey_service.verify_authentication",
        new_callable=AsyncMock,
        return_value=mock_verified_auth,
    ):
        response = await client.post(
            "/auth/login/complete",
            json={
                "challenge_id": challenge_id,
                "credential": {
                    "id": "link-test-credential",
                    "rawId": "link-test-credential",
                    "type": "public-key",
                    "response": {
                        "clientDataJSON": "mock",
                        "authenticatorData": "mock",
                        "signature": "mock",
                    },
                },
            },
        )

    # This is the critical assertion - if fetch_links doesn't work,
    # the user won't be found and login will fail with 401
    assert response.status_code == 200, f"Login failed: {response.text}"
    assert response.json()["user_id"] == user.user_id

    # Verify sign count was updated (tests the find().update() fix)
    updated_cred = await PasskeyCredential.find_one(
        PasskeyCredential.credential_id == "link-test-credential"
    )
    assert updated_cred.sign_count == 6, "Sign count should be updated"


@pytest.mark.asyncio
async def test_login_rejects_replay_attack(client: AsyncClient, test_db):
    """
    Test that login rejects potential replay attacks.

    A replay attack is detected when the new sign_count is <= the stored sign_count.
    This could indicate a cloned authenticator.
    """
    # Create user and credential with sign_count=10
    user = User(display_name="Replay Test User")
    await user.insert()

    credential = PasskeyCredential(
        credential_id="replay-test-credential",
        public_key=b"test-public-key",
        sign_count=10,
        user=user,
    )
    await credential.insert()

    # Begin login
    response = await client.post("/auth/login/begin")
    assert response.status_code == 200
    challenge_id = response.json()["challenge_id"]

    # Try to login with a LOWER sign_count (replay attack!)
    mock_verified_auth = VerifiedAuthentication(
        credential_id="replay-test-credential",
        new_sign_count=5,  # Lower than stored (10) - replay attack!
    )

    with patch(
        "services.auth.passkey_service.passkey_service.verify_authentication",
        new_callable=AsyncMock,
        return_value=mock_verified_auth,
    ):
        response = await client.post(
            "/auth/login/complete",
            json={
                "challenge_id": challenge_id,
                "credential": {
                    "id": "replay-test-credential",
                    "rawId": "replay-test-credential",
                    "type": "public-key",
                    "response": {
                        "clientDataJSON": "mock",
                        "authenticatorData": "mock",
                        "signature": "mock",
                    },
                },
            },
        )

    # Should be rejected as potential replay attack
    assert response.status_code == 401, f"Should reject replay: {response.text}"
    assert "replay" in response.json()["detail"].lower()

    # Verify sign count was NOT updated
    cred = await PasskeyCredential.find_one(
        PasskeyCredential.credential_id == "replay-test-credential"
    )
    assert cred.sign_count == 10, "Sign count should NOT be updated on replay"


@pytest.mark.asyncio
async def test_login_allows_sign_count_jump(client: AsyncClient, test_db):
    """
    Test that login allows sign_count to jump by more than 1.

    Some authenticators increment sign_count by more than 1, or the passkey
    may have been used on another device. As long as new > stored, it's OK.
    """
    # Create user and credential with sign_count=5
    user = User(display_name="Jump Test User")
    await user.insert()

    credential = PasskeyCredential(
        credential_id="jump-test-credential",
        public_key=b"test-public-key",
        sign_count=5,
        user=user,
    )
    await credential.insert()

    # Begin login
    response = await client.post("/auth/login/begin")
    assert response.status_code == 200
    challenge_id = response.json()["challenge_id"]

    # Login with sign_count that jumped from 5 to 100 (big jump, but valid)
    mock_verified_auth = VerifiedAuthentication(
        credential_id="jump-test-credential",
        new_sign_count=100,  # Big jump from 5, but still valid (100 > 5)
    )

    with patch(
        "services.auth.passkey_service.passkey_service.verify_authentication",
        new_callable=AsyncMock,
        return_value=mock_verified_auth,
    ):
        response = await client.post(
            "/auth/login/complete",
            json={
                "challenge_id": challenge_id,
                "credential": {
                    "id": "jump-test-credential",
                    "rawId": "jump-test-credential",
                    "type": "public-key",
                    "response": {
                        "clientDataJSON": "mock",
                        "authenticatorData": "mock",
                        "signature": "mock",
                    },
                },
            },
        )

    # Should succeed - big jump is allowed
    assert response.status_code == 200, f"Should allow jump: {response.text}"

    # Verify sign count was updated to new value
    cred = await PasskeyCredential.find_one(
        PasskeyCredential.credential_id == "jump-test-credential"
    )
    assert cred.sign_count == 100, "Sign count should be updated to jumped value"


@pytest.mark.asyncio
async def test_login_allows_equal_sign_count_when_zero(client: AsyncClient, test_db):
    """
    Test that first login (sign_count 0->0 or 0->1) is allowed.

    Some authenticators start at 0 and stay at 0, or increment to 1.
    We should allow this for the first login.
    """
    # Create user and credential with sign_count=0 (freshly registered)
    user = User(display_name="First Login User")
    await user.insert()

    credential = PasskeyCredential(
        credential_id="first-login-credential",
        public_key=b"test-public-key",
        sign_count=0,
        user=user,
    )
    await credential.insert()

    # Begin login
    response = await client.post("/auth/login/begin")
    assert response.status_code == 200
    challenge_id = response.json()["challenge_id"]

    # First login - some authenticators keep sign_count at 0
    mock_verified_auth = VerifiedAuthentication(
        credential_id="first-login-credential",
        new_sign_count=0,  # Some authenticators don't increment on first use
    )

    with patch(
        "services.auth.passkey_service.passkey_service.verify_authentication",
        new_callable=AsyncMock,
        return_value=mock_verified_auth,
    ):
        response = await client.post(
            "/auth/login/complete",
            json={
                "challenge_id": challenge_id,
                "credential": {
                    "id": "first-login-credential",
                    "rawId": "first-login-credential",
                    "type": "public-key",
                    "response": {
                        "clientDataJSON": "mock",
                        "authenticatorData": "mock",
                        "signature": "mock",
                    },
                },
            },
        )

    # Should succeed - first login with 0->0 is allowed (sign_count check skipped when stored is 0)
    assert response.status_code == 200, f"First login should work: {response.text}"
