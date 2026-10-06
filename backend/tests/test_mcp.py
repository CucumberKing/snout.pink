from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
import pytest
from fastapi import FastAPI
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from httpx import AsyncClient

from models import McpToken, Subscription, User


@asynccontextmanager
async def open_mcp(app: FastAPI, token: str | None) -> AsyncIterator[Client]:
    """Speak MCP to the mounted app without leaving the test process."""

    def factory(**kwargs: object) -> httpx2.AsyncClient:
        kwargs.pop("base_url", None)
        return httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app),
            base_url="http://test",
            **kwargs,
        )

    transport = StreamableHttpTransport(
        "http://test/mcp",
        auth=token,
        httpx_client_factory=factory,
    )
    async with Client(transport) as client:
        yield client


async def _bearer(authenticated_client: AsyncClient, scopes: list[str]) -> str:
    response = await authenticated_client.post(
        "/users/mcp-tokens",
        json={"name": "Agent", "scopes": scopes},
    )
    assert response.status_code == 201
    return response.json()["token"]


@pytest.mark.asyncio
async def test_mcp_rejects_missing_and_bad_tokens(
    client: AsyncClient,
    app: FastAPI,
    authenticated_client: AsyncClient,
    test_db,
):
    """Missing, unknown, and revoked bearers are 401."""
    missing = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert missing.status_code == 401

    token = await _bearer(
        authenticated_client,
        ["subscriptions:read", "subscriptions:write"],
    )
    token_id = token.split("_")[1]
    bad = f"snout_{token_id}_{'ab' * 32}"
    rejected = await client.post(
        "/mcp",
        headers={"Authorization": f"Bearer {bad}"},
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert rejected.status_code == 401

    await authenticated_client.delete(f"/users/mcp-tokens/{token_id}")
    revoked = await client.post(
        "/mcp",
        headers={"Authorization": f"Bearer {token}"},
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert revoked.status_code == 401


@pytest.mark.asyncio
async def test_read_token_can_list_but_not_create(
    app: FastAPI,
    authenticated_client: AsyncClient,
    test_user: User,
):
    """A read token lists subscriptions and is refused on create."""
    subscription = Subscription(
        user_id=test_user.user_id,
        name="Music",
        price=9.99,
        currency="EUR",
        cycle="Monthly",
        color="pink",
    )
    await subscription.insert()
    token = await _bearer(authenticated_client, ["subscriptions:read"])

    async with app.state.mcp_http.lifespan(app), open_mcp(app, token) as mcp:
        tool_names = {tool.name for tool in await mcp.list_tools()}
        assert tool_names == {"list_subscriptions", "get_subscription"}

        listed = await mcp.call_tool("list_subscriptions", {})
        assert listed.is_error is False
        text = listed.content[0].text
        assert "Music" in text
        assert subscription.subscription_id in text
        assert "Monthly total:" in text

        fetched = await mcp.call_tool(
            "get_subscription",
            {"subscription_id": subscription.subscription_id},
        )
        assert fetched.is_error is False
        assert "Music" in fetched.content[0].text

        with pytest.raises(Exception, match="Unknown tool|403|insufficient"):
            await mcp.call_tool(
                "create_subscription",
                {
                    "name": "News",
                    "price": 5,
                    "currency": "EUR",
                    "cycle": "Monthly",
                    "color": "blue",
                },
            )

    assert await Subscription.find(Subscription.user_id == test_user.user_id).count() == 1


@pytest.mark.asyncio
async def test_write_token_crud_stays_on_the_owning_user(
    app: FastAPI,
    authenticated_client: AsyncClient,
    test_user: User,
    test_db,
):
    """Write token can create, update, and delete only its own subscriptions."""
    other = User(display_name="Other")
    await other.insert()
    private = Subscription(
        user_id=other.user_id,
        name="Private",
        price=20,
        currency="EUR",
        cycle="Yearly",
        color="slate",
    )
    await private.insert()
    token = await _bearer(
        authenticated_client,
        ["subscriptions:read", "subscriptions:write"],
    )

    async with app.state.mcp_http.lifespan(app), open_mcp(app, token) as mcp:
        created = await mcp.call_tool(
            "create_subscription",
            {
                "name": "Cloud",
                "price": 12,
                "currency": "EUR",
                "cycle": "Monthly",
                "color": "cyan",
                "url": "https://example.com",
            },
        )
        assert created.is_error is False
        created_text = created.content[0].text
        assert "Created subscription" in created_text
        subscription_id = created_text.split("[", 1)[1].split("]", 1)[0]

        updated = await mcp.call_tool(
            "update_subscription",
            {"subscription_id": subscription_id, "price": 15},
        )
        assert updated.is_error is False
        assert "15" in updated.content[0].text

        hidden = await mcp.call_tool(
            "get_subscription",
            {"subscription_id": private.subscription_id},
            raise_on_error=False,
        )
        assert hidden.is_error is True
        assert "not found" in hidden.content[0].text.lower()

        deleted = await mcp.call_tool(
            "delete_subscription",
            {"subscription_id": subscription_id},
        )
        assert deleted.is_error is False
        assert "Deleted subscription" in deleted.content[0].text

        gone = await mcp.call_tool(
            "get_subscription",
            {"subscription_id": subscription_id},
            raise_on_error=False,
        )
        assert gone.is_error is True

    assert await Subscription.get(private.id) is not None
    assert await Subscription.find_one(Subscription.subscription_id == subscription_id) is None
    stored = await McpToken.find_one(McpToken.token_prefix == token[:14])
    assert stored is not None
    assert stored.last_used_at_ts is not None
