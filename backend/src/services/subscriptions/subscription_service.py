"""Subscription reads and writes. HTTP and MCP both call this module."""

import time

from config.logging import get_logger
from interfaces.api.endpoints.subscriptions.subscription_models import (
    SubscriptionCreateRequest,
    SubscriptionExportResponse,
    SubscriptionImportRequest,
    SubscriptionImportResponse,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)
from models import Subscription

log = get_logger(__name__)


class SubscriptionNotFoundError(Exception):
    """The subscription does not exist for this user."""

    def __init__(self, subscription_id: str) -> None:
        self.subscription_id = subscription_id
        super().__init__(subscription_id)


def subscription_to_response(sub: Subscription) -> SubscriptionResponse:
    """Project a stored subscription onto the public response."""
    return SubscriptionResponse(
        subscription_id=sub.subscription_id,
        user_id=sub.user_id,
        name=sub.name,
        price=sub.price,
        currency=sub.currency,
        cycle=sub.cycle,
        url=sub.url,
        color=sub.color,
        earliest_cancellation_ts=sub.earliest_cancellation_ts,
        created_ts=sub.created_ts,
        updated_ts=sub.updated_ts,
    )


async def list_subscriptions(user_id: str) -> SubscriptionListResponse:
    """List one user's subscriptions and the monthly and yearly totals."""
    subscriptions = await Subscription.find(
        Subscription.user_id == user_id,
    ).to_list()

    response_items = [subscription_to_response(sub) for sub in subscriptions]
    monthly_total = sum(sub.to_monthly() for sub in subscriptions)
    yearly_total = sum(sub.to_yearly() for sub in subscriptions)

    return SubscriptionListResponse(
        subscriptions=response_items,
        total=len(response_items),
        monthly_total=monthly_total,
        yearly_total=yearly_total,
    )


async def get_subscription(user_id: str, subscription_id: str) -> SubscriptionResponse:
    """Return one subscription owned by the user."""
    subscription = await _find_owned(user_id, subscription_id)
    return subscription_to_response(subscription)


async def create_subscription(
    user_id: str,
    request: SubscriptionCreateRequest,
) -> SubscriptionResponse:
    """Insert a subscription for the user."""
    subscription = Subscription(
        user_id=user_id,
        name=request.name,
        price=request.price,
        currency=request.currency,
        cycle=request.cycle,
        url=request.url,
        color=request.color,
        earliest_cancellation_ts=request.earliest_cancellation_ts,
    )
    await subscription.insert()

    log.info(
        "subscription_created",
        subscription_id=subscription.subscription_id,
        user_id=user_id,
    )
    return subscription_to_response(subscription)


async def update_subscription(
    user_id: str,
    subscription_id: str,
    request: SubscriptionUpdateRequest,
) -> SubscriptionResponse:
    """Apply the fields that were sent. Omitted fields stay as they are."""
    subscription = await _find_owned(user_id, subscription_id)

    if request.name is not None:
        subscription.name = request.name
    if request.price is not None:
        subscription.price = request.price
    if request.currency is not None:
        subscription.currency = request.currency
    if request.cycle is not None:
        subscription.cycle = request.cycle
    if request.url is not None:
        subscription.url = request.url
    if request.color is not None:
        subscription.color = request.color
    if request.earliest_cancellation_ts is not None:
        subscription.earliest_cancellation_ts = request.earliest_cancellation_ts

    subscription.update_timestamp()
    await subscription.save()

    log.info(
        "subscription_updated",
        subscription_id=subscription_id,
        user_id=user_id,
    )
    return subscription_to_response(subscription)


async def delete_subscription(user_id: str, subscription_id: str) -> None:
    """Delete one subscription owned by the user."""
    subscription = await _find_owned(user_id, subscription_id)
    await subscription.delete()
    log.info(
        "subscription_deleted",
        subscription_id=subscription_id,
        user_id=user_id,
    )


async def import_subscriptions(
    user_id: str,
    request: SubscriptionImportRequest,
) -> SubscriptionImportResponse:
    """Insert subscriptions. replace=True deletes the user's current rows first."""
    if request.replace:
        await Subscription.find(Subscription.user_id == user_id).delete()
        log.info("subscriptions_cleared_for_import", user_id=user_id)

    imported_count = 0
    for sub_data in request.subscriptions:
        subscription = Subscription(
            user_id=user_id,
            name=sub_data.name,
            price=sub_data.price,
            currency=sub_data.currency,
            cycle=sub_data.cycle,
            url=sub_data.url,
            color=sub_data.color,
            earliest_cancellation_ts=sub_data.earliest_cancellation_ts,
        )
        await subscription.insert()
        imported_count += 1

    log.info(
        "subscriptions_imported",
        count=imported_count,
        replace=request.replace,
        user_id=user_id,
    )
    return SubscriptionImportResponse(
        imported=imported_count,
        message=f"Successfully imported {imported_count} subscription(s)",
    )


async def export_subscriptions(user_id: str) -> SubscriptionExportResponse:
    """Export every subscription the user owns."""
    subscriptions = await Subscription.find(Subscription.user_id == user_id).to_list()
    return SubscriptionExportResponse(
        version=1,
        exported_ts=time.time(),
        subscriptions=[subscription_to_response(sub) for sub in subscriptions],
    )


async def _find_owned(user_id: str, subscription_id: str) -> Subscription:
    subscription = await Subscription.find_one(
        Subscription.subscription_id == subscription_id,
        Subscription.user_id == user_id,
    )
    if subscription is None:
        raise SubscriptionNotFoundError(subscription_id)
    return subscription
