"""BioResearch Assistant — FastAPI application entry point."""

import logging
import sys
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.endpoints import drs as drs_ep
from app.api.v1.endpoints import wes as wes_ep
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.limiter import limiter

# Configure logging before other imports that may log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    logger.info("Starting BioResearch Assistant API")
    yield
    logger.info("Shutting down BioResearch Assistant API")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "On-premise KI-System für Literature Mining, "
            "Bioinformatik-Pipelines und DSGVO-konforme Pseudonymisierung"
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    cors_origins = list(settings.cors_origins)
    if "*" in cors_origins and settings.deployment not in ("local", "development", ""):
        logger.warning(
            "CORS wildcard (*) in production. Set CORS_ORIGINS to specific origins in .env"
        )
    for origin in (
        "http://localhost:5173",
        "http://localhost:3000",
        "https://bioresearch-assistant.vercel.app",
    ):
        if origin not in cors_origins:
            cors_origins.append(origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=[
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "OPTIONS",
            "PATCH",
        ],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
        ],
    )

    @app.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.deployment and settings.deployment not in ("local", "development", ""):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,  # noqa: ANN001
    ) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        if settings.deployment in ("local", "development", ""):
            return JSONResponse(
                status_code=500,
                content={"detail": str(exc)},
            )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    app.include_router(api_router)
    app.include_router(wes_ep.router, prefix="/ga4gh/wes/v1")
    app.include_router(drs_ep.router, prefix="/ga4gh/drs/v1")

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint with API info."""
        return {
            "service": settings.app_name,
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
        }

    return app


app = create_application()
