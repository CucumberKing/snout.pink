import pytest
from httpx import AsyncClient

from models import Session, User


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_register_begin(client: AsyncClient, test_db):
    """Test registration begin endpoint."""
    response = await client.post("/auth/register/begin")
    assert response.status_code == 200

    data = response.json()
    assert "challenge_id" in data
    assert "options" in data
    assert "rp" in data["options"]
    assert "user" in data["options"]
    assert "challenge" in data["options"]

    # Verify user was created
    users = await User.find_all().to_list()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_login_begin(client: AsyncClient, test_db):
    """Test login begin endpoint."""
    response = await client.post("/auth/login/begin")
    assert response.status_code == 200

    data = response.json()
    assert "challenge_id" in data
    assert "options" in data
    assert "rpId" in data["options"]
    assert "challenge" in data["options"]


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient, test_db):
    """Test get me endpoint without authentication."""
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(authenticated_client: AsyncClient, test_user: User):
    """Test get me endpoint with authentication."""
    response = await authenticated_client.get("/auth/me")
    assert response.status_code == 200

    data = response.json()
    assert data["user_id"] == test_user.user_id
    assert data["display_name"] == test_user.display_name


@pytest.mark.asyncio
async def test_logout(authenticated_client: AsyncClient, test_session: Session):
    """Test logout endpoint."""
    response = await authenticated_client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"

    # Verify session was deleted
    session = await Session.find_one(
        Session.session_token == test_session.session_token
    )
    assert session is None


@pytest.mark.asyncio
async def test_logout_unauthenticated(client: AsyncClient, test_db):
    """Test logout endpoint without authentication."""
    response = await client.post("/auth/logout")
    assert response.status_code == 401

