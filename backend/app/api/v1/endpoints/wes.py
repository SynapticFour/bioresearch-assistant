"""GA4GH Workflow Execution Service (WES) v1.1 API endpoints.

Reference: https://ga4gh.github.io/workflow-execution-service-schemas/
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.schemas.wes import (
    RunId,
    RunListResponse,
    RunLog,
    RunRequest,
    RunStatus,
    ServiceInfo,
    ServiceOrganization,
    ServiceType,
    State,
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
    get_service_info as wes_static_service_info,
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
    settings = get_settings()
    meta = wes_static_service_info()
    return ServiceInfo(
        id="org.ga4gh.bioresearch.wes",
        name="BioResearch Assistant WES",
        type=ServiceType(group="org.ga4gh", artifact="wes", version="1.1.0"),
        organization=ServiceOrganization(
            name="Synaptic Four",
            url="https://www.synapticfour.com",
        ),
        version="1.3.0",
        description="GA4GH WES v1.1 for Nextflow workflows (on-premise).",
        contactUrl="https://www.synapticfour.com",
        documentationUrl="https://ga4gh.github.io/workflow-execution-service-schemas/",
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
        environment=settings.environment,
        workflow_type_versions={
            name: WorkflowTypeVersion(workflow_type_version=versions)
            for name, versions in meta["workflow_type_versions"].items()
        },
        # HelixTest expects at least "1.0" or "1.1" in addition to patch versions.
        supported_wes_versions=list(meta["supported_wes_versions"]),
        supported_filesystem_protocols=list(meta["supported_filesystem_protocols"]),
        workflow_engine_versions={
            name: WorkflowEngineVersion(workflow_engine_version=versions)
            for name, versions in meta["workflow_engine_versions"].items()
        },
        default_workflow_engine_parameters=[],
        system_state_counts={},  # Filled in get_service_info
        auth_instructions_url="",
        tags=dict(meta["tags"]),
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
    state: str | None = Query(
        default=None,
        description="Optional filter by WES run state (e.g. COMPLETE, RUNNING, QUEUED)",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RunListResponse:
    """List workflow runs (paginated)."""
    size = min(max(1, page_size or 100), 1000)
    state_filter: str | None = None
    if state is not None:
        key = state.strip().upper()
        try:
            state_filter = State(key).value
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid WES state: {state!r}",
            ) from e
    runs, next_token = await service_list_runs(
        db,
        page_size=size,
        page_token=page_token,
        state_filter=state_filter,
        current_user=current_user,
    )
    summaries = [run_to_run_summary(r) for r in runs]
    return RunListResponse(runs=summaries, next_page_token=next_token)


@router.post("/runs", response_model=RunId, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def run_workflow(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RunId:
    """Submit a new workflow run. Returns run_id to monitor progress.

    Accepts ``application/json`` (GA4GH WES RunRequest body) or multipart/form-data
    as used by browser clients and older integrations.
    """
    content_type = request.headers.get("content-type") or ""
    media_type = content_type.split(";")[0].strip().lower()
    attachments: list[tuple[str, bytes]] | None = None

    if media_type == "application/json":
        try:
            raw_body: Any = await request.json()
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON body: {e}",
            ) from e
        try:
            run_req = RunRequest.model_validate(raw_body)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=e.errors(),
            ) from e
    else:
        form = await request.form()
        try:
            workflow_type = str(form["workflow_type"])
            workflow_type_version = str(form["workflow_type_version"])
            workflow_url = str(form["workflow_url"])
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing form field: {e.args[0]!r}",
            ) from e

        workflow_params = form.get("workflow_params")
        params: dict[str, Any] | None = None
        if workflow_params:
            try:
                params = json.loads(str(workflow_params))
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid workflow_params JSON: {e}",
                ) from e

        tags_raw = form.get("tags")
        tags_dict: dict[str, str] | None = None
        if tags_raw:
            try:
                tags_dict = json.loads(str(tags_raw))
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tags JSON: {e}",
                ) from e

        engine_raw = form.get("workflow_engine_parameters")
        engine_params: dict[str, str] | None = None
        if engine_raw:
            try:
                engine_params = json.loads(str(engine_raw))
            except json.JSONDecodeError:
                engine_params = None

        run_req = RunRequest(
            workflow_type=workflow_type,
            workflow_type_version=workflow_type_version,
            workflow_url=workflow_url,
            workflow_params=params,
            tags=tags_dict,
            workflow_engine=str(form["workflow_engine"]) if form.get("workflow_engine") else None,
            workflow_engine_version=(
                str(form["workflow_engine_version"])
                if form.get("workflow_engine_version")
                else None
            ),
            workflow_engine_parameters=engine_params,
        )

        att_list: list[tuple[str, bytes]] = []
        for key, item in form.multi_items():
            if key != "workflow_attachment":
                continue
            if not isinstance(item, UploadFile):
                continue
            if item.filename and not item.filename.startswith(".."):
                body = await item.read()
                att_list.append((item.filename, body))
        attachments = att_list if att_list else None

    try:
        run_id = await service_create_run(
            db, run_req, workflow_attachments=attachments, current_user=current_user
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    await db.commit()
    return RunId(run_id=str(run_id))


@router.get("/runs/{run_id}/status", response_model=RunStatus, status_code=status.HTTP_200_OK)
async def get_run_status(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RunStatus:
    """Get abbreviated status of a workflow run (run_id and state).

    Declared before ``GET /runs/{run_id}`` so frameworks that match in order
    never treat ``…/status`` as a run_id suffix (mirrors Ferrum WES routing fixes).
    """
    run = await service_get_run(db, run_id, current_user=current_user)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested workflow run wasn't found.",
        )
    return run_to_run_status(run)


@router.post("/runs/{run_id}/cancel", response_model=RunId, status_code=status.HTTP_200_OK)
async def cancel_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RunId:
    """Cancel a running workflow."""
    found = await service_cancel_run(db, run_id, current_user=current_user)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested workflow run not found.",
        )
    await db.commit()
    return RunId(run_id=run_id)


@router.get("/runs/{run_id}", response_model=RunLog, status_code=status.HTTP_200_OK)
async def get_run_log(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RunLog:
    """Get detailed information about a workflow run (logs, outputs, state)."""
    run = await service_get_run(db, run_id, current_user=current_user)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested workflow run not found.",
        )
    return run_to_run_log(run)
