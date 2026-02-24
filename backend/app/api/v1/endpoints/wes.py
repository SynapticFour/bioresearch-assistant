"""GA4GH Workflow Execution Service (WES) v1.1 API endpoints.

Reference: https://ga4gh.github.io/workflow-execution-service-schemas/
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.schemas.wes import (
    RunId,
    RunListResponse,
    RunLog,
    RunRequest,
    RunStatus,
    ServiceInfo,
    ServiceOrganization,
    ServiceType,
    WorkflowEngineVersion,
    WorkflowTypeVersion,
)
from app.services.wes_service import (
    cancel_run as service_cancel_run,
)
from app.services.wes_service import (
    create_run as service_create_run,
)
from app.services.wes_service import (
    get_run as service_get_run,
)
from app.services.wes_service import (
    get_system_state_counts,
    run_to_run_log,
    run_to_run_status,
    run_to_run_summary,
)
from app.services.wes_service import (
    list_runs as service_list_runs,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WES"])


def _service_info() -> ServiceInfo:
    """Build static ServiceInfo; system_state_counts are filled per-request from DB."""
    return ServiceInfo(
        id="org.ga4gh.bioresearch.wes",
        name="BioResearch Assistant WES",
        type=ServiceType(group="org.ga4gh", artifact="wes", version="1.1.0"),
        organization=ServiceOrganization(
            name="Synaptic Four",
            url="https://synapticfour.com",
        ),
        version="0.1.0",
        description="GA4GH WES v1.1 for Nextflow workflows (on-premise).",
        workflow_type_versions={
            "NEXTFLOW": WorkflowTypeVersion(workflow_type_version=["DSL2"]),
            "CWL": WorkflowTypeVersion(workflow_type_version=["v1.0"]),
            "WDL": WorkflowTypeVersion(workflow_type_version=["1.0", "1.1"]),
        },
        supported_wes_versions=["1.1.0"],
        supported_filesystem_protocols=["file", "http", "https"],
        workflow_engine_versions={
            "nextflow": WorkflowEngineVersion(workflow_engine_version=["23.10.0", "24.04.0"]),
        },
        default_workflow_engine_parameters=[],
        system_state_counts={},  # Filled in get_service_info
        auth_instructions_url="",
        tags={"backend": "nextflow"},
    )


@router.get("/service-info", response_model=ServiceInfo, status_code=status.HTTP_200_OK)
async def get_service_info(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ServiceInfo:
    """Get information about the workflow execution service (WES v1.1)."""
    info = _service_info()
    counts = await get_system_state_counts(db)
    info.system_state_counts = counts
    return info


@router.get("/runs", response_model=RunListResponse, status_code=status.HTTP_200_OK)
async def list_runs(
    page_size: int | None = 100,
    page_token: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RunListResponse:
    """List workflow runs (paginated)."""
    size = min(max(1, page_size or 100), 1000)
    runs, next_token = await service_list_runs(db, page_size=size, page_token=page_token)
    summaries = [run_to_run_summary(r) for r in runs]
    return RunListResponse(runs=summaries, next_page_token=next_token)


@router.post("/runs", response_model=RunId, status_code=status.HTTP_200_OK)
async def run_workflow(
    workflow_type: str = Form(...),
    workflow_type_version: str = Form(...),
    workflow_url: str = Form(...),
    workflow_params: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    workflow_engine: str | None = Form(default=None),
    workflow_engine_version: str | None = Form(default=None),
    workflow_engine_parameters: str | None = Form(default=None),
    workflow_attachment: list[UploadFile] | None = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RunId:
    """Submit a new workflow run. Returns run_id to monitor progress."""
    params: dict[str, Any] | None = None
    if workflow_params:
        try:
            params = json.loads(workflow_params)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid workflow_params JSON: {e}",
            ) from e
    tags_dict: dict[str, str] | None = None
    if tags:
        try:
            tags_dict = json.loads(tags)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tags JSON: {e}",
            ) from e
    engine_params: dict[str, str] | None = None
    if workflow_engine_parameters:
        try:
            engine_params = json.loads(workflow_engine_parameters)
        except json.JSONDecodeError:
            engine_params = None

    request = RunRequest(
        workflow_type=workflow_type,
        workflow_type_version=workflow_type_version,
        workflow_url=workflow_url,
        workflow_params=params,
        tags=tags_dict,
        workflow_engine=workflow_engine,
        workflow_engine_version=workflow_engine_version,
        workflow_engine_parameters=engine_params,
    )

    attachments: list[tuple[str, bytes]] = []
    if workflow_attachment:
        for f in workflow_attachment:
            if f.filename and not f.filename.startswith(".."):
                body = await f.read()
                attachments.append((f.filename, body))

    try:
        run_id = await service_create_run(
            db, request, workflow_attachments=attachments if attachments else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    await db.commit()
    return RunId(run_id=str(run_id))


@router.get("/runs/{run_id}", response_model=RunLog, status_code=status.HTTP_200_OK)
async def get_run_log(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RunLog:
    """Get detailed information about a workflow run (logs, outputs, state)."""
    run = await service_get_run(db, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested workflow run not found.",
        )
    return run_to_run_log(run)


@router.post("/runs/{run_id}/cancel", response_model=RunId, status_code=status.HTTP_200_OK)
async def cancel_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RunId:
    """Cancel a running workflow."""
    found = await service_cancel_run(db, run_id)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested workflow run not found.",
        )
    await db.commit()
    return RunId(run_id=run_id)


@router.get("/runs/{run_id}/status", response_model=RunStatus, status_code=status.HTTP_200_OK)
async def get_run_status(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RunStatus:
    """Get abbreviated status of a workflow run (run_id and state)."""
    run = await service_get_run(db, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested workflow run wasn't found.",
        )
    return run_to_run_status(run)
