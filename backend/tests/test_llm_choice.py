"""Per-request LLM allowlist."""

from unittest.mock import MagicMock

from app.core.llm_choice import (
    apply_request_choice,
    current_choice,
    llm_catalog,
    parse_choice,
    reset_request_choice,
    resolve_backend,
    resolve_model_label,
)


def _settings(
    *,
    provider: str = "ollama",
    ollama: str = "mistral:7b",
    key: str | None = None,
) -> MagicMock:
    s = MagicMock()
    s.llm_provider = provider
    s.ollama_model = ollama
    s.llm_claude_model = "claude-haiku-4-5"
    s.openai_model = ""
    s.openai_api_base = None
    s.anthropic_api_key = key
    s.resolved_llm_backend.return_value = provider
    if provider == "ollama":
        s.effective_llm_model_label.return_value = ollama
    else:
        s.effective_llm_model_label.return_value = "claude-haiku-4-5"
    return s


def test_catalog_ollama_default_without_anthropic():
    catalog = llm_catalog(_settings())
    ids = [item["id"] for item in catalog["options"]]
    assert catalog["default_id"] == "ollama:mistral:7b"
    assert "ollama:mistral:7b" in ids
    assert not any(item["backend"] == "anthropic" for item in catalog["options"])


def test_catalog_includes_claude_when_key_present():
    catalog = llm_catalog(_settings(key="sk-ant-" + "x" * 24))
    ids = [item["id"] for item in catalog["options"]]
    assert "anthropic:claude-haiku-4-5" in ids
    assert "anthropic:claude-sonnet-5" in ids
    assert "anthropic:claude-opus-5" in ids


def test_parse_choice_allowlist():
    settings = _settings(key="sk-ant-" + "x" * 24)
    assert parse_choice("anthropic:claude-sonnet-5", settings).model == "claude-sonnet-5"
    assert parse_choice("anthropic:claude-not-a-model", settings) is None
    assert parse_choice("", settings) is None


def test_request_choice_overrides_backend():
    settings = _settings(key="sk-ant-" + "x" * 24)
    token = apply_request_choice("anthropic:claude-sonnet-5", settings)
    try:
        assert current_choice() is not None
        assert resolve_backend(settings) == "anthropic"
        assert resolve_model_label(settings) == "claude-sonnet-5"
    finally:
        reset_request_choice(token)
    assert resolve_backend(settings) == "ollama"
