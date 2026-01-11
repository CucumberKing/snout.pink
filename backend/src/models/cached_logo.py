import time

from beanie import Document, Indexed
from pydantic import Field

# Cache logos for 30 days
LOGO_CACHE_TTL_SECONDS = 30 * 24 * 60 * 60


class CachedLogo(Document):
    """Cached logo image from logo.dev stored in MongoDB."""

    domain: Indexed(str, unique=True) = Field(...)  # type: ignore[valid-type]
    image_data: bytes = Field(...)
    content_type: str = Field(default="image/png")
    fetched_ts: float = Field(default_factory=time.time)
    expires_ts: float = Field(
        default_factory=lambda: time.time() + LOGO_CACHE_TTL_SECONDS
    )

    class Settings:
        name = "cached_logos"

    def is_expired(self) -> bool:
        """Check if the cached logo has expired."""
        return time.time() > self.expires_ts
