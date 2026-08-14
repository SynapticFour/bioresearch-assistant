"""HPO (Human Phenotype Ontology) Service.

Nutzt HPO API — kein Key nötig.
"""

import logging
import re
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

# Keyword → HPO ID Fallback wenn API nicht verfügbar oder für schnelle Extraktion
COMMON_PHENOTYPES: dict[str, str | None] = {
    "krampf": "HP:0001250",
    "seizure": "HP:0001250",
    "seizures": "HP:0001250",
    "brustschmerz": "HP:0031964",
    "chest pain": "HP:0100749",
    "mutation": None,
    "tumor": "HP:0002664",
    "schwellung": "HP:0000969",
    "swelling": "HP:0000969",
    "fieber": "HP:0001945",
    "fever": "HP:0001945",
    "kopfschmerz": "HP:0002315",
    "headache": "HP:0002315",
    "fatigue": "HP:0012378",
    "erschöpfung": "HP:0012378",
}

_HPO_ID_RE = re.compile(r"HP:\d{7}")


class HPOService:
    """Search and resolve HPO terms."""

    async def search_terms(self, query: str) -> list[dict]:
        """Search HPO terms (e.g. via HPO API or bioontology).

        Returns list of { id, name, definition, synonyms }.
        """
        q = (query or "").strip()
        if not q:
            return []
        # HPO JAX API (public)
        url = f"https://hpo.jax.org/api/hpo/search?q={quote_plus(q)}&max=10&category=terms"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                data = resp.json()
                terms = data.get("terms", [])
                return [
                    {
                        "id": t.get("id", ""),
                        "name": t.get("name", ""),
                        "definition": t.get("definition", ""),
                        "synonyms": t.get("synonyms", []),
                    }
                    for t in terms
                ]
            except Exception as e:
                logger.warning("HPO search failed: %s", e)
                return []

    async def get_term(self, hpo_id: str) -> dict | None:
        """Get details for one HPO term."""
        hid = (hpo_id or "").strip()
        if not hid:
            return None
        url = f"https://hpo.jax.org/api/hpo/term/{hid}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                return resp.json()
            except Exception as e:
                logger.warning("HPO get_term failed: %s", e)
                return None

    async def extract_from_text(
        self,
        text: str,
        llm_service: object | None = None,
    ) -> list[dict]:
        """Extract HPO terms from free text.

        Keyword matching is always applied. If ``llm_service`` is provided and
        exposes ``_complete``, LLM extraction is merged as a secondary source.
        Returns list of { hpo_id, name, confidence, source? }.
        """
        if not text or not text.strip():
            return []
        found: list[dict] = []
        text_lower = text.lower()
        for keyword, hpo_id in COMMON_PHENOTYPES.items():
            if keyword in text_lower and hpo_id:
                found.append(
                    {
                        "hpo_id": hpo_id,
                        "name": keyword.capitalize(),
                        "confidence": 0.6,
                        "source": "keyword_match",
                    }
                )
        complete = getattr(llm_service, "_complete", None) if llm_service is not None else None
        if callable(complete):
            try:
                raw = await complete(
                    (
                        "Extract Human Phenotype Ontology terms from clinical text. "
                        "Reply with HP:NNNNNNN identifiers only, one per line."
                    ),
                    text[:4000],
                )
                seen = {item["hpo_id"] for item in found}
                for hid in _HPO_ID_RE.findall(raw or ""):
                    if hid not in seen:
                        seen.add(hid)
                        found.append(
                            {
                                "hpo_id": hid,
                                "name": hid,
                                "confidence": 0.5,
                                "source": "llm",
                            }
                        )
            except Exception as e:
                logger.warning("HPO LLM extract failed: %s", e)
        return found
