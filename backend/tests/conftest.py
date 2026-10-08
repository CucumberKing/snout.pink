import asyncio
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env file from backend directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Set required environment variables before importing application modules
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/snout_pink_test")
os.environ.setdefault("DEV", "true")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from beanie import init_beanie  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from pymongo import AsyncMongoClient  # noqa: E402

from models import (  # noqa: E402
    AuthChallenge,
    CachedLogo,
    McpToken,
    PasskeyCredential,
    Session,
    Subscription,
    User,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def mongo_client() -> AsyncGenerator[AsyncMongoClient]:
    """Create MongoDB client for testing."""
    mongo_uri = os.environ.get("MONGO_URI_TESTING")
    if not mongo_uri:
        pytest.skip("MONGO_URI_TESTING not set")

    client = AsyncMongoClient(mongo_uri)
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="function")
async def test_db(mongo_client: AsyncMongoClient) -> AsyncGenerator[Any]:
    """Initialize test database with Beanie."""
    database = mongo_client.get_database("habicht_test")

    await init_beanie(
        database=database,
        document_models=[
            User,
            PasskeyCredential,
            Session,
            Subscription,
            AuthChallenge,
            CachedLogo,
            McpToken,
        ],
    )

    yield database

    # Cleanup: drop all test collections
    await database.users.drop()
    await database.passkey_credentials.drop()
    await database.sessions.drop()
    await database.subscriptions.drop()
    await database.auth_challenges.drop()
    await database.cached_logos.drop()
    await database.mcp_tokens.drop()


@pytest_asyncio.fixture(scope="function")
async def app(test_db) -> FastAPI:
    """Create FastAPI app for testing."""
    from main import app as fastapi_app

    return fastapi_app


@pytest_asyncio.fixture(scope="function")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def test_user(test_db) -> User:
    """Create a test user."""
    user = User(display_name="Test User")
    await user.insert()
    return user


@pytest_asyncio.fixture(scope="function")
async def test_session(test_user: User) -> Session:
    """Create a test session."""
    session = Session(user=test_user)
    await session.insert()
    return session


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(
    app: FastAPI,
    test_session: Session,
) -> AsyncGenerator[AsyncClient]:
    """Create an authenticated async HTTP client."""
    from config.config import settings

    transport = ASGITransport(app=app)
    cookies = {settings.session_cookie_name: test_session.session_token}

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies=cookies,
    ) as ac:
        yield ac
