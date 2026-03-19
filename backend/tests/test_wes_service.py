"""Tests for GA4GH WES v1.1 service. Nextflow execution is mocked."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.workflow_run import WorkflowRun
from app.schemas.wes import RunRequest, State
from app.services import wes_service


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
    run_id = await wes_service.create_run(db_session, run_request)
    await db_session.flush()
    stmt = select(WorkflowRun).where(WorkflowRun.run_id == run_id)
    r = await db_session.execute(stmt)
    row = r.scalars().first()
    assert row is not None
    assert row.state == State.QUEUED.value


@pytest.mark.asyncio
async def test_submit_run_returns_run_id(db_session, mock_nextflow, wes_work_dir, run_request):
    """create_run returns a valid run_id (UUID)."""
    run_id = await wes_service.create_run(db_session, run_request)
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
        )
    )
    await db_session.flush()
    run = await wes_service.get_run(db_session, str(run_id))
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
        )
    )
    await db_session.flush()
    ok = await wes_service.cancel_run(db_session, str(run_id))
    assert ok is True
    r = await db_session.execute(select(WorkflowRun).where(WorkflowRun.run_id == run_id))
    row = r.scalars().first()
    assert row is not None
    assert row.state == State.CANCELED.value


@pytest.mark.asyncio
async def test_get_nonexistent_run_raises_404(db_session):
    """get_run for non-existent run_id returns None (API layer returns 404)."""
    run = await wes_service.get_run(db_session, str(uuid4()))
    assert run is None


@pytest.mark.asyncio
async def test_get_run_invalid_uuid_returns_none(db_session):
    """get_run with invalid UUID string returns None."""
    run = await wes_service.get_run(db_session, "not-a-uuid")
    assert run is None


def test_validate_workflow_url_accepts_http_descriptor() -> None:
    """Remote workflow descriptors over https are allowed (WES / Ferrum-aligned)."""
    wes_service._validate_workflow_url("https://example.org/wf/main.nf")


def test_validate_workflow_url_rejects_parent_segments_in_path() -> None:
    """Path traversal in workflow_url must be rejected."""
    with pytest.raises(ValueError, match="\\.\\."):
        wes_service._validate_workflow_url("https://example.org/../../etc/passwd")
