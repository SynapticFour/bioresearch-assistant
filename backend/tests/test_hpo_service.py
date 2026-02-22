"""Tests for HPOService (keyword extraction)."""

import pytest

from app.services.hpo_service import HPOService


@pytest.mark.asyncio
async def test_hpo_keyword_extraction() -> None:
    """extract_from_text finds keywords and returns HPO IDs."""
    service = HPOService()
    text = "Patient zeigt Krampfanfälle und Tumor"
    results = await service.extract_from_text(text)
    assert len(results) > 0
    hpo_ids = [r["hpo_id"] for r in results]
    assert "HP:0001250" in hpo_ids  # Seizures
    assert "HP:0002664" in hpo_ids  # Tumor
