import pytest
from argon2 import PasswordHasher
from fastapi import FastAPI
from httpx import AsyncClient

from config.config import settings
from models import McpToken, User
from services.mcp_tokens.mcp_token_service import verify_mcp_token


@pytest.mark.asyncio
async def test_create_mcp_token_shows_secret_once(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """The bearer is returned once, stored as Argon2id, and absent from the list."""
    created = await authenticated_client.post(
        "/users/mcp-tokens",
        json={"name": " Laptop ", "scopes": ["subscriptions:read", "subscriptions:write"]},
    )
    assert created.status_code == 201
    body = created.json()
    token = body["token"]
    assert token.startswith(f"snout_{body['token_id']}_")
    assert body["token_prefix"] == token[:14]
    assert body["name"] == "Laptop"
    assert body["mcp_url"] == f"{settings.resolved_public_base_url()}/mcp"
    assert body["client_config"]["mcpServers"]["snout"]["headers"]["Authorization"] == (
        f"Bearer {token}"
    )
    assert "secret_hash" not in body

    stored = await McpToken.find_one(McpToken.token_id == body["token_id"])
    assert stored is not None
    assert stored.user_id == test_user.user_id
    assert stored.secret_hash.startswith("$argon2id$")
    assert token not in stored.secret_hash
    secret = token.split("_", 2)[2]
    PasswordHasher().verify(stored.secret_hash, secret)

    listed = await authenticated_client.get("/users/mcp-tokens")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert "token" not in payload["mcp_tokens"][0]
    assert payload["mcp_tokens"][0]["token_prefix"] == body["token_prefix"]


@pytest.mark.asyncio
async def test_create_mcp_token_rejects_write_without_read(authenticated_client: AsyncClient):
    """Write access always includes read."""
    response = await authenticated_client.post(
        "/users/mcp-tokens",
        json={"name": "Write only", "scopes": ["subscriptions:write"]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_mcp_tokens_require_session(client: AsyncClient, test_db):
    """Token management uses the passkey session, not the bearer."""
    listed = await client.get("/users/mcp-tokens")
    created = await client.post("/users/mcp-tokens", json={"name": "Nope"})
    assert listed.status_code == 401
    assert created.status_code == 401


@pytest.mark.asyncio
async def test_revoke_mcp_token_is_scoped_to_the_user(
    authenticated_client: AsyncClient,
    test_user: User,
    test_db,
):
    """Revoke hides the token. Another user's id is a 404."""
    created = await authenticated_client.post("/users/mcp-tokens", json={"name": "Phone"})
    token_id = created.json()["token_id"]

    other = User(display_name="Other")
    await other.insert()
    foreign = McpToken(
        token_id="foreign-token",
        user_id=other.user_id,
        name="Foreign",
        token_prefix="snout_foreign",
        secret_hash="not-a-real-hash",
        scopes=["subscriptions:read"],
    )
    await foreign.insert()

    missing = await authenticated_client.delete("/users/mcp-tokens/does-not-exist")
    stolen = await authenticated_client.delete(f"/users/mcp-tokens/{foreign.token_id}")
    assert missing.status_code == 404
    assert stolen.status_code == 404

    revoked = await authenticated_client.delete(f"/users/mcp-tokens/{token_id}")
    assert revoked.status_code == 204
    again = await authenticated_client.delete(f"/users/mcp-tokens/{token_id}")
    assert again.status_code == 404

    listed = await authenticated_client.get("/users/mcp-tokens")
    assert listed.json()["total"] == 0
    stored = await McpToken.find_one(McpToken.token_id == token_id)
    assert stored is not None
    assert stored.revoked_at_ts is not None


@pytest.mark.asyncio
async def test_delete_user_removes_mcp_tokens(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Account deletion removes personal MCP tokens."""
    created = await authenticated_client.post("/users/mcp-tokens", json={"name": "Laptop"})
    token_id = created.json()["token_id"]

    response = await authenticated_client.delete("/users/me")
    assert response.status_code == 200
    assert await McpToken.find_one(McpToken.token_id == token_id) is None


@pytest.mark.asyncio
async def test_unknown_token_id_does_not_verify(test_db):
    """An unknown selector never resolves, even when it looks well formed."""
    verified = await verify_mcp_token("snout_" + "ab" * 16 + "_" + "cd" * 32)
    assert verified is None


@pytest.mark.asyncio
async def test_route_table_keeps_mcp_tokens_and_mcp_apart(app: FastAPI):
    """Token routes stay on the API. /mcp is the mounted server, not a user id."""
    paths = list(app.openapi()["paths"])
    assert "/users/mcp-tokens" in paths
    assert "/users/mcp-tokens/{token_id}" in paths
    assert "/users/me" in paths
    assert "/mcp" not in paths
    assert paths.index("/subscriptions/import") < paths.index("/subscriptions/{subscription_id}")
    assert paths.index("/subscriptions/export/data") < paths.index(
        "/subscriptions/{subscription_id}"
    )
