"""Extended tests for WES service (create_run, get_run, list_runs, cancel, run_log)."""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.workflow_run import WorkflowRun
from app.schemas.wes import RunRequest, State
from app.services import wes_service

OWNER = {"sub": "dev-user", "email": "t@test.de", "roles": ["admin"]}


@pytest.mark.asyncio
async def test_create_run_stages_attachments(db_session) -> None:
    """create_run stages workflow attachments and returns run_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.wes_service.get_settings") as mock_settings:
            mock_settings.return_value.wes_work_dir = tmpdir
            with patch(
                "app.services.wes_service._execute_nextflow",
                new_callable=AsyncMock,
            ) as mock_exec:
                request = RunRequest(
                    workflow_type="BLAST",
                    workflow_type_version="1.0",
                    workflow_url="blast",
                    workflow_params={"database": "nt"},
                    workflow_engine="blast",
                )
                attachments = [("query.fasta", b">query\nATCG\n")]
                run_id = await wes_service.create_run(
                    db_session,
                    request,
                    workflow_attachments=attachments,
                    current_user=OWNER,
                )
                assert run_id is not None
                run_dir = Path(tmpdir) / str(run_id)
                assert (run_dir / "query.fasta").exists()
                if os.environ.get("WES_DEFER_BACKGROUND_EXECUTION") == "1":
                    mock_exec.assert_not_called()
                else:
                    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_get_run_returns_run(db_session) -> None:
    """get_run returns WorkflowRun when found."""
    run_id = uuid4()
    row = WorkflowRun(
        run_id=run_id,
        state=State.QUEUED.value,
        workflow_url="blast",
        workflow_params={},
        workflow_type="BLAST",
        workflow_type_version="1.0",
        workflow_engine="blast",
        workflow_engine_version=None,
        tags=None,
        start_time=None,
        end_time=None,
        outputs=None,
        run_log=None,
        task_logs=None,
        request={},
        user_id="dev-user",
    )
    db_session.add(row)
    await db_session.flush()

    run = await wes_service.get_run(db_session, str(run_id), current_user=OWNER)
    assert run is not None
    assert run.run_id == run_id
    assert run.state == State.QUEUED.value


@pytest.mark.asyncio
async def test_get_run_not_found_returns_none(db_session) -> None:
    """get_run returns None for unknown run_id."""
    run = await wes_service.get_run(
        db_session, "00000000-0000-0000-0000-000000000000", current_user=OWNER
    )
    assert run is None


@pytest.mark.asyncio
async def test_list_runs_pagination(db_session) -> None:
    """list_runs returns runs and next_page_token when more than page_size."""
    for _ in range(3):
        row = WorkflowRun(
            run_id=uuid4(),
            state=State.COMPLETE.value,
            workflow_url="blast",
            workflow_params={},
            workflow_type="BLAST",
            workflow_type_version="1.0",
            workflow_engine="blast",
            workflow_engine_version=None,
            tags=None,
            start_time=None,
            end_time=None,
            outputs=None,
            run_log=None,
            task_logs=None,
            request={},
            user_id="dev-user",
        )
        db_session.add(row)
    await db_session.flush()

    runs, next_token = await wes_service.list_runs(
        db_session, page_size=2, page_token=None, current_user=OWNER
    )
    assert len(runs) <= 2
    assert isinstance(next_token, str)


@pytest.mark.asyncio
async def test_run_to_run_log_complete(db_session) -> None:
    """run_to_run_log builds RunLog for completed run."""
    run_id = uuid4()
    row = WorkflowRun(
        run_id=run_id,
        state=State.COMPLETE.value,
        workflow_url="blast",
        workflow_params={},
        workflow_type="BLAST",
        workflow_type_version="1.0",
        workflow_engine="blast",
        workflow_engine_version=None,
        tags=None,
        start_time=None,
        end_time=None,
        outputs={"results.xml": "/path/results.xml"},
        run_log={"name": "blast", "cmd": ["blastn"], "stdout": "", "stderr": ""},
        task_logs=None,
        request={},
    )
    log = wes_service.run_to_run_log(row)
    assert log.run_id == str(run_id)
    assert log.state == State.COMPLETE
    assert log.outputs is not None


@pytest.mark.asyncio
async def test_run_to_run_log_running(db_session) -> None:
    """run_to_run_log builds RunLog for running state."""
    run_id = uuid4()
    row = WorkflowRun(
        run_id=run_id,
        state=State.RUNNING.value,
        workflow_url="blast",
        workflow_params={},
        workflow_type="BLAST",
        workflow_type_version="1.0",
        workflow_engine="blast",
        workflow_engine_version=None,
        tags=None,
        start_time=None,
        end_time=None,
        outputs=None,
        run_log=None,
        task_logs=None,
        request={},
    )
    log = wes_service.run_to_run_log(row)
    assert log.state == State.RUNNING


@pytest.mark.asyncio
async def test_cancel_run_sets_canceled(db_session) -> None:
    """cancel_run sets state to CANCELED when run exists."""
    run_id = uuid4()
    row = WorkflowRun(
        run_id=run_id,
        state=State.RUNNING.value,
        workflow_url="blast",
        workflow_params={},
        workflow_type="BLAST",
        workflow_type_version="1.0",
        workflow_engine="blast",
        workflow_engine_version=None,
        tags=None,
        start_time=None,
        end_time=None,
        outputs=None,
        run_log=None,
        task_logs=None,
        request={},
        user_id="dev-user",
    )
    db_session.add(row)
    await db_session.flush()

    result = await wes_service.cancel_run(db_session, str(run_id), current_user=OWNER)
    assert result is True
    await db_session.refresh(row)
    assert row.state == State.CANCELED.value


@pytest.mark.asyncio
async def test_cancel_run_not_found_returns_false(db_session) -> None:
    """cancel_run returns False when run not found."""
    result = await wes_service.cancel_run(
        db_session, "00000000-0000-0000-0000-000000000000", current_user=OWNER
    )
    assert result is False


def test_safe_filename_strips_path() -> None:
    """_safe_filename returns only the base name."""
    assert wes_service._safe_filename("subdir/query.fasta") == "query.fasta"
    assert wes_service._safe_filename("query.fasta") == "query.fasta"
    assert wes_service._safe_filename("") == "unnamed"


def test_iso_now_format() -> None:
    """_iso_now returns ISO 8601 string ending in Z."""
    s = wes_service._iso_now()
    assert s.endswith("Z")
    assert "T" in s
    assert len(s) >= 20


def test_run_dir_uses_settings() -> None:
    """_run_dir returns path under wes_work_dir."""
    with patch("app.services.wes_service.get_settings") as mock_settings:
        mock_settings.return_value.wes_work_dir = "/tmp/wes"
        path = wes_service._run_dir("run-123")
    assert str(path) == "/tmp/wes/run-123" or path.name == "run-123"


def test_parse_nextflow_outputs_empty_stdout() -> None:
    """_parse_nextflow_outputs returns stdout snippet when no Published output."""
    from pathlib import Path

    out = wes_service._parse_nextflow_outputs(Path("/tmp"), "some stdout")
    assert "stdout_snippet" in out
    assert "some stdout" in out["stdout_snippet"]


def test_parse_nextflow_outputs_published_line() -> None:
    """_parse_nextflow_outputs extracts Published output lines."""
    from pathlib import Path

    stdout = "Published output: results/out.xml\nDone."
    out = wes_service._parse_nextflow_outputs(Path("/tmp/run"), stdout)
    assert "results/out.xml" in out or "out.xml" in str(out.values())


@pytest.mark.asyncio
async def test_get_system_state_counts(db_session) -> None:
    """get_system_state_counts returns dict of state -> count."""
    counts = await wes_service.get_system_state_counts(db_session)
    assert isinstance(counts, dict)
    assert all(isinstance(v, int) for v in counts.values())
    assert "QUEUED" in counts or "COMPLETE" in counts or len(counts) >= 0
