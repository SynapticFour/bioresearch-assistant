"""SSRF rules for registry-resolved Ferrum URLs. One test per rule."""

from __future__ import annotations

import logging

import pytest

from app.core.config import get_settings
from app.services.ferrum_backend import _resolve_base
from app.services.service_registry import (
    RegistryLookupError,
    choose_fresh_url,
    validate_service_url,
)

PUBLIC = ["203.0.113.10"]


def _check(
    url: str,
    allowlist: list[str] | None = None,
    scheme: str = "https",
    resolved: list[str] | None = None,
) -> str:
    return validate_service_url(
        url,
        registry_scheme=scheme,
        allowlist=allowlist or [],
        resolve_host=lambda _host: PUBLIC if resolved is None else resolved,
    )


def test_empty_allowlist_allows_a_public_host() -> None:
    assert _check("https://ferrum.example/ga4gh/drs/v1") == "https://ferrum.example/ga4gh/drs/v1"


def test_empty_allowlist_blocks_loopback() -> None:
    with pytest.raises(RegistryLookupError, match="loopback"):
        _check("https://127.0.0.1/ga4gh/drs/v1")
    with pytest.raises(RegistryLookupError, match="loopback"):
        _check("https://[::1]/ga4gh/drs/v1")


def test_empty_allowlist_blocks_link_local() -> None:
    with pytest.raises(RegistryLookupError, match="link-local"):
        _check("https://169.254.1.1/ga4gh/drs/v1")
    with pytest.raises(RegistryLookupError, match="link-local"):
        _check("https://[fe80::1]/ga4gh/drs/v1")


def test_empty_allowlist_blocks_cloud_metadata() -> None:
    with pytest.raises(RegistryLookupError, match="metadata"):
        _check("https://169.254.169.254/latest")
    with pytest.raises(RegistryLookupError, match="metadata"):
        _check("https://metadata.google.internal/computeMetadata")
    with pytest.raises(RegistryLookupError, match="metadata"):
        _check("https://[fd00:ec2::254]/latest")


def test_dns_answer_in_a_blocked_range_is_rejected() -> None:
    with pytest.raises(RegistryLookupError, match="loopback"):
        _check("https://ferrum.example/ga4gh/drs/v1", resolved=["127.0.0.1"])


def test_allowlist_explicitly_allows_a_restricted_host() -> None:
    assert _check("https://127.0.0.1/ga4gh/drs/v1", allowlist=["127.0.0.1"]).startswith(
        "https://127.0.0.1"
    )
    assert _check(
        "https://metadata.google.internal/latest",
        allowlist=["metadata.google.internal"],
        resolved=["169.254.169.254"],
    ).startswith("https://metadata.google.internal")


def test_nonempty_allowlist_rejects_other_hosts() -> None:
    with pytest.raises(RegistryLookupError, match="allowlist"):
        _check("https://other.example/ga4gh/drs/v1", allowlist=["ferrum.example"])


def test_scheme_must_match_the_registry_and_be_http_or_https() -> None:
    with pytest.raises(RegistryLookupError, match="scheme"):
        _check("http://ferrum.example/ga4gh/drs/v1", scheme="https")
    with pytest.raises(RegistryLookupError, match="scheme"):
        _check("file:///etc/passwd", scheme="https")


def test_several_fresh_rows_error_unless_id_or_organization_selects_one() -> None:
    rows = [
        {
            "id": "org.example.a",
            "url": "https://a.example/ga4gh/drs/v1",
            "type": {"artifact": "drsservice"},
            "organization": {"name": "A"},
        },
        {
            "id": "org.example.b",
            "url": "https://b.example/ga4gh/drs/v1",
            "type": {"artifact": "drsservice"},
            "organization": {"name": "B"},
        },
    ]
    with pytest.raises(RegistryLookupError, match="more than one fresh drsservice"):
        choose_fresh_url(rows, "drsservice")
    assert (
        choose_fresh_url(rows, "drsservice", service_id="org.example.b")
        == "https://b.example/ga4gh/drs/v1"
    )
    assert (
        choose_fresh_url(rows, "drsservice", organization="A") == "https://a.example/ga4gh/drs/v1"
    )


def test_stale_rows_are_skipped_and_a_missing_stale_field_is_fresh() -> None:
    rows = [
        {
            "id": "old",
            "url": "https://old.example/ga4gh/drs/v1",
            "type": {"artifact": "drsservice"},
            "stale": True,
        },
        {
            "id": "new",
            "url": "https://new.example/ga4gh/drs/v1",
            "type": {"artifact": "drsservice"},
        },
    ]
    assert choose_fresh_url(rows, "drsservice") == "https://new.example/ga4gh/drs/v1"
    with pytest.raises(RegistryLookupError, match="no fresh drsservice"):
        choose_fresh_url(rows[:1], "drsservice")


@pytest.mark.asyncio
async def test_lookup_failure_uses_the_static_url_and_says_so(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "service_registry_url", "https://registry.example")
    monkeypatch.setattr(settings, "service_registry_host_allowlist", [])
    monkeypatch.setattr(settings, "service_registry_service_id", None)
    monkeypatch.setattr(settings, "service_registry_organization", None)
    monkeypatch.setattr(settings, "service_registry_cache_ttl_seconds", 60)

    async def _fail(**_kwargs: object) -> str:
        raise RegistryLookupError("registry down")

    monkeypatch.setattr("app.services.ferrum_backend.lookup_service_url", _fail)
    static = "https://static.example/ga4gh/drs/v1"
    with caplog.at_level(logging.WARNING):
        base, from_registry = await _resolve_base(
            settings, artifact="drsservice", static_url=static
        )
    assert base == static
    assert from_registry is False
    assert "static fallback" in caplog.text
