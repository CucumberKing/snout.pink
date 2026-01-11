import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from models import CachedLogo


@pytest.mark.asyncio
async def test_get_logo_not_configured(client: AsyncClient, test_db):
    """Test logo endpoint when LOGO_DEV_TOKEN is not configured."""
    with patch("services.logo.logo_service.settings") as mock_settings:
        mock_settings.logo_dev_token = None

        response = await client.get("/logos/spotify.com")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_logo_from_cache(client: AsyncClient, test_db):
    """Test logo endpoint returns cached logo."""
    # Create a cached logo
    cached = CachedLogo(
        domain="netflix.com",
        image_data=b"fake_png_data",
        content_type="image/png",
        fetched_ts=time.time(),
        expires_ts=time.time() + 86400,  # Expires in 1 day
    )
    await cached.insert()

    response = await client.get("/logos/netflix.com")
    assert response.status_code == 200
    assert response.content == b"fake_png_data"
    assert response.headers["content-type"] == "image/png"
    assert "cache-control" in response.headers


@pytest.mark.asyncio
async def test_get_logo_expired_cache(client: AsyncClient, test_db):
    """Test logo endpoint fetches new logo when cache is expired."""
    # Create an expired cached logo
    cached = CachedLogo(
        domain="expired.com",
        image_data=b"old_data",
        content_type="image/png",
        fetched_ts=time.time() - 86400,
        expires_ts=time.time() - 3600,  # Expired 1 hour ago
    )
    await cached.insert()

    # Mock the API call
    with patch("services.logo.logo_service.settings") as mock_settings:
        mock_settings.logo_dev_token = "test_token"

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = b"new_png_data"
        mock_response.headers = {"content-type": "image/png"}

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        mock_http_client.__aenter__.return_value = mock_http_client
        mock_http_client.__aexit__.return_value = None

        with patch("services.logo.logo_service.httpx.AsyncClient", return_value=mock_http_client):
            response = await client.get("/logos/expired.com")

            # Should have fetched new data
            assert response.status_code == 200
            assert response.content == b"new_png_data"


@pytest.mark.asyncio
async def test_get_logo_cache_miss_fetches_from_api(client: AsyncClient, test_db):
    """Test logo endpoint fetches from API on cache miss."""
    with patch("services.logo.logo_service.settings") as mock_settings:
        mock_settings.logo_dev_token = "test_token"

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = b"api_png_data"
        mock_response.headers = {"content-type": "image/png"}

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        mock_http_client.__aenter__.return_value = mock_http_client
        mock_http_client.__aexit__.return_value = None

        with patch("services.logo.logo_service.httpx.AsyncClient", return_value=mock_http_client):
            response = await client.get("/logos/newdomain.com")

            assert response.status_code == 200
            assert response.content == b"api_png_data"

            # Verify it was cached
            cached = await CachedLogo.find_one(CachedLogo.domain == "newdomain.com")
            assert cached is not None
            assert cached.image_data == b"api_png_data"


@pytest.mark.asyncio
async def test_get_logo_api_error_returns_404(client: AsyncClient, test_db):
    """Test logo endpoint returns 404 when API fails."""
    with patch("services.logo.logo_service.settings") as mock_settings:
        mock_settings.logo_dev_token = "test_token"

        mock_response = AsyncMock()
        mock_response.status_code = 404

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        mock_http_client.__aenter__.return_value = mock_http_client
        mock_http_client.__aexit__.return_value = None

        with patch("services.logo.logo_service.httpx.AsyncClient", return_value=mock_http_client):
            response = await client.get("/logos/nonexistent.com")

            assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_logo_normalizes_domain(client: AsyncClient, test_db):
    """Test logo endpoint normalizes domain to lowercase."""
    cached = CachedLogo(
        domain="uppercase.com",
        image_data=b"cached_data",
        content_type="image/png",
        fetched_ts=time.time(),
        expires_ts=time.time() + 86400,
    )
    await cached.insert()

    response = await client.get("/logos/UPPERCASE.COM")
    assert response.status_code == 200
    assert response.content == b"cached_data"


@pytest.mark.asyncio
async def test_get_logo_empty_domain(client: AsyncClient, test_db):
    """Test logo endpoint returns 404 for empty domain."""
    response = await client.get("/logos/")
    # FastAPI will likely return 404 for missing path parameter
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_logo_sets_browser_cache_header(client: AsyncClient, test_db):
    """Test logo response includes cache-control header."""
    cached = CachedLogo(
        domain="cachetest.com",
        image_data=b"data",
        content_type="image/png",
        fetched_ts=time.time(),
        expires_ts=time.time() + 86400,
    )
    await cached.insert()

    response = await client.get("/logos/cachetest.com")
    assert response.status_code == 200
    assert "max-age=86400" in response.headers.get("cache-control", "")
