"""Tests for configurable isolation (user/team/open)."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.auth import get_current_user
from app.main import app

USER_A = {
    "sub": "user-a",
    "email": "a@test.de",
    "roles": [],
    "passports": [],
    "visas": [],
}
USER_B = {
    "sub": "user-b",
    "email": "b@test.de",
    "roles": [],
    "passports": [],
    "visas": [],
}
USER_C_UKHD = {
    "sub": "user-c",
    "email": "c@ukhd.de",
    "roles": [],
    "passports": [],
    "visas": [],
}
USER_D_UKHD = {
    "sub": "user-d",
    "email": "d@ukhd.de",
    "roles": [],
    "passports": [],
    "visas": [],
}

PAPER_A = {
    "pmid": "isolation-test-001",
    "title": "Paper von User A",
    "abstract": "Abstract A",
    "authors": ["User A"],
    "year": "2024",
    "journal": "Test Journal",
}

PAPER_TEAM = {
    "pmid": "isolation-test-002",
    "title": "Team Paper UKHD",
    "abstract": "Abstract Team",
    "authors": ["User C"],
    "year": "2024",
    "journal": "Test Journal",
}


async def _override_user_a() -> dict:
    return USER_A


async def _override_user_b() -> dict:
    return USER_B


async def _override_user_c() -> dict:
    return USER_C_UKHD


async def _override_user_d() -> dict:
    return USER_D_UKHD


@pytest.mark.asyncio
async def test_scope_filter_user_mode() -> None:
    """get_scope_filter returns user_id in user mode."""
    from app.core.isolation import get_scope_filter

    with patch("app.core.isolation.get_settings") as m:
        m.return_value.isolation_mode = "user"
        scope = get_scope_filter(USER_A)
    assert scope == {"user_id": "user-a"}


@pytest.mark.asyncio
async def test_scope_filter_team_mode() -> None:
    """get_scope_filter returns team_id in team mode."""
    from app.core.isolation import get_scope_filter

    with patch("app.core.isolation.get_settings") as m:
        m.return_value.isolation_mode = "team"
        scope = get_scope_filter(USER_C_UKHD)
    assert scope == {"team_id": "domain:ukhd.de"}


@pytest.mark.asyncio
async def test_scope_filter_open_mode() -> None:
    """get_scope_filter returns empty dict in open mode."""
    from app.core.isolation import get_scope_filter

    with patch("app.core.isolation.get_settings") as m:
        m.return_value.isolation_mode = "open"
        scope = get_scope_filter(USER_A)
    assert scope == {}


@pytest.mark.asyncio
async def test_scope_filter_unknown_mode_fails_closed() -> None:
    """Unknown ISOLATION_MODE is treated as user, not open."""
    from app.core.isolation import get_scope_filter

    with patch("app.core.isolation.get_settings") as m:
        m.return_value.isolation_mode = "typo"
        scope = get_scope_filter(USER_A)
    assert scope == {"user_id": "user-a"}


@pytest.mark.asyncio
async def test_extract_team_id_from_email() -> None:
    """Team ID is extracted from email domain."""
    from app.core.isolation import _extract_team_id

    team_id = _extract_team_id(USER_C_UKHD)
    assert team_id == "domain:ukhd.de"


@pytest.mark.asyncio
async def test_extract_team_id_from_ga4gh_passport() -> None:
    """Team ID is extracted from GA4GH Passport visa."""
    from app.core.isolation import _extract_team_id

    user_with_passport = {
        "sub": "user-passport",
        "email": "forscher@ukhd.de",
        "visas": [
            {
                "type": "AffiliationAndRole",
                "value": "faculty@ukhd.de",
            }
        ],
    }
    team_id = _extract_team_id(user_with_passport)
    assert team_id == "org:faculty@ukhd.de"


@pytest.mark.asyncio
async def test_auth_me_includes_isolation_info(async_client: AsyncClient) -> None:
    """GET /auth/me returns isolation_mode, team_id and scope."""
    resp = await async_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert "isolation_mode" in data
    assert "team_id" in data
    assert "scope" in data


@pytest.mark.asyncio
async def test_user_isolation_shows_own_papers(async_client: AsyncClient) -> None:
    """In user mode, user sees their own papers."""
    app.dependency_overrides[get_current_user] = _override_user_a
    try:
        with patch("app.core.isolation.get_settings") as m:
            m.return_value.isolation_mode = "user"
            resp_post = await async_client.post(
                "/api/v1/library/papers",
                json=PAPER_A,
            )
        assert resp_post.status_code in (200, 201)
        resp = await async_client.get("/api/v1/library/papers")
        assert resp.status_code == 200
        titles = [p["title"] for p in resp.json()]
        assert "Paper von User A" in titles
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_user_isolation_hides_other_papers(async_client: AsyncClient) -> None:
    """In user mode, user B does not see papers from user A."""
    app.dependency_overrides[get_current_user] = _override_user_a
    try:
        with patch("app.core.isolation.get_settings") as m:
            m.return_value.isolation_mode = "user"
            await async_client.post("/api/v1/library/papers", json=PAPER_A)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    app.dependency_overrides[get_current_user] = _override_user_b
    try:
        with patch("app.core.isolation.get_settings") as m:
            m.return_value.isolation_mode = "user"
            resp = await async_client.get("/api/v1/library/papers")
        assert resp.status_code == 200
        titles = [p["title"] for p in resp.json()]
        assert "Paper von User A" not in titles
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_team_isolation_shares_within_domain(async_client: AsyncClient) -> None:
    """In team mode, all @ukhd.de see the same papers."""
    app.dependency_overrides[get_current_user] = _override_user_c
    try:
        with patch("app.core.isolation.get_settings") as m:
            m.return_value.isolation_mode = "team"
            await async_client.post("/api/v1/library/papers", json=PAPER_TEAM)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    app.dependency_overrides[get_current_user] = _override_user_d
    try:
        with patch("app.core.isolation.get_settings") as m:
            m.return_value.isolation_mode = "team"
            resp = await async_client.get("/api/v1/library/papers")
        assert resp.status_code == 200
        titles = [p["title"] for p in resp.json()]
        assert "Team Paper UKHD" in titles
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_team_isolation_hides_from_other_domain(async_client: AsyncClient) -> None:
    """In team mode, test.de does not see ukhd.de papers."""
    app.dependency_overrides[get_current_user] = _override_user_c
    try:
        with patch("app.core.isolation.get_settings") as m:
            m.return_value.isolation_mode = "team"
            await async_client.post("/api/v1/library/papers", json=PAPER_TEAM)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    app.dependency_overrides[get_current_user] = _override_user_a
    try:
        with patch("app.core.isolation.get_settings") as m:
            m.return_value.isolation_mode = "team"
            resp = await async_client.get("/api/v1/library/papers")
        assert resp.status_code == 200
        titles = [p["title"] for p in resp.json()]
        assert "Team Paper UKHD" not in titles
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_open_mode_shows_all(async_client: AsyncClient) -> None:
    """In open mode, list papers returns 200."""
    with patch("app.core.isolation.get_settings") as m:
        m.return_value.isolation_mode = "open"
        resp = await async_client.get("/api/v1/library/papers")
    assert resp.status_code == 200
