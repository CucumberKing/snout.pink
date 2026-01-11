import time

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.endpoints.subscriptions.subscription_models import (
    SubscriptionCreateRequest,
    SubscriptionDeleteResponse,
    SubscriptionExportResponse,
    SubscriptionImportRequest,
    SubscriptionImportResponse,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)
from config.logging import get_logger
from models import Subscription, User

log = get_logger(__name__)
router = APIRouter()


def subscription_to_response(sub: Subscription) -> SubscriptionResponse:
    """Convert a Subscription document to a response model."""
    return SubscriptionResponse(
        subscription_id=sub.subscription_id,
        user_id=sub.user_id,
        name=sub.name,
        price=sub.price,
        currency=sub.currency,
        cycle=sub.cycle,
        url=sub.url,
        color=sub.color,
        created_ts=sub.created_ts,
        updated_ts=sub.updated_ts,
    )


@router.get("", response_model=SubscriptionListResponse)
async def list_subscriptions(
    user: User = Depends(get_current_user),
) -> SubscriptionListResponse:
    """
    List all subscriptions for the current user.
    """
    subscriptions = await Subscription.find(
        Subscription.user_id == user.user_id,
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


@router.post(
    "", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED
)
async def create_subscription(
    request: SubscriptionCreateRequest,
    user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """
    Create a new subscription.
    """
    subscription = Subscription(
        user_id=user.user_id,
        name=request.name,
        price=request.price,
        currency=request.currency,
        cycle=request.cycle,
        url=request.url,
        color=request.color,
    )

    await subscription.insert()

    log.info(
        "subscription_created",
        subscription_id=subscription.subscription_id,
        user_id=user.user_id,
    )

    return subscription_to_response(subscription)


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """
    Get a specific subscription by ID.
    """
    subscription = await Subscription.find_one(
        Subscription.subscription_id == subscription_id,
        Subscription.user_id == user.user_id,
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    return subscription_to_response(subscription)


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    request: SubscriptionUpdateRequest,
    user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """
    Update a subscription.
    """
    subscription = await Subscription.find_one(
        Subscription.subscription_id == subscription_id,
        Subscription.user_id == user.user_id,
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    # Update fields if provided
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

    subscription.update_timestamp()
    await subscription.save()

    log.info(
        "subscription_updated",
        subscription_id=subscription_id,
        user_id=user.user_id,
    )

    return subscription_to_response(subscription)


@router.delete("/{subscription_id}", response_model=SubscriptionDeleteResponse)
async def delete_subscription(
    subscription_id: str,
    user: User = Depends(get_current_user),
) -> SubscriptionDeleteResponse:
    """
    Delete a subscription.
    """
    subscription = await Subscription.find_one(
        Subscription.subscription_id == subscription_id,
        Subscription.user_id == user.user_id,
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    await subscription.delete()

    log.info(
        "subscription_deleted",
        subscription_id=subscription_id,
        user_id=user.user_id,
    )

    return SubscriptionDeleteResponse(message="Subscription deleted successfully")


@router.post("/import", response_model=SubscriptionImportResponse)
async def import_subscriptions(
    request: SubscriptionImportRequest,
    user: User = Depends(get_current_user),
) -> SubscriptionImportResponse:
    """
    Import subscriptions from a list.
    If replace=True, deletes all existing subscriptions first.
    """
    if request.replace:
        await Subscription.find(
            Subscription.user_id == user.user_id,
        ).delete()
        log.info("subscriptions_cleared_for_import", user_id=user.user_id)

    imported_count = 0
    for sub_data in request.subscriptions:
        subscription = Subscription(
            user_id=user.user_id,
            name=sub_data.name,
            price=sub_data.price,
            currency=sub_data.currency,
            cycle=sub_data.cycle,
            url=sub_data.url,
            color=sub_data.color,
        )
        await subscription.insert()
        imported_count += 1

    log.info(
        "subscriptions_imported",
        count=imported_count,
        replace=request.replace,
        user_id=user.user_id,
    )

    return SubscriptionImportResponse(
        imported=imported_count,
        message=f"Successfully imported {imported_count} subscription(s)",
    )


@router.get("/export/data", response_model=SubscriptionExportResponse)
async def export_subscriptions(
    user: User = Depends(get_current_user),
) -> SubscriptionExportResponse:
    """
    Export all subscriptions as JSON.
    """
    subscriptions = await Subscription.find(
        Subscription.user_id == user.user_id,
    ).to_list()

    response_items = [subscription_to_response(sub) for sub in subscriptions]

    return SubscriptionExportResponse(
        version=1,
        exported_ts=time.time(),
        subscriptions=response_items,
    )
