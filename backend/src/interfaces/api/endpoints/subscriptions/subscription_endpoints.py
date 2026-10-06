from fastapi import APIRouter, Depends, HTTPException, status

from interfaces.api.dependencies import get_current_user
from interfaces.api.endpoints.subscriptions.subscription_models import (
    SubscriptionCreateRequest,
    SubscriptionDeleteResponse,
    SubscriptionExportResponse,
    SubscriptionImportRequest,
    SubscriptionImportResponse,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)
from models import User
from services.subscriptions.subscription_service import (
    SubscriptionNotFoundError,
    create_subscription,
    delete_subscription,
    export_subscriptions,
    get_subscription,
    import_subscriptions,
    list_subscriptions,
    update_subscription,
)

router = APIRouter()


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Subscription not found",
    )


@router.get("", response_model=SubscriptionListResponse)
async def list_subscriptions_endpoint(
    user: User = Depends(get_current_user),
) -> SubscriptionListResponse:
    """List all subscriptions for the current user."""
    return await list_subscriptions(user.user_id)


@router.post(
    "", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED
)
async def create_subscription_endpoint(
    request: SubscriptionCreateRequest,
    user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """Create a new subscription."""
    return await create_subscription(user.user_id, request)


@router.post("/import", response_model=SubscriptionImportResponse)
async def import_subscriptions_endpoint(
    request: SubscriptionImportRequest,
    user: User = Depends(get_current_user),
) -> SubscriptionImportResponse:
    """Import subscriptions. replace=True deletes existing rows first."""
    return await import_subscriptions(user.user_id, request)


@router.get("/export/data", response_model=SubscriptionExportResponse)
async def export_subscriptions_endpoint(
    user: User = Depends(get_current_user),
) -> SubscriptionExportResponse:
    """Export all subscriptions as JSON."""
    return await export_subscriptions(user.user_id)


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription_endpoint(
    subscription_id: str,
    user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """Get a specific subscription by ID."""
    try:
        return await get_subscription(user.user_id, subscription_id)
    except SubscriptionNotFoundError as exc:
        raise _not_found() from exc


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription_endpoint(
    subscription_id: str,
    request: SubscriptionUpdateRequest,
    user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """Update a subscription."""
    try:
        return await update_subscription(user.user_id, subscription_id, request)
    except SubscriptionNotFoundError as exc:
        raise _not_found() from exc


@router.delete("/{subscription_id}", response_model=SubscriptionDeleteResponse)
async def delete_subscription_endpoint(
    subscription_id: str,
    user: User = Depends(get_current_user),
) -> SubscriptionDeleteResponse:
    """Delete a subscription."""
    try:
        await delete_subscription(user.user_id, subscription_id)
    except SubscriptionNotFoundError as exc:
        raise _not_found() from exc
    return SubscriptionDeleteResponse(message="Subscription deleted successfully")
