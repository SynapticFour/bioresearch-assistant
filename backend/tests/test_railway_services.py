"""Tests for Railway-stub services (embedding_service_railway, pseudonymization_service_railway)."""

import pytest

from app.schemas.pubmed import PubMedArticle


# ─── EmbeddingService (Railway) ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_railway_embed_returns_none(db_session):
    """Railway EmbeddingService.embed_text returns None."""
    from app.services.embedding_service_railway import EmbeddingService

    svc = EmbeddingService()
    assert svc.embed_text("some text") is None


@pytest.mark.asyncio
async def test_railway_embed_async_returns_none(db_session):
    """Railway EmbeddingService.embed_text_async returns None."""
    from app.services.embedding_service_railway import EmbeddingService

    svc = EmbeddingService()
    out = await svc.embed_text_async("some text")
    assert out is None


@pytest.mark.asyncio
async def test_railway_find_similar_returns_empty(db_session):
    """Railway EmbeddingService.find_similar returns empty list."""
    from app.services.embedding_service_railway import EmbeddingService

    svc = EmbeddingService()
    result = await svc.find_similar(db_session, "query", limit=10)
    assert result == []


@pytest.mark.asyncio
async def test_railway_store_paper_no_embedding(db_session):
    """Railway store_paper stores paper with embedding=None."""
    from app.models.paper import Paper
    from app.services.embedding_service_railway import EmbeddingService

    svc = EmbeddingService()
    paper = PubMedArticle(
        pmid="99999",
        title="Railway Test",
        abstract="No embedding.",
        authors=[],
        year=2024,
        journal="Test",
        doi=None,
    )
    created = await svc.store_paper(db_session, paper, user_id="u1")
    assert created.pmid == "99999"
    assert created.title == "Railway Test"
    assert created.embedding is None


# ─── Pseudonymization (Railway) ──────────────────────────────────────────────


def test_railway_pseudonymize_basic():
    """Railway pseudonymize (regex-only) replaces email/phone/date."""
    from app.services.pseudonymization_service_railway import pseudonymize

    text = "Contact: max@example.com or 0123-456789."
    result = pseudonymize(text, language="de")
    assert "pseudonymized_text" in result
    assert "max@example.com" not in result.get("pseudonymized_text", "")
    assert result.get("entities_found")


def test_railway_pseudonymize_no_entities():
    """Railway pseudonymize returns original text when no PII."""
    from app.services.pseudonymization_service_railway import pseudonymize

    text = "Only normal text without PII."
    result = pseudonymize(text, language="de")
    assert result["pseudonymized_text"] == text
    assert result["entities_found"] == []
    assert result["plain_mapping"] == {}
    assert result["mapping_id"] is None


def test_railway_analyze_returns_entities():
    """Railway pseudonymize returns entities_found (analyze shape)."""
    from app.services.pseudonymization_service_railway import pseudonymize

    text = "Patient 01.02.1990 and test@mail.de"
    result = pseudonymize(text)
    assert "entities_found" in result
    assert len(result["entities_found"]) >= 1
    assert "encrypted_mapping_bytes" in result


def test_railway_restore_roundtrip():
    """Railway restore reverses pseudonymize when mapping given."""
    from app.services.pseudonymization_service_railway import (
        pseudonymize,
        restore,
    )

    text = "Email: a@b.de"
    out = pseudonymize(text)
    if out.get("encrypted_mapping_bytes"):
        restored = restore(
            out["pseudonymized_text"],
            out["encrypted_mapping_bytes"],
        )
        assert "a@b.de" in restored
