"""Tests for GA4GH WES v1.1 service. Nextflow execution is mocked."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.workflow_run import WorkflowRun
from app.schemas.wes import RunRequest, State
from app.services import wes_service

OWNER = {"sub": "dev-user", "email": "t@test.de", "roles": ["admin"]}


@pytest.fixture
def mock_nextflow(mocker):
    """Mock asyncio.create_subprocess_exec so Nextflow is not actually run."""
    mock_process = mocker.MagicMock()
    mock_process.communicate = mocker.AsyncMock(return_value=(b"Workflow completed", b""))
    mock_process.returncode = 0
    mock = mocker.patch("app.services.wes_service.asyncio.create_subprocess_exec")
    mock.return_value = mock_process
    return mock


@pytest.fixture
def wes_work_dir(tmp_path, mocker):
    """Point WES work dir to tmp_path."""
    mocker.patch("app.services.wes_service.get_settings").return_value.wes_work_dir = str(tmp_path)
    return tmp_path


@pytest.fixture
def run_request():
    """Minimal valid RunRequest."""
    return RunRequest(
        workflow_url="main.nf",
        workflow_type="NEXTFLOW",
        workflow_type_version="1.0",
        workflow_params={"input": "data.txt"},
    )


@pytest.mark.asyncio
async def test_submit_run_creates_workflow_run_in_db(
    db_session, mock_nextflow, wes_work_dir, run_request
):
    """create_run adds a WorkflowRun row in QUEUED state."""
    # Prevent background task from using real DB (patch update_db path)
    run_id = await wes_service.create_run(db_session, run_request, current_user=OWNER)
    await db_session.flush()
    stmt = select(WorkflowRun).where(WorkflowRun.run_id == run_id)
    r = await db_session.execute(stmt)
    row = r.scalars().first()
    assert row is not None
    assert row.state == State.QUEUED.value


@pytest.mark.asyncio
async def test_submit_run_returns_run_id(db_session, mock_nextflow, wes_work_dir, run_request):
    """create_run returns a valid run_id (UUID)."""
    run_id = await wes_service.create_run(db_session, run_request, current_user=OWNER)
    assert run_id is not None
    assert str(run_id)  # UUID string representation


@pytest.mark.asyncio
async def test_get_run_status_returns_correct_state(db_session):
    """get_run and run_to_run_status return correct state."""
    run_id = uuid4()
    db_session.add(
        WorkflowRun(
            run_id=run_id,
            state=State.RUNNING.value,
            workflow_url="x.nf",
            workflow_type="NEXTFLOW",
            workflow_type_version="1.0",
            user_id="dev-user",
        )
    )
    await db_session.flush()
    run = await wes_service.get_run(db_session, str(run_id), current_user=OWNER)
    assert run is not None
    status = wes_service.run_to_run_status(run)
    assert status.run_id == str(run_id)
    assert status.state == State.RUNNING


@pytest.mark.asyncio
async def test_cancel_run_updates_state(db_session):
    """cancel_run sets state to CANCELED."""
    run_id = uuid4()
    db_session.add(
        WorkflowRun(
            run_id=run_id,
            state=State.QUEUED.value,
            workflow_url="x.nf",
            workflow_type="NEXTFLOW",
            workflow_type_version="1.0",
            user_id="dev-user",
        )
    )
    await db_session.flush()
    ok = await wes_service.cancel_run(db_session, str(run_id), current_user=OWNER)
    assert ok is True
    r = await db_session.execute(select(WorkflowRun).where(WorkflowRun.run_id == run_id))
    row = r.scalars().first()
    assert row is not None
    assert row.state == State.CANCELED.value


@pytest.mark.asyncio
async def test_get_nonexistent_run_raises_404(db_session):
    """get_run for non-existent run_id returns None (API layer returns 404)."""
    run = await wes_service.get_run(db_session, str(uuid4()), current_user=OWNER)
    assert run is None


@pytest.mark.asyncio
async def test_get_run_invalid_uuid_returns_none(db_session):
    """get_run with invalid UUID string returns None."""
    run = await wes_service.get_run(db_session, "not-a-uuid", current_user=OWNER)
    assert run is None


def test_validate_workflow_url_rejects_http_descriptor_by_default() -> None:
    """Remote http(s) workflow URLs are disabled unless WES_ALLOW_REMOTE_WORKFLOWS=1."""
    with pytest.raises(ValueError, match="Remote http"):
        wes_service._validate_workflow_url("https://example.org/wf/main.nf")


def test_validate_workflow_url_accepts_http_descriptor_when_enabled(monkeypatch) -> None:
    """Remote workflow descriptors over https are allowed when opted in."""
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "wes_allow_remote_workflows", True)
    wes_service._validate_workflow_url("https://example.org/wf/main.nf")


def test_validate_workflow_url_rejects_parent_segments_in_path() -> None:
    """Path traversal in workflow_url must be rejected."""
    with pytest.raises(ValueError, match="\\.\\."):
        wes_service._validate_workflow_url("https://example.org/../../etc/passwd")


def test_validate_workflow_url_accepts_helixtest_trs_descriptors() -> None:
    """SynapticFour/HelixTest TRS conformance stubs are allowlisted."""
    for url in wes_service.HELIXTEST_TRS_URLS:
        wes_service._validate_workflow_url(url)


def test_normalize_workflow_type_aliases() -> None:
    """WES workflow_type aliases (Ferrum-style NFL/NXF → NEXTFLOW)."""
    assert wes_service._normalize_workflow_type("NFL") == "NEXTFLOW"
    assert wes_service._normalize_workflow_type("nxf") == "NEXTFLOW"
    assert wes_service._normalize_workflow_type("cwl") == "CWL"
    assert wes_service._normalize_workflow_type("custom") == "custom"


@pytest.mark.asyncio
async def test_create_run_normalizes_workflow_type_alias(
    db_session, mock_nextflow, wes_work_dir
) -> None:
    """create_run persists canonical NEXTFLOW when client sends NFL."""
    req = RunRequest(
        workflow_url="main.nf",
        workflow_type="NFL",
        workflow_type_version="DSL2",
    )
    run_id = await wes_service.create_run(db_session, req, current_user=OWNER)
    await db_session.flush()
    stmt = select(WorkflowRun).where(WorkflowRun.run_id == run_id)
    row = (await db_session.execute(stmt)).scalars().first()
    assert row is not None
    assert row.workflow_type == "NEXTFLOW"


@pytest.mark.asyncio
async def test_list_runs_filters_by_state(db_session) -> None:
    """list_runs optional state_filter restricts rows to that state.

    Do not assert total row count: other tests may leave QUEUED rows in the
    shared in-memory engine (StaticPool); we only verify our fixtures and
    that every returned row matches the filter.
    """
    r1 = uuid4()
    r2 = uuid4()
    db_session.add(
        WorkflowRun(
            run_id=r1,
            state=State.COMPLETE.value,
            workflow_url="a.nf",
            workflow_type="NEXTFLOW",
            workflow_type_version="1.0",
            user_id="dev-user",
        )
    )
    db_session.add(
        WorkflowRun(
            run_id=r2,
            state=State.QUEUED.value,
            workflow_url="b.nf",
            workflow_type="NEXTFLOW",
            workflow_type_version="1.0",
            user_id="dev-user",
        )
    )
    await db_session.flush()
    rows, _ = await wes_service.list_runs(
        db_session,
        page_size=100,
        state_filter=State.QUEUED.value,
        current_user=OWNER,
    )
    returned_ids = {r.run_id for r in rows}
    assert r2 in returned_ids
    assert r1 not in returned_ids
    assert all(r.state == State.QUEUED.value for r in rows)
