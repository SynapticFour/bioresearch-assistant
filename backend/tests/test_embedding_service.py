"""Tests for EmbeddingService (sentence-transformers + pgvector)."""

from unittest.mock import MagicMock

import pytest

from app.models.paper import EMBEDDING_DIM, Paper
from app.schemas.pubmed import PubMedArticle
from app.services.embedding_service import EmbeddingService


@pytest.fixture
def mock_embedding_model(mocker):
    """Mock SentenceTransformer at source; encode returns EMBEDDING_DIM vector with .tolist()."""
    mock_model = MagicMock()
    mock_encode_result = MagicMock()
    mock_encode_result.tolist.return_value = [0.1] * EMBEDDING_DIM
    mock_model.encode.return_value = mock_encode_result
    mocker.patch(
        "sentence_transformers.SentenceTransformer",
        return_value=mock_model,
    )
    return mock_model


@pytest.fixture
def embedding_service(mock_embedding_model):
    """EmbeddingService with mocked model."""
    return EmbeddingService()


def test_embed_text_returns_vector_of_correct_length(mock_embedding_model):
    """embed_text returns a list of length EMBEDDING_DIM (768)."""
    service = EmbeddingService()
    result = service.embed_text("Some text to embed.")
    assert len(result) == EMBEDDING_DIM
    assert all(x == 0.1 for x in result)


def test_embed_text_empty_string_returns_vector(mock_embedding_model):
    """Empty string still returns a vector (zeros) after loading model."""
    service = EmbeddingService()
    result = service.embed_text("")
    assert len(result) == EMBEDDING_DIM
    assert all(x == 0.0 for x in result)


@pytest.mark.asyncio
async def test_find_similar_returns_ranked_results(
    mock_embedding_model, db_session, embedding_service
):
    """find_similar returns papers ordered by cosine distance."""
    vec = [0.1] * EMBEDDING_DIM
    paper = Paper(
        pmid="12345",
        title="Test",
        abstract="Abstract",
        authors=[],
        embedding=vec,
    )
    db_session.add(paper)
    await db_session.flush()

    results = await embedding_service.find_similar(db_session, "query", limit=10)
    assert len(results) <= 10
    if results:
        assert results[0].pmid == "12345"


@pytest.mark.asyncio
async def test_find_similar_limit_zero_returns_empty(
    mock_embedding_model, db_session, embedding_service
):
    """find_similar with limit=0 returns empty list."""
    results = await embedding_service.find_similar(db_session, "query", limit=0)
    assert results == []


@pytest.mark.asyncio
async def test_store_paper_saves_with_embedding(
    mock_embedding_model, db_session, embedding_service
):
    """store_paper persists a paper with its abstract embedding."""
    article = PubMedArticle(
        pmid="99999",
        title="Test Paper",
        abstract="This is the abstract.",
        authors=["Author A"],
        year=2024,
        journal="Test Journal",
    )
    paper = await embedding_service.store_paper(db_session, article)
    assert paper.pmid == "99999"
    assert paper.title == "Test Paper"
    assert paper.embedding is not None
    assert len(paper.embedding) == EMBEDDING_DIM

    article2 = PubMedArticle(
        pmid="99999",
        title="Updated Title",
        abstract="Updated abstract.",
        authors=[],
    )
    paper2 = await embedding_service.store_paper(db_session, article2)
    assert paper2.pmid == "99999"
    assert paper2.title == "Updated Title"


@pytest.mark.asyncio
async def test_store_paper_without_abstract_uses_title(mock_embedding_model, db_session):
    """store_paper uses title when abstract is empty."""
    service = EmbeddingService()
    article = PubMedArticle(
        pmid="88888",
        title="Title only",
        abstract="",
        authors=[],
    )
    paper = await service.store_paper(db_session, article)
    assert paper.pmid == "88888"
    assert paper.embedding is not None


@pytest.mark.asyncio
async def test_store_paper_same_pmid_does_not_steal_ownership(
    mock_embedding_model, db_session, embedding_service
):
    """Two users may store the same PMID; upsert must not overwrite the other row."""
    article = PubMedArticle(
        pmid="55555",
        title="Shared PMID",
        abstract="Abstract",
        authors=["A"],
        year=2024,
        journal="J",
    )
    a = await embedding_service.store_paper(db_session, article, user_id="user-a", team_id="t-a")
    b = await embedding_service.store_paper(db_session, article, user_id="user-b", team_id="t-b")
    assert a.id != b.id
    assert a.user_id == "user-a"
    assert b.user_id == "user-b"

    updated = PubMedArticle(
        pmid="55555",
        title="User A update",
        abstract="New abstract",
        authors=["A"],
    )
    a2 = await embedding_service.store_paper(db_session, updated, user_id="user-a")
    assert a2.id == a.id
    assert a2.title == "User A update"
    await db_session.refresh(b)
    assert b.title == "Shared PMID"
    assert b.user_id == "user-b"
