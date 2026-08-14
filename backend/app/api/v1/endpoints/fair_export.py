"""FAIR Data Export API endpoints."""

import logging
from io import BytesIO
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.isolation import apply_scope, get_scope_filter
from app.core.limiter import limiter
from app.models.notebook import Notebook
from app.models.paper import Paper
from app.models.patient_record import PatientRecordModel
from app.schemas.fair_export import FAIRComplianceReport, FAIRExportOptions
from app.services.fair_export_service import FAIRExportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fair-export", tags=["fair-export"])

# SSRF protection: only these hosts are used for Zenodo (no user-controlled URLs)
ALLOWED_ZENODO_HOSTS = frozenset({"zenodo.org", "sandbox.zenodo.org"})


class ZenodoUploadRequest(BaseModel):
    """Body for POST /fair-export/zenodo: options + token override."""

    zenodo_token: str | None = Field(default=None, description="Override env ZENODO_TOKEN")
    options: FAIRExportOptions


@router.post("/preview", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def fair_export_preview(
    request: Request,
    body: FAIRExportOptions,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Preview what would be included in the export."""
    scope = get_scope_filter(current_user)
    papers_stmt = select(func.count()).select_from(Paper)
    papers_stmt = apply_scope(papers_stmt, Paper, scope)
    papers_count = await db.scalar(papers_stmt) or 0
    pp_stmt = select(func.count()).select_from(PatientRecordModel)
    pp_stmt = apply_scope(pp_stmt, PatientRecordModel, scope)
    pheno_count = await db.scalar(pp_stmt) or 0
    nb_stmt = select(func.count()).select_from(Notebook)
    nb_stmt = apply_scope(nb_stmt, Notebook, scope)
    notebooks_count = await db.scalar(nb_stmt) or 0
    return {
        "papers_count": papers_count,
        "phenopackets_count": pheno_count,
        "notebooks_count": notebooks_count,
        "include_papers": body.include_papers,
        "include_phenopackets": body.include_phenopackets,
        "include_notebooks": body.include_notebooks,
        "include_drs": body.include_drs,
    }


@router.post("/compliance-check", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def fair_compliance_check(
    request: Request,
    body: FAIRExportOptions,
    current_user: dict = Depends(get_current_user),
) -> FAIRComplianceReport:
    """Compute FAIR compliance score for the given options."""
    service = FAIRExportService()
    package = {
        "title": body.title,
        "license": body.license,
        "funding": body.funding,
    }
    return await service.check_fair_compliance(package)


@router.post("/download", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def fair_export_download(
    request: Request,
    body: FAIRExportOptions,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Generate and download FAIR export as ZIP."""
    service = FAIRExportService()
    zip_bytes = await service.create_export_package(db, current_user, body)
    logger.info(
        "FAIR export download by user=%s title=%s",
        current_user.get("sub", "dev"),
        body.title[:80] if body.title else "",
    )
    filename = "".join(c for c in body.title if c.isalnum() or c in " ._-").strip() or "fair_export"
    filename = f"{filename}.zip"
    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/zenodo", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
async def fair_export_zenodo(
    request: Request,
    body: ZenodoUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Upload FAIR package to Zenodo (optional; requires ZENODO_TOKEN in .env or in body)."""
    settings = get_settings()
    token = body.zenodo_token or settings.zenodo_token
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zenodo upload not configured. Set ZENODO_TOKEN in .env or pass zenodo_token.",
        )
    logger.info(
        "Zenodo upload started for user=%s",
        current_user.get("sub", "dev"),
    )
    service = FAIRExportService()
    zip_bytes = await service.create_export_package(db, current_user, body.options)

    def _zenodo_host_allowed(url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return host in ALLOWED_ZENODO_HOSTS

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://zenodo.org/api/deposit/depositions",
                params={"access_token": token.strip()},
                json={},
            )
            r.raise_for_status()
            dep = r.json()
            dep_id = dep.get("id")
            if not dep_id:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Zenodo: no deposition ID",
                )
            upload_url = dep.get("links", {}).get("bucket")
            if not upload_url or not _zenodo_host_allowed(str(upload_url)):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Zenodo: bucket URL missing or not on an allowlisted host",
                )
            safe_title = (
                "".join(c for c in body.options.title if c.isalnum() or c in " ._-").strip()
                or "fair_export"
            )
            filename = f"{safe_title}.zip"
            up = await client.put(
                f"{upload_url}/{filename}",
                params={"access_token": token.strip()},
                content=zip_bytes,
            )
            up.raise_for_status()
            metadata = await service.generate_datacite_metadata(body.options)
            patch = await client.patch(
                f"https://zenodo.org/api/deposit/depositions/{dep_id}",
                params={"access_token": token.strip()},
                json={"metadata": metadata},
            )
            patch.raise_for_status()
            return {
                "deposition_id": dep_id,
                "doi": dep.get("doi"),
                "record_url": dep.get("links", {}).get("record"),
                "message": "Upload successful. Publish from Zenodo dashboard to get DOI.",
            }
    except httpx.HTTPStatusError as e:
        logger.warning("Zenodo API error: %s %s", e.response.status_code, e.response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Zenodo API error: {e.response.text}",
        ) from e
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Zenodo request failed: {e}",
        ) from e
