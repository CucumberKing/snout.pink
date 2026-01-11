import pytest
from httpx import AsyncClient

from models import PasskeyCredential, Session, User


@pytest.mark.asyncio
async def test_get_user_profile(authenticated_client: AsyncClient, test_user: User):
    """Test get user profile endpoint."""
    response = await authenticated_client.get("/users/me")
    assert response.status_code == 200

    data = response.json()
    assert data["user_id"] == test_user.user_id
    assert data["display_name"] == test_user.display_name
    assert "created_ts" in data
    assert "updated_ts" in data


@pytest.mark.asyncio
async def test_get_user_profile_unauthenticated(client: AsyncClient, test_db):
    """Test get user profile without authentication."""
    response = await client.get("/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_user_profile(authenticated_client: AsyncClient, test_user: User):
    """Test update user profile endpoint."""
    new_display_name = "Updated Name"
    response = await authenticated_client.patch(
        "/users/me",
        json={"display_name": new_display_name},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["display_name"] == new_display_name
    assert data["message"] == "Profile updated successfully"

    # Verify in database
    await test_user.sync()
    assert test_user.display_name == new_display_name


@pytest.mark.asyncio
async def test_update_user_profile_empty_name(authenticated_client: AsyncClient):
    """Test update user profile with empty name."""
    response = await authenticated_client.patch(
        "/users/me",
        json={"display_name": ""},
    )
    # Should fail validation (min_length=1)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_user(authenticated_client: AsyncClient, test_user: User, test_db):
    """Test delete user endpoint."""
    user_id = test_user.user_id

    # Create a credential for this user
    credential = PasskeyCredential(
        credential_id="test_credential_id",
        public_key=b"test_public_key",
        user=test_user,
    )
    await credential.insert()

    response = await authenticated_client.delete("/users/me")
    assert response.status_code == 200
    assert response.json()["message"] == "Account deleted successfully"

    # Verify user was deleted
    user = await User.find_one(User.user_id == user_id)
    assert user is None

    # Verify credentials were deleted
    creds = await PasskeyCredential.find(
        PasskeyCredential.credential_id == "test_credential_id"
    ).to_list()
    assert len(creds) == 0

    # Verify sessions were deleted
    sessions = await Session.find_all().to_list()
    assert len(sessions) == 0


@pytest.mark.asyncio
async def test_delete_user_unauthenticated(client: AsyncClient, test_db):
    """Test delete user without authentication."""
    response = await client.delete("/users/me")
    assert response.status_code == 401

