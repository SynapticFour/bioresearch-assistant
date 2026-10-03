"""Resolve Ferrum DRS/WES base URLs from a GA4GH service registry.

An empty host allowlist does not restrict ordinary public hosts. That is unsafe
for a public deployment. Loopback, link-local, and cloud metadata addresses are
still refused unless that host is listed.
"""

from __future__ import annotations

import ipaddress
import logging
import time
from collections.abc import Callable
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

METADATA_HOSTS = frozenset({"metadata.google.internal", "metadata.goog"})
METADATA_IPS = frozenset(
    {
        ipaddress.ip_address("169.254.169.254"),
        ipaddress.ip_address("169.254.170.2"),
        ipaddress.ip_address("fd00:ec2::254"),
    }
)

_CACHE: dict[tuple[str, str, str, str], tuple[float, str]] = {}


class RegistryLookupError(Exception):
    """A registry lookup or URL check failed closed."""


def clear_registry_cache() -> None:
    _CACHE.clear()


def restricted_address_kind(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str | None:
    """Return why an address must not be fetched, or None when it is ordinary."""
    if address.is_loopback or address.is_unspecified:
        return "loopback"
    if address in METADATA_IPS:
        return "metadata"
    if address.is_link_local:
        return "link-local"
    return None


def validate_service_url(
    url: str,
    *,
    registry_scheme: str,
    allowlist: list[str],
    resolve_host: Callable[[str], list[str]],
) -> str:
    """Accept a registry URL or raise ``RegistryLookupError``.

    ``allowlist`` empty skips the hostname restriction and still blocks
    loopback, link-local, and metadata. A listed host is an explicit allow,
    including for those addresses.
    """
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise RegistryLookupError("service URL scheme must be http or https")
    if parsed.scheme != registry_scheme:
        raise RegistryLookupError("service URL scheme must match the registry URL")
    if parsed.username or parsed.password:
        raise RegistryLookupError("service URL must not carry userinfo")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise RegistryLookupError("service URL has no host")
    allowed = {item.lower().rstrip(".") for item in allowlist if item.strip()}
    explicit = host in allowed
    if allowed and not explicit:
        raise RegistryLookupError("service host is not in the allowlist")
    if host in METADATA_HOSTS and not explicit:
        raise RegistryLookupError("cloud metadata host is blocked")
    addresses = _addresses_for(host, resolve_host)
    for address in addresses:
        kind = restricted_address_kind(address)
        if kind and not explicit:
            raise RegistryLookupError(f"{kind} address is blocked")
    return url


def choose_fresh_url(
    entries: list[dict],
    artifact: str,
    *,
    service_id: str | None = None,
    organization: str | None = None,
) -> str:
    """Pick the one fresh URL for ``artifact``.

    A missing ``stale`` field is fresh. Zero or several fresh rows is an error
    unless ``service_id`` or ``organization`` narrows them to one.
    """
    fresh = [
        entry for entry in entries if _matches(entry, artifact) and not entry.get("stale", False)
    ]
    if service_id:
        fresh = [entry for entry in fresh if str(entry.get("id") or "") == service_id]
    if organization:
        fresh = [
            entry
            for entry in fresh
            if str((entry.get("organization") or {}).get("name") or "") == organization
        ]
    if len(fresh) == 1:
        url = fresh[0].get("url")
        if not isinstance(url, str) or not url:
            raise RegistryLookupError(f"fresh {artifact} entry has no url")
        return url
    if not fresh:
        raise RegistryLookupError(f"no fresh {artifact} entry")
    raise RegistryLookupError(f"more than one fresh {artifact} entry")


async def lookup_service_url(
    *,
    registry_url: str,
    artifact: str,
    allowlist: list[str],
    service_id: str | None,
    organization: str | None,
    cache_ttl_seconds: float,
    client: httpx.AsyncClient,
    resolve_host: Callable[[str], list[str]],
    now: float | None = None,
) -> str:
    """GET the registry, choose one fresh row, and check the URL."""
    moment = time.monotonic() if now is None else now
    cache_key = (
        registry_url.rstrip("/"),
        artifact,
        service_id or "",
        organization or "",
    )
    cached = _CACHE.get(cache_key)
    if cached and moment - cached[0] < cache_ttl_seconds:
        return cached[1]
    registry = urlsplit(registry_url)
    if registry.scheme not in {"http", "https"}:
        raise RegistryLookupError("registry URL scheme must be http or https")
    response = await client.get(
        f"{registry_url.rstrip('/')}/services",
        params={"type": artifact},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise RegistryLookupError("registry response was not a list")
    chosen = choose_fresh_url(
        payload,
        artifact,
        service_id=service_id,
        organization=organization,
    )
    checked = validate_service_url(
        chosen,
        registry_scheme=registry.scheme,
        allowlist=allowlist,
        resolve_host=resolve_host,
    )
    _CACHE[cache_key] = (moment, checked)
    return checked


def _matches(entry: dict, artifact: str) -> bool:
    type_info = entry.get("type") or {}
    found = str(type_info.get("artifact") or "")
    return found == artifact


def _addresses_for(
    host: str, resolve_host: Callable[[str], list[str]]
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        resolved = resolve_host(host)
    addresses = []
    for item in resolved:
        addresses.append(ipaddress.ip_address(item))
    if not addresses:
        raise RegistryLookupError("service host did not resolve")
    return addresses
