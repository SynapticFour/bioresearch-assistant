"""Locus: RAG over curated, institution-shared index chunks (not the user Paper library)."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.prompt_security import sanitize_for_llm
from app.models.locus_chunk import LocusChunk
from app.schemas.locus import LocusRAGResponse, LocusSource
from app.services.embedding_service import (
    EmbeddingService,
    EmbeddingServiceError,
    _preprocess_query,
)
from app.services.llm_service import LLMService, LLMServiceError

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 4000


def _cosine_distance_1_minus_dot(a: list[float], b: list[float]) -> float:
    """For L2-normalized vectors: cosine distance = 1 - dot(a,b)."""
    if len(a) != len(b) or not a:
        return 2.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return 1.0 - float(dot)


class LocusService:
    """Retrieve from Locus chunks and answer via LLM (on-prem; same Ollama/Claude as BRA)."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self._embed = embedding_service or EmbeddingService()
        self._llm = llm_service or LLMService()

    async def find_chunks(
        self,
        db: AsyncSession,
        query: str,
        *,
        top_k: int = 5,
        threshold: float = 1.5,
        corpus_ids: list[str] | None = None,
    ) -> list[LocusChunk]:
        """Top-K Locus chunks by embedding similarity to query."""
        if top_k <= 0:
            return []
        q = _preprocess_query((query or "").strip())
        if not q:
            return []
        try:
            qemb = await self._embed.embed_text_async(q)
        except EmbeddingServiceError as e:
            logger.warning("Locus embed failed: %s", e)
            raise

        bind = db.get_bind()
        dialect = bind.dialect.name if bind is not None else "postgresql"

        if dialect == "sqlite":
            return await self._find_sqlite(db, qemb, top_k, threshold, corpus_ids)

        distance_expr = LocusChunk.embedding.cosine_distance(qemb)
        stmt = select(LocusChunk, distance_expr.label("distance")).where(
            LocusChunk.embedding.isnot(None)
        )
        if corpus_ids:
            stmt = stmt.where(LocusChunk.corpus_id.in_(corpus_ids))
        stmt = stmt.where(distance_expr <= threshold)
        stmt = stmt.order_by(distance_expr).limit(top_k)
        result = await db.execute(stmt)
        rows = result.all()
        out: list[LocusChunk] = []
        for ch, dist in rows:
            score = max(0.0, 1.0 - (float(dist) / 2.0))
            ch._similarity_score = round(score * 100, 1)  # type: ignore[attr-defined]
            out.append(ch)
        return out

    async def _find_sqlite(
        self,
        db: AsyncSession,
        qemb: list[float],
        top_k: int,
        threshold: float,
        corpus_ids: list[str] | None,
    ) -> list[LocusChunk]:
        """Brute-force similarity for TESTING (SQLite) without pgvector."""
        stmt = select(LocusChunk).where(LocusChunk.embedding.isnot(None))
        if corpus_ids:
            stmt = stmt.where(LocusChunk.corpus_id.in_(corpus_ids))
        r = await db.execute(stmt)
        all_chunks = r.scalars().all()
        scored: list[tuple[LocusChunk, float]] = []
        for ch in all_chunks:
            raw = ch.embedding
            if raw is None:
                continue
            if isinstance(raw, str):
                import json

                raw = json.loads(raw)
            if not isinstance(raw, list) or len(raw) != len(qemb):
                continue
            d = _cosine_distance_1_minus_dot([float(x) for x in raw], [float(x) for x in qemb])
            if d > threshold:
                continue
            scored.append((ch, d))
        scored.sort(key=lambda x: x[1])
        out: list[LocusChunk] = []
        for ch, dist in scored[:top_k]:
            score = max(0.0, 1.0 - (float(dist) / 2.0))
            ch._similarity_score = round(score * 100, 1)  # type: ignore[attr-defined]
            out.append(ch)
        return out

    async def answer(
        self,
        question: str,
        db: AsyncSession,
        top_k: int = 5,
        language: str = "de",
        corpus_ids: list[str] | None = None,
    ) -> LocusRAGResponse:
        question = (question or "").strip()
        if not question:
            raise ValueError("question must not be empty")
        question = sanitize_for_llm(question)
        try:
            chunks = await self.find_chunks(
                db, question, top_k=top_k, corpus_ids=corpus_ids, threshold=1.5
            )
        except EmbeddingServiceError:
            raise

        if not chunks:
            raise ValueError(
                "Keine Locus-Index-Texte passend zu dieser Frage. "
                "Indexe müssen zuerst geladen und eingebettet werden (siehe docs/LOCUS-MODULE.md)."
            )

        context_parts: list[str] = []
        sources: list[tuple[LocusChunk, int]] = []
        total = 0
        for i, ch in enumerate(chunks, 1):
            t = sanitize_for_llm((ch.title or "").strip() or f"Korpus {ch.corpus_id}")
            body = sanitize_for_llm((ch.content or "").strip() or "")
            ref = (ch.source_ref or "").strip() or f"locus:{ch.corpus_id}:{ch.id}"
            block = f"[{i}] {t}\n{ref}\n{body}\n"
            if total + len(block) > MAX_CONTEXT_CHARS and context_parts:
                break
            context_parts.append(block)
            used = min(len(body), MAX_CONTEXT_CHARS)
            sources.append((ch, used))
            total += len(block)
            if total >= MAX_CONTEXT_CHARS:
                break

        context = "\n".join(context_parts)
        if not context.strip():
            raise ValueError("Kontext leer.")

        try:
            answer_text = await self._llm.rag_answer_locus(
                question=question,
                context=context,
                language=language or "de",
            )
        except LLMServiceError as e:
            raise LLMServiceError(str(e)) from e

        settings = get_settings()
        model_used = (
            settings.llm_claude_model
            if (settings.anthropic_api_key or "").strip()
            else settings.ollama_model
        )

        src_list = [
            LocusSource(
                chunk_id=ch.id,
                corpus_id=ch.corpus_id,
                source_ref=(ch.source_ref or "").strip() or str(ch.id),
                title=(ch.title or "").strip() or ch.corpus_id,
                similarity_score=float(getattr(ch, "_similarity_score", 0.0) or 0.0),
                used_chars=used,
            )
            for (ch, used) in sources
        ]
        return LocusRAGResponse(
            answer=answer_text,
            sources=src_list,
            question=question,
            model_used=model_used or "unknown",
            context_chunks=len(src_list),
        )
