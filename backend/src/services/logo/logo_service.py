import time

import httpx

from config.config import settings
from config.logging import get_logger
from models.cached_logo import LOGO_CACHE_TTL_SECONDS, CachedLogo

log = get_logger(__name__)


class LogoService:
    """Service for fetching and caching company logos from logo.dev."""

    async def get_logo(self, domain: str) -> tuple[bytes, str] | None:
        """
        Get a logo for a domain, using cache if available.

        Returns:
            Tuple of (image_data, content_type) or None if not available.
        """
        # Normalize domain (lowercase, strip whitespace)
        domain = domain.lower().strip()

        if not domain:
            return None

        # Check cache first
        cached = await self._get_from_cache(domain)
        if cached:
            log.debug("logo_cache_hit", domain=domain)
            return cached

        # Fetch from logo.dev
        log.debug("logo_cache_miss", domain=domain)
        result = await self._fetch_from_api(domain)

        if result:
            await self._save_to_cache(domain, result[0], result[1])

        return result

    async def _get_from_cache(self, domain: str) -> tuple[bytes, str] | None:
        """Get logo from cache if available and not expired."""
        cached = await CachedLogo.find_one(CachedLogo.domain == domain)

        if not cached:
            return None

        if cached.is_expired():
            # Delete expired entry
            await cached.delete()
            log.debug("logo_cache_expired", domain=domain)
            return None

        return (cached.image_data, cached.content_type)

    async def _fetch_from_api(self, domain: str) -> tuple[bytes, str] | None:
        """Fetch logo from logo.dev API."""
        if not settings.logo_dev_token:
            log.warning("logo_dev_token_not_configured")
            return None

        url = (
            f"https://img.logo.dev/{domain}"
            f"?token={settings.logo_dev_token}"
            f"&size=100&retina=true&format=png"
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, follow_redirects=True)

                if response.status_code != 200:
                    log.warning(
                        "logo_fetch_failed",
                        domain=domain,
                        status=response.status_code,
                    )
                    return None

                content_type = response.headers.get("content-type", "image/png")
                return (response.content, content_type)

        except httpx.TimeoutException:
            log.warning("logo_fetch_timeout", domain=domain)
            return None
        except httpx.RequestError as e:
            log.warning("logo_fetch_error", domain=domain, error=str(e))
            return None

    async def _save_to_cache(
        self, domain: str, image_data: bytes, content_type: str
    ) -> None:
        """Save logo to cache."""
        now = time.time()
        cached = CachedLogo(
            domain=domain,
            image_data=image_data,
            content_type=content_type,
            fetched_ts=now,
            expires_ts=now + LOGO_CACHE_TTL_SECONDS,
        )

        try:
            await cached.insert()
            log.debug("logo_cached", domain=domain, size=len(image_data))
        except Exception as e:
            # Might fail due to unique constraint race condition - that's ok
            log.debug("logo_cache_insert_failed", domain=domain, error=str(e))

    async def cleanup_expired(self) -> int:
        """Delete all expired cached logos. Returns count of deleted entries."""
        now = time.time()
        result = await CachedLogo.find(CachedLogo.expires_ts < now).delete()
        deleted = result.deleted_count if result else 0

        if deleted > 0:
            log.info("expired_logos_cleaned", count=deleted)

        return deleted


# Singleton instance
logo_service = LogoService()
