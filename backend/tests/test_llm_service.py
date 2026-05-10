"""Tests for LLMService (Claude / Ollama). All external API calls are mocked."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.llm import BiologicalEntities, PaperSummary
from app.services.llm_service import LLMService


@pytest.fixture
def mock_settings(mocker):
    """Patch get_settings at source (app.core.config)."""
    settings = MagicMock()
    settings.anthropic_api_key = "sk-test-key"
    settings.ollama_base_url = "http://localhost:11434"
    settings.llm_claude_model = "claude-sonnet-4-6"
    settings.ollama_model = "mistral:7b"
    settings.openai_api_base = ""
    settings.openai_model = ""
    settings.openai_api_key = None
    settings.resolved_llm_backend = MagicMock(return_value="anthropic")
    mocker.patch("app.core.config.get_settings", return_value=settings)
    return settings


@pytest.fixture
def mock_settings_no_key(mocker):
    """Settings without API key (use Ollama)."""
    settings = MagicMock()
    settings.anthropic_api_key = None
    settings.ollama_base_url = "http://localhost:11434"
    settings.llm_claude_model = "claude-sonnet-4-6"
    settings.ollama_model = "mistral:7b"
    settings.openai_api_base = ""
    settings.openai_model = ""
    settings.openai_api_key = None
    settings.resolved_llm_backend = MagicMock(return_value="ollama")
    mocker.patch("app.core.config.get_settings", return_value=settings)
    return settings


@pytest.fixture
def mock_anthropic_client(mocker):
    """Mock AsyncAnthropic so messages.create returns a summary (async)."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=(
                '{"summary": "This paper investigates BRCA1 mutations.", '
                '"key_findings": ["BRCA1"], "methods": ["PCR"], "relevance_score": null}'
            )
        )
    ]
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    mocker.patch("anthropic.AsyncAnthropic", return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_ollama(mocker):
    """Mock httpx.AsyncClient for Ollama fallback."""
    mock_client = mocker.patch("app.services.llm_service.httpx.AsyncClient")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "content": (
                '{"summary": "Summary of the paper.", "key_findings": [], '
                '"methods": [], "relevance_score": null}'
            )
        }
    }
    mock_client.return_value.post = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.mark.asyncio
async def test_summarize_paper_returns_summary(mock_anthropic_client, mock_settings):
    """summarize_paper returns a PaperSummary when Claude returns valid JSON."""
    service = LLMService()
    result = await service.summarize_paper(abstract="We studied BRCA1 in breast cancer.")
    assert isinstance(result, PaperSummary)
    assert "BRCA1" in result.summary
    assert result.key_findings == ["BRCA1"]
    assert result.methods == ["PCR"]
    assert result.relevance_score is None


@pytest.mark.asyncio
async def test_summarize_paper_with_context_includes_relevance(
    mock_anthropic_client, mock_settings
):
    """When context is provided, relevance_score is parsed and clamped 0-1."""
    mock_anthropic_client.messages.create = AsyncMock(
        return_value=MagicMock(
            content=[
                MagicMock(
                    text=(
                        '{"summary": "Relevant.", "key_findings": [], '
                        '"methods": [], "relevance_score": 0.85}'
                    )
                )
            ]
        )
    )
    service = LLMService()
    result = await service.summarize_paper(
        abstract="BRCA1 mutations.",
        context="Breast cancer genetics",
    )
    assert result.relevance_score == 0.85


@pytest.mark.asyncio
async def test_summarize_paper_falls_back_to_ollama_when_no_api_key(
    mock_ollama, mock_settings_no_key
):
    """When no Anthropic API key, Ollama is used and response is parsed."""
    service = LLMService()
    result = await service.summarize_paper(abstract="Some abstract.")
    assert isinstance(result, PaperSummary)
    assert "Summary of the paper" in result.summary


@pytest.mark.asyncio
async def test_summarize_paper_openai_compatible(mocker, mock_ollama):
    """When LLM_PROVIDER routes to openai_compatible, POST /v1/chat/completions is used."""
    settings = MagicMock()
    settings.anthropic_api_key = None
    settings.ollama_base_url = "http://localhost:11434"
    settings.llm_claude_model = "claude-sonnet-4-6"
    settings.ollama_model = "mistral:7b"
    settings.openai_api_base = "http://localhost:30000/v1"
    settings.openai_model = "MiniMaxAI/MiniMax-M2"
    settings.openai_api_key = ""
    settings.resolved_llm_backend = MagicMock(return_value="openai_compatible")
    mocker.patch("app.core.config.get_settings", return_value=settings)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"summary": "OpenAI-compatible summary.", '
                        '"key_findings": [], "methods": [], "relevance_score": null}'
                    )
                }
            }
        ]
    }
    mock_ollama.return_value.post = AsyncMock(return_value=mock_response)

    service = LLMService()
    result = await service.summarize_paper(abstract="Some abstract text for testing.")
    assert isinstance(result, PaperSummary)
    assert "OpenAI-compatible" in result.summary
    post_url = mock_ollama.return_value.post.call_args[0][0]
    assert post_url == "http://localhost:30000/v1/chat/completions"


@pytest.mark.asyncio
async def test_extract_entities_returns_genes_and_diseases(mock_anthropic_client, mock_settings):
    """extract_entities returns BiologicalEntities with genes and diseases."""
    mock_anthropic_client.messages.create = AsyncMock(
        return_value=MagicMock(
            content=[
                MagicMock(
                    text=(
                        '{"genes": ["BRCA1", "TP53"], "proteins": [], '
                        '"diseases": ["Breast cancer"], "organisms": [], "chemicals": []}'
                    )
                )
            ]
        )
    )
    service = LLMService()
    result = await service.extract_entities("BRCA1 and TP53 are linked to breast cancer.")
    assert isinstance(result, BiologicalEntities)
    assert result.genes == ["BRCA1", "TP53"]
    assert result.diseases == ["Breast cancer"]


@pytest.mark.asyncio
async def test_generate_overview_combines_summaries(mock_anthropic_client, mock_settings):
    """generate_research_overview returns a single overview string."""
    mock_anthropic_client.messages.create = AsyncMock(
        return_value=MagicMock(content=[MagicMock(text="This is the research overview.")])
    )
    service = LLMService()
    papers = [
        PaperSummary(summary="First.", key_findings=[], methods=[], relevance_score=None),
        PaperSummary(summary="Second.", key_findings=[], methods=[], relevance_score=None),
    ]
    result = await service.generate_research_overview(papers)
    assert result == "This is the research overview."


@pytest.mark.asyncio
async def test_summarize_in_german_uses_german_prompt(mock_anthropic_client, mock_settings):
    """Language 'de' leads to German summary instruction in system prompt."""
    service = LLMService()
    await service.summarize_paper(abstract="Test.", language="de")
    call_kwargs = mock_anthropic_client.messages.create.call_args[1]
    assert "Deutsch" in call_kwargs["system"]


@pytest.mark.asyncio
async def test_summarize_in_english_uses_english_prompt(mock_anthropic_client, mock_settings):
    """Language 'en' leads to English summary instruction in system prompt."""
    service = LLMService()
    await service.summarize_paper(abstract="Test.", language="en")
    call_kwargs = mock_anthropic_client.messages.create.call_args[1]
    assert "English" in call_kwargs["system"]


@pytest.mark.asyncio
async def test_summarize_paper_empty_abstract_returns_empty_summary(mock_settings):
    """Empty abstract returns empty PaperSummary without calling API."""
    service = LLMService()
    result = await service.summarize_paper(abstract="")
    assert result.summary == ""
    assert result.key_findings == []
    assert result.methods == []
    assert result.relevance_score is None


@pytest.mark.asyncio
async def test_extract_entities_empty_text_returns_empty_entities(mock_settings):
    """Empty text returns empty BiologicalEntities without calling API."""
    service = LLMService()
    result = await service.extract_entities("")
    assert result.genes == []
    assert result.diseases == []
    assert result.proteins == []


@pytest.mark.asyncio
async def test_generate_research_overview_empty_list_returns_empty_string(mock_settings):
    """Empty papers list returns empty string without calling API."""
    service = LLMService()
    result = await service.generate_research_overview([])
    assert result == ""
