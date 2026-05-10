"""Direct tests for health.check_features() to improve coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints import health


@pytest.mark.asyncio
async def test_check_features_returns_all_keys() -> None:
    """check_features returns dict with all expected feature keys."""
    with (
        patch("app.api.v1.endpoints.health.get_settings") as mock_settings,
        patch("app.api.v1.endpoints.health.shutil.which", return_value=None),
    ):
        mock_settings.return_value.anthropic_api_key = "sk-ant-x" + "x" * 25
        mock_settings.return_value.locus_enabled = False
        mock_settings.return_value.resolved_llm_backend = MagicMock(return_value="anthropic")
        features = await health.check_features()
    assert "embeddings" in features
    assert "semantic_search" in features
    assert "llm_summaries" in features
    assert "locus_rag" in features
    assert "spacy_ner" in features
    assert "blast" in features
    assert "nextflow" in features
    assert features["locus_rag"] is False


@pytest.mark.asyncio
async def test_check_features_llm_true_when_anthropic_key_valid() -> None:
    """check_features sets llm_summaries True when anthropic key is valid sk-ant-..."""
    with (
        patch("app.api.v1.endpoints.health.get_settings") as mock_settings,
        patch("app.api.v1.endpoints.health.shutil.which", return_value=None),
    ):
        mock_settings.return_value.anthropic_api_key = "sk-ant-api03-" + "x" * 40
        mock_settings.return_value.resolved_llm_backend = MagicMock(return_value="anthropic")
        features = await health.check_features()
    assert features["llm_summaries"] is True


@pytest.mark.asyncio
async def test_check_features_llm_false_when_dummy_key() -> None:
    """check_features sets llm_summaries False when Anthropic key is dummy."""
    with (
        patch("app.api.v1.endpoints.health.get_settings") as mock_settings,
        patch("app.api.v1.endpoints.health.shutil.which", return_value=None),
    ):
        mock_settings.return_value.anthropic_api_key = "dummy"
        mock_settings.return_value.resolved_llm_backend = MagicMock(return_value="anthropic")
        features = await health.check_features()
    assert features["llm_summaries"] is False


@pytest.mark.asyncio
async def test_check_features_ollama_returns_models() -> None:
    """check_features sets llm_summaries True when Ollama returns models."""
    with (
        patch("app.api.v1.endpoints.health.get_settings") as mock_settings,
        patch("app.api.v1.endpoints.health.httpx.AsyncClient") as MockClient,
        patch("app.api.v1.endpoints.health.shutil.which", return_value=None),
    ):
        mock_settings.return_value.anthropic_api_key = ""
        mock_settings.return_value.ollama_base_url = "http://localhost:11434"
        mock_settings.return_value.resolved_llm_backend = MagicMock(return_value="ollama")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "mistral:latest"}]}
        inst = MagicMock()
        inst.get = AsyncMock(return_value=mock_resp)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=inst)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
        features = await health.check_features()
    assert features["llm_summaries"] is True


@pytest.mark.asyncio
async def test_check_features_ollama_non_200() -> None:
    """check_features sets llm_summaries False when Ollama returns non-200."""
    with (
        patch("app.api.v1.endpoints.health.get_settings") as mock_settings,
        patch("app.api.v1.endpoints.health.httpx.AsyncClient") as MockClient,
        patch("app.api.v1.endpoints.health.shutil.which", return_value=None),
    ):
        mock_settings.return_value.anthropic_api_key = ""
        mock_settings.return_value.ollama_base_url = "http://localhost:11434"
        mock_settings.return_value.resolved_llm_backend = MagicMock(return_value="ollama")
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        inst = MagicMock()
        inst.get = AsyncMock(return_value=mock_resp)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=inst)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
        features = await health.check_features()
    assert features["llm_summaries"] is False


@pytest.mark.asyncio
async def test_check_features_openai_compatible_models_ok() -> None:
    """check_features probes GET {base}/models when backend is openai_compatible."""
    with (
        patch("app.api.v1.endpoints.health.get_settings") as mock_settings,
        patch("app.api.v1.endpoints.health.httpx.AsyncClient") as MockClient,
        patch("app.api.v1.endpoints.health.shutil.which", return_value=None),
    ):
        mock_settings.return_value.openai_api_base = "http://inference:30000/v1"
        mock_settings.return_value.openai_api_key = ""
        mock_settings.return_value.resolved_llm_backend = MagicMock(
            return_value="openai_compatible"
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        inst = MagicMock()
        inst.get = AsyncMock(return_value=mock_resp)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=inst)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
        features = await health.check_features()
        inst.get.assert_called_once()
        assert inst.get.call_args[0][0] == "http://inference:30000/v1/models"
    assert features["llm_summaries"] is True


@pytest.mark.asyncio
async def test_check_features_blast_true_when_which() -> None:
    """check_features sets blast True when blastn in PATH."""
    with (
        patch("app.api.v1.endpoints.health.get_settings") as mock_settings,
        patch("app.api.v1.endpoints.health.shutil.which") as mock_which,
    ):
        mock_settings.return_value.anthropic_api_key = "sk-ant-x" + "x" * 25
        mock_settings.return_value.resolved_llm_backend = MagicMock(return_value="anthropic")

        def which(cmd: str) -> str | None:
            return "/usr/bin/blastn" if cmd == "blastn" else None

        mock_which.side_effect = which
        features = await health.check_features()
    assert features["blast"] is True


@pytest.mark.asyncio
async def test_check_features_nextflow_true_when_which() -> None:
    """check_features sets nextflow True when nextflow in PATH."""
    with (
        patch("app.api.v1.endpoints.health.get_settings") as mock_settings,
        patch("app.api.v1.endpoints.health.shutil.which") as mock_which,
    ):
        mock_settings.return_value.anthropic_api_key = "sk-ant-x" + "x" * 25
        mock_settings.return_value.resolved_llm_backend = MagicMock(return_value="anthropic")

        def which(cmd: str) -> str | None:
            return "/usr/bin/nextflow" if cmd == "nextflow" else None

        mock_which.side_effect = which
        features = await health.check_features()
    assert features["nextflow"] is True


@pytest.mark.asyncio
async def test_health_check_data_sovereignty_full_when_no_anthropic() -> None:
    """health_check returns data_sovereignty full when LLM backend is not Anthropic cloud."""
    with patch("app.api.v1.endpoints.health.get_settings") as mock_settings:
        mock_settings.return_value.anthropic_api_key = ""
        mock_settings.return_value.version = "0.1.0"
        mock_settings.return_value.deployment = "test"
        mock_settings.return_value.resolved_llm_backend = MagicMock(return_value="ollama")
        with patch(
            "app.api.v1.endpoints.health.check_features",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await health.health_check()
    assert result["data_sovereignty"] == "full"


@pytest.mark.asyncio
async def test_check_features_ollama_exception_keeps_llm_false() -> None:
    """check_features sets llm_summaries False when Ollama request raises."""
    with (
        patch("app.api.v1.endpoints.health.get_settings") as mock_settings,
        patch("app.api.v1.endpoints.health.httpx.AsyncClient") as MockClient,
        patch("app.api.v1.endpoints.health.shutil.which", return_value=None),
    ):
        mock_settings.return_value.anthropic_api_key = ""
        mock_settings.return_value.ollama_base_url = "http://localhost:11434"
        mock_settings.return_value.resolved_llm_backend = MagicMock(return_value="ollama")
        inst = MagicMock()
        inst.get = AsyncMock(side_effect=Exception("connection refused"))
        MockClient.return_value.__aenter__ = AsyncMock(return_value=inst)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
        features = await health.check_features()
    assert features["llm_summaries"] is False


@pytest.mark.asyncio
async def test_health_check_data_sovereignty_partial_when_anthropic() -> None:
    """health_check returns data_sovereignty partial when Anthropic cloud is selected."""
    with patch("app.api.v1.endpoints.health.get_settings") as mock_settings:
        mock_settings.return_value.anthropic_api_key = "sk-ant-xxx"
        mock_settings.return_value.version = "0.1.0"
        mock_settings.return_value.deployment = "test"
        mock_settings.return_value.resolved_llm_backend = MagicMock(return_value="anthropic")
        with patch(
            "app.api.v1.endpoints.health.check_features",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await health.health_check()
    assert result["data_sovereignty"] == "partial"
