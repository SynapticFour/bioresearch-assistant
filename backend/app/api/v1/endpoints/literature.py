"""Literature Mining API: PubMed search, fetch by PMID, and save paper."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.paper import Paper
from app.schemas.pubmed import (
    LiteratureStatsResponse,
    PubMedArticle,
    PubMedSearchRequest,
    PubMedSearchResponse,
)
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError
from app.services.pubmed_service import PubMedService, PubMedServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/literature", tags=["Literature Mining"])


def _article_to_response(article: PubMedArticle) -> PubMedSearchResponse:
    """Map PubMedArticle to PubMedSearchResponse (year str -> int when possible)."""
    year_int: int | None = None
    if article.year is not None:
        try:
            year_int = int(article.year.strip())
        except ValueError:
            pass
    return PubMedSearchResponse(
        pmid=article.pmid,
        title=article.title,
        abstract=article.abstract or None,
        authors=article.authors,
        year=year_int,
        journal=article.journal or None,
        doi=article.doi,
        summary=None,
    )


@router.post("/search", response_model=list[PubMedSearchResponse], status_code=status.HTTP_200_OK)
async def search_literature(
    request: PubMedSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[PubMedSearchResponse]:
    """Suche PubMed Papers und speichere mit KI-Zusammenfassung."""
    async with PubMedService() as service:
        try:
            articles = await service.search_pubmed(
                request.query,
                max_results=request.max_results,
            )
        except PubMedServiceError as e:
            logger.warning("Literature search failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"PubMed search failed: {e}",
            ) from e
    return [_article_to_response(a) for a in articles]


@router.get(
    "/stats",
    response_model=LiteratureStatsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_literature_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> LiteratureStatsResponse:
    """Dashboard: total papers count and last stored papers (from DB)."""
    count_result = await db.execute(select(func.count()).select_from(Paper))
    total = count_result.scalar_one() or 0
    stmt = select(Paper).order_by(Paper.created_at.desc()).limit(3)
    result = await db.execute(stmt)
    papers = result.scalars().all()
    recent = [
        PubMedSearchResponse(
            pmid=p.pmid,
            title=p.title or "",
            abstract=p.abstract or None,
            authors=list(p.authors) if p.authors else [],
            year=int(p.year) if p.year and str(p.year).strip().isdigit() else None,
            journal=p.journal or None,
            doi=p.doi,
            summary=None,
        )
        for p in papers
    ]
    return LiteratureStatsResponse(total_papers=total, recent_papers=recent)


@router.post(
    "/papers",
    response_model=PubMedSearchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_paper(
    body: PubMedArticle,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PubMedSearchResponse:
    """Speichere ein Paper (z. B. aus Suchergebnissen) in der DB inkl. Embedding."""
    service = EmbeddingService()
    try:
        paper = await service.store_paper(db, body)
        await db.commit()
    except EmbeddingServiceError as e:
        logger.warning("Save paper failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
    return PubMedSearchResponse(
        pmid=paper.pmid,
        title=paper.title or "",
        abstract=paper.abstract or None,
        authors=list(paper.authors) if paper.authors else [],
        year=int(paper.year) if paper.year and str(paper.year).strip().isdigit() else None,
        journal=paper.journal or None,
        doi=paper.doi,
        summary=None,
    )


@router.get(
    "/papers/{pmid}",
    response_model=PubMedSearchResponse,
    status_code=status.HTTP_200_OK,
)
async def get_paper(
    pmid: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PubMedSearchResponse:
    """Hole ein spezifisches Paper per PMID."""
    async with PubMedService() as service:
        try:
            article = await service.fetch_article(pmid)
        except PubMedServiceError as e:
            logger.warning("Fetch paper %s failed: %s", pmid, e)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paper not found",
            ) from e
    return _article_to_response(article)
