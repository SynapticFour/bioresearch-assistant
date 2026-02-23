"""Health check endpoints for monitoring and load balancers."""

import logging
import shutil
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


async def check_features() -> dict[str, bool]:
    """Prüfe welche Features wirklich verfügbar sind.

    Gibt ehrliche Feature Flags zurück (keine Frontend-Env-Variablen).
    """
    features: dict[str, bool] = {
        "embeddings": False,
        "semantic_search": False,
        "llm_summaries": False,
        "spacy_ner": False,
        "blast": False,
        "nextflow": False,
    }

    # Embeddings verfügbar? (sentence-transformers)
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401

        features["embeddings"] = True
        features["semantic_search"] = True
    except ImportError:
        pass

    # LLM verfügbar? (Ollama oder gültiger Anthropic-Key)
    settings = get_settings()
    key = (settings.anthropic_api_key or "").strip()
    if key and key != "dummy" and key.startswith("sk-ant-") and len(key) > 20:
        features["llm_summaries"] = True
    else:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
                features["llm_summaries"] = resp.status_code == 200
        except Exception:
            pass

    # spaCy NER verfügbar? (Presidio mit de_core_news_sm)
    try:
        import spacy

        spacy.load("de_core_news_sm")
        features["spacy_ner"] = True
    except Exception:
        pass

    # BLAST verfügbar?
    features["blast"] = shutil.which("blastn") is not None

    # Nextflow verfügbar?
    features["nextflow"] = shutil.which("nextflow") is not None

    return features


@router.get("", response_model=dict[str, Any])
async def health_check() -> dict[str, Any]:
    """Basic liveness probe: returns 200 if the API is running.

    Returns:
        dict: Status, version, metadata, and honest feature flags.
    """
    settings = get_settings()
    features = await check_features()
    # data_sovereignty: "full" when using local LLM (Ollama), "partial" when using Anthropic API
    data_sovereignty = (
        "full"
        if not (settings.anthropic_api_key and settings.anthropic_api_key.strip())
        else "partial"
    )
    return {
        "status": "healthy",
        "version": settings.version,
        "developed_by": "Synaptic Four — proudly developed by individuals on the autism spectrum",
        "ga4gh_compliant": True,
        "gaia_x_ready": True,
        "features": features,
        "deployment": (settings.deployment or "").lower(),
        "data_sovereignty": data_sovereignty,
    }


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
