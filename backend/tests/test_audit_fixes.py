"""Regression tests for the Python audit fixes (auth, WES, DRS, FAIR, health)."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.services.auth_service import extract_roles
from app.services.fair_export_service import FAIRExportService
from app.services.wes_service import ALLOWED_BLAST_PROGRAMS, _validate_workflow_url


@pytest.mark.asyncio
async def test_get_current_user_fail_closed_when_deployment_empty() -> None:
    """Empty DEPLOYMENT is production: no OIDC means 401, not a synthetic admin."""
    from app.core.auth import get_current_user

    settings = MagicMock()
    settings.auth_enabled = False
    settings.allows_unauthenticated_dev = False
    with patch("app.core.auth.get_settings", return_value=settings):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=None, auth_service=MagicMock())
    assert exc.value.status_code == 401


def test_extract_roles_from_keycloak_realm_access() -> None:
    """Admin checks must see Keycloak realm_access.roles, not only a top-level roles claim."""
    assert extract_roles({"realm_access": {"roles": ["admin", "user"]}}) == ["admin", "user"]
    assert extract_roles({"roles": ["researcher"]}) == ["researcher"]


@pytest.mark.asyncio
async def test_jwks_refreshes_on_unknown_kid() -> None:
    """Unknown kid triggers a JWKS refetch instead of caching forever."""
    from app.services.auth_service import AuthService

    service = AuthService()
    service._jwks = {"keys": [{"kty": "RSA", "kid": "old"}]}
    with patch.object(service, "get_jwks", new_callable=AsyncMock) as mock_jwks:
        mock_jwks.side_effect = [
            {"keys": [{"kty": "RSA", "kid": "old"}]},
            {"keys": [{"kty": "RSA", "kid": "new"}]},
        ]
        with patch(
            "app.services.auth_service._get_signing_key_from_jwks",
            side_effect=[ValueError("No matching key found in JWKS"), MagicMock()],
        ):
            with patch("app.services.auth_service.jwt.decode", return_value={"sub": "u1"}):
                claims = await service.verify_token("header.payload.sig")
    assert claims["sub"] == "u1"
    assert mock_jwks.await_count == 2
    assert mock_jwks.await_args_list[1].kwargs.get("force_refresh") is True


@pytest.mark.asyncio
async def test_oauth_callback_state_mismatch_400(unauthed_client: AsyncClient) -> None:
    """OIDC callback rejects missing/mismatched CSRF state cookie."""
    with patch("app.api.v1.endpoints.auth.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(auth_enabled=True)
        resp = await unauthed_client.get(
            "/api/v1/auth/callback",
            params={"code": "abc", "state": "attacker-state"},
        )
    assert resp.status_code == 400
    assert "state" in resp.json()["detail"].lower()


def test_blast_program_allowlist() -> None:
    """BLAST argv[0] is restricted to known NCBI programs."""
    assert "blastn" in ALLOWED_BLAST_PROGRAMS
    assert "python" not in ALLOWED_BLAST_PROGRAMS
    assert "/bin/sh" not in ALLOWED_BLAST_PROGRAMS


def test_wes_remote_url_allowed_with_host_allowlist(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "wes_allow_remote_workflows", True)
    monkeypatch.setattr(settings, "wes_allowed_workflow_hosts", ["workflows.example.org"])
    _validate_workflow_url("https://workflows.example.org/main.nf")
    with pytest.raises(ValueError, match="allowlisted"):
        _validate_workflow_url("https://evil.example/main.nf")


@pytest.mark.asyncio
async def test_fair_score_bonus_only_when_no_recommendations() -> None:
    """Complete packages keep a 100 score; missing fields must not collapse to 0."""
    svc = FAIRExportService()
    complete = await svc.check_fair_compliance(
        {"title": "Dataset", "license": "CC-BY-4.0", "funding": "DFG"}
    )
    assert complete.recommendations == []
    assert complete.score == 100

    incomplete = await svc.check_fair_compliance({})
    assert incomplete.recommendations
    assert incomplete.score == 50
    assert incomplete.score != 0


@pytest.mark.asyncio
async def test_drs_list_hides_other_users_objects(tmp_path, monkeypatch) -> None:
    """DRS listing is scoped; objects without a matching ACL are hidden in user mode."""
    from app.services import drs_service

    mock_settings = MagicMock()
    mock_settings.drs_storage_path = str(tmp_path)
    monkeypatch.setattr("app.services.drs_service.get_settings", lambda: mock_settings)
    monkeypatch.setattr(
        "app.services.drs_service.get_scope_filter",
        lambda user: {"user_id": user.get("sub")},
    )
    monkeypatch.setattr(
        "app.services.drs_service.get_scope_values",
        lambda user: {"user_id": user.get("sub"), "team_id": None},
    )

    owner = {"sub": "owner-1"}
    other = {"sub": "other-2"}
    object_id = drs_service.register_object("owned.txt", b"secret", current_user=owner)
    visible = drs_service.list_objects(current_user=owner)
    hidden = drs_service.list_objects(current_user=other)
    assert any(item["id"] == object_id for item in visible)
    assert not any(item["id"] == object_id for item in hidden)
    assert drs_service.get_object(object_id, current_user=other) is None
    assert drs_service.get_object(object_id, current_user=owner) is not None


@pytest.mark.asyncio
async def test_health_ready_503_body() -> None:
    """Disconnected DB readiness probe uses HTTP 503 with not_ready payload."""
    from app.core.database import get_db
    from app.main import app

    async def failing_db() -> AsyncGenerator[MagicMock, None]:
        session = MagicMock()
        session.execute = AsyncMock(side_effect=RuntimeError("connection lost"))
        yield session

    app.dependency_overrides[get_db] = failing_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/health/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "not_ready"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_db_rolls_back_safe_methods() -> None:
    """GET/HEAD/OPTIONS discard ORM writes; POST commits."""
    from app.core.database import get_db

    session = MagicMock()
    session.new = set()
    session.dirty = set()
    session.deleted = set()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    class _CM:
        async def __aenter__(self) -> MagicMock:
            return session

        async def __aexit__(self, *args: object) -> None:
            return None

    with patch("app.core.database.get_async_session_maker", return_value=lambda: _CM()):
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/api/v1/health"
        agen = get_db(request)
        await agen.__anext__()
        with pytest.raises(StopAsyncIteration):
            await agen.__anext__()
        session.rollback.assert_awaited()
        session.commit.assert_not_awaited()

        session.rollback.reset_mock()
        session.commit.reset_mock()
        request.method = "POST"
        agen = get_db(request)
        await agen.__anext__()
        with pytest.raises(StopAsyncIteration):
            await agen.__anext__()
        session.commit.assert_awaited()
        session.rollback.assert_not_awaited()


def test_unknown_isolation_mode_fails_closed() -> None:
    """Settings validator maps unknown ISOLATION_MODE to user, not open."""
    from app.core.config import Settings

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        pseudonymization_encryption_key="a" * 64,
        isolation_mode="not-a-mode",
    )
    assert settings.isolation_mode == "user"


def test_testing_env_refuses_production_deployment(monkeypatch) -> None:
    """TESTING=1 on a non-dev DEPLOYMENT must not start."""
    from app.main import assert_testing_env_safe

    monkeypatch.setenv("TESTING", "1")
    settings = MagicMock()
    settings.allows_unauthenticated_dev = False
    with patch("app.main.get_settings", return_value=settings):
        with pytest.raises(RuntimeError, match="TESTING=1"):
            assert_testing_env_safe()


@pytest.mark.asyncio
async def test_oauth_login_sets_pkce_challenge(unauthed_client: AsyncClient) -> None:
    """OIDC login advertises S256 PKCE and stores the verifier cookie."""
    settings = MagicMock()
    settings.auth_enabled = True
    settings.oidc_issuer = "https://idp.example"
    settings.oidc_client_id = "cid"
    settings.oidc_redirect_uri = "http://localhost/callback"
    settings.jwt_secret = "j" * 32
    settings.pseudonymization_encryption_key = "a" * 64
    settings.allows_unauthenticated_dev = True
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"authorization_endpoint": "https://idp.example/auth"}
    with patch("app.api.v1.endpoints.auth.get_settings", return_value=settings):
        with patch("app.api.v1.endpoints.auth.httpx.AsyncClient") as mock_client:
            inst = MagicMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = inst
            resp = await unauthed_client.get(
                "/api/v1/auth/login",
                params={"provider": "oidc"},
                follow_redirects=False,
            )
    assert resp.status_code in (302, 307)
    location = str(resp.headers.get("location") or "")
    assert "code_challenge=" in location
    assert "code_challenge_method=S256" in location
    assert "bra_oauth_verifier" in resp.cookies


@pytest.mark.asyncio
async def test_oauth_callback_missing_pkce_verifier_400(unauthed_client: AsyncClient) -> None:
    """Callback with a valid state cookie still requires the PKCE verifier."""
    from app.api.v1.endpoints import auth as auth_ep

    settings = MagicMock()
    settings.auth_enabled = True
    settings.jwt_secret = "j" * 32
    settings.pseudonymization_encryption_key = "a" * 64
    with patch("app.api.v1.endpoints.auth.get_settings", return_value=settings):
        state = auth_ep._sign_oauth_state("oidc")
        resp = await unauthed_client.get(
            "/api/v1/auth/callback",
            params={"code": "abc", "state": state},
            cookies={auth_ep._OAUTH_STATE_COOKIE: state},
        )
    assert resp.status_code == 400
    assert "pkce" in resp.json()["detail"].lower()


def test_drs_list_pagination(tmp_path, monkeypatch) -> None:
    """DRS list honors skip/limit after ACL filtering."""
    from app.services import drs_service

    mock_settings = MagicMock()
    mock_settings.drs_storage_path = str(tmp_path)
    monkeypatch.setattr("app.services.drs_service.get_settings", lambda: mock_settings)
    monkeypatch.setattr(
        "app.services.drs_service.get_scope_filter",
        lambda user: {"user_id": user.get("sub")},
    )
    monkeypatch.setattr(
        "app.services.drs_service.get_scope_values",
        lambda user: {"user_id": user.get("sub"), "team_id": None},
    )
    owner = {"sub": "owner-1"}
    for name in ("a.txt", "b.txt", "c.txt"):
        drs_service.register_object(name, name.encode(), current_user=owner)
    page = drs_service.list_objects(current_user=owner, skip=1, limit=1)
    assert len(page) == 1
    full = drs_service.list_objects(current_user=owner)
    assert len(full) == 3


@pytest.mark.asyncio
async def test_kill_run_process_uses_pid_file(tmp_path, monkeypatch) -> None:
    """Same-host cancel kills via executor.pid when this worker has no handle."""
    import signal

    from app.services import wes_service

    monkeypatch.setattr(wes_service, "_run_dir", lambda run_id: tmp_path / run_id)
    run_id = "run-pid"
    (tmp_path / run_id).mkdir()
    (tmp_path / run_id / "executor.pid").write_text("4242")
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(
        wes_service.os,
        "kill",
        lambda pid, sig: killed.append((pid, sig)),
    )
    await wes_service._kill_run_process(run_id)
    assert killed == [(4242, signal.SIGKILL)]
    assert not (tmp_path / run_id / "executor.pid").exists()


def test_phenopacket_hpo_conditions_sqlite_uses_contains() -> None:
    from app.services.phenoflow_service import _phenopacket_hpo_conditions

    conditions = _phenopacket_hpo_conditions(["HP:0001250"], "sqlite")
    assert len(conditions) == 1
