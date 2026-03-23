"""GAIA-X Self-Description and compliance endpoints."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gaia-x", tags=["GAIA-X"])

# Resolve path to docs/ at repo root (parent of backend/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_SELF_DESCRIPTION_PATH = _REPO_ROOT / "docs" / "gaia-x-self-description.json"
# Fallback if run from backend as root (e.g. in Docker)
_FALLBACK_PATH = _BACKEND_DIR / "docs" / "gaia-x-self-description.json"


@router.get("/self-description")
async def get_self_description() -> dict:
    """GAIA-X Self-Description dieses Service."""
    path = _SELF_DESCRIPTION_PATH if _SELF_DESCRIPTION_PATH.exists() else _FALLBACK_PATH
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail="GAIA-X Self-Description file not found",
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.exception("Failed to load GAIA-X self-description: %s", e)
        raise HTTPException(
            status_code=503,
            detail="GAIA-X Self-Description temporarily unavailable",
        ) from e


@router.get("/compliance")
async def get_compliance_status() -> dict:
    """GAIA-X Alignment-Status und implementierte Prinzipien (keine Zertifizierung).

    Hinweis:
        Dieses JSON beschreibt technische und architektonische Ausrichtung
        an GAIA-X-Prinzipien. Es stellt **keine** formale Bestätigung von
        GAIA-X-Compliance oder einer Zertifizierung dar.
    """
    return {
        "gaia_x_ready": True,
        "version": "1.0.0",
        "principles": {
            "data_sovereignty": True,
            "gdpr_alignment": True,
            "open_standards": True,
            "transparency": True,
            "portability": True,
            "interoperability": True,
        },
        "standards": [
            "GA4GH-DRS-v1.3",
            "GA4GH-WES-v1.1",
            "GA4GH-Phenopackets-v2",
        ],
        "deployment_model": "on-premise",
        "data_location": "DE",
        "certification_status": "self-declared",
        "certification_note": (
            "GAIA-X Ready by Design — architectural alignment, "
            "not yet formally certified by GAIA-X Association"
        ),
        "roadmap": ["HL7-FHIR (geplant)"],
    }
