"""Per-request LLM choice for BioResearch Assistant (header X-BRA-LLM).

Server default stays LLM_PROVIDER / Ollama. The UI may send an allowlisted
override so a researcher can pick local vs Claude for one reasoning call.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings

LLM_CHOICE_HEADER = "X-BRA-LLM"

# Cloud Claude options offered in the UI when a valid Anthropic key is present.
CLAUDE_REASONING_MODELS: tuple[tuple[str, str], ...] = (
    ("claude-haiku-4-5", "Claude Haiku"),
    ("claude-sonnet-5", "Claude Sonnet"),
    ("claude-opus-5", "Claude Opus"),
)

_choice: ContextVar[LlmChoice | None] = ContextVar("bra_llm_choice", default=None)


def _load_settings(settings: Settings | None = None) -> Settings:
    if settings is not None:
        return settings
    from app.core.config import get_settings

    return get_settings()


@dataclass(frozen=True)
class LlmChoice:
    backend: str
    model: str

    @property
    def option_id(self) -> str:
        return f"{self.backend}:{self.model}"


def anthropic_key_usable(settings: Settings | None = None) -> bool:
    settings = _load_settings(settings)
    key = (settings.anthropic_api_key or "").strip()
    return bool(key and key != "dummy" and key.startswith("sk-ant-") and len(key) > 20)


def llm_catalog(settings: Settings | None = None) -> dict[str, Any]:
    """Options for the header dropdown. Default is the process LLM_PROVIDER."""
    settings = _load_settings(settings)
    default_backend = settings.resolved_llm_backend()
    default_model = settings.effective_llm_model_label()
    default_id = f"{default_backend}:{default_model}"

    options: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(
        *,
        backend: str,
        model: str,
        label: str,
        sovereignty: str,
        available: bool,
    ) -> None:
        option_id = f"{backend}:{model}"
        if option_id in seen or not model:
            return
        seen.add(option_id)
        options.append(
            {
                "id": option_id,
                "backend": backend,
                "model": model,
                "label": label,
                "sovereignty": sovereignty,
                "available": available,
            }
        )

    backend_titles = {
        "ollama": "Ollama",
        "anthropic": "Claude",
        "openai_compatible": "OpenAI-compatible",
    }
    add(
        backend=default_backend,
        model=default_model,
        label=f"{backend_titles.get(default_backend, default_backend)} ({default_model})",
        sovereignty="partial" if default_backend == "anthropic" else "full",
        available=True,
    )
    add(
        backend="ollama",
        model=settings.ollama_model,
        label=f"Ollama ({settings.ollama_model})",
        sovereignty="full",
        available=True,
    )
    if anthropic_key_usable(settings):
        for model_id, label in CLAUDE_REASONING_MODELS:
            add(
                backend="anthropic",
                model=model_id,
                label=f"{label} (Cloud)",
                sovereignty="partial",
                available=True,
            )
    if default_backend == "openai_compatible" and (settings.openai_api_base or "").strip():
        add(
            backend="openai_compatible",
            model=settings.openai_model or "openai-compatible",
            label=f"OpenAI-compatible ({settings.openai_model or 'configured'})",
            sovereignty="full",
            available=True,
        )

    return {
        "default_id": default_id,
        "header": LLM_CHOICE_HEADER,
        "options": options,
    }


def parse_choice(raw: str, settings: Settings | None = None) -> LlmChoice | None:
    """Return an allowlisted choice, or None to keep the server default."""
    text = (raw or "").strip()
    if not text:
        return None
    catalog = llm_catalog(settings)
    allowed = {str(item["id"]) for item in catalog["options"] if item.get("available")}
    if text not in allowed:
        return None
    backend, _, model = text.partition(":")
    if not backend or not model:
        return None
    return LlmChoice(backend=backend, model=model)


def apply_request_choice(raw: str, settings: Settings | None = None) -> Token[LlmChoice | None]:
    return _choice.set(parse_choice(raw, settings))


def reset_request_choice(token: Token[LlmChoice | None]) -> None:
    _choice.reset(token)


def current_choice() -> LlmChoice | None:
    return _choice.get()


def resolve_backend(settings: Settings | None = None) -> str:
    settings = _load_settings(settings)
    choice = current_choice()
    if choice is not None:
        return choice.backend
    return settings.resolved_llm_backend()


def resolve_model_label(settings: Settings | None = None) -> str:
    settings = _load_settings(settings)
    choice = current_choice()
    if choice is not None:
        return choice.model
    return settings.effective_llm_model_label()
