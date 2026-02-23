"""GA4GH Phenopackets v2 API endpoints.

All patient identifiers are pseudonym ID only (no real PII).
Reference: https://phenopacket-schema.readthedocs.io/
"""

import logging
import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.isolation import get_scope_filter, get_scope_values
from app.core.limiter import limiter
from app.models.patient_record import PatientRecordModel
from app.schemas.phenopackets import (
    DiseaseTerm,
    GeneOfInterest,
    OntologyTerm,
    PatientData,
    ValidationResult,
)
from app.services.hpo_service import HPOService
from app.services.phenopacket_service import (
    create_phenopacket,
    export_phenopacket,
    phenopacket_to_dict,
    validate_phenopacket,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/phenopackets", tags=["phenopackets"])


class PatientDataCreate(BaseModel):
    """Accept simple string lists for phenotypes/diseases/genes (API convenience)."""

    pseudonym_id: str = Field(..., min_length=1)
    phenotypes: list[str] | list[dict[str, Any]] = Field(default_factory=list)
    diseases: list[str] | list[dict[str, Any]] = Field(default_factory=list)
    genes_of_interest: list[str] | list[dict[str, Any]] = Field(default_factory=list)
    notes: str | None = Field(default=None, description="Optional free-text notes")


def _normalize_to_patient_data(body: PatientDataCreate) -> PatientData:
    """Convert API input (strings or dicts) to PatientData."""
    phenotypes: list[OntologyTerm] = []
    for p in body.phenotypes:
        if isinstance(p, str):
            phenotypes.append(OntologyTerm(id=p.strip(), label=None))
        elif isinstance(p, dict) and p.get("id"):
            phenotypes.append(OntologyTerm(id=p["id"], label=p.get("label")))
    diseases: list[DiseaseTerm] = []
    for d in body.diseases:
        if isinstance(d, str):
            diseases.append(DiseaseTerm(id=d.strip(), label=None))
        elif isinstance(d, dict) and d.get("id"):
            diseases.append(DiseaseTerm(id=d["id"], label=d.get("label")))
    genes: list[GeneOfInterest] = []
    for g in body.genes_of_interest:
        if isinstance(g, str):
            s = g.strip()
            genes.append(GeneOfInterest(value_id=f"HGNC:{s}", symbol=s))
        elif isinstance(g, dict) and (g.get("symbol") or g.get("value_id")):
            genes.append(
                GeneOfInterest(
                    value_id=g.get("value_id") or f"HGNC:{g.get('symbol', '')}",
                    symbol=g.get("symbol") or str(g.get("value_id", "")).split(":")[-1],
                )
            )
    return PatientData(
        pseudonym_id=body.pseudonym_id.strip(),
        phenotypes=phenotypes,
        diseases=diseases,
        genes_of_interest=genes,
    )


class ExtractPhenotypesRequest(BaseModel):
    """Request body for POST /phenopackets/extract."""

    text: str = Field(..., min_length=1, description="Clinical free text to analyze")


@router.get(
    "/hpo/search",
    status_code=status.HTTP_200_OK,
    summary="HPO-Terme suchen",
    description="Sucht HPO-Terme (Human Phenotype Ontology) nach Freitext.",
)
@limiter.limit("30/minute")
async def hpo_search(
    request: Request,
    q: Annotated[str, Query(max_length=100)] = "",
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    """Search HPO terms (e.g. ?q=seizure)."""
    service = HPOService()
    return await service.search_terms(q)


@router.post(
    "/extract",
    status_code=status.HTTP_200_OK,
    summary="Phänotypen aus Text extrahieren",
    description="Extrahiert HPO-Terme und Gene aus klinischem Freitext.",
)
@limiter.limit("20/minute")
async def extract_phenotypes(
    request: Request,
    body: ExtractPhenotypesRequest,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Extract HPO terms and genes from clinical text."""
    service = HPOService()
    terms = await service.extract_from_text(body.text)
    # Simple gene extraction: look for common genes in text
    gene_pattern = re.compile(rb"\b(BRCA1|BRCA2|TP53|EGFR|KRAS|BRAF)\b", re.I)
    text_bytes = body.text.encode("utf-8", errors="ignore")
    genes = list({m.decode("utf-8").upper() for m in gene_pattern.findall(text_bytes)})
    return {"terms": terms, "genes": genes}


@router.get("", response_model=list[dict[str, Any]])
async def list_phenopackets(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Liste Phenopackets (scoped by isolation mode)."""
    scope = get_scope_filter(current_user)
    stmt = select(PatientRecordModel).order_by(PatientRecordModel.pseudonym_id)
    if "user_id" in scope and scope["user_id"]:
        stmt = stmt.where(PatientRecordModel.user_id == scope["user_id"])
    elif "team_id" in scope and scope["team_id"]:
        stmt = stmt.where(PatientRecordModel.team_id == scope["team_id"])
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [row.phenopacket_json for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_phenopacket_endpoint(
    body: PatientDataCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a phenopacket from PatientData and store by pseudonym_id.

    Patient data must use pseudonym_id only (no real patient identifiers).
    Accepts phenotypes/diseases as list of CURIE strings (e.g. ["HP:0001250"])
    and genes_of_interest as list of gene symbols (e.g. ["BRCA1"]).
    """
    patient_data = _normalize_to_patient_data(body)
    pp = create_phenopacket(patient_data)
    pp_dict = phenopacket_to_dict(pp)
    scope_values = get_scope_values(current_user)
    record = PatientRecordModel(
        pseudonym_id=patient_data.pseudonym_id,
        phenopacket_json=pp_dict,
        user_id=scope_values.get("user_id"),
        team_id=scope_values.get("team_id"),
    )
    db.add(record)
    try:
        await db.flush()
        await db.commit()
    except IntegrityError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phenopacket with this pseudonym_id already exists",
        ) from err
    return pp_dict


@router.get("/{id}", status_code=status.HTTP_200_OK)
async def get_phenopacket(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a phenopacket by pseudonym_id (id), scoped by isolation mode."""
    scope = get_scope_filter(current_user)
    stmt = select(PatientRecordModel).where(PatientRecordModel.pseudonym_id == id)
    if "user_id" in scope and scope["user_id"]:
        stmt = stmt.where(PatientRecordModel.user_id == scope["user_id"])
    elif "team_id" in scope and scope["team_id"]:
        stmt = stmt.where(PatientRecordModel.team_id == scope["team_id"])
    r = await db.execute(stmt)
    row = r.scalars().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phenopacket not found",
        )
    return row.phenopacket_json


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phenopacket(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    """Delete a phenopacket by pseudonym_id (scoped by isolation mode)."""
    scope = get_scope_filter(current_user)
    stmt = select(PatientRecordModel).where(PatientRecordModel.pseudonym_id == id)
    if "user_id" in scope and scope["user_id"]:
        stmt = stmt.where(PatientRecordModel.user_id == scope["user_id"])
    elif "team_id" in scope and scope["team_id"]:
        stmt = stmt.where(PatientRecordModel.team_id == scope["team_id"])
    r = await db.execute(stmt)
    row = r.scalars().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phenopacket not found",
        )
    await db.delete(row)
    await db.commit()


@router.get("/{id}/export", status_code=status.HTTP_200_OK)
async def export_phenopacket_endpoint(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Export phenopacket as JSON-LD by pseudonym_id (scoped by isolation mode)."""
    scope = get_scope_filter(current_user)
    stmt = select(PatientRecordModel).where(PatientRecordModel.pseudonym_id == id)
    if "user_id" in scope and scope["user_id"]:
        stmt = stmt.where(PatientRecordModel.user_id == scope["user_id"])
    elif "team_id" in scope and scope["team_id"]:
        stmt = stmt.where(PatientRecordModel.team_id == scope["team_id"])
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
