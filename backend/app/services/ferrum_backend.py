"""Optional Ferrum DRS/WES client (GA4GH HTTP proxy).

When ``FERRUM_DRS_URL`` / ``FERRUM_WES_URL`` are set, BRA forwards the matching
``/ga4gh/drs/v1`` and ``/ga4gh/wes/v1`` traffic to Ferrum. Standalone local DRS/WES
remains the default. One institute, one DRS: Ferrum's ``service-info`` is the
source of truth when the proxy is on.
"""

from __future__ import annotations

import logging
import socket

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.core.config import Settings, get_settings
from app.services.service_registry import RegistryLookupError, lookup_service_url

logger = logging.getLogger(__name__)

_DRS_PREFIX = "/ga4gh/drs/v1"
_WES_PREFIX = "/ga4gh/wes/v1"

_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "content-encoding",
}


def build_upstream_url(base: str, prefix: str, path: str, query: str) -> str:
    """Map a BRA GA4GH path onto the Ferrum base URL (which already includes the prefix)."""
    rest = path[len(prefix) :] if path.startswith(prefix) else path
    if not rest:
        rest = "/"
    elif not rest.startswith("/"):
        rest = "/" + rest
    target = base.rstrip("/") + rest
    if query:
        target = f"{target}?{query}"
    return target


async def maybe_proxy_ferrum(request: Request) -> Response | None:
    """Proxy DRS/WES to Ferrum when a URL is configured or resolved; else ``None``."""
    settings = get_settings()
    path = request.url.path
    if path.startswith(_DRS_PREFIX) and (settings.service_registry_url or settings.ferrum_drs_url):
        base, from_registry = await _resolve_base(
            settings,
            artifact="drsservice",
            static_url=settings.ferrum_drs_url,
        )
        if not base:
            return JSONResponse(
                status_code=502,
                content={"detail": "service registry lookup failed for drsservice"},
            )
        return await _proxy(
            request,
            base_url=base,
            prefix=_DRS_PREFIX,
            bearer_token=settings.ferrum_bearer_token,
            follow_redirects=not from_registry,
        )
    if path.startswith(_WES_PREFIX) and (settings.service_registry_url or settings.ferrum_wes_url):
        base, from_registry = await _resolve_base(
            settings,
            artifact="wes",
            static_url=settings.ferrum_wes_url,
        )
        if not base:
            return JSONResponse(
                status_code=502,
                content={"detail": "service registry lookup failed for wes"},
            )
        return await _proxy(
            request,
            base_url=base,
            prefix=_WES_PREFIX,
            bearer_token=settings.ferrum_bearer_token,
            follow_redirects=not from_registry,
        )
    return None


async def _resolve_base(
    settings: Settings,
    *,
    artifact: str,
    static_url: str | None,
) -> tuple[str | None, bool]:
    registry = settings.service_registry_url
    if not registry:
        return static_url, False
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0), follow_redirects=False) as client:
            url = await lookup_service_url(
                registry_url=registry,
                artifact=artifact,
                allowlist=list(settings.service_registry_host_allowlist),
                service_id=settings.service_registry_service_id,
                organization=settings.service_registry_organization,
                cache_ttl_seconds=settings.service_registry_cache_ttl_seconds,
                client=client,
                resolve_host=_resolve_host,
            )
        return url, True
    except (RegistryLookupError, httpx.HTTPError) as exc:
        if static_url:
            logger.warning(
                "service registry lookup failed for %s; using static fallback: %s",
                artifact,
                exc,
            )
            return static_url, False
        logger.warning("service registry lookup failed for %s: %s", artifact, exc)
        return None, True


def _resolve_host(host: str) -> list[str]:
    return [item[4][0] for item in socket.getaddrinfo(host, None)]


async def _proxy(
    request: Request,
    *,
    base_url: str,
    prefix: str,
    bearer_token: str | None,
    follow_redirects: bool = True,
) -> Response:
    target = build_upstream_url(base_url, prefix, request.url.path, request.url.query)
    headers: dict[str, str] = {}
    for key, value in request.headers.items():
        lowered = key.lower()
        if lowered in _HOP_BY_HOP or lowered == "authorization":
            continue
        headers[key] = value
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    elif auth := request.headers.get("authorization"):
        headers["Authorization"] = auth

    body = await request.body()
    timeout = httpx.Timeout(60.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=follow_redirects) as client:
            upstream = await client.request(
                request.method,
                target,
                headers=headers,
                content=body,
            )
    except httpx.RequestError as exc:
        logger.warning("Ferrum GA4GH proxy failed for %s: %s", target, exc)
        return JSONResponse(
            status_code=502,
            content={"detail": f"Ferrum unreachable at {base_url.rstrip('/')}: {exc}"},
        )

    resp_headers = {
        key: value for key, value in upstream.headers.items() if key.lower() not in _HOP_BY_HOP
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=resp_headers,
        media_type=upstream.headers.get("content-type"),
    )
