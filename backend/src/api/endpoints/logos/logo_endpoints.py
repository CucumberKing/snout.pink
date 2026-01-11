from fastapi import APIRouter, Response
from fastapi.responses import Response as FastAPIResponse

from config.logging import get_logger
from services.logo import logo_service

log = get_logger(__name__)
router = APIRouter()


@router.get("/{domain:path}")
async def get_logo(domain: str) -> FastAPIResponse:
    """
    Get a company logo by domain.

    The logo is fetched from logo.dev and cached in MongoDB for 30 days.
    This endpoint is public (no authentication required) to allow use in
    img tags without auth headers.

    Args:
        domain: The domain to fetch logo for (e.g., "spotify.com", "netflix.com")

    Returns:
        The logo image (PNG) or a 404 if not found.
    """
    result = await logo_service.get_logo(domain)

    if not result:
        log.debug("logo_not_found", domain=domain)
        return Response(status_code=404)

    image_data, content_type = result

    return Response(
        content=image_data,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400",  # Browser cache 1 day
        },
    )
