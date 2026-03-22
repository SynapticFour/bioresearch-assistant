"""Normalize GA4GH DRS access URL payloads (Ferrum-style lesson learned).

Clients and databases may store ``access_url`` as either a plain string or a
JSON object ``{"url": "https://..."}``. Centralizing parsing avoids divergent
behaviour between object listings and ``GET .../access/{access_id}``.

Reference pattern: SynapticFour/Ferrum ``ferrum-drs`` ``access_url`` module.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract_download_url(value: str | dict[str, Any] | None) -> str | None:
    """Return a concrete HTTPS/HTTP URL string from a stored access_url shape.

    Args:
        value: Raw ``access_url`` from JSON/API: string, object with ``url``, or None.

    Returns:
        Non-empty URL string, or None if unsupported or missing.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        u = value.get("url")
        if isinstance(u, str) and u.strip():
            return u.strip()
        logger.debug("access_url object missing string url key")
        return None
    return None


def access_url_for_json_listing(value: str | dict[str, Any] | None) -> str | dict[str, Any] | None:
    """Map stored value to a shape suitable for ``AccessMethod.access_url`` JSON.

    Strings pass through; dicts with a ``url`` key pass through; otherwise None.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value if value.strip() else None
    if isinstance(value, dict) and isinstance(value.get("url"), str):
        return value
    return None
