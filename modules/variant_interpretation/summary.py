"""Structured summary: literature references beside Ferrum technical metadata.

No HTTP client, no database, and no new data source. Inputs are values the
caller already holds. The summary does not add a recommendation or a diagnosis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

DISCLAIMER = "Nicht diagnostisch, keine klinische Entscheidungsunterstützung"

_LITERATURE_KEYS = ("source_ref", "title", "corpus_id")

# GA4GH DRS/WES fields that describe an object or a run, not a person.
_TECHNICAL_KEYS = (
    "drs_id",
    "self_uri",
    "name",
    "size",
    "created_time",
    "updated_time",
    "version",
    "mime_type",
    "checksums",
    "wes_run_id",
    "wes_state",
)


@dataclass(frozen=True)
class InterpretationSummary:
    """Side-by-side summary. ``active`` is false when the module is off."""

    active: bool
    literature: tuple[Mapping[str, str], ...]
    technical_metadata: Mapping[str, object]
    disclaimer: str = DISCLAIMER


def _configured(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return bool(str(value).strip())


def is_active(
    *,
    locus_enabled: bool,
    ferrum_drs_url: str | None,
    ferrum_wes_url: str | None,
) -> bool:
    """True only when Locus and both Ferrum URLs are configured."""
    return bool(locus_enabled) and _configured(ferrum_drs_url) and _configured(ferrum_wes_url)


def _literature(locus_response: Mapping[str, object] | None) -> tuple[Mapping[str, str], ...]:
    if not locus_response:
        return ()
    sources = locus_response.get("sources") or []
    if not isinstance(sources, list):
        return ()
    rows: list[Mapping[str, str]] = []
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        rows.append({key: str(source.get(key) or "") for key in _LITERATURE_KEYS})
    return tuple(rows)


def _checksums(value: object) -> list[Mapping[str, str]]:
    if not isinstance(value, list):
        return []
    kept: list[Mapping[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        kept.append(
            {
                "type": str(item.get("type") or ""),
                "checksum": str(item.get("checksum") or ""),
            }
        )
    return kept


def _technical(ferrum_metadata: Mapping[str, object] | None) -> Mapping[str, object]:
    if not ferrum_metadata:
        return {}
    kept: dict[str, object] = {}
    for key in _TECHNICAL_KEYS:
        if key not in ferrum_metadata:
            continue
        value = ferrum_metadata[key]
        if key == "checksums":
            kept[key] = _checksums(value)
        elif value is None:
            continue
        else:
            kept[key] = value
    return kept


def summarize(
    locus_response: Mapping[str, object] | None,
    ferrum_metadata: Mapping[str, object] | None,
    *,
    locus_enabled: bool,
    ferrum_drs_url: str | None,
    ferrum_wes_url: str | None,
) -> InterpretationSummary:
    """Juxtapose literature references and technical metadata.

    Returns an inactive summary, without raising, when Locus or either Ferrum
    URL is unset. Does not read ``answer`` from the Locus response.
    """
    if not is_active(
        locus_enabled=locus_enabled,
        ferrum_drs_url=ferrum_drs_url,
        ferrum_wes_url=ferrum_wes_url,
    ):
        return InterpretationSummary(active=False, literature=(), technical_metadata={})
    return InterpretationSummary(
        active=True,
        literature=_literature(locus_response),
        technical_metadata=_technical(ferrum_metadata),
    )
