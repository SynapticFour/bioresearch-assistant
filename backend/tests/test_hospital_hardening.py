"""Hospital-bar hardening: isolation, allowlists, production start guards."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings, get_settings
from app.schemas.wes import RunRequest
from app.services import wes_service

OWNER_A = {"sub": "user-a", "email": "a@uk-example.de", "roles": ["researcher"]}
OWNER_B = {"sub": "user-b", "email": "b@uk-example.de", "roles": ["researcher"]}


def _hospital_settings(monkeypatch, **overrides: object) -> Settings:
    s = get_settings()
    monkeypatch.setattr(s, "environment", "production")
    monkeypatch.setattr(s, "deployment", "dfn")
    monkeypatch.setattr(s, "isolation_mode", "user")
    monkeypatch.setattr(s, "oidc_issuer", "https://idp.uk-example.de/realms/hospital")
    monkeypatch.setattr(s, "oidc_client_id", "bioresearch")
    monkeypatch.setattr(s, "cors_origins", ["https://bra.uk-example.de"])
    monkeypatch.setattr(s, "database_url", "postgresql+asyncpg://bra:unique-secret@db:5432/bra")
    for key, value in overrides.items():
        monkeypatch.setattr(s, key, value)
    return s


def test_assert_runtime_hardened_accepts_hospital_config(monkeypatch) -> None:
    _hospital_settings(monkeypatch).assert_runtime_hardened()


def test_assert_runtime_hardened_rejects_open_isolation(monkeypatch) -> None:
    with pytest.raises(RuntimeError, match="ISOLATION_MODE=open"):
        _hospital_settings(monkeypatch, isolation_mode="open").assert_runtime_hardened()


def test_assert_runtime_hardened_rejects_default_db_password(monkeypatch) -> None:
    with pytest.raises(RuntimeError, match="bioresearch"):
        _hospital_settings(
            monkeypatch,
            database_url="postgresql+asyncpg://bioresearch:bioresearch@db:5432/bioresearch",
        ).assert_runtime_hardened()


def test_assert_runtime_hardened_rejects_wildcard_cors(monkeypatch) -> None:
    with pytest.raises(RuntimeError, match="CORS"):
        _hospital_settings(monkeypatch, cors_origins=["*"]).assert_runtime_hardened()


def test_assert_runtime_hardened_rejects_missing_oidc(monkeypatch) -> None:
    with pytest.raises(RuntimeError, match="OIDC"):
        _hospital_settings(monkeypatch, oidc_issuer="", oidc_client_id="").assert_runtime_hardened()


def test_blast_database_allowlist_rejects_path() -> None:
    with pytest.raises(ValueError, match="allowlisted"):
        wes_service.resolve_blast_database("/etc/passwd")
    with pytest.raises(ValueError, match="allowlisted"):
        wes_service.resolve_blast_database("nt; cat /etc/shadow")
    assert wes_service.resolve_blast_database("nt") == "nt"
    assert wes_service.resolve_blast_database("/blast/db/swissprot") == "swissprot"


def test_local_nf_must_be_basename() -> None:
    wes_service._validate_workflow_url("main.nf")
    with pytest.raises(ValueError, match="basename"):
        wes_service._validate_workflow_url("../evil.nf")
    with pytest.raises(ValueError, match="basename"):
        wes_service._validate_workflow_url("subdir/pipeline.nf")


def test_helixtest_trs_disabled_outside_conformance(monkeypatch) -> None:
    monkeypatch.setattr(wes_service, "_helixtest_stubs_enabled", lambda: False)
    with pytest.raises(ValueError, match="HelixTest TRS stubs are disabled"):
        wes_service._validate_workflow_url(wes_service.HELIXTEST_TRS_ECHO)


@pytest.mark.asyncio
async def test_create_run_requires_user_outside_open(db_session, mocker) -> None:
    mocker.patch("app.services.wes_service.current_isolation_mode", return_value="user")
    req = RunRequest(
        workflow_url="main.nf",
        workflow_type="NEXTFLOW",
        workflow_type_version="1.0",
    )
    with pytest.raises(ValueError, match="Authenticated user required"):
        await wes_service.create_run(db_session, req)


@pytest.mark.asyncio
async def test_wes_run_not_visible_to_other_user(db_session, mocker, tmp_path) -> None:
    mocker.patch("app.services.wes_service.get_settings").return_value.wes_work_dir = str(tmp_path)
    mocker.patch("app.services.wes_service.current_isolation_mode", return_value="user")
    req = RunRequest(
        workflow_url="main.nf",
        workflow_type="NEXTFLOW",
        workflow_type_version="1.0",
    )
    run_id = await wes_service.create_run(db_session, req, current_user=OWNER_A)
    await db_session.flush()
    own = await wes_service.get_run(db_session, str(run_id), current_user=OWNER_A)
    other = await wes_service.get_run(db_session, str(run_id), current_user=OWNER_B)
    assert own is not None
    assert other is None


@pytest.mark.asyncio
async def test_oauth_callback_sets_httponly_cookie_and_redirects(
    unauthed_client,
) -> None:
    from app.api.v1.endpoints import auth as auth_ep

    settings = MagicMock()
    settings.auth_enabled = True
    settings.jwt_secret = "j" * 32
    settings.pseudonymization_encryption_key = "a" * 64
    settings.oidc_redirect_uri = "http://localhost:5173/api/v1/auth/callback"
    settings.oidc_client_id = "bra"
    settings.oidc_client_secret = "secret"
    settings.frontend_base_url = "http://localhost:5173"
    settings.session_cookie_name = "bra_access_token"
    settings.allows_unauthenticated_dev = True
    mock_auth = MagicMock()

    async def _oidc_config() -> dict:
        return {"token_endpoint": "https://idp.example/token"}

    mock_auth.get_oidc_config = _oidc_config

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"access_token": "tok-hospital", "expires_in": 3600}

    class _Client:
        async def __aenter__(self) -> "_Client":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> _Resp:
            return _Resp()

    from app.core.auth import get_auth_service
    from app.main import app

    app.dependency_overrides[get_auth_service] = lambda: mock_auth
    try:
        with (
            patch("app.api.v1.endpoints.auth.get_settings", return_value=settings),
            patch("app.api.v1.endpoints.auth.httpx.AsyncClient", return_value=_Client()),
        ):
            state = auth_ep._sign_oauth_state("oidc")
            resp = await unauthed_client.get(
                "/api/v1/auth/callback",
                params={"code": "abc", "state": state},
                cookies={
                    auth_ep._OAUTH_STATE_COOKIE: state,
                    auth_ep._OAUTH_VERIFIER_COOKIE: "verifier",
                },
                follow_redirects=False,
            )
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
    assert resp.status_code in (302, 307)
    assert "/auth/callback" in (resp.headers.get("location") or "")
    assert "bra_access_token" in resp.cookies
    cookie_header = resp.headers.get("set-cookie") or ""
    assert "httponly" in cookie_header.lower()
    assert "tok-hospital" not in (resp.text or "")
