"""Embedding service using sentence-transformers (local) and pgvector for similarity search."""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import EMBEDDING_DIM, Paper
from app.schemas.pubmed import PubMedArticle

logger = logging.getLogger(__name__)

# Multilingual — versteht DE + EN + 50 andere Sprachen
SENTENCE_TRANSFORMER_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

GERMAN_STOPWORDS = frozenset(
    [
        "zeige",
        "mir",
        "alle",
        "papers",
        "für",
        "über",
        "zu",
        "mit",
        "von",
        "und",
        "oder",
        "die",
        "der",
        "das",
        "eine",
        "ein",
        "ist",
        "sind",
        "hat",
        "haben",
        "zum",
        "zur",
        "im",
        "in",
        "an",
        "auf",
        "bei",
        "nach",
        "ich",
        "möchte",
        "suche",
        "finde",
        "liste",
        "zeig",
        "bitte",
        "alles",
        "was",
        "related",
        "show",
        "me",
        "find",
        "all",
        "about",
        "with",
    ]
)


def _preprocess_query(query: str) -> str:
    """Extract keywords from natural language query.

    Removes German/English stopwords and command
    phrases to get clean keywords for embedding.

    Example:
        "Zeige mir alle Papers für BRCA1"
        → "BRCA1"

        "show me papers about breast cancer therapy"
        → "breast cancer therapy"
    """
    words = (query or "").split()
    keywords = [w for w in words if w.lower().strip(".,!?") not in GERMAN_STOPWORDS and len(w) > 2]
    result = " ".join(keywords).strip()
    return result if result else (query or "")


class EmbeddingServiceError(Exception):
    """Raised when embedding or DB operations fail."""

    pass


class EmbeddingService:
    """Local embeddings via sentence-transformers and paper storage with pgvector."""

    def __init__(self, model_name: str = SENTENCE_TRANSFORMER_MODEL) -> None:
        """Initialize; model is loaded lazily on first embed_text call."""
        self._model_name = model_name
        self._model: object | None = None

    def _get_model(self) -> object:
        """Load and cache the sentence-transformers model (sync, run in executor)."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self._model_name)
                logger.info(
                    "Embedding model: %s — multilingual (DE/EN/50+ languages)",
                    self._model_name,
                )
            except ImportError as e:
                raise EmbeddingServiceError(
                    "sentence-transformers not installed; pip install sentence-transformers"
                ) from e
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """Compute embedding for a single text (blocking; run in executor from async code).

        Uses paraphrase-multilingual-mpnet-base-v2; output dimension is EMBEDDING_DIM (768).

        Args:
            text: Input text (e.g. abstract or search query).

        Returns:
            List of EMBEDDING_DIM (768) floats (normalized vector).

        Raises:
            EmbeddingServiceError: On model load or encode failure.
        """
        text = (text or "").strip()
        if not text:
            model = self._get_model()
            # Empty string can produce zeros or a default vector; return zeros to match dim
            return [0.0] * EMBEDDING_DIM
        try:
            model = self._get_model()
            embedding = model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.warning("Embedding encode error: %s", e)
            raise EmbeddingServiceError(f"Embedding failed: {e}") from e

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Batch-embed texts (blocking; run in executor from async code)."""
        model = self._get_model()
        cleaned = [(t or "").strip() or " " for t in texts]
        try:
            embeddings = model.encode(cleaned, normalize_embeddings=True, batch_size=32)
            return [row.tolist() for row in embeddings]
        except Exception as e:
            logger.warning("Embedding batch encode error: %s", e)
            raise EmbeddingServiceError(f"Embedding failed: {e}") from e

    async def embed_text_async(self, text: str) -> list[float]:
        """Async wrapper: run embed_text in thread pool to avoid blocking."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.embed_text, text)

    async def embed_texts_async(self, texts: list[str]) -> list[list[float]]:
        """Async wrapper for batch encode."""
        if not texts:
            return []
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.embed_texts, texts)

    async def store_paper(
        self,
        db: AsyncSession,
        paper: PubMedArticle,
        *,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> Paper:
        """Store a paper and its abstract embedding; upsert by (pmid, user_id).

        Args:
            db: Async SQLAlchemy session.
            paper: PubMed article to store.
            user_id: Optional user id for isolation.
            team_id: Optional team id for isolation.

        Returns:
            Paper instance (persisted, with embedding).

        Raises:
            EmbeddingServiceError: On embedding or DB error.
        """
        text_to_embed = (paper.abstract or paper.title or "").strip() or " "
        embedding = await self.embed_text_async(text_to_embed)
        authors_list = list(paper.authors) if paper.authors else []

        stmt = select(Paper).where(Paper.pmid == paper.pmid)
        if user_id is not None:
            stmt = stmt.where(Paper.user_id == user_id)
        else:
            stmt = stmt.where(Paper.user_id.is_(None))
        result = await db.execute(stmt)
        existing = result.scalars().first()
        if existing:
            existing.title = paper.title or ""
            existing.abstract = paper.abstract or ""
            existing.authors = authors_list
            existing.year = str(paper.year) if paper.year is not None else None
            existing.journal = paper.journal or ""
            existing.doi = paper.doi
            if paper.summary is not None:
                existing.summary = paper.summary
            if paper.summary_language is not None:
                existing.summary_language = paper.summary_language
            if paper.summary_model is not None:
                existing.summary_model = paper.summary_model
            if embedding is not None:
                existing.embedding = embedding
            else:
                existing.embedding = None  # NULL when embeddings unavailable
            await db.flush()
            await db.refresh(existing)
            return existing

        new_paper = Paper(
            pmid=paper.pmid,
            title=paper.title or "",
            abstract=paper.abstract or "",
            authors=authors_list,
            year=str(paper.year) if paper.year is not None else None,
            journal=paper.journal or "",
            doi=paper.doi,
            embedding=embedding if embedding is not None else None,  # NULL when unavailable
            user_id=user_id,
            team_id=team_id,
            summary=paper.summary,
            summary_language=paper.summary_language,
            summary_model=paper.summary_model,
        )
        db.add(new_paper)
        await db.flush()
        await db.refresh(new_paper)
        return new_paper

    async def find_similar(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 10,
        *,
        threshold: float | None = None,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> list[Paper]:
        """Return papers most similar to the query (cosine similarity via pgvector).

        Args:
            db: Async SQLAlchemy session.
            query: Search query text.
            limit: Maximum number of papers to return.
            threshold: Optional max cosine distance (0=same, 2=opposite). Only return
                papers with distance <= threshold. None = no filter.
            user_id: Optional scope filter (isolation).
            team_id: Optional scope filter (isolation).

        Returns:
            List of Paper ordered by cosine similarity (most similar first).

        Raises:
            EmbeddingServiceError: On embedding failure.
        """
        if limit <= 0:
            return []
        processed_query = _preprocess_query(query or "")
        query_embedding = await self.embed_text_async(processed_query)
        bind = db.get_bind()
        dialect = bind.dialect.name if bind is not None else "postgresql"
        if dialect == "sqlite":
            return await self._find_similar_sqlite(
                db,
                query_embedding,
                limit,
                threshold=threshold,
                user_id=user_id,
                team_id=team_id,
            )
        distance_expr = Paper.embedding.cosine_distance(query_embedding)
        stmt = select(Paper, distance_expr.label("distance")).where(Paper.embedding.isnot(None))
        if user_id is not None:
            stmt = stmt.where(Paper.user_id == user_id)
        if team_id is not None:
            stmt = stmt.where(Paper.team_id == team_id)
        if threshold is not None:
            stmt = stmt.where(distance_expr <= threshold)
        stmt = stmt.order_by(distance_expr).limit(limit)
        result = await db.execute(stmt)
        rows = result.all()
        papers_with_scores = []
        for paper, distance in rows:
            score = max(0.0, 1.0 - (float(distance) / 2.0))
            paper._similarity_score = round(score * 100, 1)
            papers_with_scores.append(paper)
        return papers_with_scores

    async def _find_similar_sqlite(
        self,
        db: AsyncSession,
        query_embedding: list[float],
        limit: int,
        *,
        threshold: float | None,
        user_id: str | None,
        team_id: str | None,
    ) -> list[Paper]:
        """Cosine ranking without pgvector (tests / SQLite)."""
        stmt = select(Paper).where(Paper.embedding.isnot(None))
        if user_id is not None:
            stmt = stmt.where(Paper.user_id == user_id)
        if team_id is not None:
            stmt = stmt.where(Paper.team_id == team_id)
        result = await db.execute(stmt)
        scored: list[tuple[float, Paper]] = []
        for paper in result.scalars().all():
            emb = paper.embedding
            if not isinstance(emb, list) or len(emb) != len(query_embedding):
                continue
            dot = sum(a * b for a, b in zip(query_embedding, emb, strict=True))
            distance = 1.0 - float(dot)
            if threshold is not None and distance > threshold:
                continue
            score = max(0.0, 1.0 - (distance / 2.0))
            paper._similarity_score = round(score * 100, 1)
            scored.append((distance, paper))
        scored.sort(key=lambda item: item[0])
        return [paper for _, paper in scored[:limit]]


_embedding_singleton: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Return the process embedding service (Railway stub when DEPLOYMENT=railway)."""
    global _embedding_singleton
    if _embedding_singleton is None:
        from app.core.config import get_settings

        if (get_settings().deployment or "").strip().lower() == "railway":
            from app.services.embedding_service_railway import (
                EmbeddingService as RailwayEmbeddingService,
            )

            _embedding_singleton = RailwayEmbeddingService()
        else:
            _embedding_singleton = EmbeddingService()
    return _embedding_singleton


def reset_embedding_service() -> None:
    """Drop cached embedding service (tests)."""
    global _embedding_singleton
    _embedding_singleton = None
