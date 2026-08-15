"""Health check endpoints for monitoring and load balancers."""

import logging
import os
import shutil
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

_FEATURES_TTL_SECONDS = 60.0
_features_cache: tuple[float, dict[str, bool]] | None = None


def reset_features_cache() -> None:
    """Drop cached feature flags (tests)."""
    global _features_cache
    _features_cache = None


async def check_features() -> dict[str, bool]:
    """Prüfe welche Features wirklich verfügbar sind.

    Gibt ehrliche Feature Flags zurück (keine Frontend-Env-Variablen).
    Cached for 60s in non-test deployments so probes do not load spaCy/models.
    """
    global _features_cache
    testing = os.environ.get("TESTING") == "1"
    now = time.monotonic()
    if not testing and _features_cache is not None:
        cached_at, cached = _features_cache
        if now - cached_at < _FEATURES_TTL_SECONDS:
            return dict(cached)

    features = await _compute_features()
    if not testing:
        _features_cache = (now, features)
    return dict(features)


async def _compute_features() -> dict[str, bool]:
    features: dict[str, bool] = {
        "embeddings": False,
        "semantic_search": False,
        "llm_summaries": False,
        "locus_rag": False,
        "spacy_ner": False,
        "blast": False,
        "nextflow": False,
    }

    # Import only — do not construct SentenceTransformer (downloads/loads weights).
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401

        features["embeddings"] = True
        features["semantic_search"] = True
    except ImportError:
        pass

    settings = get_settings()
    backend = settings.resolved_llm_backend()
    if backend == "anthropic":
        key = (settings.anthropic_api_key or "").strip()
        features["llm_summaries"] = bool(
            key and key != "dummy" and key.startswith("sk-ant-") and len(key) > 20
        )
    elif backend == "openai_compatible":
        base = (settings.openai_api_base or "").strip().rstrip("/")
        if base:
            try:
                headers: dict[str, str] = {}
                ok = (settings.openai_api_key or "").strip()
                if ok:
                    headers["Authorization"] = f"Bearer {ok}"
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{base}/models", headers=headers)
                    features["llm_summaries"] = resp.status_code == 200
            except (httpx.HTTPError, OSError, ValueError):
                features["llm_summaries"] = False
        else:
            features["llm_summaries"] = False
    else:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{settings.ollama_base_url.rstrip('/')}/api/tags",
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("models", [])
                    features["llm_summaries"] = len(models) > 0
                else:
                    features["llm_summaries"] = False
        except (httpx.HTTPError, OSError, ValueError):
            features["llm_summaries"] = False

    # Package presence only — do not load the spaCy pipeline on every probe.
    try:
        import spacy

        features["spacy_ner"] = bool(spacy.util.is_package("de_core_news_sm"))
    except ImportError:
        pass

    features["blast"] = shutil.which("blastn") is not None
    features["nextflow"] = shutil.which("nextflow") is not None
    features["locus_rag"] = bool(getattr(settings, "locus_enabled", False))
    return features


@router.get("", response_model=dict[str, Any])
async def health_check() -> dict[str, Any]:
    """Basic liveness probe: returns 200 if the API is running.

    Returns:
        dict: Status, version, metadata, and honest feature flags.
    """
    settings = get_settings()
    features = await check_features()
    data_sovereignty = "partial" if settings.resolved_llm_backend() == "anthropic" else "full"
    return {
        "status": "healthy",
        "version": settings.version,
        "developed_by": (
            "Synaptic Four — proudly developed by individuals on the autism spectrum in Germany."
        ),
        "ga4gh_alignment": True,
        "gaia_x_alignment": True,
        "features": features,
        "deployment": (settings.deployment or "").lower(),
        "data_sovereignty": data_sovereignty,
        "ga4gh_backend": {
            "drs": "ferrum" if settings.ferrum_drs_url else "local",
            "wes": "ferrum" if settings.ferrum_wes_url else "local",
        },
    }


@router.get("/ready", response_model=dict[str, Any])
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    """Readiness probe: checks database connectivity.

    Returns 200 only if a simple DB query succeeds. Returns 503 when the DB
    is unreachable (Kubernetes readiness / load balancer).
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.exception("Readiness check failed: %s", e)
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "disconnected", "error": str(e)},
        )
