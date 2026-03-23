"""PhenoFlow API endpoints (Search-to-Execution bridge)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.isolation import get_scope_filter
from app.models.phenoflow_run import PhenoFlowRun
from app.models.phenoflow_run_item import PhenoFlowRunItem
from app.models.workflow_run import WorkflowRun
from app.schemas.phenoflow import (
    PhenoFlowRunDetailResponse,
    PhenoFlowRunListItem,
    PhenoFlowRunListResponse,
    PhenoFlowRunRequest,
    PhenoFlowRunResponse,
)
from app.schemas.wes import State
from app.services.phenoflow_service import submit_pheno_flow_run

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/phenoflow", tags=["phenoflow"])


@router.post("/runs", response_model=PhenoFlowRunResponse, status_code=status.HTTP_201_CREATED)
async def create_pheno_flow_run(
    body: PhenoFlowRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PhenoFlowRunResponse:
    """Submit a PhenoFlow run (match Phenopackets -> resolve DRS -> submit WES)."""
    response = await submit_pheno_flow_run(db, body, current_user=current_user)
    await db.commit()
    return response


@router.get("/runs", response_model=PhenoFlowRunListResponse, status_code=status.HTTP_200_OK)
async def list_pheno_flow_runs(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PhenoFlowRunListResponse:
    """List recent PhenoFlow runs in current isolation scope."""
    stmt = select(PhenoFlowRun).order_by(PhenoFlowRun.created_at.desc())
    scope = get_scope_filter(current_user)
    if "user_id" in scope and scope["user_id"]:
        stmt = stmt.where(PhenoFlowRun.user_id == scope["user_id"])
    elif "team_id" in scope and scope["team_id"]:
        stmt = stmt.where(PhenoFlowRun.team_id == scope["team_id"])
    r = await db.execute(stmt)
    runs = list(r.scalars().all())

    items: list[PhenoFlowRunListItem] = []
    for run in runs:
        items_stmt = select(PhenoFlowRunItem).where(
            PhenoFlowRunItem.phenoflow_run_id == run.phenoflow_run_id,
        )
        items_r = await db.execute(items_stmt)
        run_items = list(items_r.scalars().all())
        submitted_count = sum(1 for i in run_items if i.wes_run_id is not None)
        items.append(
            PhenoFlowRunListItem(
                phenoflow_run_id=str(run.phenoflow_run_id),
                status=run.status,
                created_at=run.created_at.isoformat() if run.created_at else None,
                matched_count=len(run_items),
                submitted_count=submitted_count,
            ),
        )
    return PhenoFlowRunListResponse(items=items)


@router.get(
    "/runs/{phenoflow_run_id}",
    response_model=PhenoFlowRunDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_pheno_flow_run(
    phenoflow_run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PhenoFlowRunDetailResponse:
    """Get a PhenoFlow run and its item-level provenance."""
    try:
        run_uuid = UUID(phenoflow_run_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phenoflow_run_id",
        ) from e

    run_stmt = select(PhenoFlowRun).where(PhenoFlowRun.phenoflow_run_id == run_uuid)
    scope = get_scope_filter(current_user)
    if "user_id" in scope and scope["user_id"]:
        run_stmt = run_stmt.where(PhenoFlowRun.user_id == scope["user_id"])
    elif "team_id" in scope and scope["team_id"]:
        run_stmt = run_stmt.where(PhenoFlowRun.team_id == scope["team_id"])

    r = await db.execute(run_stmt)
    run = r.scalars().first()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PhenoFlow run not found")

    items_stmt = select(PhenoFlowRunItem).where(PhenoFlowRunItem.phenoflow_run_id == run_uuid)
    items_r = await db.execute(items_stmt)
    items = list(items_r.scalars().all())

    wes_run_ids = [i.wes_run_id for i in items if i.wes_run_id is not None]
    wes_map: dict[str, str] = {}
    if wes_run_ids:
        wes_stmt = select(WorkflowRun).where(WorkflowRun.run_id.in_(wes_run_ids))
        wes_r = await db.execute(wes_stmt)
        for wr in wes_r.scalars().all():
            wes_map[str(wr.run_id)] = wr.state

    def _state_from_item(item: PhenoFlowRunItem) -> str:
        if item.wes_run_id is None:
            return item.state_snapshot or State.UNKNOWN.value
        return wes_map.get(str(item.wes_run_id), item.state_snapshot or State.UNKNOWN.value)

    out_items = []
    for item in items:
        out_items.append(
            {
                "pseudonym_id": item.pseudonym_id,
                "drs_object_id": item.drs_object_id,
                "file_type": item.file_type,
                "wes_run_id": str(item.wes_run_id) if item.wes_run_id is not None else None,
                "state_snapshot": _state_from_item(item),
                "error": item.error,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            },
        )

    return PhenoFlowRunDetailResponse(
        phenoflow_run_id=str(run.phenoflow_run_id),
        status=run.status,
        query_spec=run.query_spec,
        workflow_spec=run.workflow_spec,
        items=out_items,
    )
