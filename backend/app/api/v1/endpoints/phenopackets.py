"""GA4GH Phenopackets v2 API endpoints.

All patient identifiers are pseudonym ID only (no real PII).
Reference: https://phenopacket-schema.readthedocs.io/
"""

import json
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
from app.models.phenopacket_asset import PhenopacketAsset
from app.schemas.phenoflow import (
    PhenopacketAssetFileType,
    PhenopacketAssetLinkRequest,
    PhenopacketAssetLinkResponse,
    PhenopacketAssetSummary,
)
from app.schemas.phenopackets import (
    DiseaseTerm,
    GeneOfInterest,
    OntologyTerm,
    PatientData,
    ValidationResult,
)
from app.services.drs_service import get_object as drs_get_object
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

    def _to_dict(record: PatientRecordModel) -> dict[str, Any]:
        raw = record.phenopacket_json
        return json.loads(raw) if isinstance(raw, str) else raw

    return [_to_dict(r) for r in rows]


def _apply_scope_assets(
    stmt: object,
    current_user: dict[str, object],
) -> object:
    """Apply isolation scope to asset mapping queries."""
    scope = get_scope_filter(current_user)
    if "user_id" in scope and scope["user_id"]:
        return stmt.where(PhenopacketAsset.user_id == scope["user_id"])
    if "team_id" in scope and scope["team_id"]:
        return stmt.where(PhenopacketAsset.team_id == scope["team_id"])
    return stmt


@router.get(
    "/{id}/assets",
    response_model=list[PhenopacketAssetSummary],
    status_code=status.HTTP_200_OK,
)
async def list_phenopacket_assets(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[PhenopacketAssetSummary]:
    """List DRS assets linked to a phenopacket (by pseudonym_id)."""
    scope = get_scope_filter(current_user)
    stmt_pp = select(PatientRecordModel).where(PatientRecordModel.pseudonym_id == id)
    if "user_id" in scope and scope["user_id"]:
        stmt_pp = stmt_pp.where(PatientRecordModel.user_id == scope["user_id"])
    elif "team_id" in scope and scope["team_id"]:
        stmt_pp = stmt_pp.where(PatientRecordModel.team_id == scope["team_id"])
    r = await db.execute(stmt_pp)
    row = r.scalars().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phenopacket not found")

    stmt = (
        select(PhenopacketAsset)
        .where(PhenopacketAsset.pseudonym_id == id)
        .order_by(PhenopacketAsset.id)
    )
    stmt = _apply_scope_assets(stmt, current_user)
    assets_r = await db.execute(stmt)
    assets = list(assets_r.scalars().all())

    return [
        PhenopacketAssetSummary(
            asset_id=a.id,
            drs_object_id=a.drs_object_id,
            file_type=PhenopacketAssetFileType(a.file_type),
        )
        for a in assets
    ]


@router.post(
    "/{id}/assets",
    response_model=PhenopacketAssetLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_phenopacket_asset(
    id: str,
    body: PhenopacketAssetLinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PhenopacketAssetLinkResponse:
    """Link a DRS object to a stored phenopacket (creates phenopacket_assets row)."""
    # Ensure phenopacket exists in current isolation scope.
    scope = get_scope_filter(current_user)
    stmt_pp = select(PatientRecordModel).where(PatientRecordModel.pseudonym_id == id)
    if "user_id" in scope and scope["user_id"]:
        stmt_pp = stmt_pp.where(PatientRecordModel.user_id == scope["user_id"])
    elif "team_id" in scope and scope["team_id"]:
        stmt_pp = stmt_pp.where(PatientRecordModel.team_id == scope["team_id"])
    r = await db.execute(stmt_pp)
    row = r.scalars().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phenopacket not found")

    # Validate that the DRS object exists (no actual byte streaming here).
    obj = drs_get_object(body.drs_object_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DRS object not found")

    scope_values = get_scope_values(current_user)
    asset = PhenopacketAsset(
        pseudonym_id=id,
        drs_object_id=body.drs_object_id,
        file_type=body.file_type.value,
        user_id=scope_values.get("user_id"),
        team_id=scope_values.get("team_id"),
    )
    db.add(asset)
    try:
        await db.flush()
        await db.commit()
    except IntegrityError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="DRS asset already linked to this phenopacket",
        ) from err

    return PhenopacketAssetLinkResponse(
        asset_id=asset.id,
        pseudonym_id=asset.pseudonym_id,
        drs_object_id=asset.drs_object_id,
        file_type=PhenopacketAssetFileType(asset.file_type),
    )


@router.delete(
    "/{id}/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_phenopacket_asset(
    id: str,
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    """Delete a linked DRS asset from a phenopacket mapping."""
    stmt = (
        select(PhenopacketAsset)
        .where(PhenopacketAsset.id == asset_id)
        .where(PhenopacketAsset.pseudonym_id == id)
    )
    stmt = _apply_scope_assets(stmt, current_user)
    r = await db.execute(stmt)
    asset = r.scalars().first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset mapping not found")
    await db.delete(asset)
    await db.commit()
    return None


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
    phenopacket_data = (
        json.loads(row.phenopacket_json)
        if isinstance(row.phenopacket_json, str)
        else row.phenopacket_json
    )
    return phenopacket_data


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
    phenopacket_data = (
        json.loads(row.phenopacket_json)
        if isinstance(row.phenopacket_json, str)
        else row.phenopacket_json
    )
    return export_phenopacket(phenopacket_data)


@router.post("/validate", response_model=ValidationResult, status_code=status.HTTP_200_OK)
async def validate_phenopacket_endpoint(phenopacket: dict[str, Any]) -> ValidationResult:
    """Validate a phenopacket dict against Phenopackets v2 schema."""
    return validate_phenopacket(phenopacket)
