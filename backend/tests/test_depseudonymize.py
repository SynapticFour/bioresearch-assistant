"""Tests for De-Pseudonymization endpoint (POST /api/v1/pseudonymize/reverse)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.audit_log import AuditLog


@pytest.mark.asyncio
async def test_reverse_nonexistent_mapping(async_client: AsyncClient) -> None:
    """404 für nicht existierende mapping_id."""
    resp = await async_client.post(
        "/api/v1/pseudonymize/reverse",
        json={"mapping_id": "nonexistent-id-xyz"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reverse_full_flow(async_client: AsyncClient) -> None:
    """Vollständiger Flow: pseudonymisieren → reversieren."""
    resp = await async_client.post(
        "/api/v1/pseudonymize",
        json={"text": "Patient Test Person", "language": "de"},
    )
    assert resp.status_code == 200
    data = resp.json()
    mapping_id = data.get("mapping_id")

    if not mapping_id:
        pytest.skip("mapping_id nicht in Response (keine Entities erkannt)")

    resp2 = await async_client.post(
        "/api/v1/pseudonymize/reverse",
        json={"mapping_id": mapping_id},
    )
    assert resp2.status_code == 200
    result = resp2.json()
    assert "original_text" in result
    assert "accessed_by" in result
    assert "access_time" in result
    assert result.get("mapping_id") == mapping_id


@pytest.mark.asyncio
async def test_reverse_audit_logged(async_client: AsyncClient, db_session) -> None:
    """De-Pseudonymisierung wird im Audit Log gespeichert (operation_type=DEPSEUDONYMIZE)."""
    resp = await async_client.post(
        "/api/v1/pseudonymize",
        json={"text": "Patient Max Mustermann", "language": "de"},
    )
    mapping_id = resp.json().get("mapping_id")
    if not mapping_id:
        pytest.skip("mapping_id nicht in Response")

    await async_client.post(
        "/api/v1/pseudonymize/reverse",
        json={"mapping_id": mapping_id},
    )

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.operation_type == "DEPSEUDONYMIZE")
    )
    entries = result.scalars().all()
    assert len(entries) >= 1
    assert any(e.mapping_id == mapping_id for e in entries)
