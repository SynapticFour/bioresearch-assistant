"""Library API: list/delete saved papers and semantic search."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.isolation import get_scope_filter, get_scope_values
from app.models.paper import Paper
from app.schemas.pubmed import PubMedArticle, PubMedSearchResponse
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/library", tags=["library"])


class SemanticSearchRequest(BaseModel):
    """Request body for POST /library/search/semantic."""

    query: str = Field(default="", description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Max number of results")


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
        summary=None,
    )


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
        )
        return [_paper_to_response(p) for p in papers]
    except EmbeddingServiceError as e:
        logger.warning("Semantic search failed: %s", e)
        return []
