"""CRUD and lookup for terminology mapping overrides."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.terminology_mapping_override import TerminologyMappingOverride


async def load_active_override_maps(
    db: AsyncSession,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return (disease_raw_id -> target, lab_raw_id -> target) for MII export."""
    stmt = select(TerminologyMappingOverride).where(TerminologyMappingOverride.is_active.is_(True))
    result = await db.execute(stmt)
    rows = result.scalars().all()
    disease: dict[str, dict[str, Any]] = {}
    lab: dict[str, dict[str, Any]] = {}
    for r in rows:
        target = {
            "system": r.target_system,
            "code": r.target_code,
            "display": r.target_display,
        }
        if r.module == "diagnosis":
            disease[r.raw_id] = target
        elif r.module == "laboratory":
            lab[r.raw_id] = target
    return disease, lab


async def list_overrides(db: AsyncSession) -> list[TerminologyMappingOverride]:
    stmt = select(TerminologyMappingOverride).order_by(
        TerminologyMappingOverride.module,
        TerminologyMappingOverride.raw_id,
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def upsert_override(
    db: AsyncSession,
    *,
    module: str,
    raw_id: str,
    target_system: str,
    target_code: str,
    target_display: str | None,
    notes: str | None,
    user_id: str | None,
) -> TerminologyMappingOverride:
    stmt = select(TerminologyMappingOverride).where(
        TerminologyMappingOverride.module == module,
        TerminologyMappingOverride.raw_id == raw_id,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        existing.target_system = target_system
        existing.target_code = target_code
        existing.target_display = target_display
        existing.notes = notes
        existing.is_active = True
        existing.created_by_user_id = user_id
    else:
        existing = TerminologyMappingOverride(
            id=uuid4(),
            module=module,
            raw_id=raw_id,
            target_system=target_system,
            target_code=target_code,
            target_display=target_display,
            notes=notes,
            is_active=True,
            created_by_user_id=user_id,
        )
        db.add(existing)
    await db.commit()
    await db.refresh(existing)
    return existing


async def deactivate_override(db: AsyncSession, override_id: str) -> bool:
    from uuid import UUID

    try:
        oid = UUID(override_id)
    except ValueError:
        return False
    stmt = select(TerminologyMappingOverride).where(TerminologyMappingOverride.id == oid)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        return False
    row.is_active = False
    await db.commit()
    return True
