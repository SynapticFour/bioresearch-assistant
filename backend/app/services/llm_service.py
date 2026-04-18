"""LLM service: Claude (primary) or Ollama (fallback) for summarization and entity extraction."""

import asyncio
import json
import logging
import re

import httpx

from app.core.prompt_security import sanitize_for_llm
from app.schemas.llm import BiologicalEntities, PaperSummary

logger = logging.getLogger(__name__)

# Default timeout for LLM API calls (RAG can take up to 5 min with large models)
LLM_TIMEOUT = 300.0  # 5 Minuten für RAG


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

    async def _call_ollama_with_retry(
        self,
        system: str,
        user: str,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> str:
        """Ollama chat with automatic retry on 500/OOM."""
        url = f"{self._ollama_base}/api/chat"
        payload = {
            "model": self._ollama_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                resp = await self._client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                msg = data.get("message") or {}
                content = (msg.get("content") or "").strip()
                if not content:
                    raise LLMServiceError("Ollama returned empty content")
                return content
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(
                        "Ollama attempt %d/%d failed: %s — retrying in %.0fs",
                        attempt + 1,
                        max_retries,
                        e,
                        retry_delay,
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
        if isinstance(last_error, httpx.HTTPStatusError):
            raise LLMServiceError(f"Ollama API error: {last_error}") from last_error
        if isinstance(last_error, httpx.RequestError):
            raise LLMServiceError(f"Ollama request failed: {last_error}") from last_error
        raise LLMServiceError(f"Ollama failed: {last_error}") from last_error

    async def _call_ollama(self, system: str, user: str) -> str:
        """Call Ollama /api/chat. Returns assistant message content (with retry)."""
        return await self._call_ollama_with_retry(system=system, user=user)

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

    async def rag_answer(
        self,
        question: str,
        context: str,
        language: str = "de",
    ) -> str:
        """RAG: answer question based only on provided paper excerpts.

        Uses same retry logic as Ollama calls. No new HTTP code.
        """
        question = (question or "").strip()
        context = (context or "").strip()
        if not context:
            return "Kein Kontext vorhanden."
        lang = (language or "de").lower()
        lang_instruction = (
            "Antworte auf Deutsch."
            if lang == "de"
            else "Reply in English."
            if lang == "en"
            else "Reply in the requested language."
        )
        system = (
            "You are a biomedical research assistant. "
            "Answer the question ONLY based on the provided paper excerpts. "
            "If the answer is not in the excerpts, say so clearly. "
            f"{lang_instruction} "
            "Do not invent information."
        )
        user = f"Paper excerpts:\n\n{context}\n\nQuestion: {question}"
        return (await self._complete(system=system, user=user)).strip()

    async def rag_answer_locus(
        self,
        question: str,
        context: str,
        language: str = "de",
    ) -> str:
        """Locus: curated corpus (guidelines, GA4GH, KDS) — not individual patient data."""
        question = (question or "").strip()
        context = (context or "").strip()
        if not context:
            return "Kein Kontext vorhanden."
        lang = (language or "de").lower()
        lang_instruction = (
            "Antworte auf Deutsch."
            if lang == "de"
            else "Reply in English."
            if lang == "en"
            else "Reply in the requested language."
        )
        # Locus: curated index; on-prem / GDPR as in docs/LOCUS-MODULE.md
        system = (
            "You are the Locus module of BioResearch Assistant: a clinical bioinformatics "
            "and research documentation assistant (German and international lab/university use). "
            "Answer only from the curated index excerpts above—e.g. S3/ESMO/NCCN-style "
            "guideline text if present, MII KDS or FHIR-oriented notes, GA4GH specs, or "
            "genomics/oncology reference snippets. If the excerpts do not contain the "
            "answer, say you cannot derive it from the given text. "
            "Do not fabricate guidelines, citations, or patient data. "
            "This is not a medical device: "
            "no diagnosis, no individual treatment plan, and no replacement for PACS, LIS, "
            "or qualified review. "
            "You may give general educational wording (e.g. what VUS, pathogenic, or likely "
            "pathogenic means) only if that content is supported by the excerpts. Favour "
            "Drittmittel/MTB-style context and colleague-facing explanations, not bedside "
            "decisions. "
            f"{lang_instruction} "
            "Prefer plain text; use markdown only if the user explicitly asks for it."
        )
        user = f"Curated index excerpts (Locus):\n\n{context}\n\nQuestion: {question}"
        return (await self._complete(system=system, user=user)).strip()

    async def notebook_ai_assist(
        self,
        content: str,
        mode: str = "both",
        linked_context: str = "",
    ) -> tuple[str | None, str | None]:
        """Generate summary and/or next steps for notebook content.

        Args:
            content: Markdown notebook content.
            mode: One of 'summary', 'next_steps', 'both'.
            linked_context: Optional context from linked papers (title + abstract excerpts).

        Returns:
            (summary, next_steps) — one or both may be None depending on mode.

        Raises:
            LLMServiceError: On API or parsing errors.
        """
        content = sanitize_for_llm((content or "").strip())
        if not content:
            return (None, None)

        linked_context_safe = sanitize_for_llm((linked_context or "").strip())
        linked_section = ""
        if linked_context_safe:
            linked_section = f"\n\nZusätzlich verknüpfte Papers:\n{linked_context_safe}\n"

        summary: str | None = None
        next_steps: str | None = None

        if mode in ("summary", "both"):
            system = (
                "You are a biomedical research assistant. "
                "Summarize the following lab notebook entry in 2-4 concise sentences. "
                "You may use information from linked papers if provided. "
                "Output plain text only, no markdown."
            )
            user = f"Notebook content:\n\n{content}{linked_section}"
            summary = (await self._complete(system=system, user=user)).strip()

        if mode in ("next_steps", "both"):
            system = (
                "You are a biomedical research assistant. "
                "Based on the following lab notebook entry (and linked papers if provided), "
                "suggest 3-5 concrete next research steps. "
                "Output a short bullet list as plain text (one line per step)."
            )
            user = f"Notebook content:\n\n{content}{linked_section}"
            next_steps = (await self._complete(system=system, user=user)).strip()

        return (summary, next_steps)
