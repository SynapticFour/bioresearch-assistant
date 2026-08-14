"""API tests for PhenoFlow endpoints."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.models.patient_record import PatientRecordModel
from app.models.phenoflow_run import PhenoFlowRun
from app.models.phenoflow_run_item import PhenoFlowRunItem
from app.models.phenopacket_asset import PhenopacketAsset
from app.schemas.phenoflow import (
    PhenoFlowRunRequest,
    PhenopacketAssetFileType,
    PhenopacketAssetLinkRequest,
)


@pytest.fixture(autouse=True)
async def _isolate_phenoflow_rows(db_session) -> None:
    """Ensure API tests do not pollute global test DB state."""
    await db_session.execute(delete(PhenoFlowRunItem))
    await db_session.execute(delete(PhenoFlowRun))
    await db_session.execute(delete(PhenopacketAsset))
    await db_session.execute(delete(PatientRecordModel))
    await db_session.flush()
    yield
    await db_session.execute(delete(PhenoFlowRunItem))
    await db_session.execute(delete(PhenoFlowRun))
    await db_session.execute(delete(PhenopacketAsset))
    await db_session.execute(delete(PatientRecordModel))
    await db_session.flush()


@pytest.mark.asyncio
async def test_create_and_get_pheno_flow_run(
    async_client,
    db_session,
    mock_current_user,
    monkeypatch,
) -> None:
    record = PatientRecordModel(
        pseudonym_id="pp-api-1",
        phenopacket_json={
            "phenotypic_features": [
                {"type": {"id": "HP:0001250", "label": "Seizures"}},
            ],
        },
        user_id="dev-user",
        team_id=None,
    )
    db_session.add(record)
    await db_session.flush()

    asset = PhenopacketAsset(
        pseudonym_id="pp-api-1",
        drs_object_id="asset-api-1.bam",
        file_type=PhenopacketAssetFileType.bam.value,
        user_id="dev-user",
        team_id=None,
    )
    db_session.add(asset)
    await db_session.flush()

    monkeypatch.setattr(
        "app.services.phenoflow_service.get_access_url",
        lambda object_id, access_id: type("Access", (), {"url": "http://drs/stream"})(),
    )

    wes_uuid = uuid4()
    monkeypatch.setattr(
        "app.services.phenoflow_service.create_wes_run",
        AsyncMock(return_value=wes_uuid),
    )

    req = PhenoFlowRunRequest(
        hpo_terms=["HP:0001250"],
        file_type=PhenopacketAssetFileType.bam,
        limit_matches=10,
        workflow_url="nextflow",
        workflow_type="NEXTFLOW",
        workflow_type_version="DSL2",
        workflow_params_template={"input_bam": "{{drs_stream_url}}"},
    )

    post_resp = await async_client.post("/api/v1/phenoflow/runs", json=req.model_dump())
    assert post_resp.status_code == 201
    body = post_resp.json()
    assert body["submitted_count"] == 1
    phenoflow_run_id = body["phenoflow_run_id"]

    get_resp = await async_client.get(f"/api/v1/phenoflow/runs/{phenoflow_run_id}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["phenoflow_run_id"] == phenoflow_run_id
    assert detail["status"] == "SUBMITTED"
    assert len(detail["items"]) == 1


@pytest.mark.asyncio
async def test_list_pheno_flow_runs(async_client, db_session, monkeypatch) -> None:
    record = PatientRecordModel(
        pseudonym_id="pp-api-list-1",
        phenopacket_json={
            "phenotypic_features": [
                {"type": {"id": "HP:0001250", "label": "Seizures"}},
            ],
        },
        user_id="dev-user",
        team_id=None,
    )
    db_session.add(record)
    await db_session.flush()

    asset = PhenopacketAsset(
        pseudonym_id="pp-api-list-1",
        drs_object_id="asset-api-list-1.bam",
        file_type=PhenopacketAssetFileType.bam.value,
        user_id="dev-user",
        team_id=None,
    )
    db_session.add(asset)
    await db_session.flush()

    monkeypatch.setattr(
        "app.services.phenoflow_service.get_access_url",
        lambda object_id, access_id: type("Access", (), {"url": "http://drs/stream"})(),
    )
    monkeypatch.setattr(
        "app.services.phenoflow_service.create_wes_run",
        AsyncMock(return_value=uuid4()),
    )

    req = PhenoFlowRunRequest(
        hpo_terms=["HP:0001250"],
        file_type=PhenopacketAssetFileType.bam,
        limit_matches=10,
        workflow_url="nextflow",
        workflow_type="NEXTFLOW",
        workflow_type_version="DSL2",
        workflow_params_template={"input_bam": "{{drs_stream_url}}"},
    )
    create_resp = await async_client.post("/api/v1/phenoflow/runs", json=req.model_dump())
    assert create_resp.status_code == 201

    list_resp = await async_client.get("/api/v1/phenoflow/runs")
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert "items" in body
    assert len(body["items"]) >= 1
    assert body["items"][0]["matched_count"] >= 1
    assert "phenoflow_run_id" in body["items"][0]


@pytest.mark.asyncio
async def test_create_pheno_flow_run_rejects_invalid_hpo(async_client) -> None:
    response = await async_client.post(
        "/api/v1/phenoflow/runs",
        json={
            "hpo_terms": ["not-an-hpo"],
            "workflow_url": "nextflow",
            "workflow_type": "NEXTFLOW",
            "workflow_type_version": "DSL2",
            "workflow_params_template": {},
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_asset_linking_endpoints(
    async_client,
    db_session,
    monkeypatch,
) -> None:
    # Create phenopacket record.
    record = PatientRecordModel(
        pseudonym_id="pp-link-1",
        phenopacket_json={"phenotypic_features": [{"type": {"id": "HP:0001250"}}]},
        user_id="dev-user",
        team_id=None,
    )
    db_session.add(record)
    await db_session.flush()

    monkeypatch.setattr(
        "app.api.v1.endpoints.phenopackets.drs_get_object",
        lambda object_id, current_user=None: MagicMock(),
    )

    link_req = PhenopacketAssetLinkRequest(
        drs_object_id="asset-link-1.bam",
        file_type=PhenopacketAssetFileType.bam,
    )
    post_resp = await async_client.post(
        "/api/v1/phenopackets/pp-link-1/assets",
        json=link_req.model_dump(),
    )
    assert post_resp.status_code == 201
    asset_body: dict[str, Any] = post_resp.json()
    assert asset_body["drs_object_id"] == "asset-link-1.bam"

    list_resp = await async_client.get("/api/v1/phenopackets/pp-link-1/assets")
    assert list_resp.status_code == 200
    assets = list_resp.json()
    assert len(assets) == 1
    assert assets[0]["file_type"] == PhenopacketAssetFileType.bam.value

    delete_resp = await async_client.delete(
        f"/api/v1/phenopackets/pp-link-1/assets/{asset_body['asset_id']}"
    )
    assert delete_resp.status_code == 204
