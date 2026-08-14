"""BLAST search API: WES-backed Nextflow workflow and result parsing."""

import logging
import os
import shutil
import subprocess

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.limiter import limiter
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


@router.get("/db-status")
@limiter.limit("30/minute")
async def blast_db_status(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Check if BLAST database is available."""
    if not shutil.which("blastn"):
        return {
            "available": False,
            "reason": "BLAST not installed",
        }

    # Prüfe ob nt Datenbank existiert
    db_path = "/blast/db/nt"
    result = subprocess.run(
        ["blastdbcmd", "-db", db_path, "-info"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return {
            "available": True,
            "database": db_path,
            "info": (result.stdout or "")[:200],
        }

    # Prüfe ob andere DBs vorhanden
    db_dir = "/blast/db"
    if os.path.exists(db_dir):
        dbs = [f[:-4] for f in os.listdir(db_dir) if f.endswith(".nsi")]
        if dbs:
            return {
                "available": True,
                "database": db_dir,
                "databases": dbs[:20],
            }

    return {
        "available": False,
        "reason": "No BLAST database found",
        "setup": "Run ./setup-blast-db.sh",
    }


@router.post("/search", response_model=BLASTSearchResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def blast_search(
    request: Request,
    body: BLASTSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> BLASTSearchResponse:
    """Start BLAST search (WES + Nextflow). Returns run_id; poll GET /blast/results/{run_id}."""
    params = BLASTParams(
        database=body.database,
        evalue=body.evalue if body.evalue is not None else 0.001,
        max_hits=body.max_hits if body.max_hits is not None else 10,
        sequence_type=body.sequence_type or "auto",
        db_path=None,
    )
    try:
        run_id = await run_blast_search(
            db, body.query, body.database, params, current_user=current_user
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
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
@limiter.limit("30/minute")
async def blast_results(
    request: Request,
    run_id: str,
    papers: bool = Query(
        False,
        description="Include related papers from Literature Mining (find_papers_for_hits)",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> BLASTResultsResponse:
    """Get BLAST results for run_id (from results.xml). Optionally include related papers."""
    try:
        results = await get_blast_results(db, run_id, current_user=current_user)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    papers_list: list[PaperRef] | None = None
    if papers:
        paper_models = await find_papers_for_hits(
            db, results, max_papers_per_hit=5, current_user=current_user
        )
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
