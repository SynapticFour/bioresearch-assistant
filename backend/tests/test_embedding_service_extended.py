"""Extended tests for EmbeddingService (_preprocess_query, find_similar, store_paper)."""

from unittest.mock import MagicMock, patch

import pytest

from app.models.paper import EMBEDDING_DIM
from app.schemas.pubmed import PubMedArticle
from app.services.embedding_service import (
    EmbeddingService,
    _preprocess_query,
)

# ─── _preprocess_query (module-level) ──────────────────────────────────────


def test_preprocess_query_removes_german_stopwords():
    """German stopwords are removed, keywords kept."""
    result = _preprocess_query("Zeige mir alle Papers für BRCA1")
    assert "Zeige" not in result
    assert "mir" not in result
    assert "BRCA1" in result


def test_preprocess_query_keeps_keywords():
    """English keywords are kept."""
    result = _preprocess_query("show me papers about breast cancer therapy")
    assert "breast" in result
    assert "cancer" in result
    assert "therapy" in result


def test_preprocess_query_empty_returns_empty():
    """Empty string returns empty string (then caller uses original)."""
    result = _preprocess_query("")
    assert result == ""


def test_preprocess_query_none_returns_empty():
    """None-like returns empty."""
    result = _preprocess_query(None)
    assert result == ""


def test_preprocess_query_all_stopwords_returns_original():
    """When only stopwords, result is original query (fallback)."""
    result = _preprocess_query("und oder mit")
    # After stripping stopwords, remainder may be empty so fallback to original
    assert "und" in result or result == "und oder mit"


def test_preprocess_query_short_words_filtered():
    """Words with len <= 2 are filtered (except in fallback)."""
    result = _preprocess_query("ab CD ef GH ij")
    # Only words > 2 chars kept for keywords
    assert "CD" not in result or result == "ab CD ef GH ij"


# ─── embed_text / embed_text_async (multilingual) ──────────────────────────


def test_embed_text_multilingual_de():
    """embed_text accepts German text (mock returns vector)."""
    with patch("app.services.embedding_service.EmbeddingService._get_model") as mock_get:
        mock_model = MagicMock()
        mock_encode = MagicMock()
        mock_encode.tolist.return_value = [0.2] * EMBEDDING_DIM
        mock_model.encode.return_value = mock_encode
        mock_get.return_value = mock_model
        svc = EmbeddingService()
        out = svc.embed_text("BRCA1 Mutation und Therapie")
        assert len(out) == EMBEDDING_DIM
        mock_model.encode.assert_called_once()


def test_embed_text_multilingual_en():
    """embed_text accepts English text."""
    with patch("app.services.embedding_service.EmbeddingService._get_model") as mock_get:
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.3] * EMBEDDING_DIM)
        mock_get.return_value = mock_model
        svc = EmbeddingService()
        out = svc.embed_text("breast cancer therapy")
        assert len(out) == EMBEDDING_DIM


# ─── find_similar (with threshold, scores, empty DB) ────────────────────────


@pytest.mark.asyncio
async def test_find_similar_empty_db_returns_empty(db_session):
    """find_similar with no papers in DB returns empty list."""
    with patch("app.services.embedding_service.EmbeddingService._get_model") as mock_get:
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * EMBEDDING_DIM)
        mock_get.return_value = mock_model
        svc = EmbeddingService()
        result = await svc.find_similar(db_session, "query", limit=10)
        assert result == []


# ─── store_paper / reembed ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_store_paper_generates_embedding(db_session):
    """store_paper generates embedding via embed_text_async."""
    with patch("app.services.embedding_service.EmbeddingService._get_model") as mock_get:
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * EMBEDDING_DIM)
        mock_get.return_value = mock_model
        svc = EmbeddingService()
        article = PubMedArticle(
            pmid="77777",
            title="Test",
            abstract="Abstract text",
            authors=[],
            year=2024,
            journal="J",
            doi=None,
        )
        paper = await svc.store_paper(db_session, article)
        assert paper.pmid == "77777"
        assert paper.embedding is not None
        assert len(paper.embedding) == EMBEDDING_DIM


@pytest.mark.asyncio
async def test_reembed_updates_existing_paper(db_session):
    """Re-embedding updates existing paper's embedding."""
    with patch("app.services.embedding_service.EmbeddingService._get_model") as mock_get:
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.5] * EMBEDDING_DIM)
        mock_get.return_value = mock_model
        svc = EmbeddingService()
        article = PubMedArticle(
            pmid="66666",
            title="First",
            abstract="First abstract",
            authors=[],
            year=2023,
            journal="J1",
            doi=None,
        )
        p1 = await svc.store_paper(db_session, article)
        article2 = PubMedArticle(
            pmid="66666",
            title="First",
            abstract="Updated abstract",
            authors=[],
            year=2023,
            journal="J1",
            doi=None,
        )
        p2 = await svc.store_paper(db_session, article2)
        assert p2.pmid == p1.pmid
        assert p2.abstract == "Updated abstract"
        assert p2.embedding is not None
