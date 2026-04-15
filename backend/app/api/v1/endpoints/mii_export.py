"""MII-KDS FHIR Bundle export API."""

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.isolation import get_scope_filter, get_scope_values
from app.core.limiter import limiter
from app.models.mii_export import MiiExportArtifact, MiiExportJob
from app.schemas.mii_export import (
    MiiBundleExportRequest,
    MiiBundleExportResponse,
    MiiExportJobCreate,
    MiiExportJobMetricsRead,
    MiiExportJobRead,
)
from app.services import mii_export_service as mii_svc
from app.services.mii_export_worker import run_mii_export_job_task

router = APIRouter(prefix="/mii-export", tags=["mii-export"])


def _job_to_read(job: MiiExportJob, art: MiiExportArtifact | None = None) -> MiiExportJobRead:
    return MiiExportJobRead(
        id=str(job.id),
        status=job.status,
        error_message=job.error_message,
        consent_check_summary=job.consent_check_summary or {},
        validation_summary=job.validation_summary,
        validator_ig_package_id=job.validator_ig_package_id,
        validator_ig_package_version=job.validator_ig_package_version,
        validator_mode=job.validator_mode,
        artifact_id=str(art.id) if art else None,
        created_at=job.created_at.isoformat() if job.created_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        next_run_at=job.next_run_at.isoformat() if job.next_run_at else None,
    )


@router.post("/bundles", response_model=MiiBundleExportResponse)
@limiter.limit("20/minute")
async def export_mii_bundle(
    request: Request,
    body: MiiBundleExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> MiiBundleExportResponse:
    """Build a pseudonymized MII-oriented FHIR Bundle (synchronous)."""
    settings = get_settings()
    scope = get_scope_filter(current_user)
    policy_id = body.policy_id or settings.mii_default_consent_policy_id
    modules = (
        list(body.modules)
        if body.modules
        else [
            "diagnosis",
            "laboratory",
            "biospecimen",
            "genomics",
        ]
    )
    try:
        bundle, summary, validation_summary = await mii_svc.build_mii_bundle_for_pseudonyms(
            db,
            body.pseudonym_ids,
            modules,
            policy_id,
            body.research_project_ids,
            scope,
            strict_profile_validation=body.strict_profile_validation,
            fail_on_partial_mapping=body.fail_on_partial_mapping,
        )
    except ValueError as e:
        if str(e) == "consent_denied":
            summ, _ = await mii_svc.run_consent_gate(
                db,
                body.pseudonym_ids,
                policy_id,
                body.research_project_ids,
                scope,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"message": "Consent check failed", "consent_check_summary": summ},
            ) from e
        if str(e) == "validation_failed":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="FHIR bundle validation failed",
            ) from e
        if str(e) == "mapping_incomplete":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="FHIR mapping incomplete for requested modules",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return MiiBundleExportResponse(
        bundle=bundle,
        consent_check_summary=summary,
        validation_summary=validation_summary,
        validator_ig_package_id=settings.mii_ig_package_id,
        validator_ig_package_version=settings.mii_ig_package_version,
        validator_mode="strict-profile" if body.strict_profile_validation else "basic",
        profile_set_version=f"MII-KDS-{settings.mii_kds_release}",
    )


@router.post("/jobs", response_model=MiiExportJobRead, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def create_mii_export_job(
    request: Request,
    background_tasks: BackgroundTasks,
    body: MiiExportJobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> MiiExportJobRead:
    """Persist export job and process asynchronously (same bundle as /bundles)."""
    settings = get_settings()
    scope = get_scope_filter(current_user)
    scope_values = get_scope_values(current_user)
    policy_id = body.policy_id or settings.mii_default_consent_policy_id
    modules = (
        list(body.modules)
        if body.modules
        else [
            "diagnosis",
            "laboratory",
            "biospecimen",
            "genomics",
        ]
    )
    summ, errs = await mii_svc.run_consent_gate(
        db,
        body.pseudonym_ids,
        policy_id,
        body.research_project_ids,
        scope,
    )
    if errs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Consent check failed", "consent_check_summary": summ},
        )
    records = await mii_svc.load_export_patient_records(db, body.pseudonym_ids, scope)
    missing = [p for p in body.pseudonym_ids if p not in records]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"missing_patients:{missing}",
        )

    job = await mii_svc.enqueue_mii_export_job(
        db,
        user_id=current_user.get("sub") or "unknown",
        scope_snapshot=scope_values,
        pseudonym_ids=body.pseudonym_ids,
        modules=modules,
        policy_id=policy_id,
        research_project_ids=body.research_project_ids,
        strict_profile_validation=body.strict_profile_validation,
        fail_on_partial_mapping=body.fail_on_partial_mapping,
    )
    background_tasks.add_task(run_mii_export_job_task, job.id)
    return _job_to_read(job, None)


@router.get("/jobs/metrics", response_model=MiiExportJobMetricsRead)
@limiter.limit("60/minute")
async def get_mii_export_job_metrics(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> MiiExportJobMetricsRead:
    """Per-user export job counts by status (queued, running, succeeded, failed, dead_letter)."""
    sub = current_user.get("sub") or "unknown"
    by_status = await mii_svc.get_mii_export_metrics_for_user(db, sub)
    return MiiExportJobMetricsRead(by_status=by_status)


@router.get("/jobs/{job_id}", response_model=MiiExportJobRead)
@limiter.limit("60/minute")
async def get_mii_export_job(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> MiiExportJobRead:
    sub = current_user.get("sub") or "unknown"
    job, art = await mii_svc.get_job_and_artifact(db, job_id, sub)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _job_to_read(job, art)


@router.get("/jobs/{job_id}/artifact")
@limiter.limit("60/minute")
async def download_mii_export_artifact(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Response:
    """Download stored FHIR Bundle JSON."""
    sub = current_user.get("sub") or "unknown"
    job, art = await mii_svc.get_job_and_artifact(db, job_id, sub)
    if not job or not art:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return Response(
        content=json.dumps(art.bundle_json, ensure_ascii=False),
        media_type="application/fhir+json",
        headers={"Content-Disposition": f'attachment; filename="mii-bundle-{job_id}.json"'},
    )


@router.get("/jobs/{job_id}/validation-report")
@limiter.limit("60/minute")
async def get_mii_export_validation_report(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return persisted validation report and validator metadata for a job."""
    sub = current_user.get("sub") or "unknown"
    job, _ = await mii_svc.get_job_and_artifact(db, job_id, sub)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {
        "job_id": str(job.id),
        "validation_summary": job.validation_summary or {},
        "validator_ig_package_id": job.validator_ig_package_id,
        "validator_ig_package_version": job.validator_ig_package_version,
        "validator_mode": job.validator_mode,
    }
