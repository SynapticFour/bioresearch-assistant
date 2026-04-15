"""Intention-level quality tests for MII export validation and async worker."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.database import get_db_context
from app.interoperability.mii.constants import MII_FHIR_CANONICAL_BASE
from app.models.mii_export import MiiExportArtifact, MiiExportJob
from app.services.fhir_validation_service import validate_bundle
from app.services import mii_export_service as mii_svc
from app.services import mii_export_worker


def test_validate_bundle_strict_fails_on_invalid_diagnosis_binding() -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-1",
                    "meta": {"profile": ["https://www.medizininformatik-initiative.de/fhir/core/modul-person/StructureDefinition/Patient"]},
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-1",
                    "meta": {"profile": ["https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Condition"]},
                    "code": {"coding": [{"system": "http://example.org/cs", "code": "X"}]},
                }
            },
        ],
    }
    summary = validate_bundle(bundle, strict_profile_validation=True)
    assert summary["ok"] is False
    assert summary["binding_checks"] >= 1
    assert any("Condition.code.system" in e for e in summary["errors"])


def test_validate_bundle_strict_accepts_known_bindings() -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-1",
                    "meta": {"profile": ["https://www.medizininformatik-initiative.de/fhir/core/modul-person/StructureDefinition/Patient"]},
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-1",
                    "meta": {"profile": ["https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Condition"]},
                    "code": {"coding": [{"system": "http://www.orpha.net", "code": "558"}]},
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "observation-lab-1",
                    "meta": {"profile": ["https://www.medizininformatik-initiative.de/fhir/core/modul-labor/StructureDefinition/ObservationLab"]},
                    "category": [{"coding": [{"code": "laboratory"}]}],
                    "code": {"coding": [{"system": "http://loinc.org", "code": "718-7"}]},
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "observation-genomics-1",
                    "meta": {"profile": ["https://www.medizininformatik-initiative.de/fhir/core/modul-molgen/StructureDefinition/Observation"]},
                    "category": [{"coding": [{"code": "laboratory"}]}],
                    "code": {"coding": [{"system": MII_FHIR_CANONICAL_BASE, "code": "genomic-finding"}]},
                }
            },
        ],
    }
    summary = validate_bundle(bundle, strict_profile_validation=True)
    assert summary["ok"] is True
    assert summary["binding_checks"] >= 2


@pytest.mark.asyncio
async def test_worker_retries_then_succeeds(monkeypatch, db_session) -> None:
    job = await mii_svc.enqueue_mii_export_job(
        db_session,
        user_id="dev-user",
        scope_snapshot={"user_id": "dev-user"},
        pseudonym_ids=["pp-1"],
        modules=["diagnosis"],
        policy_id="mii-broad-consent",
        research_project_ids=[],
    )
    calls = {"n": 0}

    async def fake_build(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("temporary-db")
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": {"resourceType": "Patient", "id": "p"}}],
        }
        return bundle, {"ok": True}, {"ok": True, "errors": [], "warnings": []}

    async def fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(mii_export_worker.mii_svc, "build_mii_bundle_for_pseudonyms", fake_build)
    monkeypatch.setattr(mii_export_worker.asyncio, "sleep", fake_sleep)

    await mii_export_worker.run_mii_export_job_task(job.id)

    async with get_db_context() as fresh:
        result = await fresh.execute(select(MiiExportJob).where(MiiExportJob.id == job.id))
        row = result.scalar_one()
        art_result = await fresh.execute(select(MiiExportArtifact).where(MiiExportArtifact.job_id == job.id))
        artifact = art_result.scalar_one()
    assert row.status == "succeeded"
    assert row.attempt_count == 2
    assert artifact is not None


@pytest.mark.asyncio
async def test_worker_dead_letters_after_max_attempts(monkeypatch, db_session) -> None:
    job = await mii_svc.enqueue_mii_export_job(
        db_session,
        user_id="dev-user",
        scope_snapshot={"user_id": "dev-user"},
        pseudonym_ids=["pp-2"],
        modules=["diagnosis"],
        policy_id="mii-broad-consent",
        research_project_ids=[],
    )
    job.max_attempts = 1
    await db_session.commit()

    async def fake_build(*args, **kwargs):
        raise RuntimeError("temporary-db")

    async def fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(mii_export_worker.mii_svc, "build_mii_bundle_for_pseudonyms", fake_build)
    monkeypatch.setattr(mii_export_worker.asyncio, "sleep", fake_sleep)
    await mii_export_worker.run_mii_export_job_task(job.id)

    async with get_db_context() as fresh:
        result = await fresh.execute(select(MiiExportJob).where(MiiExportJob.id == job.id))
        row = result.scalar_one()
    assert row.status == "dead_letter"
    assert row.attempt_count == 1
    assert row.error_message == "max_retries_exceeded"


@pytest.mark.asyncio
async def test_worker_valueerror_is_permanent_failure(monkeypatch, db_session) -> None:
    job = await mii_svc.enqueue_mii_export_job(
        db_session,
        user_id="dev-user",
        scope_snapshot={"user_id": "dev-user"},
        pseudonym_ids=[f"pp-{uuid4().hex[:6]}"],
        modules=["diagnosis"],
        policy_id="mii-broad-consent",
        research_project_ids=[],
    )

    async def fake_build(*args, **kwargs):
        raise ValueError("validation_failed")

    monkeypatch.setattr(mii_export_worker.mii_svc, "build_mii_bundle_for_pseudonyms", fake_build)
    await mii_export_worker.run_mii_export_job_task(job.id)

    async with get_db_context() as fresh:
        result = await fresh.execute(select(MiiExportJob).where(MiiExportJob.id == job.id))
        row = result.scalar_one()
    assert row.status == "failed"
    assert row.error_message == "validation_failed"
    assert row.attempt_count == 1
