from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from api.endpoints.auth.auth_endpoints import router as auth_router
from api.endpoints.logos.logo_endpoints import router as logos_router
from api.endpoints.subscriptions.subscription_endpoints import (
    router as subscriptions_router,
)
from api.endpoints.users.users_endpoints import router as users_router
from config.config import settings
from config.logging import configure_logging, get_logger
from models import (
    AuthChallenge,
    CachedLogo,
    PasskeyCredential,
    Session,
    Subscription,
    User,
)

# Configure logging before anything else
configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan manager."""
    log.info("starting_application", dev=settings.dev)

    # Initialize MongoDB connection
    client = AsyncIOMotorClient(settings.mongo_uri)
    database = client.get_default_database()

    log.info("initializing_beanie", database=database.name)
    await init_beanie(
        database=database,
        document_models=[
            User,
            PasskeyCredential,
            Session,
            Subscription,
            AuthChallenge,
            CachedLogo,
        ],
    )

    yield

    # Cleanup
    log.info("shutting_down_application")
    client.close()


app = FastAPI(
    title="Snout Pink API",
    description="Passkey-authenticated API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - allow all origins in dev mode
if settings.dev:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(
    subscriptions_router, prefix="/subscriptions", tags=["subscriptions"]
)
app.include_router(logos_router, prefix="/logos", tags=["logos"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/app-info")
async def app_info() -> dict[str, str | None]:
    """Public app info including legal URLs."""
    return {
        "imprint_url": settings.imprint_url,
        "privacy_url": settings.privacy_url,
        "github_url": settings.github_url,
    }
