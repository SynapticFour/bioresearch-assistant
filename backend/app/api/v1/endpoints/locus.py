"""Locus — curated on-prem RAG (optional module; see docs/LOCUS-MODULE.md)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.locus_chunk import LocusChunk
from app.schemas.locus import LocusRAGRequest, LocusRAGResponse, LocusStatusResponse
from app.services.embedding_service import EmbeddingServiceError
from app.services.llm_service import LLMServiceError
from app.services.locus_service import LocusService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/locus", tags=["locus"])


@router.get(
    "/status",
    response_model=LocusStatusResponse,
    summary="Locus-Index Status",
    description="Ob Locus API aktiv ist und wie viele Chunks in der DB liegen.",
)
async def locus_status(
    db: AsyncSession = Depends(get_db),
) -> LocusStatusResponse:
    settings = get_settings()
    if not settings.locus_enabled:
        return LocusStatusResponse(
            locus_enabled=False,
            chunk_count=0,
            corpora=[],
        )
    cnt = await db.scalar(
        select(func.count()).select_from(LocusChunk).where(LocusChunk.id.isnot(None))
    )
    cids = (await db.execute(select(LocusChunk.corpus_id).distinct())).scalars().all()
    return LocusStatusResponse(
        locus_enabled=True,
        chunk_count=int(cnt or 0),
        corpora=[str(c) for c in cids if c],
    )


@router.post(
    "/rag",
    response_model=LocusRAGResponse,
    status_code=status.HTTP_200_OK,
    summary="Locus RAG (kuratierte Indizes)",
    description="Frage an den Locus-Index (nicht an die persönliche Paper-Bibliothek).",
)
@limiter.limit("10/minute")
async def locus_rag(
    request: Request,
    body: LocusRAGRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> LocusRAGResponse:
    _ = current_user  # auth for tenant/limit; index is not user-scoped
    settings = get_settings()
    if not settings.locus_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Locus-Modul ist deaktiviert. Setze LOCUS_ENABLED=1 in der Konfiguration.",
        )
    service = LocusService()
    try:
        return await service.answer(
            question=body.question,
            db=db,
            top_k=body.top_k,
            language=(body.language or "de").strip().lower() or "de",
            corpus_ids=body.corpus_ids,
        )
    except ValueError as e:
        if "Keine Locus" in str(e) or "Kein" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except LLMServiceError as e:
        logger.warning("Locus RAG LLM failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM nicht verfügbar. Prüfen Sie Ollama/Anthropic.",
        ) from e
    except EmbeddingServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
