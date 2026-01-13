import secrets
import time
from typing import Literal

from beanie import Document, Indexed
from pydantic import Field

BillingCycle = Literal["Monthly", "Yearly", "Weekly"]

SubscriptionColor = Literal[
    "purple",
    "blue",
    "cyan",
    "green",
    "yellow",
    "orange",
    "pink",
    "rose",
    "slate",
    "indigo",
    "teal",
    "amber",
]


def generate_subscription_id() -> str:
    """Generate a random subscription ID (12 bytes hex = 24 chars)."""
    return secrets.token_hex(12)


class Subscription(Document):
    """Subscription document stored in MongoDB."""

    subscription_id: Indexed(str, unique=True) = Field(
        default_factory=generate_subscription_id
    )  # type: ignore[valid-type]
    user_id: Indexed(str) = Field(...)  # type: ignore[valid-type]
    name: str = Field(...)
    price: float = Field(...)
    currency: str = Field(...)
    cycle: BillingCycle = Field(...)
    url: str | None = Field(default=None)
    color: SubscriptionColor = Field(...)
    earliest_cancellation_ts: float | None = Field(default=None)
    created_ts: float = Field(default_factory=time.time)
    updated_ts: float = Field(default_factory=time.time)

    class Settings:
        name = "subscriptions"
        use_state_management = True

    def update_timestamp(self) -> None:
        """Update the updated_ts field to current time."""
        self.updated_ts = time.time()

    def to_monthly(self) -> float:
        """Convert price to monthly equivalent."""
        if self.cycle == "Yearly":
            return self.price / 12
        if self.cycle == "Weekly":
            return self.price * 4.33
        return self.price

    def to_yearly(self) -> float:
        """Convert price to yearly equivalent."""
        if self.cycle == "Yearly":
            return self.price
        if self.cycle == "Weekly":
            return self.price * 52
        return self.price * 12
