"""API v1 router aggregating all endpoint modules."""

from fastapi import APIRouter

from app.api.v1.endpoints import blast as blast_ep
from app.api.v1.endpoints import gaia_x as gaia_x_ep
from app.api.v1.endpoints import health
from app.api.v1.endpoints import library as library_ep
from app.api.v1.endpoints import literature as literature_ep
from app.api.v1.endpoints import phenopackets as phenopackets_ep
from app.api.v1.endpoints import pseudonymize as pseudonymize_ep
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter(prefix=settings.api_v1_prefix)

api_router.include_router(health.router)
api_router.include_router(gaia_x_ep.router)
api_router.include_router(literature_ep.router)
api_router.include_router(library_ep.router)
api_router.include_router(pseudonymize_ep.router)
api_router.include_router(phenopackets_ep.router)
api_router.include_router(blast_ep.router)
