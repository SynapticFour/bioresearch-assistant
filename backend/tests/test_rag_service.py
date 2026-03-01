"""Tests for RAG service and notebook AI assist with linked papers. All external calls mocked."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.rag import RAGResponse
from app.services.llm_service import LLMService, LLMServiceError
from app.services.rag_service import MAX_CONTEXT_CHARS, RAGService


def _make_mock_paper(pmid: str, title: str, abstract: str, score: float = 85.0) -> MagicMock:
    """Create a minimal Paper-like object with _similarity_score."""
    p = MagicMock()
    p.pmid = pmid
    p.title = title
    p.abstract = abstract
    p._similarity_score = score
    return p


@pytest.fixture
def mock_db():
    """AsyncSession mock."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def current_user():
    return {"sub": "user-1"}


# --- RAGService.answer ---


@pytest.mark.asyncio
async def test_rag_no_papers(mock_db, current_user):
    """When find_similar returns no papers, RAGService.answer raises ValueError (→ 404)."""
    embedding = MagicMock()
    embedding.find_similar = AsyncMock(return_value=[])
    llm = MagicMock()
    service = RAGService(embedding_service=embedding, llm_service=llm)

    with pytest.raises(ValueError) as exc_info:
        await service.answer("Was sind Nebenwirkungen?", db=mock_db, current_user=current_user)

    assert "Keine Papers" in str(exc_info.value)
    embedding.find_similar.assert_called_once()
    llm.rag_answer.assert_not_called()


@pytest.mark.asyncio
async def test_rag_success(mock_db, current_user):
    """RAG returns answer and sources when papers and LLM succeed."""
    papers = [
        _make_mock_paper("123", "Metformin side effects", "Abstract about metformin.", 94.0),
        _make_mock_paper("456", "Type 2 diabetes therapy", "Abstract about diabetes.", 71.0),
    ]
    embedding = MagicMock()
    embedding.find_similar = AsyncMock(return_value=papers)
    llm = MagicMock()
    llm.rag_answer = AsyncMock(
        return_value="In deinen Papers werden folgende Nebenwirkungen beschrieben: ..."
    )
    service = RAGService(embedding_service=embedding, llm_service=llm)

    result = await service.answer(
        question="Welche Nebenwirkungen von Metformin?",
        db=mock_db,
        current_user=current_user,
        top_k=5,
        language="de",
    )

    assert isinstance(result, RAGResponse)
    assert "Nebenwirkungen" in result.answer
    assert result.question == "Welche Nebenwirkungen von Metformin?"
    assert result.context_papers == 2
    assert len(result.sources) == 2
    assert result.sources[0].pmid == "123"
    assert result.sources[0].similarity_score == 94.0
    assert result.sources[1].pmid == "456"
    llm.rag_answer.assert_called_once()
    call_kw = llm.rag_answer.call_args[1]
    assert call_kw["language"] == "de"
    assert "Paper [1]:" in call_kw["context"]
    assert "Metformin" in call_kw["context"]


@pytest.mark.asyncio
async def test_rag_llm_unavailable(mock_db, current_user):
    """When LLM raises LLMServiceError, RAGService.answer propagates it (→ 502)."""
    papers = [_make_mock_paper("1", "Title", "Abstract", 90.0)]
    embedding = MagicMock()
    embedding.find_similar = AsyncMock(return_value=papers)
    llm = MagicMock()
    llm.rag_answer = AsyncMock(side_effect=LLMServiceError("Ollama unreachable"))
    service = RAGService(embedding_service=embedding, llm_service=llm)

    with pytest.raises(LLMServiceError) as exc_info:
        await service.answer("Frage?", db=mock_db, current_user=current_user)

    assert "Ollama" in str(exc_info.value) or "unreachable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rag_context_truncation(mock_db, current_user):
    """Context passed to LLM is limited to MAX_CONTEXT_CHARS."""
    long_abstract = "A" * 5000
    papers = [
        _make_mock_paper("1", "First", long_abstract, 99.0),
        _make_mock_paper("2", "Second", long_abstract, 80.0),
    ]
    embedding = MagicMock()
    embedding.find_similar = AsyncMock(return_value=papers)
    llm = MagicMock()
    llm.rag_answer = AsyncMock(return_value="Short answer.")
    service = RAGService(embedding_service=embedding, llm_service=llm)

    await service.answer(
        question="Summarize?",
        db=mock_db,
        current_user=current_user,
        top_k=10,
    )

    call_kw = llm.rag_answer.call_args[1]
    context = call_kw["context"]
    assert len(context) <= MAX_CONTEXT_CHARS + 100  # allow small overshoot for boundary


@pytest.mark.asyncio
async def test_rag_sources_ordered_by_similarity(mock_db, current_user):
    """Sources list order matches find_similar order (most similar first)."""
    papers = [
        _make_mock_paper("a", "A", "Abs", 95.0),
        _make_mock_paper("b", "B", "Abs", 70.0),
        _make_mock_paper("c", "C", "Abs", 60.0),
    ]
    embedding = MagicMock()
    embedding.find_similar = AsyncMock(return_value=papers)
    llm = MagicMock()
    llm.rag_answer = AsyncMock(return_value="Answer")
    service = RAGService(embedding_service=embedding, llm_service=llm)

    result = await service.answer("Q?", db=mock_db, current_user=current_user, top_k=3)

    assert [s.pmid for s in result.sources] == ["a", "b", "c"]
    assert [s.similarity_score for s in result.sources] == [95.0, 70.0, 60.0]


@pytest.mark.asyncio
async def test_rag_language_de(mock_db, current_user):
    """language=de is passed to rag_answer."""
    papers = [_make_mock_paper("1", "T", "A", 80.0)]
    embedding = MagicMock()
    embedding.find_similar = AsyncMock(return_value=papers)
    llm = MagicMock()
    llm.rag_answer = AsyncMock(return_value="Antwort auf Deutsch.")
    service = RAGService(embedding_service=embedding, llm_service=llm)

    await service.answer("Frage?", db=mock_db, current_user=current_user, language="de")

    llm.rag_answer.assert_called_once()
    assert llm.rag_answer.call_args[1]["language"] == "de"


@pytest.mark.asyncio
async def test_rag_language_en(mock_db, current_user):
    """language=en is passed to rag_answer."""
    papers = [_make_mock_paper("1", "T", "A", 80.0)]
    embedding = MagicMock()
    embedding.find_similar = AsyncMock(return_value=papers)
    llm = MagicMock()
    llm.rag_answer = AsyncMock(return_value="Answer in English.")
    service = RAGService(embedding_service=embedding, llm_service=llm)

    await service.answer("Question?", db=mock_db, current_user=current_user, language="en")

    llm.rag_answer.assert_called_once()
    assert llm.rag_answer.call_args[1]["language"] == "en"


# --- LLMService.notebook_ai_assist with linked_context ---


@pytest.mark.asyncio
async def test_notebook_ai_assist_with_linked_papers(mocker):
    """notebook_ai_assist includes linked_context in the prompt when provided."""
    mock_complete = AsyncMock(return_value="Summary and next steps.")
    mocker.patch.object(LLMService, "_complete", mock_complete)
    service = LLMService()

    summary, next_steps = await service.notebook_ai_assist(
        content="Today we tested BRCA1.",
        mode="both",
        linked_context="Paper: BRCA1 and cancer.\nAbstract: This paper describes BRCA1.",
    )

    assert summary is not None
    assert next_steps is not None
    assert mock_complete.call_count >= 1
    for call in mock_complete.call_args_list:
        user = call.kwargs.get("user", call.args[1] if len(call.args) > 1 else "")
        if "Paper:" in (user or "") or "BRCA1 and cancer" in (user or ""):
            break
    else:
        pytest.fail("linked_context (Paper: / BRCA1) not found in any _complete user prompt")


@pytest.mark.asyncio
async def test_notebook_ai_assist_without_linked_papers(mocker):
    """notebook_ai_assist works with empty linked_context."""
    mocker.patch("app.services.llm_service.LLMService._complete", new_callable=AsyncMock)
    service = LLMService()
    service._complete = AsyncMock(return_value="Summary.")

    summary, next_steps = await service.notebook_ai_assist(
        content="Lab notes here.",
        mode="summary",
        linked_context="",
    )

    assert summary == "Summary."
    assert next_steps is None
    service._complete.assert_called()
    call_kw = service._complete.call_args[1]
    assert "Lab notes here" in (call_kw.get("user") or "")
