"""MII-KDS FHIR Bundle export with consent gate."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.interoperability.fhir.bundle_builder import build_collection_bundle
from app.interoperability.mii.ig_loader import profile_by_module
from app.interoperability.mii import phenopacket_to_fhir as pp2f
from app.models.mii_export import MiiExportArtifact, MiiExportJob
from app.models.patient_record import PatientRecordModel
from app.services.fhir_validation_service import validate_bundle
from app.services.terminology_mapping_service import summarize_coding_quality
from app.services.terminology_override_service import load_active_override_maps
from app.services import consent_service as cs

logger = logging.getLogger(__name__)


def _apply_scope_patient(stmt, scope: dict):
    if "user_id" in scope and scope["user_id"]:
        return stmt.where(PatientRecordModel.user_id == scope["user_id"])
    if "team_id" in scope and scope["team_id"]:
        return stmt.where(PatientRecordModel.team_id == scope["team_id"])
    return stmt


async def load_export_patient_records(
    db: AsyncSession,
    pseudonym_ids: list[str],
    scope: dict,
) -> dict[str, PatientRecordModel]:
    """Load patient rows for export (scoped); exposed for API pre-checks."""
    return await _load_patient_records(db, pseudonym_ids, scope)


async def _load_patient_records(
    db: AsyncSession,
    pseudonym_ids: list[str],
    scope: dict,
) -> dict[str, PatientRecordModel]:
    stmt = select(PatientRecordModel).where(PatientRecordModel.pseudonym_id.in_(pseudonym_ids))
    stmt = _apply_scope_patient(stmt, scope)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {r.pseudonym_id: r for r in rows}


async def run_consent_gate(
    db: AsyncSession,
    pseudonym_ids: list[str],
    policy_id: str,
    research_project_ids: list[str],
    scope: dict,
) -> tuple[dict[str, Any], list[str]]:
    """Returns summary dict and list of error codes (empty if ok)."""
    summary: dict[str, Any] = {"policy_id": policy_id, "per_pseudonym": {}}
    errors: list[str] = []
    for pid in pseudonym_ids:
        c = await cs.find_active_consent(db, pid, policy_id, scope)
        entry: dict[str, Any] = {
            "consent_id": str(c.id) if c else None,
            "ok": False,
        }
        if not c:
            entry["reason"] = "no_active_consent"
            errors.append(f"no_consent:{pid}")
        elif not cs.projects_covered(c, research_project_ids):
            entry["reason"] = "project_not_covered"
            errors.append(f"project_not_covered:{pid}")
        else:
            entry["ok"] = True
        summary["per_pseudonym"][pid] = entry
    return summary, errors


def _bundle_sha256(bundle: dict[str, Any]) -> str:
    raw = json.dumps(bundle, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def build_mii_bundle_for_pseudonyms(
    db: AsyncSession,
    pseudonym_ids: list[str],
    modules: list[str],
    policy_id: str,
    research_project_ids: list[str],
    scope: dict,
    *,
    strict_profile_validation: bool = False,
    fail_on_partial_mapping: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build FHIR Bundle + consent summary."""
    summary, errors = await run_consent_gate(
        db, pseudonym_ids, policy_id, research_project_ids, scope
    )
    if errors:
        raise ValueError("consent_denied")

    records = await _load_patient_records(db, pseudonym_ids, scope)
    missing = [p for p in pseudonym_ids if p not in records]
    if missing:
        raise ValueError(f"missing_patients:{missing}")

    settings = get_settings()
    disease_ov, lab_ov = await load_active_override_maps(db)
    attach = settings.mii_bundle_attach_meta_profile or strict_profile_validation
    patient_profile = profile_by_module("person")
    diagnosis_profile = profile_by_module("diagnosis")
    phenotype_profile = profile_by_module("phenotype")
    laboratory_profile = profile_by_module("laboratory")
    biospecimen_profile = profile_by_module("biospecimen")
    genomics_profile = profile_by_module("genomics")

    entries: list[dict[str, Any]] = []
    mapping_issues: list[str] = []
    for pid in pseudonym_ids:
        rec = records[pid]
        pp = rec.phenopacket_json or {}
        sections = pp2f.extract_phenopacket_sections(pp)
        meta = pp.get("meta_data") or {}
        recorded_date = meta.get("created") or meta.get("created_at")
        patient = pp2f.build_patient(pid, attach_profile=attach, profile_url=patient_profile)
        pref = f"Patient/{patient['id']}"
        entries.append(patient)

        if "diagnosis" in modules:
            if not sections["diseases"] and not sections["phenotypic_features"]:
                mapping_issues.append(f"{pid}:diagnosis:no_disease_or_phenotype")
            entries.extend(
                pp2f.build_conditions_from_diseases(
                    pid,
                    pref,
                    sections["diseases"],
                    attach_profile=attach,
                    profile_url=diagnosis_profile,
                    disease_overrides=disease_ov,
                    recorded_date=str(recorded_date) if recorded_date else None,
                )
            )
            entries.extend(
                pp2f.build_observations_from_phenotypes(
                    pid,
                    pref,
                    sections["phenotypic_features"],
                    attach_profile=attach,
                    profile_url=phenotype_profile,
                )
            )
        if "laboratory" in modules:
            if not sections["measurements"]:
                mapping_issues.append(f"{pid}:laboratory:no_measurements")
            entries.extend(
                pp2f.build_laboratory_observations_from_measurements(
                    pid,
                    pref,
                    sections["measurements"],
                    attach_profile=attach,
                    profile_url=laboratory_profile,
                    lab_overrides=lab_ov,
                )
            )
        if "biospecimen" in modules:
            if not sections["biosamples"]:
                mapping_issues.append(f"{pid}:biospecimen:no_biosamples")
            entries.extend(
                pp2f.build_specimens_from_biosamples(
                    pid,
                    pref,
                    sections["biosamples"],
                    attach_profile=attach,
                    profile_url=biospecimen_profile,
                )
            )
        if "genomics" in modules:
            if not sections["interpretations"]:
                mapping_issues.append(f"{pid}:genomics:no_interpretations")
            entries.extend(
                pp2f.build_genomic_observations_from_interpretations(
                    pid,
                    pref,
                    sections["interpretations"],
                    attach_profile=attach,
                    profile_url=genomics_profile,
                )
            )

    bundle = build_collection_bundle(entries)
    bundle.setdefault(
        "identifier",
        {"system": "urn:ietf:rfc:3986", "value": f"mii-export-{_bundle_sha256(bundle)[:16]}"},
    )
    validation_summary = validate_bundle(
        bundle,
        strict_profile_validation=strict_profile_validation,
    )
    validation_summary["mapping_issues"] = mapping_issues
    validation_summary["terminology_summary"] = summarize_coding_quality(
        [entry.get("resource", {}) for entry in bundle.get("entry", []) if isinstance(entry, dict)]
    )
    if fail_on_partial_mapping and mapping_issues:
        raise ValueError("mapping_incomplete")
    if not validation_summary["ok"]:
        raise ValueError("validation_failed")
    return bundle, summary, validation_summary


async def enqueue_mii_export_job(
    db: AsyncSession,
    *,
    user_id: str,
    scope_snapshot: dict,
    pseudonym_ids: list[str],
    modules: list[str],
    policy_id: str,
    research_project_ids: list[str],
    strict_profile_validation: bool = False,
    fail_on_partial_mapping: bool = False,
) -> MiiExportJob:
    """Create a queued MII export job (background worker completes it)."""
    settings = get_settings()
    job_id = uuid4()
    job = MiiExportJob(
        id=job_id,
        requested_by_user_id=user_id,
        scope_snapshot=scope_snapshot,
        input={
            "pseudonym_ids": pseudonym_ids,
            "modules": modules,
            "policy_id": policy_id,
            "research_project_ids": research_project_ids,
            "strict_profile_validation": strict_profile_validation,
            "fail_on_partial_mapping": fail_on_partial_mapping,
        },
        status="queued",
        max_attempts=settings.mii_export_max_attempts,
        attempt_count=0,
        consent_check_summary=None,
        validation_summary=None,
        validator_ig_package_id=None,
        validator_ig_package_version=None,
        validator_mode=None,
        error_message=None,
        finished_at=None,
        next_run_at=None,
        started_at=None,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def load_mii_export_job_for_worker(
    db: AsyncSession, job_id: UUID
) -> MiiExportJob | None:
    """Load job row by id (worker; no user filter)."""
    stmt = select(MiiExportJob).where(MiiExportJob.id == job_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def persist_job_success(
    db: AsyncSession,
    job: MiiExportJob,
    bundle: dict[str, Any],
    summary: dict[str, Any],
    validation_summary: dict[str, Any],
) -> MiiExportArtifact:
    """Mark job succeeded and store artifact."""
    settings = get_settings()
    now = datetime.now(UTC)
    job.status = "succeeded"
    job.consent_check_summary = summary
    job.validation_summary = validation_summary
    job.validator_ig_package_id = settings.mii_ig_package_id
    job.validator_ig_package_version = settings.mii_ig_package_version
    job.validator_mode = "strict-profile" if job.input.get("strict_profile_validation") else "basic"
    job.error_message = None
    job.finished_at = now
    job.started_at = None
    job.next_run_at = None
    art = MiiExportArtifact(
        id=uuid4(),
        job_id=job.id,
        content_type="application/fhir+json",
        bundle_json=bundle,
        sha256=_bundle_sha256(bundle),
        profile_set_version=f"MII-KDS-{settings.mii_kds_release}",
    )
    db.add(art)
    await db.commit()
    await db.refresh(job)
    await db.refresh(art)
    return art


async def mark_job_permanent_failure(
    db: AsyncSession, job: MiiExportJob, message: str
) -> None:
    job.status = "failed"
    job.error_message = message
    job.finished_at = datetime.now(UTC)
    job.started_at = None
    job.next_run_at = None
    await db.commit()


async def mark_job_dead_letter(db: AsyncSession, job: MiiExportJob, message: str) -> None:
    job.status = "dead_letter"
    job.error_message = message
    job.finished_at = datetime.now(UTC)
    job.started_at = None
    job.next_run_at = None
    await db.commit()


async def mark_job_queued_retry(
    db: AsyncSession, job: MiiExportJob, message: str
) -> None:
    job.status = "queued"
    job.error_message = message
    job.started_at = None
    await db.commit()


async def get_mii_export_metrics_for_user(db: AsyncSession, user_sub: str) -> dict[str, int]:
    """Count export jobs by status for one user."""
    stmt = (
        select(MiiExportJob.status, func.count())
        .where(MiiExportJob.requested_by_user_id == user_sub)
        .group_by(MiiExportJob.status)
    )
    result = await db.execute(stmt)
    rows = result.all()
    out: dict[str, int] = {}
    for status_key, n in rows:
        out[str(status_key)] = int(n)
    return out


async def get_job_and_artifact(
    db: AsyncSession,
    job_id: str,
    current_user_sub: str,
) -> tuple[MiiExportJob | None, MiiExportArtifact | None]:
    try:
        jid = UUID(job_id)
    except ValueError:
        return None, None
    stmt = select(MiiExportJob).where(MiiExportJob.id == jid)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job or job.requested_by_user_id != current_user_sub:
        return None, None
    a_stmt = select(MiiExportArtifact).where(MiiExportArtifact.job_id == jid)
    ar = await db.execute(a_stmt)
    artifact = ar.scalar_one_or_none()
    return job, artifact
