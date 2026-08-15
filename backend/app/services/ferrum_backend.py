"""Optional Ferrum DRS/WES client (GA4GH HTTP proxy).

When ``FERRUM_DRS_URL`` / ``FERRUM_WES_URL`` are set, BRA forwards the matching
``/ga4gh/drs/v1`` and ``/ga4gh/wes/v1`` traffic to Ferrum. Standalone local DRS/WES
remains the default. One institute, one DRS: Ferrum's ``service-info`` is the
source of truth when the proxy is on.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.core.config import get_settings

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
    """Proxy DRS/WES to Ferrum when the matching URL is configured; else ``None``."""
    settings = get_settings()
    path = request.url.path
    if settings.ferrum_drs_url and path.startswith(_DRS_PREFIX):
        return await _proxy(
            request,
            base_url=settings.ferrum_drs_url,
            prefix=_DRS_PREFIX,
            bearer_token=settings.ferrum_bearer_token,
        )
    if settings.ferrum_wes_url and path.startswith(_WES_PREFIX):
        return await _proxy(
            request,
            base_url=settings.ferrum_wes_url,
            prefix=_WES_PREFIX,
            bearer_token=settings.ferrum_bearer_token,
        )
    return None


async def _proxy(
    request: Request,
    *,
    base_url: str,
    prefix: str,
    bearer_token: str | None,
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
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
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
