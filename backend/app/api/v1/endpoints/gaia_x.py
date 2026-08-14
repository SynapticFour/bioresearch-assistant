"""GAIA-X Self-Description and compliance endpoints."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gaia-x", tags=["GAIA-X"])

# Resolve candidate locations: repo docs/, backend/docs (Docker COPY . .), /app/docs (Railway).
_HERE = Path(__file__).resolve()
_SELF_DESCRIPTION_CANDIDATES = (
    _HERE.parents[5] / "docs" / "gaia-x-self-description.json",  # repo root
    _HERE.parents[4] / "docs" / "gaia-x-self-description.json",  # backend or /app
    Path("/app/docs/gaia-x-self-description.json"),
)


@router.get("/self-description")
async def get_self_description() -> dict:
    """GAIA-X Self-Description dieses Service."""
    path = next((p for p in _SELF_DESCRIPTION_CANDIDATES if p.exists()), None)
    if path is None:
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
        "gaia_x_ready": False,
        "gaia_x_certified": False,
        "version": "1.3.0",
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
        "roadmap": ["HL7-FHIR / MII-KDS export (implemented)", "GAIA-X Level 1 credential"],
    }
