"""Subscription tools. They call the same service as the HTTP API."""

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import require_scopes
from fastmcp.server.dependencies import get_access_token
from pydantic import ValidationError

from interfaces.api.endpoints.subscriptions.subscription_models import (
    SubscriptionCreateRequest,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)
from models.subscription import BillingCycle, SubscriptionColor
from services.mcp_tokens.mcp_token_service import (
    SUBSCRIPTIONS_READ,
    SUBSCRIPTIONS_WRITE,
)
from services.subscriptions.subscription_service import (
    SubscriptionNotFoundError,
    create_subscription,
    delete_subscription,
    get_subscription,
    list_subscriptions,
    update_subscription,
)


def register_subscription_tools(mcp: FastMCP) -> None:
    """Register read and write tools on the server."""

    @mcp.tool(
        name="list_subscriptions",
        description=(
            "List the signed-in user's subscriptions, including monthly and yearly "
            "totals. Read-only. Each entry includes a subscription_id for follow-up calls."
        ),
        auth=require_scopes(SUBSCRIPTIONS_READ),
    )
    async def list_subscriptions_tool() -> str:
        result = await list_subscriptions(_user_id())
        return _format_list(result)

    @mcp.tool(
        name="get_subscription",
        description=(
            "Get one subscription by subscription_id. Read-only. "
            "Use list_subscriptions first when the id is unknown."
        ),
        auth=require_scopes(SUBSCRIPTIONS_READ),
    )
    async def get_subscription_tool(subscription_id: str) -> str:
        try:
            subscription = await get_subscription(_user_id(), subscription_id)
        except SubscriptionNotFoundError as exc:
            raise ToolError(f"Subscription {exc.subscription_id} not found") from exc
        return _format_subscription(subscription)

    @mcp.tool(
        name="create_subscription",
        description=(
            "Create a subscription. Requires write access. "
            "cycle is Monthly, Yearly, or Weekly. "
            "color is one of purple, blue, cyan, green, yellow, orange, pink, "
            "rose, slate, indigo, teal, amber. currency is a 3-letter code."
        ),
        auth=require_scopes(SUBSCRIPTIONS_WRITE),
    )
    async def create_subscription_tool(
        name: str,
        price: float,
        currency: str,
        cycle: BillingCycle,
        color: SubscriptionColor,
        url: str | None = None,
        earliest_cancellation_ts: float | None = None,
    ) -> str:
        request = _parse(
            SubscriptionCreateRequest,
            name=name,
            price=price,
            currency=currency,
            cycle=cycle,
            color=color,
            url=url,
            earliest_cancellation_ts=earliest_cancellation_ts,
        )
        created = await create_subscription(_user_id(), request)
        return "Created subscription\n" + _format_subscription(created)

    @mcp.tool(
        name="update_subscription",
        description=(
            "Update a subscription. Requires write access. Only fields you pass are changed. "
            "Use list_subscriptions first to get subscription_id."
        ),
        auth=require_scopes(SUBSCRIPTIONS_WRITE),
    )
    async def update_subscription_tool(
        subscription_id: str,
        name: str | None = None,
        price: float | None = None,
        currency: str | None = None,
        cycle: BillingCycle | None = None,
        color: SubscriptionColor | None = None,
        url: str | None = None,
        earliest_cancellation_ts: float | None = None,
    ) -> str:
        request = _parse(
            SubscriptionUpdateRequest,
            name=name,
            price=price,
            currency=currency,
            cycle=cycle,
            color=color,
            url=url,
            earliest_cancellation_ts=earliest_cancellation_ts,
        )
        try:
            updated = await update_subscription(_user_id(), subscription_id, request)
        except SubscriptionNotFoundError as exc:
            raise ToolError(f"Subscription {exc.subscription_id} not found") from exc
        return "Updated subscription\n" + _format_subscription(updated)

    @mcp.tool(
        name="delete_subscription",
        description=(
            "Delete a subscription by subscription_id. Requires write access. "
            "This cannot be undone."
        ),
        auth=require_scopes(SUBSCRIPTIONS_WRITE),
    )
    async def delete_subscription_tool(subscription_id: str) -> str:
        try:
            existing = await get_subscription(_user_id(), subscription_id)
            await delete_subscription(_user_id(), subscription_id)
        except SubscriptionNotFoundError as exc:
            raise ToolError(f"Subscription {exc.subscription_id} not found") from exc
        return f"Deleted subscription {existing.subscription_id} ({existing.name})"


def _user_id() -> str:
    token = get_access_token()
    if token is None or not token.subject:
        raise ToolError("Not authenticated")
    return token.subject


def _parse[T](model: type[T], **data: object) -> T:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        parts = [
            f"{'.'.join(str(item) for item in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        raise ToolError("; ".join(parts)[:500]) from exc


def _format_subscription(subscription: SubscriptionResponse) -> str:
    lines = [
        f"[{subscription.subscription_id}] {subscription.name}",
        f"Price: {subscription.price} {subscription.currency} / {subscription.cycle}",
        f"Color: {subscription.color}",
    ]
    if subscription.url:
        lines.append(f"URL: {subscription.url}")
    if subscription.earliest_cancellation_ts is not None:
        lines.append(f"Earliest cancellation ts: {subscription.earliest_cancellation_ts}")
    return "\n".join(lines)


def _format_list(result: SubscriptionListResponse) -> str:
    header = (
        f"Found {result.total} subscriptions\n"
        f"Monthly total: {result.monthly_total}\n"
        f"Yearly total: {result.yearly_total}"
    )
    if result.total == 0:
        return header
    body = "\n\n".join(
        f"{index}. {_format_subscription(subscription)}"
        for index, subscription in enumerate(result.subscriptions, start=1)
    )
    return f"{header}\n\n{body}"
