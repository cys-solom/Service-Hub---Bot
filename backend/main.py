"""Diaa Store — FastAPI Application"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import engine
from models.base import Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown"""
    logger.info("🚀 Starting Diaa Store Backend...")
    # Create tables (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables ready")

    # Seed default admin if needed
    from services.seed import seed_defaults
    await seed_defaults()

    yield

    logger.info("🔒 Shutting down...")
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from api.v1 import router as api_v1_router
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # WebSocket
    from api.v1.websocket import router as ws_router
    app.include_router(ws_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.APP_NAME}

    return app


app = create_app()
