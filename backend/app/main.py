"""BioResearch Assistant — FastAPI application entry point."""

import logging
import os
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
from app.services.ferrum_backend import maybe_proxy_ferrum

# Configure logging before other imports that may log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def assert_testing_env_safe() -> None:
    """Refuse to start if TESTING=1 is set on a non-dev deployment.

    Import-time test doubles (Presidio, BLAST parser, pgvector) key off TESTING=1.
    That must never silently apply in production.
    """
    if os.environ.get("TESTING") == "1" and not get_settings().allows_unauthenticated_dev:
        raise RuntimeError(
            "TESTING=1 is set but DEPLOYMENT is not local|development|test. "
            "Refusing to start: test doubles would replace production implementations."
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    assert_testing_env_safe()
    get_settings().assert_runtime_hardened()
    logger.info("Starting BioResearch Assistant API")
    yield
    from app.services.llm_service import close_llm_service

    await close_llm_service()
    logger.info("Shutting down BioResearch Assistant API")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance.
    """
    settings = get_settings()
    settings.assert_runtime_hardened()

    expose_docs = settings.allows_unauthenticated_dev or settings.debug
    app = FastAPI(
        title=settings.app_name,
        description=(
            "On-premise KI-System für Literature Mining, "
            "Bioinformatik-Pipelines und datenschutzfreundliche Pseudonymisierung"
        ),
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs" if expose_docs else None,
        redoc_url="/redoc" if expose_docs else None,
        openapi_url="/openapi.json" if expose_docs else None,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    cors_origins = list(settings.cors_origins)
    if "*" in cors_origins:
        if settings.is_production_runtime or not settings.allows_unauthenticated_dev:
            raise RuntimeError(
                "CORS_ORIGINS=* is forbidden outside explicit local/development/test deploys"
            )
        logger.warning("CORS wildcard (*) enabled only because DEPLOYMENT is local/dev/test")
    if settings.allows_unauthenticated_dev:
        for origin in (
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ):
            if origin not in cors_origins:
                cors_origins.append(origin)
    allow_origin_regex = None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=allow_origin_regex,
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
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.is_production_runtime or (
            settings.deployment and settings.deployment not in ("local", "development", "test", "")
        ):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
            )
        return response

    @app.middleware("http")
    async def ferrum_ga4gh_backend(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        proxied = await maybe_proxy_ferrum(request)
        if proxied is not None:
            return proxied
        return await call_next(request)

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,  # noqa: ANN001
    ) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        if settings.deployment in ("local", "development", "test"):
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
    async def root() -> dict[str, str | None]:
        """Root endpoint with API info."""
        return {
            "service": settings.app_name,
            "docs": "/docs" if expose_docs else None,
            "health": f"{settings.api_v1_prefix}/health",
        }

    return app


app = create_application()
