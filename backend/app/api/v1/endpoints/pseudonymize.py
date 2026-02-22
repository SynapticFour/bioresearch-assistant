"""Pseudonymization API endpoints (DSGVO)."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.pseudonymization_mapping import PseudonymizationMapping
from app.schemas.pseudonymize import (
    AuditLogEntry,
    PseudonymizationResult,
    PseudonymizeRequest,
    RestoreRequest,
    RestoreResult,
)
from app.services.pseudonymization_service import (
    input_hash_for_audit,
)
from app.services.pseudonymization_service import (
    pseudonymize as pseudonymize_service,
)
from app.services.pseudonymization_service import (
    restore as restore_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pseudonymize", tags=["pseudonymization"])

OPERATION_TYPE_PSEUDONYMIZE = "pseudonymize"
OPERATION_TYPE_RESTORE = "restore"


async def get_optional_user_id(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> str | None:
    """Optional user ID from header for audit (no auth enforced here)."""
    return x_user_id


def require_restore_permission(
    x_restore_api_key: Annotated[str | None, Header(alias="X-Restore-API-Key")] = None,
) -> None:
    """Dependency: require valid restore API key for restore endpoint."""
    settings = get_settings()
    if not settings.restore_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Restore is not configured (RESTORE_API_KEY not set)",
        )
    if x_restore_api_key != settings.restore_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Restore-API-Key",
        )


@router.post("", response_model=PseudonymizationResult, status_code=status.HTTP_200_OK)
async def pseudonymize(
    body: PseudonymizeRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_optional_user_id),
) -> PseudonymizationResult:
    """Pseudonymize clinical text; returns pseudonymized text and mapping_id for restore.

    Detects PERSON, DATE_TIME, MEDICAL_LICENSE, PHONE_NUMBER, EMAIL, and German patient IDs.
    Mapping is stored encrypted (AES-256). Audit log records operation with input hash only.
    """
    result = pseudonymize_service(body.text, language=body.language)
    pseudonymized_text = result["pseudonymized_text"]
    entities_found = result["entities_found"]
    encrypted_bytes = result.get("encrypted_mapping_bytes")

    operation_id = uuid.uuid4().hex
    mapping_id: str | None = None
    if encrypted_bytes is not None:
        mapping_id = uuid.uuid4().hex
        mapping_row = PseudonymizationMapping(
            mapping_id=mapping_id,
            encrypted_mapping=encrypted_bytes,
        )
        db.add(mapping_row)

    input_hash = input_hash_for_audit(body.text)
    audit_row = AuditLog(
        operation_id=operation_id,
        user_id=user_id,
        entities_count=len(entities_found),
        input_hash=input_hash,
        operation_type=OPERATION_TYPE_PSEUDONYMIZE,
        language=body.language,
        mapping_id=mapping_id,
    )
    db.add(audit_row)
    await db.flush()

    entities = [{"type": e["type"], "start": e["start"], "end": e["end"]} for e in entities_found]
    return PseudonymizationResult(
        pseudonymized_text=pseudonymized_text,
        mapping_id=mapping_id,
        entities_found=entities,
    )


@router.post(
    "/restore",
    response_model=RestoreResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_restore_permission)],
)
async def restore(
    body: RestoreRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_optional_user_id),
) -> RestoreResult:
    """Restore original text from pseudonymized text and mapping_id. Requires X-Restore-API-Key."""
    stmt = select(PseudonymizationMapping).where(
        PseudonymizationMapping.mapping_id == body.mapping_id
    )
    r = await db.execute(stmt)
    row = r.scalars().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found or expired",
        )
    restored_text = restore_service(body.pseudonymized_text, row.encrypted_mapping)

    operation_id = uuid.uuid4().hex
    audit_row = AuditLog(
        operation_id=operation_id,
        user_id=user_id,
        entities_count=0,
        input_hash=input_hash_for_audit(body.pseudonymized_text),
        operation_type=OPERATION_TYPE_RESTORE,
        language=None,
        mapping_id=body.mapping_id,
    )
    db.add(audit_row)
    await db.flush()

    return RestoreResult(restored_text=restored_text)


@router.get("/audit-log", response_model=list[AuditLogEntry], status_code=status.HTTP_200_OK)
async def get_audit_log(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogEntry]:
    """Return recent pseudonymization/restore audit log entries (no raw text)."""
    from sqlalchemy import desc

    stmt = select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(min(limit, 500)).offset(offset)
    r = await db.execute(stmt)
    rows = r.scalars().all()
    return [
        AuditLogEntry(
            operation_id=row.operation_id,
            user_id=row.user_id,
            timestamp=row.timestamp.isoformat(),
            entities_count=row.entities_count,
            input_hash=row.input_hash,
            operation_type=row.operation_type,
            language=getattr(row, "language", None),
            mapping_id=getattr(row, "mapping_id", None),
        )
        for row in rows
    ]
