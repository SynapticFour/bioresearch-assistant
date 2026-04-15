"""Research consent (MII Broad Consent) API."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.isolation import get_scope_filter, get_scope_values
from app.core.limiter import limiter
from app.schemas.consent import (
    ResearchConsentCreate,
    ResearchConsentRead,
    ResearchConsentUpdate,
    WithdrawConsentBody,
)
from app.services import consent_service as cs

router = APIRouter(prefix="/consents", tags=["consents"])


@router.get("/by-pseudonym/{pseudonym_id}", response_model=list[ResearchConsentRead])
@limiter.limit("60/minute")
async def list_consents_by_pseudonym(
    request: Request,
    pseudonym_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[ResearchConsentRead]:
    """List consent records for a pseudonym (scoped)."""
    scope = get_scope_filter(current_user)
    rows = await cs.list_consents_for_pseudonym(db, pseudonym_id, scope)
    return [ResearchConsentRead.model_validate(r) for r in rows]


@router.get("", response_model=list[ResearchConsentRead])
@limiter.limit("60/minute")
async def list_consents(
    request: Request,
    pseudonym_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[ResearchConsentRead]:
    """List consent records (optional filter by pseudonym_id)."""
    scope = get_scope_filter(current_user)
    rows = await cs.list_consents(db, scope, pseudonym_id=pseudonym_id)
    return [ResearchConsentRead.model_validate(r) for r in rows]


@router.post("", response_model=ResearchConsentRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_consent(
    request: Request,
    body: ResearchConsentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ResearchConsentRead:
    """Create a consent record."""
    scope = get_scope_filter(current_user)
    scope_values = get_scope_values(current_user)
    try:
        row = await cs.create_consent(
            db,
            body,
            scope,
            scope_values,
            actor_user_id=current_user.get("sub"),
        )
    except ValueError as e:
        if str(e) == "pseudonym_not_found_or_out_of_scope":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pseudonym not found or out of scope",
            ) from e
        raise
    return ResearchConsentRead.model_validate(row)


@router.get("/{consent_id}", response_model=ResearchConsentRead)
@limiter.limit("60/minute")
async def get_consent(
    request: Request,
    consent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ResearchConsentRead:
    scope = get_scope_filter(current_user)
    row = await cs.get_consent(db, consent_id, scope)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    return ResearchConsentRead.model_validate(row)


@router.patch("/{consent_id}", response_model=ResearchConsentRead)
@limiter.limit("30/minute")
async def patch_consent(
    request: Request,
    consent_id: UUID,
    body: ResearchConsentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ResearchConsentRead:
    scope = get_scope_filter(current_user)
    row = await cs.update_consent(
        db, consent_id, body, scope, actor_user_id=current_user.get("sub")
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    return ResearchConsentRead.model_validate(row)


@router.post("/{consent_id}/withdraw", response_model=ResearchConsentRead)
@limiter.limit("30/minute")
async def withdraw_consent(
    request: Request,
    consent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    body: WithdrawConsentBody | None = None,
) -> ResearchConsentRead:
    scope = get_scope_filter(current_user)
    row = await cs.withdraw_consent(
        db,
        consent_id,
        scope,
        actor_user_id=current_user.get("sub"),
        reason=body.reason if body else None,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    return ResearchConsentRead.model_validate(row)


@router.get("/{consent_id}/fhir")
@limiter.limit("60/minute")
async def get_consent_fhir(
    request: Request,
    consent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Response:
    """Export consent as FHIR R4 Consent resource (JSON)."""
    scope = get_scope_filter(current_user)
    row = await cs.get_consent(db, consent_id, scope)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    payload = cs.consent_to_fhir_dict(row)
    return Response(
        content=json.dumps(payload, ensure_ascii=False),
        media_type="application/fhir+json",
    )
