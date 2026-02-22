"""GA4GH Phenopackets v2 API endpoints.

All patient identifiers are pseudonym IDs only (no real PII).
Reference: https://phenopacket-schema.readthedocs.io/
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.patient_record import PatientRecordModel
from app.schemas.phenopackets import PatientData, ValidationResult
from app.services.phenopacket_service import (
    create_phenopacket,
    export_phenopacket,
    phenopacket_to_dict,
    validate_phenopacket,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/phenopackets", tags=["phenopackets"])


@router.get("", response_model=list[dict[str, Any]])
async def list_phenopackets(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Liste alle Phenopackets (als JSON-Dicts)."""
    stmt = select(PatientRecordModel).order_by(PatientRecordModel.pseudonym_id)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [row.phenopacket_json for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_phenopacket_endpoint(
    body: PatientData,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a phenopacket from PatientData and store by pseudonym_id.

    Patient data must use pseudonym_id only (no real patient identifiers).
    """
    pp = create_phenopacket(body)
    pp_dict = phenopacket_to_dict(pp)
    record = PatientRecordModel(
        pseudonym_id=body.pseudonym_id,
        phenopacket_json=pp_dict,
    )
    db.add(record)
    try:
        await db.flush()
    except IntegrityError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phenopacket with this pseudonym_id already exists",
        ) from err
    return pp_dict


@router.get("/{id}", status_code=status.HTTP_200_OK)
async def get_phenopacket(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a phenopacket by pseudonym_id (id)."""
    stmt = select(PatientRecordModel).where(PatientRecordModel.pseudonym_id == id)
    r = await db.execute(stmt)
    row = r.scalars().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phenopacket not found",
        )
    return row.phenopacket_json


@router.get("/{id}/export", status_code=status.HTTP_200_OK)
async def export_phenopacket_endpoint(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Export phenopacket as JSON-LD by pseudonym_id."""
    stmt = select(PatientRecordModel).where(PatientRecordModel.pseudonym_id == id)
    r = await db.execute(stmt)
    row = r.scalars().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phenopacket not found",
        )
    return export_phenopacket(row.phenopacket_json)


@router.post("/validate", response_model=ValidationResult, status_code=status.HTTP_200_OK)
async def validate_phenopacket_endpoint(phenopacket: dict[str, Any]) -> ValidationResult:
    """Validate a phenopacket dict against Phenopackets v2 schema."""
    return validate_phenopacket(phenopacket)
