"""LLM service: Claude (primary) or Ollama (fallback) for summarization and entity extraction."""

import json
import logging
import re

import httpx

from app.schemas.llm import BiologicalEntities, PaperSummary

logger = logging.getLogger(__name__)

# Default timeout for LLM API calls (Mistral 7B etc. need time)
LLM_TIMEOUT = 120.0


class LLMServiceError(Exception):
    """Raised when an LLM API call or response parsing fails."""

    pass


def _extract_json_block(text: str) -> str:
    """Extract first JSON object or array from markdown code block or raw text."""
    text = text.strip()
    # Optional markdown code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    # Find first { ... } or [ ... ]
    start_obj = text.find("{")
    start_arr = text.find("[")
    if start_obj >= 0 and (start_arr < 0 or start_obj < start_arr):
        depth = 0
        for i in range(start_obj, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start_obj : i + 1]
    elif start_arr >= 0:
        depth = 0
        for i in range(start_arr, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    return text[start_arr : i + 1]
    return text


class LLMService:
    """Async LLM service using Claude (Anthropic) or Ollama as fallback."""

    def __init__(
        self,
        *,
        anthropic_api_key: str | None = None,
        ollama_base_url: str | None = None,
        claude_model: str | None = None,
        ollama_model: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize from explicit args; missing values are read from app config."""
        from app.core.config import get_settings

        settings = get_settings()
        self._api_key = (
            anthropic_api_key if anthropic_api_key is not None else settings.anthropic_api_key
        )
        self._ollama_base = (ollama_base_url or settings.ollama_base_url).rstrip("/")
        self._claude_model = claude_model or settings.llm_claude_model
        self._ollama_model = ollama_model or settings.ollama_model
        self._client = http_client or httpx.AsyncClient(timeout=LLM_TIMEOUT)
        self._own_client = http_client is None

    @property
    def _use_anthropic(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    async def close(self) -> None:
        if self._own_client:
            await self._client.aclose()

    async def __aenter__(self) -> "LLMService":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def _call_claude(self, system: str, user: str) -> str:
        """Call Claude API (Anthropic). Returns assistant text content."""
        try:
            from anthropic import AsyncAnthropic
        except ImportError as e:
            raise LLMServiceError("anthropic package not installed") from e
        client = AsyncAnthropic(api_key=self._api_key)
        try:
            message = await client.messages.create(
                model=self._claude_model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as e:
            logger.warning("Claude API error: %s", e)
            raise LLMServiceError(f"Claude API failed: {e}") from e
        if not message.content:
            raise LLMServiceError("Claude returned empty content")
        block = message.content[0]
        if hasattr(block, "text"):
            return block.text
        raise LLMServiceError("Unexpected Claude response format")

    async def _call_ollama(self, system: str, user: str) -> str:
        """Call Ollama /api/chat. Returns assistant message content."""
        url = f"{self._ollama_base}/api/chat"
        payload = {
            "model": self._ollama_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("Ollama HTTP error: %s", e)
            raise LLMServiceError(f"Ollama API error: {e}") from e
        except httpx.RequestError as e:
            logger.warning("Ollama request error: %s", e)
            raise LLMServiceError(f"Ollama request failed: {e}") from e
        except ValueError as e:
            raise LLMServiceError("Invalid Ollama response") from e
        msg = data.get("message") or {}
        content = msg.get("content") or ""
        if not content.strip():
            raise LLMServiceError("Ollama returned empty content")
        return content

    async def _complete(self, system: str, user: str) -> str:
        """Run completion with configured provider (Claude or Ollama)."""
        if self._use_anthropic:
            return await self._call_claude(system=system, user=user)
        return await self._call_ollama(system=system, user=user)

    async def summarize_paper(
        self,
        abstract: str,
        context: str = "",
        language: str = "de",
        title: str = "",
    ) -> PaperSummary:
        """Summarize a paper abstract; optionally score relevance to context.

        Args:
            abstract: The paper abstract text.
            context: Optional research context; if provided, relevance_score is set (0-1).
            language: Output language for summary ('de' or 'en').
            title: Optional paper title for structured summary.

        Returns:
            PaperSummary with summary, key_findings, methods, and optional relevance_score.

        Raises:
            LLMServiceError: On API or parsing errors.
        """
        abstract = (abstract or "").strip()
        if not abstract:
            return PaperSummary(
                summary="",
                key_findings=[],
                methods=[],
                relevance_score=None,
            )
        has_context = bool((context or "").strip())
        lang = (language or "de").lower()
        lang_instruction = {
            "de": (
                "Antworte ausschließlich auf Deutsch. Erstelle eine strukturierte Zusammenfassung."
            ),
            "en": ("Reply in English only. Create a structured summary."),
        }.get(lang, "Reply in the same language as the abstract.")
        system = (
            "You are a biomedical research assistant. Output valid JSON only, no markdown. "
            "Use the exact keys: summary, key_findings, methods, relevance_score. "
            "summary: structured 2-4 sentences covering: 1) Fragestellung/Ziel, 2) Methoden, "
            "3) Ergebnisse, 4) Klinische Relevanz. key_findings and methods: arrays of strings. "
            f"{lang_instruction} "
        )
        if has_context:
            system += "relevance_score: number 0-1 (how relevant is the paper to the context). "
        else:
            system += "relevance_score: null. "

        title_part = (title or "").strip()
        user = ""
        if title_part:
            user += f"Titel: {title_part}\n\n"
        user += f"Abstract:\n{abstract}\n\n"
        if has_context:
            user += f"Research context:\n{context}\n\n"
        user += "Return JSON with summary, key_findings, methods, relevance_score."

        raw = await self._complete(system=system, user=user)
        try:
            json_str = _extract_json_block(raw)
            data = json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("summarize_paper JSON parse error: %s", e)
            raise LLMServiceError("Failed to parse summary JSON") from e

        summary = (data.get("summary") or "").strip()
        key_findings = data.get("key_findings")
        methods = data.get("methods")
        relevance_score = data.get("relevance_score")
        if not isinstance(key_findings, list):
            key_findings = []
        if not isinstance(methods, list):
            methods = []
        key_findings = [str(x).strip() for x in key_findings if x]
        methods = [str(x).strip() for x in methods if x]
        if relevance_score is not None:
            try:
                relevance_score = float(relevance_score)
                relevance_score = max(0.0, min(1.0, relevance_score))
            except (TypeError, ValueError):
                relevance_score = None
        if not has_context:
            relevance_score = None

        return PaperSummary(
            summary=summary,
            key_findings=key_findings,
            methods=methods,
            relevance_score=relevance_score,
        )

    async def extract_entities(self, text: str) -> BiologicalEntities:
        """Extract biological entities (genes, proteins, diseases, organisms, chemicals) from text.

        Args:
            text: Input text (e.g. abstract or full paper excerpt).

        Returns:
            BiologicalEntities with lists of extracted entity names.

        Raises:
            LLMServiceError: On API or parsing errors.
        """
        text = (text or "").strip()
        if not text:
            return BiologicalEntities()

        system = (
            "You are a biomedical NER assistant. Output valid JSON only. "
            "Use exactly these keys: genes, proteins, diseases, organisms, chemicals. "
            "Each value is an array of strings (entity names/symbols). "
            "Extract only clearly mentioned entities; use empty array if none."
        )
        user = f"Text:\n{text}\n\nReturn JSON with genes, proteins, diseases, organisms, chemicals."

        raw = await self._complete(system=system, user=user)
        try:
            json_str = _extract_json_block(raw)
            data = json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("extract_entities JSON parse error: %s", e)
            raise LLMServiceError("Failed to parse entities JSON") from e

        def to_list(v: object) -> list[str]:
            if not isinstance(v, list):
                return []
            return [str(x).strip() for x in v if x]

        return BiologicalEntities(
            genes=to_list(data.get("genes")),
            proteins=to_list(data.get("proteins")),
            diseases=to_list(data.get("diseases")),
            organisms=to_list(data.get("organisms")),
            chemicals=to_list(data.get("chemicals")),
        )

    async def generate_research_overview(self, papers: list[PaperSummary]) -> str:
        """Generate a short narrative overview summarizing multiple paper summaries.

        Args:
            papers: List of PaperSummary objects (e.g. from summarize_paper).

        Returns:
            A single string with the research overview.

        Raises:
            LLMServiceError: On API errors.
        """
        if not papers:
            return ""

        # Serialize for prompt
        parts = []
        for i, p in enumerate(papers, 1):
            parts.append(
                f"Paper {i}: Summary: {p.summary}. "
                f"Key findings: {', '.join(p.key_findings) or 'None'}. "
                f"Methods: {', '.join(p.methods) or 'None'}."
            )
        combined = "\n\n".join(parts)

        system = (
            "You are a biomedical research assistant. "
            "Write a concise research overview (a few paragraphs) that synthesizes "
            "the given paper summaries. Do not use markdown. Output plain text only."
        )
        user = f"Paper summaries:\n\n{combined}\n\nWrite a research overview."

        return (await self._complete(system=system, user=user)).strip()
