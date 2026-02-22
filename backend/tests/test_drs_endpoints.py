"""Tests for GA4GH DRS API: service-info, list, register."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_drs_service_info(async_client: AsyncClient) -> None:
    """GET /ga4gh/drs/v1/service-info returns 200 and service id."""
    response = await async_client.get("/ga4gh/drs/v1/service-info")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data.get("type", {}).get("artifact") == "drs"
    assert "name" in data


@pytest.mark.asyncio
async def test_list_drs_objects(async_client: AsyncClient) -> None:
    """GET /ga4gh/drs/v1/objects returns 200 (list may be empty)."""
    response = await async_client.get("/ga4gh/drs/v1/objects")
    assert response.status_code == 200
    data = response.json()
    assert "objects" in data
    assert isinstance(data["objects"], list)


@pytest.mark.asyncio
async def test_register_drs_object(async_client: AsyncClient) -> None:
    """POST /ga4gh/drs/v1/objects with name and file returns 201."""
    payload = b"test content for DRS object"
    response = await async_client.post(
        "/ga4gh/drs/v1/objects",
        data={"name": "test.vcf"},
        files={"file": ("test.vcf", payload, "text/vcf")},
    )
    assert response.status_code == 201
    obj = response.json()
    assert "id" in obj
    assert obj.get("size") == len(payload)
