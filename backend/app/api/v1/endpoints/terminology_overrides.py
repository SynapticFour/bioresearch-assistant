"""Terminology mapping overrides (MII export governance)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.limiter import limiter
from app.schemas.terminology_override import (
    TerminologyOverrideCreate,
    TerminologyOverrideListResponse,
    TerminologyOverrideRead,
)
from app.services import terminology_override_service as tov_svc

router = APIRouter(prefix="/terminology", tags=["terminology"])


def _row_to_read(row) -> TerminologyOverrideRead:
    return TerminologyOverrideRead(
        id=str(row.id),
        module=row.module,
        raw_id=row.raw_id,
        target_system=row.target_system,
        target_code=row.target_code,
        target_display=row.target_display,
        notes=row.notes,
        is_active=row.is_active,
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get("/overrides", response_model=TerminologyOverrideListResponse)
@limiter.limit("60/minute")
async def list_terminology_overrides(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TerminologyOverrideListResponse:
    """List all terminology mapping overrides (active and inactive)."""
    _ = current_user
    rows = await tov_svc.list_overrides(db)
    items = [_row_to_read(r) for r in rows]
    return TerminologyOverrideListResponse(items=items, total=len(items))


@router.post("/overrides", response_model=TerminologyOverrideRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_terminology_override(
    request: Request,
    body: TerminologyOverrideCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TerminologyOverrideRead:
    """Create or replace an override for (module, raw_id)."""
    uid = current_user.get("sub")
    row = await tov_svc.upsert_override(
        db,
        module=body.module,
        raw_id=body.raw_id.strip(),
        target_system=body.target_system.strip(),
        target_code=body.target_code.strip(),
        target_display=body.target_display.strip() if body.target_display else None,
        notes=body.notes,
        user_id=uid,
    )
    return _row_to_read(row)


@router.delete("/overrides/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_terminology_override(
    request: Request,
    override_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    """Deactivate an override (soft delete)."""
    _ = current_user
    ok = await tov_svc.deactivate_override(db, override_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")
