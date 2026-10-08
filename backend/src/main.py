import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import AsyncMongoClient
from pymongo.errors import (
    NotPrimaryError,
    OperationFailure,
    ServerSelectionTimeoutError,
)

from config.config import settings
from config.logging import configure_logging, get_logger
from interfaces.api.endpoints.auth.auth_endpoints import router as auth_router
from interfaces.api.endpoints.logos.logo_endpoints import router as logos_router
from interfaces.api.endpoints.mcp_tokens.mcp_tokens_endpoints import (
    router as mcp_tokens_router,
)
from interfaces.api.endpoints.subscriptions.subscription_endpoints import (
    router as subscriptions_router,
)
from interfaces.api.endpoints.users.users_endpoints import router as users_router
from interfaces.mcp.server import build_mcp
from models import (
    AuthChallenge,
    CachedLogo,
    McpToken,
    PasskeyCredential,
    Session,
    Subscription,
    User,
)

configure_logging()
log = get_logger(__name__)

_DOCUMENT_MODELS = [
    User,
    PasskeyCredential,
    Session,
    Subscription,
    AuthChallenge,
    CachedLogo,
    McpToken,
]


def create_app(*, connect_db: bool = True) -> FastAPI:
    """Create the API and mount the MCP server at /mcp."""
    mcp = build_mcp()
    mcp_http = mcp.http_app(
        path="/mcp",
        transport="streamable-http",
        stateless_http=True,
        host_origin_protection=False,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        """Application lifespan manager."""
        log.info("starting_application", dev=settings.dev)
        client: AsyncMongoClient | None = None
        if connect_db:
            client = AsyncMongoClient(settings.mongo_uri)
            database = client.get_default_database()
            log.info("initializing_beanie", database=database.name)
            while True:
                try:
                    await init_beanie(
                        database=database,
                        document_models=_DOCUMENT_MODELS,
                    )
                    break
                except (NotPrimaryError, OperationFailure, ServerSelectionTimeoutError) as exc:
                    waiting = settings.standby_mode and (
                        "not primary" in str(exc).lower() or isinstance(exc, NotPrimaryError)
                    )
                    if waiting:
                        log.info("standby_waiting_for_primary", retry_in=5)
                        await asyncio.sleep(5)
                    else:
                        raise

        async with mcp_http.lifespan(app):
            yield

        log.info("shutting_down_application")
        if client is not None:
            await client.close()

    app = FastAPI(
        title="Snout Pink API",
        description="Passkey-authenticated API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.mcp_http = mcp_http

    if settings.dev:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(mcp_tokens_router, prefix="/users", tags=["mcp-tokens"])
    app.include_router(users_router, prefix="/users", tags=["users"])
    app.include_router(subscriptions_router, prefix="/subscriptions", tags=["subscriptions"])
    app.include_router(logos_router, prefix="/logos", tags=["logos"])

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.get("/app-info")
    async def app_info() -> dict[str, str | None]:
        """Public app info including legal URLs and analytics config."""
        return {
            "imprint_url": settings.imprint_url,
            "privacy_url": settings.privacy_url,
            "github_url": settings.github_url,
            "umami_website_id": settings.umami_website_id,
            "umami_host_url": settings.umami_host_url,
        }

    app.mount("/", mcp_http)
    return app


app = create_app()
