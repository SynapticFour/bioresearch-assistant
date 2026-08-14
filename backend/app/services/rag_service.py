"""RAG service: question → similar papers → context → LLM answer with sources."""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.isolation import get_scope_filter
from app.core.prompt_security import sanitize_for_llm
from app.schemas.rag import RAGResponse, RAGSource
from app.services.embedding_service import (
    EmbeddingService,
    EmbeddingServiceError,
    get_embedding_service,
)
from app.services.llm_service import LLMService, LLMServiceError, get_llm_service

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 4000  # Schneller für Mistral 7B


class RAGService:
    """Retrieval Augmented Generation: answer natural language questions over the library."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self._embedding = embedding_service or get_embedding_service()
        self._llm = llm_service or get_llm_service()

    async def answer(
        self,
        question: str,
        db: AsyncSession,
        current_user: dict[str, Any],
        top_k: int = 3,  # Weniger Papers = schneller
        language: str = "de",
    ) -> RAGResponse:
        """Vollständiger RAG-Ablauf.

        1. Embedding der Frage
        2. Top-K ähnliche Papers via pgvector
        3. Kontext aus Titeln + Abstracts aufbauen (max MAX_CONTEXT_CHARS)
        4. LLM mit Kontext + Frage aufrufen
        5. Antwort + Quellen zurückgeben
        """
        question = (question or "").strip()
        if not question:
            raise ValueError("question must not be empty")
        question = sanitize_for_llm(question)

        scope = get_scope_filter(current_user)
        user_id = scope.get("user_id") if scope else None
        team_id = scope.get("team_id") if scope else None

        try:
            papers = await self._embedding.find_similar(
                db,
                question,
                limit=top_k,
                threshold=1.5,
                user_id=user_id,
                team_id=team_id,
            )
        except EmbeddingServiceError as e:
            logger.warning("RAG find_similar failed: %s", e)
            raise

        if not papers:
            raise ValueError(
                "Keine Papers mit Embeddings gefunden. "
                "Bitte erst Papers speichern und ggf. /library/reembed-all aufrufen."
            )

        context_parts: list[str] = []
        sources_with_used: list[tuple[Any, int]] = []
        total_chars = 0

        for i, paper in enumerate(papers, 1):
            title = sanitize_for_llm((paper.title or "").strip() or "Ohne Titel")
            abstract = sanitize_for_llm((paper.abstract or "").strip() or "")
            header = f"Paper [{i}]: {title}\n"
            block = header + abstract
            block_len = len(block)

            if total_chars + block_len <= MAX_CONTEXT_CHARS:
                context_parts.append(block)
                sources_with_used.append((paper, len(abstract)))
                total_chars += block_len
            else:
                remaining = MAX_CONTEXT_CHARS - total_chars
                if remaining > len(header) + 50:
                    trunc_block = block[:remaining].rsplit("\n", 1)[0]
                    if len(trunc_block) < len(header):
                        trunc_block = block[:remaining]
                    context_parts.append(trunc_block + "\n[...]")
                    abstract_in_block = max(0, len(trunc_block) - len(header))
                    sources_with_used.append((paper, min(len(abstract), abstract_in_block)))
                    total_chars = MAX_CONTEXT_CHARS
                break

        context = "\n\n".join(context_parts)
        if not context.strip():
            raise ValueError("Kontext leer nach Aufbau.")

        try:
            answer_text = await self._llm.rag_answer(
                question=question,
                context=context,
                language=language or "de",
            )
        except LLMServiceError as e:
            logger.warning("RAG LLM call failed: %s", e)
            raise

        settings = get_settings()
        model_used = settings.effective_llm_model_label()

        sources = [
            RAGSource(
                pmid=p.pmid,
                title=(p.title or "").strip() or p.pmid,
                similarity_score=float(getattr(p, "_similarity_score", 0.0) or 0.0),
                used_chars=used,
            )
            for (p, used) in sources_with_used
        ]

        return RAGResponse(
            answer=answer_text,
            sources=sources,
            question=question,
            model_used=model_used or "unknown",
            context_papers=len(sources),
        )
