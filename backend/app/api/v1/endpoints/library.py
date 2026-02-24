"""Library API: list/delete saved papers and semantic search."""

import csv
import io
import json
import logging
import re
import zipfile
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.isolation import get_scope_filter, get_scope_values
from app.core.limiter import limiter
from app.models.paper import Paper
from app.schemas.pubmed import PubMedArticle, PubMedSearchResponse
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError
from app.services.llm_service import LLMService, LLMServiceError
from app.services.metadata_service import MetadataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/library", tags=["library"])


class SemanticSearchRequest(BaseModel):
    """Request body for POST /library/search/semantic."""

    query: str = Field(default="", description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Max number of results")
    threshold: float | None = Field(
        default=None,
        ge=0,
        le=2,
        description=(
            "Max cosine distance (0=same, 2=opposite). "
            "Only return papers with distance <= threshold."
        ),
    )


DOI_REGEX = re.compile(r"^10\.\d{4,}/\S+$")


class SummarizeRequest(BaseModel):
    """Request body for POST /library/summarize."""

    pmid: str = Field(..., min_length=1, description="PubMed ID of the paper to summarize")
    language: str = Field(default="de", description="Language for summary (de, en)")


class MetadataExtractionRequest(BaseModel):
    """Request body for POST /library/extract-metadata."""

    doi: str | None = Field(default=None, description="DOI (e.g. 10.1038/...)")
    pmid: str | None = Field(default=None, description="PubMed ID")
    text: str | None = Field(default=None, description="Freitext mit Paper-Info (optional)")

    @field_validator("doi")
    @classmethod
    def doi_format(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = (v or "").strip()
        if not s:
            return None
        if not DOI_REGEX.match(s):
            raise ValueError("Ungültiges DOI-Format (erwartet: 10.xxxx/...)")
        return s


def _paper_to_response(p: Paper) -> PubMedSearchResponse:
    """Map Paper model to PubMedSearchResponse."""
    year_int: int | None = None
    if p.year is not None:
        try:
            year_int = int(str(p.year).strip())
        except ValueError:
            pass
    return PubMedSearchResponse(
        pmid=p.pmid,
        title=p.title or "",
        abstract=p.abstract or None,
        authors=list(p.authors) if p.authors else [],
        year=year_int,
        journal=p.journal or None,
        doi=p.doi,
        summary=p.summary,
    )


@router.post(
    "/summarize",
    status_code=status.HTTP_200_OK,
    summary="KI-Zusammenfassung generieren",
    description="Generiert eine KI-Zusammenfassung für ein gespeichertes Paper (Abstract).",
)
@limiter.limit("30/minute")
async def summarize_paper(
    request: Request,
    body: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Generiere KI-Zusammenfassung für ein Paper aus der Bibliothek (mit Cache)."""
    settings = get_settings()
    scope = get_scope_filter(current_user)
    language = (body.language or "de").strip().lower() or "de"
    stmt = select(Paper).where(Paper.pmid == body.pmid.strip())
    if "user_id" in scope and scope["user_id"]:
        stmt = stmt.where(Paper.user_id == scope["user_id"])
    elif "team_id" in scope and scope["team_id"]:
        stmt = stmt.where(Paper.team_id == scope["team_id"])
    r = await db.execute(stmt)
    paper = r.scalars().first()
    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper nicht gefunden",
        )
    if paper.summary and paper.summary_language == language:
        return {
            "summary": paper.summary,
            "cached": True,
            "language": language,
        }
    abstract = (paper.abstract or "").strip()
    if not abstract:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paper hat keinen Abstract",
        )
    try:
        llm = LLMService()
        result = await llm.summarize_paper(
            abstract=abstract,
            language=language,
            title=(paper.title or "").strip() or None,
        )
        summary_model = (
            settings.llm_claude_model
            if (settings.anthropic_api_key or "").strip()
            else settings.ollama_model
        )
        paper.summary = result.summary
        paper.summary_language = language
        paper.summary_model = summary_model
        await db.commit()
        return {
            "summary": result.summary,
            "cached": False,
            "language": language,
        }
    except LLMServiceError as e:
        logger.warning("Summarize failed for pmid=%s: %s", body.pmid, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="KI-Zusammenfassung fehlgeschlagen. Prüfen Sie Ollama/Anthropic.",
        ) from e


@router.post(
    "/extract-metadata",
    status_code=status.HTTP_200_OK,
    summary="Metadaten extrahieren",
    description="Metadaten aus DOI (CrossRef) oder PMID (PubMed). Vorausgefüllte Felder.",
)
async def extract_metadata(
    request: MetadataExtractionRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Extrahiere Metadaten automatisch (DOI oder PMID).

    Gibt vorausgefüllte Felder zurück — User kann prüfen und bestätigen.
    """
    service = MetadataService()
    metadata = None
    if request.doi:
        metadata = await service.extract_from_doi(request.doi)
    elif request.pmid and request.pmid.strip():
        metadata = await service.extract_from_pmid(request.pmid.strip())
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keine Metadaten gefunden",
        )
    return metadata


@router.get(
    "/papers",
    response_model=list[PubMedSearchResponse],
    status_code=status.HTTP_200_OK,
)
async def list_papers(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    year: Annotated[str | None, Query(description="Filter by publication year")] = None,
    journal: Annotated[str | None, Query(description="Filter by journal name")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PubMedSearchResponse]:
    """List saved papers with optional filters; scoped by isolation mode."""
    scope = get_scope_filter(current_user)
    stmt = select(Paper).order_by(desc(Paper.created_at)).limit(limit).offset(offset)
    if "user_id" in scope and scope["user_id"]:
        stmt = stmt.where(Paper.user_id == scope["user_id"])
    elif "team_id" in scope and scope["team_id"]:
        stmt = stmt.where(Paper.team_id == scope["team_id"])
    if year is not None and year.strip():
        stmt = stmt.where(Paper.year == year.strip())
    if journal is not None and journal.strip():
        stmt = stmt.where(Paper.journal.ilike(f"%{journal.strip()}%"))
    result = await db.execute(stmt)
    papers = result.scalars().all()
    return [_paper_to_response(p) for p in papers]


@router.post(
    "/papers",
    response_model=PubMedSearchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_paper(
    body: PubMedArticle,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PubMedSearchResponse:
    """Add a paper to the library (same as POST /literature/papers)."""
    scope_values = get_scope_values(current_user)
    service = EmbeddingService()
    try:
        paper = await service.store_paper(
            db,
            body,
            user_id=scope_values.get("user_id"),
            team_id=scope_values.get("team_id"),
        )
        await db.commit()
    except EmbeddingServiceError as e:
        logger.warning("Add paper failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
    return _paper_to_response(paper)


@router.delete(
    "/papers/{pmid}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_paper(
    pmid: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    """Remove a paper from the library (scoped by isolation mode)."""
    scope = get_scope_filter(current_user)
    stmt = select(Paper).where(Paper.pmid == pmid)
    if "user_id" in scope and scope["user_id"]:
        stmt = stmt.where(Paper.user_id == scope["user_id"])
    elif "team_id" in scope and scope["team_id"]:
        stmt = stmt.where(Paper.team_id == scope["team_id"])
    r = await db.execute(stmt)
    paper = r.scalars().first()
    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )
    await db.delete(paper)
    await db.commit()


@router.post(
    "/search/semantic",
    response_model=list[PubMedSearchResponse],
    status_code=status.HTTP_200_OK,
)
async def semantic_search(
    body: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[PubMedSearchResponse]:
    """Semantic search over saved papers (pgvector). On Railway returns empty list."""
    settings = get_settings()
    if (settings.deployment or "").lower() == "railway":
        return []

    query = (body.query or "").strip()
    limit = body.limit

    if not query:
        return []

    scope = get_scope_filter(current_user)
    user_id = scope.get("user_id") if scope else None
    team_id = scope.get("team_id") if scope else None

    try:
        service = EmbeddingService()
        papers = await service.find_similar(
            db,
            query,
            limit=limit,
            user_id=user_id,
            team_id=team_id,
            threshold=body.threshold if body.threshold is not None else 1.5,
        )
        return [_paper_to_response(p) for p in papers]
    except EmbeddingServiceError as e:
        logger.warning("Semantic search failed: %s", e)
        return []


@router.post(
    "/reembed-all",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def reembed_all_papers(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Re-embed all papers that have no embedding (e.g. saved before embeddings were enabled)."""
    scope = get_scope_filter(current_user)
    stmt = select(Paper).where(Paper.embedding.is_(None))
    if "user_id" in scope and scope["user_id"]:
        stmt = stmt.where(Paper.user_id == scope["user_id"])
    elif "team_id" in scope and scope["team_id"]:
        stmt = stmt.where(Paper.team_id == scope["team_id"])
    result = await db.execute(stmt)
    papers = result.scalars().all()

    service = EmbeddingService()
    count = 0
    for paper in papers:
        try:
            text = f"{paper.title} {paper.abstract or ''}".strip() or " "
            embedding = await service.embed_text_async(text)
            paper.embedding = embedding
            count += 1
        except Exception as e:
            logger.warning(
                "Re-embed failed for %s: %s", paper.pmid, e
            )
    await db.commit()
    return {
        "reembedded": count,
        "message": f"{count} Papers neu eingebettet",
    }


MAX_BULK_IMPORT_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_BULK_ENTRIES = 1000


def _normalize_paper_data(data: dict) -> dict:
    """Normalize a single paper dict for import (pmid, title, authors, year, etc.)."""
    authors = data.get("authors")
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(",") if a.strip()]
    elif not isinstance(authors, list):
        authors = []
    year = data.get("year")
    if year is not None and year != "":
        year = str(year)
    else:
        year = None
    return {
        "pmid": (data.get("pmid") or "").strip() or f"import-{uuid4().hex[:12]}",
        "title": (data.get("title") or "").strip() or "",
        "abstract": (data.get("abstract") or "").strip() or "",
        "authors": authors,
        "year": year,
        "journal": (data.get("journal") or "").strip() or "",
        "doi": (data.get("doi") or "").strip() or None,
    }


async def _import_single_paper(
    data: dict,
    scope_values: dict,
    db: AsyncSession,
    results: dict,
) -> None:
    """Import one paper into DB; updates results['imported'] and results['errors']."""
    try:
        normalized = _normalize_paper_data(data)
        paper = Paper(
            pmid=normalized["pmid"],
            title=normalized["title"],
            abstract=normalized["abstract"],
            authors=normalized["authors"],
            year=normalized["year"],
            journal=normalized["journal"],
            doi=normalized["doi"],
            user_id=scope_values.get("user_id"),
            team_id=scope_values.get("team_id"),
        )
        db.add(paper)
        results["imported"] += 1
    except Exception as e:
        results["errors"].append(str(e))
        results["skipped"] += 1


@router.post(
    "/bulk-import",
    status_code=status.HTTP_200_OK,
    summary="Bulk Import",
    description="Import mehrerer Papers (ZIP/JSON/CSV). Max 50MB, max 1000 Einträge.",
)
@limiter.limit("5/minute")
async def bulk_import(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Bulk import papers from ZIP, JSON or CSV. Returns imported/skipped/errors."""
    content = await file.read()
    if len(content) > MAX_BULK_IMPORT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Datei zu groß (max. 50 MB)",
        )
    scope_values = get_scope_values(current_user)
    results: dict = {"imported": 0, "skipped": 0, "errors": []}
    filename = (file.filename or "").lower()

    if filename.endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                names = zf.namelist()
                if len(names) > MAX_BULK_ENTRIES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"ZIP enthält zu viele Einträge (max. {MAX_BULK_ENTRIES})",
                    )
                for name in names:
                    if name.endswith("/"):
                        continue
                    try:
                        raw = zf.read(name).decode("utf-8")
                        data = json.loads(raw)
                        if isinstance(data, list):
                            for item in data:
                                await _import_single_paper(item, scope_values, db, results)
                                if results["imported"] + results["skipped"] >= MAX_BULK_ENTRIES:
                                    break
                        else:
                            await _import_single_paper(data, scope_values, db, results)
                    except Exception as e:
                        results["errors"].append(f"{name}: {e}")
                        results["skipped"] += 1
        except zipfile.BadZipFile as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ungültige ZIP-Datei",
            ) from err
    elif filename.endswith(".json"):
        try:
            data = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ungültiges JSON",
            ) from err
        papers = data if isinstance(data, list) else [data]
        for paper_data in papers[:MAX_BULK_ENTRIES]:
            await _import_single_paper(paper_data, scope_values, db, results)
    elif filename.endswith(".csv"):
        try:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
            rows = list(reader)[:MAX_BULK_ENTRIES]
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ungültiges CSV",
            ) from err
        for row in rows:
            await _import_single_paper(row, scope_values, db, results)
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format nicht unterstützt. Bitte ZIP, JSON oder CSV.",
        )

    await db.commit()
    return results
