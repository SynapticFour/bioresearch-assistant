"""Tests for phenopackets API: list, create (with string lists)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_phenopackets_empty(async_client: AsyncClient) -> None:
    """GET /phenopackets returns 200 and empty list when none."""
    response = await async_client.get("/api/v1/phenopackets")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_phenopacket(async_client: AsyncClient) -> None:
    """POST /phenopackets with string lists returns 201 and stored phenopacket."""
    phenopacket = {
        "pseudonym_id": "PATIENT-TEST-001",
        "phenotypes": ["HP:0001250"],
        "diseases": ["OMIM:143100"],
        "genes_of_interest": ["BRCA1"],
    }
    response = await async_client.post(
        "/api/v1/phenopackets",
        json=phenopacket,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "PATIENT-TEST-001"
    assert "subject" in data
    assert "phenotypic_features" in data
    assert "diseases" in data


@pytest.mark.asyncio
async def test_create_phenopacket_no_real_names(async_client: AsyncClient) -> None:
    """System accepts only pseudonym_id (no real names)."""
    phenopacket = {
        "pseudonym_id": "PATIENT-002",
        "phenotypes": ["HP:0002013"],
        "genes_of_interest": ["TP53"],
    }
    response = await async_client.post(
        "/api/v1/phenopackets",
        json=phenopacket,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "PATIENT-002"
