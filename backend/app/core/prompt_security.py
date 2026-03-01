"""Prompt-injection mitigation for LLM context (OWASP A03)."""

import logging
import re

logger = logging.getLogger(__name__)

# Patterns that may indicate prompt injection — filter/replace, do not block
_DANGEROUS_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "system prompt",
    "jailbreak",
    "du bist jetzt",
    "vergiss alle",
]


def sanitize_for_llm(text: str) -> str:
    """Prevent prompt injection in LLM context.

    Replaces dangerous patterns with [FILTERED] and logs a warning.
    Does not block the request; allows processing with sanitized content.
    """
    if not text or not isinstance(text, str):
        return text
    text_lower = text.lower()
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in text_lower:
            logger.warning(
                "Potential prompt injection detected (pattern filtered)",
                extra={"pattern_length": len(pattern)},
            )
            # Case-insensitive replacement
            text = re.sub(re.escape(pattern), "[FILTERED]", text, flags=re.IGNORECASE)
    return text
