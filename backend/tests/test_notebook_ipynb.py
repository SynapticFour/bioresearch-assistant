"""M1: JupyterLite-class ipynb notebooks (nbformat v4, no server kernel)."""

import json

import pytest
from httpx import AsyncClient

from app.core.ipynb import starter_ipynb_json, validate_ipynb


def test_starter_ipynb_is_nbformat_4() -> None:
    raw = starter_ipynb_json()
    validate_ipynb(raw)
    data = json.loads(raw)
    assert data["nbformat"] == 4
    assert any("Phenopacket" in "".join(c.get("source") or []) for c in data["cells"])
    assert "postgresql://" not in raw
    assert "DATABASE_URL=" not in raw


def test_validate_ipynb_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="JSON"):
        validate_ipynb("not-json")
    with pytest.raises(ValueError, match="nbformat"):
        validate_ipynb(json.dumps({"nbformat": 3, "cells": []}))
    with pytest.raises(ValueError, match="cells"):
        validate_ipynb(json.dumps({"nbformat": 4}))


@pytest.mark.asyncio
async def test_create_ipynb_seeds_starter(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/notebooks",
        json={"title": "Phenopacket notebook", "format": "ipynb", "content": ""},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["format"] == "ipynb"
    validate_ipynb(data["content"])
    assert "Phenopacket" in data["content"]


@pytest.mark.asyncio
async def test_create_markdown_notebook_default(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/notebooks",
        json={"title": "ELN", "content": "# notes"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["format"] == "markdown"
    assert data["content"] == "# notes"


@pytest.mark.asyncio
async def test_create_ipynb_rejects_invalid_json(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/notebooks",
        json={"title": "bad", "format": "ipynb", "content": "{nope"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_ipynb_validates(async_client: AsyncClient) -> None:
    created = await async_client.post(
        "/api/v1/notebooks",
        json={"title": "nb", "format": "ipynb"},
    )
    nb_id = created.json()["id"]
    bad = await async_client.put(
        f"/api/v1/notebooks/{nb_id}",
        json={"content": "not-a-notebook"},
    )
    assert bad.status_code == 400
    good_body = json.dumps({"nbformat": 4, "nbformat_minor": 5, "metadata": {}, "cells": []})
    ok = await async_client.put(
        f"/api/v1/notebooks/{nb_id}",
        json={"content": good_body},
    )
    assert ok.status_code == 200
    assert ok.json()["format"] == "ipynb"
