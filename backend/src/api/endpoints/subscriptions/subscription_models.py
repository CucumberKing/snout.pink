from pydantic import BaseModel, Field

from models.subscription import BillingCycle, SubscriptionColor


class SubscriptionResponse(BaseModel):
    """Response model for subscription data."""

    subscription_id: str
    user_id: str
    name: str
    price: float
    currency: str
    cycle: BillingCycle
    url: str | None
    color: SubscriptionColor
    created_ts: float
    updated_ts: float


class SubscriptionCreateRequest(BaseModel):
    """Request model for creating a subscription."""

    name: str = Field(..., min_length=1, max_length=200)
    price: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    cycle: BillingCycle
    url: str | None = Field(default=None, max_length=500)
    color: SubscriptionColor


class SubscriptionUpdateRequest(BaseModel):
    """Request model for updating a subscription."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    price: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    cycle: BillingCycle | None = None
    url: str | None = Field(default=None, max_length=500)
    color: SubscriptionColor | None = None


class SubscriptionListResponse(BaseModel):
    """Response model for subscription list."""

    subscriptions: list[SubscriptionResponse]
    total: int
    monthly_total: float
    yearly_total: float


class SubscriptionDeleteResponse(BaseModel):
    """Response model for subscription deletion."""

    message: str


class SubscriptionImportRequest(BaseModel):
    """Request model for importing subscriptions."""

    subscriptions: list[SubscriptionCreateRequest]
    replace: bool = Field(
        default=False, description="Replace all existing subscriptions"
    )


class SubscriptionImportResponse(BaseModel):
    """Response model for subscription import."""

    imported: int
    message: str


class SubscriptionExportResponse(BaseModel):
    """Response model for subscription export."""

    version: int = 1
    exported_ts: float
    subscriptions: list[SubscriptionResponse]
