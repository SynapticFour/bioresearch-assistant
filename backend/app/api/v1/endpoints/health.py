"""Health check endpoints for monitoring and load balancers."""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=dict[str, Any])
async def health_check() -> dict[str, Any]:
    """Basic liveness probe: returns 200 if the API is running.

    Returns:
        dict: Status and app name.
    """
    return {"status": "ok", "service": "BioResearch Assistant API"}


@router.get("/ready", response_model=dict[str, Any])
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Readiness probe: checks database connectivity.

    Returns 200 only if a simple DB query succeeds. Use for Kubernetes
    readiness probes or load balancer health checks.

    Args:
        db: Injected async database session.

    Returns:
        dict: Status and database connectivity.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.exception("Readiness check failed: %s", e)
        return {"status": "not_ready", "database": "disconnected", "error": str(e)}
