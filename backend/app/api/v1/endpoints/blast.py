"""BLAST search API: WES-backed Nextflow workflow and result parsing."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.blast import (
    BLASTParams,
    BLASTResultsResponse,
    BLASTSearchRequest,
    BLASTSearchResponse,
    PaperRef,
)
from app.services.blast_service import (
    find_papers_for_hits,
    get_blast_results,
    run_blast_search,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blast", tags=["blast"])


@router.post("/search", response_model=BLASTSearchResponse, status_code=status.HTTP_202_ACCEPTED)
async def blast_search(
    body: BLASTSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> BLASTSearchResponse:
    """Start BLAST search (WES + Nextflow). Returns run_id; poll GET /blast/results/{run_id}."""
    params = BLASTParams(
        database=body.database,
        evalue=body.evalue if body.evalue is not None else 0.001,
        max_hits=body.max_hits if body.max_hits is not None else 10,
        sequence_type=body.sequence_type or "auto",
        db_path=body.db_path,
    )
    try:
        run_id = await run_blast_search(db, body.query, body.database, params)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"BLAST workflow not available: {e}",
        ) from e
    await db.commit()
    return BLASTSearchResponse(run_id=run_id)


@router.get(
    "/results/{run_id}", response_model=BLASTResultsResponse, status_code=status.HTTP_200_OK
)
async def blast_results(
    run_id: str,
    papers: bool = Query(
        False,
        description="Include related papers from Literature Mining (find_papers_for_hits)",
    ),
    db: AsyncSession = Depends(get_db),
) -> BLASTResultsResponse:
    """Get BLAST results for run_id (from results.xml). Optionally include related papers."""
    try:
        results = await get_blast_results(db, run_id)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    papers_list: list[PaperRef] | None = None
    if papers:
        paper_models = await find_papers_for_hits(db, results, max_papers_per_hit=5)
        papers_list = [
            PaperRef(
                pmid=p.pmid,
                title=p.title,
                abstract=p.abstract or "",
                authors=p.authors or [],
                year=p.year,
                journal=p.journal or "",
                doi=p.doi,
            )
            for p in paper_models
        ]

    return BLASTResultsResponse(results=results, papers=papers_list)
