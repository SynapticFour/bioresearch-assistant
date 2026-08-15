"""Ferrum DRS/WES client: proxy when URLs are set; local store otherwise."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.services.ferrum_backend import build_upstream_url


def test_build_upstream_url_strips_prefix() -> None:
    assert (
        build_upstream_url(
            "http://ferrum.test/ga4gh/drs/v1",
            "/ga4gh/drs/v1",
            "/ga4gh/drs/v1/objects/abc",
            "expand=true",
        )
        == "http://ferrum.test/ga4gh/drs/v1/objects/abc?expand=true"
    )


def test_build_upstream_url_service_info() -> None:
    assert (
        build_upstream_url(
            "http://ferrum.test/ga4gh/wes/v1/",
            "/ga4gh/wes/v1",
            "/ga4gh/wes/v1/service-info",
            "",
        )
        == "http://ferrum.test/ga4gh/wes/v1/service-info"
    )


class _UpstreamResp:
    def __init__(self, payload: bytes, status: int = 200) -> None:
        self.status_code = status
        self.content = payload
        self.headers = httpx.Headers({"content-type": "application/json"})


class _FakeAsyncClient:
    captured: dict[str, str] = {}
    payload: bytes = b"{}"
    status: int = 200

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
    ) -> _UpstreamResp:
        self.captured["method"] = method
        self.captured["url"] = url
        self.captured["authorization"] = (headers or {}).get("Authorization", "")
        self.captured["content_len"] = str(len(content or b""))
        return _UpstreamResp(self.payload, self.status)


class _BoomClient:
    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    async def __aenter__(self) -> _BoomClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def request(self, *args: object, **kwargs: object) -> _UpstreamResp:
        raise httpx.ConnectError("connection refused")


@pytest.mark.asyncio
async def test_drs_proxies_to_ferrum_when_url_set(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ferrum_drs_url", "http://ferrum.test/ga4gh/drs/v1")
    monkeypatch.setattr(settings, "ferrum_wes_url", None)
    monkeypatch.setattr(settings, "ferrum_bearer_token", "tok-1")
    captured: dict[str, str] = {}
    _FakeAsyncClient.captured = captured
    _FakeAsyncClient.payload = b'{"id":"org.ga4gh.ferrum.drs","type":{"artifact":"drs"}}'
    _FakeAsyncClient.status = 200
    with patch("app.services.ferrum_backend.httpx.AsyncClient", _FakeAsyncClient):
        response = await async_client.get("/ga4gh/drs/v1/service-info")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "org.ga4gh.ferrum.drs"
    assert "bioresearch" not in body["id"]
    assert captured["url"] == "http://ferrum.test/ga4gh/drs/v1/service-info"
    assert captured["authorization"] == "Bearer tok-1"


@pytest.mark.asyncio
async def test_wes_run_post_proxies_to_ferrum(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ferrum_drs_url", None)
    monkeypatch.setattr(settings, "ferrum_wes_url", "http://ferrum.test/ga4gh/wes/v1")
    monkeypatch.setattr(settings, "ferrum_bearer_token", None)
    captured: dict[str, str] = {}
    _FakeAsyncClient.captured = captured
    _FakeAsyncClient.payload = b'{"run_id":"ferrum-run-1"}'
    _FakeAsyncClient.status = 200
    with patch("app.services.ferrum_backend.httpx.AsyncClient", _FakeAsyncClient):
        response = await async_client.post(
            "/ga4gh/wes/v1/runs",
            data={"workflow_url": "https://example.org/wf.wdl", "workflow_type": "WDL"},
        )
    assert response.status_code == 200
    assert response.json()["run_id"] == "ferrum-run-1"
    assert captured["method"] == "POST"
    assert captured["url"] == "http://ferrum.test/ga4gh/wes/v1/runs"


@pytest.mark.asyncio
async def test_ferrum_unreachable_is_502(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ferrum_drs_url", "http://ferrum.test/ga4gh/drs/v1")
    monkeypatch.setattr(settings, "ferrum_wes_url", None)
    with patch("app.services.ferrum_backend.httpx.AsyncClient", _BoomClient):
        response = await async_client.get("/ga4gh/drs/v1/objects/abc")
    assert response.status_code == 502
    assert "Ferrum unreachable" in response.json()["detail"]
