"""Unit tests for PhenoFlow service orchestration."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select

from app.models.patient_record import PatientRecordModel
from app.models.phenoflow_run import PhenoFlowRun
from app.models.phenoflow_run_item import PhenoFlowRunItem
from app.models.phenopacket_asset import PhenopacketAsset
from app.schemas.drs import AccessURL
from app.schemas.phenoflow import (
    PhenoFlowRunRequest,
    PhenopacketAssetFileType,
)
from app.services.phenoflow_service import _extract_hpo_ids, submit_pheno_flow_run


@pytest.fixture(autouse=True)
async def _isolate_phenoflow_rows(db_session) -> None:
    """Ensure PhenoFlow tests do not leak fixtures across test files."""
    await db_session.execute(delete(PhenoFlowRunItem))
    await db_session.execute(delete(PhenoFlowRun))
    await db_session.execute(delete(PhenopacketAsset))
    await db_session.execute(delete(PatientRecordModel))
    await db_session.flush()


def test_extract_hpo_ids_parses_phenotypic_features() -> None:
    phenopacket_json: dict[str, Any] = {
        "phenotypic_features": [
            {"type": {"id": "HP:0001250", "label": "Seizures"}},
            {"type": {"id": "HP:0000707", "label": "Seizure disorder"}},
        ]
    }
    out = _extract_hpo_ids(phenopacket_json)
    assert "HP:0001250" in out
    assert "HP:0000707" in out


@pytest.mark.asyncio
async def test_submit_pheno_flow_run_submits_matching_pairs(
    db_session,
    mock_current_user,
    monkeypatch,
) -> None:
    record = PatientRecordModel(
        pseudonym_id="pp-1",
        phenopacket_json={
            "phenotypic_features": [
                {"type": {"id": "HP:0001250", "label": "Seizures"}},
            ],
        },
        user_id=None,
        team_id=None,
    )
    db_session.add(record)
    await db_session.flush()

    asset = PhenopacketAsset(
        pseudonym_id="pp-1",
        drs_object_id="asset-1.bam",
        file_type=PhenopacketAssetFileType.bam.value,
        user_id=None,
        team_id=None,
    )
    db_session.add(asset)
    await db_session.flush()

    access = AccessURL(url="http://drs.example/stream/asset-1.bam")
    monkeypatch.setattr(
        "app.services.phenoflow_service.get_access_url",
        lambda object_id, access_id: access if object_id == "asset-1.bam" else None,
    )

    wes_uuid = uuid4()
    create_run_mock: AsyncMock = AsyncMock(return_value=wes_uuid)
    monkeypatch.setattr("app.services.phenoflow_service.create_wes_run", create_run_mock)

    req = PhenoFlowRunRequest(
        hpo_terms=["HP:0001250"],
        file_type=PhenopacketAssetFileType.bam,
        limit_matches=10,
        workflow_url="nextflow",
        workflow_type="NEXTFLOW",
        workflow_type_version="DSL2",
        workflow_params_template={
            "input_bam": "{{drs_stream_url}}",
            "sample_id": "{{pseudonym_id}}",
        },
    )

    resp = await submit_pheno_flow_run(db_session, req, current_user=mock_current_user)

    assert resp.matched_count == 1
    assert resp.submitted_count == 1
    assert resp.errors == []
    assert len(resp.items) == 1
    assert resp.items[0].wes_run_id == str(wes_uuid)
    assert resp.items[0].state_snapshot == "QUEUED"

    run_uuid = UUID(resp.phenoflow_run_id)
    run_stmt = select(PhenoFlowRun).where(PhenoFlowRun.phenoflow_run_id == run_uuid)
    run = (await db_session.execute(run_stmt)).scalars().first()
    assert run is not None
    assert run.status == "SUBMITTED"

    items_stmt = select(PhenoFlowRunItem).where(PhenoFlowRunItem.phenoflow_run_id == run_uuid)
    items = list((await db_session.execute(items_stmt)).scalars().all())
    assert len(items) == 1
    assert items[0].wes_run_id == wes_uuid
    assert items[0].state_snapshot == "QUEUED"


@pytest.mark.asyncio
async def test_submit_pheno_flow_run_records_drs_errors_as_items(
    db_session,
    mock_current_user,
    monkeypatch,
) -> None:
    record = PatientRecordModel(
        pseudonym_id="pp-2",
        phenopacket_json={
            "phenotypic_features": [
                {"type": {"id": "HP:0001250", "label": "Seizures"}},
            ],
        },
        user_id=None,
        team_id=None,
    )
    db_session.add(record)
    await db_session.flush()

    asset = PhenopacketAsset(
        pseudonym_id="pp-2",
        drs_object_id="asset-missing.bam",
        file_type=PhenopacketAssetFileType.bam.value,
        user_id=None,
        team_id=None,
    )
    db_session.add(asset)
    await db_session.flush()

    monkeypatch.setattr(
        "app.services.phenoflow_service.get_access_url",
        lambda object_id, access_id: None,
    )
    create_run_mock: AsyncMock = AsyncMock()
    monkeypatch.setattr("app.services.phenoflow_service.create_wes_run", create_run_mock)

    req = PhenoFlowRunRequest(
        hpo_terms=["HP:0001250"],
        file_type=PhenopacketAssetFileType.bam,
        limit_matches=10,
        workflow_url="nextflow",
        workflow_type="NEXTFLOW",
        workflow_type_version="DSL2",
    )

    resp = await submit_pheno_flow_run(db_session, req, current_user=mock_current_user)

    assert resp.matched_count == 1
    assert resp.submitted_count == 0
    assert len(resp.items) == 1
    assert resp.items[0].wes_run_id is None
    assert resp.items[0].state_snapshot == "ERROR"
    assert resp.items[0].error is not None

    create_run_mock.assert_not_called()
