"""Tests for WES workflow execution: _run_blast_direct, _execute_nextflow (mocked subprocess/DB)."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.workflow_run import WorkflowRun
from app.schemas.wes import State
from app.services import wes_service


async def _await_coro(coro, timeout=None):
    """Await the given coroutine (for mocking asyncio.wait_for)."""
    return await coro


@pytest.mark.asyncio
async def test_run_blast_direct_early_return_when_no_query_fasta() -> None:
    """_run_blast_direct returns early when query.fasta does not exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        # Do not create query.fasta
        with patch("app.services.wes_service.get_async_session_maker"):
            await wes_service._run_blast_direct("run-1", run_dir, {"database": "nt"})
    # No subprocess should be created
    assert not (run_dir / "results.xml").exists()


@pytest.mark.asyncio
async def test_run_blast_direct_success_complete(db_session) -> None:
    """_run_blast_direct runs subprocess and sets state COMPLETE when exit 0 and results.xml exists."""
    row = WorkflowRun(
        run_id=uuid4(),
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
    )
    db_session.add(row)
    await db_session.flush()
    run_id = str(row.run_id)
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "query.fasta").write_text(">q\nATCG\n")
        (run_dir / "results.xml").write_text("<xml/>")

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"stdout", b"stderr"))

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_factory = MagicMock(return_value=mock_cm)

        with patch("app.services.wes_service.asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_process):
            with patch("app.services.wes_service.asyncio.wait_for", new_callable=AsyncMock, side_effect=_await_coro):
                with patch("app.services.wes_service.get_async_session_maker", return_value=mock_factory):
                    await wes_service._run_blast_direct(run_id, run_dir, {"database": "nt"})

        await db_session.refresh(row)
        assert row.state == State.COMPLETE.value


@pytest.mark.asyncio
async def test_run_blast_direct_timeout_sets_executor_error(db_session) -> None:
    """_run_blast_direct sets EXECUTOR_ERROR on TimeoutError."""
    run_id = str(uuid4())
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "query.fasta").write_text(">q\nATCG\n")
        row = WorkflowRun(
            run_id=uuid4(),
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
            run_log={},
            task_logs=[],
            request={},
        )
        db_session.add(row)
        await db_session.flush()
        run_id = str(row.run_id)

        with patch("app.services.wes_service.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_process = MagicMock()
            mock_exec.return_value = mock_process
            mock_process.communicate = AsyncMock(side_effect=TimeoutError())
            with patch("app.services.wes_service.asyncio.wait_for", new_callable=AsyncMock, side_effect=TimeoutError):
                with patch("app.services.wes_service.get_async_session_maker") as mock_get_sess:
                    mock_sess_instance = MagicMock()
                    mock_sess_instance.__aenter__ = AsyncMock(return_value=db_session)
                    mock_sess_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_get_sess.return_value.return_value = mock_sess_instance

                    await wes_service._run_blast_direct(run_id, run_dir, {})

        await db_session.refresh(row)
        assert row.state == State.EXECUTOR_ERROR.value


@pytest.mark.asyncio
async def test_run_blast_direct_exception_sets_system_error(db_session) -> None:
    """_run_blast_direct sets SYSTEM_ERROR on generic Exception."""
    run_id = str(uuid4())
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "query.fasta").write_text(">q\nATCG\n")
        row = WorkflowRun(
            run_id=uuid4(),
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
            run_log={},
            task_logs=[],
            request={},
        )
        db_session.add(row)
        await db_session.flush()
        run_id = str(row.run_id)

        with patch("app.services.wes_service.asyncio.create_subprocess_exec", new_callable=AsyncMock, side_effect=RuntimeError("subprocess failed")):
            with patch("app.services.wes_service.get_async_session_maker") as mock_get_sess:
                mock_sess_instance = MagicMock()
                mock_sess_instance.__aenter__ = AsyncMock(return_value=db_session)
                mock_sess_instance.__aexit__ = AsyncMock(return_value=None)
                mock_get_sess.return_value.return_value = mock_sess_instance

                await wes_service._run_blast_direct(run_id, run_dir, {})

        await db_session.refresh(row)
        assert row.state == State.SYSTEM_ERROR.value


@pytest.mark.asyncio
async def test_execute_nextflow_blast_delegates_to_run_blast_direct() -> None:
    """_execute_nextflow with workflow_url=blast delegates to _run_blast_direct."""
    run_id = "run-123"
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "query.fasta").write_text(">q\nATCG\n")
        with patch("app.services.wes_service._run_blast_direct", new_callable=AsyncMock) as mock_blast:
            await wes_service._execute_nextflow(run_id, run_dir, "blast", {"database": "nt"})
            mock_blast.assert_called_once_with(run_id, run_dir, {"database": "nt"})


@pytest.mark.asyncio
async def test_execute_nextflow_nextflow_success(db_session) -> None:
    """_execute_nextflow with nextflow run sets COMPLETE when process exits 0."""
    run_id = str(uuid4())
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        row = WorkflowRun(
            run_id=uuid4(),
            state=State.RUNNING.value,
            workflow_url="main.nf",
            workflow_params={},
            workflow_type="Nextflow",
            workflow_type_version="1.0",
            workflow_engine="nextflow",
            workflow_engine_version=None,
            tags=None,
            start_time=None,
            end_time=None,
            outputs=None,
            run_log={},
            task_logs=[],
            request={},
        )
        db_session.add(row)
        await db_session.flush()
        run_id = str(row.run_id)
        (run_dir / "main.nf").write_text("// dummy")

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Published output: out.txt", b""))

        with patch("app.services.wes_service.asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_process):
            with patch("app.services.wes_service.get_async_session_maker") as mock_get_sess:
                mock_sess_instance = MagicMock()
                mock_sess_instance.__aenter__ = AsyncMock(return_value=db_session)
                mock_sess_instance.__aexit__ = AsyncMock(return_value=None)
                mock_get_sess.return_value.return_value = mock_sess_instance

                await wes_service._execute_nextflow(run_id, run_dir, "main.nf", {})

        await db_session.refresh(row)
        assert row.state == State.COMPLETE.value


@pytest.mark.asyncio
async def test_execute_nextflow_exception_sets_system_error(db_session) -> None:
    """_execute_nextflow sets SYSTEM_ERROR on generic Exception."""
    run_id = str(uuid4())
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        row = WorkflowRun(
            run_id=uuid4(),
            state=State.RUNNING.value,
            workflow_url="main.nf",
            workflow_params={},
            workflow_type="Nextflow",
            workflow_type_version="1.0",
            workflow_engine="nextflow",
            workflow_engine_version=None,
            tags=None,
            start_time=None,
            end_time=None,
            outputs=None,
            run_log={},
            task_logs=[],
            request={},
        )
        db_session.add(row)
        await db_session.flush()
        run_id = str(row.run_id)

        with patch("app.services.wes_service.asyncio.create_subprocess_exec", new_callable=AsyncMock, side_effect=FileNotFoundError("nextflow not found")):
            with patch("app.services.wes_service.get_async_session_maker") as mock_get_sess:
                mock_sess_instance = MagicMock()
                mock_sess_instance.__aenter__ = AsyncMock(return_value=db_session)
                mock_sess_instance.__aexit__ = AsyncMock(return_value=None)
                mock_get_sess.return_value.return_value = mock_sess_instance

                await wes_service._execute_nextflow(run_id, run_dir, "main.nf", {})

        await db_session.refresh(row)
        assert row.state == State.SYSTEM_ERROR.value


def test_run_to_run_summary_with_times() -> None:
    """run_to_run_summary includes start_time and end_time when set."""
    from datetime import datetime, timezone

    run = WorkflowRun(
        run_id=uuid4(),
        state=State.COMPLETE.value,
        workflow_url="blast",
        workflow_params={},
        workflow_type="BLAST",
        workflow_type_version="1.0",
        workflow_engine="blast",
        workflow_engine_version=None,
        tags=None,
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        outputs=None,
        run_log=None,
        task_logs=None,
        request={},
    )
    summary = wes_service.run_to_run_summary(run)
    assert summary.run_id == str(run.run_id)
    assert summary.state == State.COMPLETE
    assert summary.start_time is not None
    assert summary.end_time is not None


def test_run_to_run_log_with_task_logs_with_id() -> None:
    """run_to_run_log builds TaskLog when task has 'id'."""
    run = WorkflowRun(
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
        run_log={"name": "blast", "cmd": [], "stdout": "", "stderr": ""},
        task_logs=[{"id": "t1", "name": "blast", "cmd": [], "stdout": "", "stderr": "", "exit_code": 0}],
        request={"workflow_url": "blast", "workflow_type": "BLAST", "workflow_type_version": "1.0"},
    )
    log = wes_service.run_to_run_log(run)
    assert log.task_logs is not None
    assert len(log.task_logs) == 1


@pytest.mark.asyncio
async def test_cancel_run_already_complete_returns_true(db_session) -> None:
    """cancel_run returns True when run is already COMPLETE (terminal state)."""
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
    )
    db_session.add(row)
    await db_session.flush()
    result = await wes_service.cancel_run(db_session, str(row.run_id))
    assert result is True


@pytest.mark.asyncio
async def test_run_blast_direct_exit_nonzero_sets_executor_error(db_session) -> None:
    """_run_blast_direct sets EXECUTOR_ERROR when subprocess exit code != 0."""
    row = WorkflowRun(
        run_id=uuid4(),
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
    )
    db_session.add(row)
    await db_session.flush()
    run_id = str(row.run_id)
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "query.fasta").write_text(">q\nATCG\n")
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"error"))
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        with patch("app.services.wes_service.asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_process):
            with patch("app.services.wes_service.asyncio.wait_for", new_callable=AsyncMock, side_effect=_await_coro):
                with patch("app.services.wes_service.get_async_session_maker", return_value=MagicMock(return_value=mock_cm)):
                    await wes_service._run_blast_direct(run_id, run_dir, {})
        await db_session.refresh(row)
        assert row.state == State.EXECUTOR_ERROR.value


@pytest.mark.asyncio
async def test_run_blast_direct_no_results_xml_sets_executor_error(db_session) -> None:
    """_run_blast_direct sets EXECUTOR_ERROR when exit 0 but results.xml missing."""
    row = WorkflowRun(
        run_id=uuid4(),
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
    )
    db_session.add(row)
    await db_session.flush()
    run_id = str(row.run_id)
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "query.fasta").write_text(">q\nATCG\n")
        # Do not create results.xml
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        with patch("app.services.wes_service.asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_process):
            with patch("app.services.wes_service.asyncio.wait_for", new_callable=AsyncMock, side_effect=_await_coro):
                with patch("app.services.wes_service.get_async_session_maker", return_value=MagicMock(return_value=mock_cm)):
                    await wes_service._run_blast_direct(run_id, run_dir, {})
        await db_session.refresh(row)
        assert row.state == State.EXECUTOR_ERROR.value


@pytest.mark.asyncio
async def test_execute_nextflow_exit_nonzero_sets_executor_error(db_session) -> None:
    """_execute_nextflow sets EXECUTOR_ERROR when nextflow process exits non-zero."""
    row = WorkflowRun(
        run_id=uuid4(),
        state=State.RUNNING.value,
        workflow_url="main.nf",
        workflow_params={},
        workflow_type="Nextflow",
        workflow_type_version="1.0",
        workflow_engine="nextflow",
        workflow_engine_version=None,
        tags=None,
        start_time=None,
        end_time=None,
        outputs=None,
        run_log={},
        task_logs=[],
        request={},
    )
    db_session.add(row)
    await db_session.flush()
    run_id = str(row.run_id)
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "main.nf").write_text("// dummy")
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"nextflow error"))
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        with patch("app.services.wes_service.asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_process):
            with patch("app.services.wes_service.get_async_session_maker", return_value=MagicMock(return_value=mock_cm)):
                await wes_service._execute_nextflow(run_id, run_dir, "main.nf", {})
        await db_session.refresh(row)
        assert row.state == State.EXECUTOR_ERROR.value


@pytest.mark.asyncio
async def test_execute_nextflow_cancelled_sets_canceled(db_session) -> None:
    """_execute_nextflow sets CANCELED and re-raises when CancelledError is raised."""
    row = WorkflowRun(
        run_id=uuid4(),
        state=State.RUNNING.value,
        workflow_url="main.nf",
        workflow_params={},
        workflow_type="Nextflow",
        workflow_type_version="1.0",
        workflow_engine="nextflow",
        workflow_engine_version=None,
        tags=None,
        start_time=None,
        end_time=None,
        outputs=None,
        run_log={},
        task_logs=[],
        request={},
    )
    db_session.add(row)
    await db_session.flush()
    run_id = str(row.run_id)
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "main.nf").write_text("// dummy")
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        async def raise_cancelled(*args, **kwargs):
            raise asyncio.CancelledError()

        with patch("app.services.wes_service.asyncio.create_subprocess_exec", new_callable=AsyncMock, side_effect=raise_cancelled):
            with patch("app.services.wes_service.get_async_session_maker", return_value=MagicMock(return_value=mock_cm)):
                with pytest.raises(asyncio.CancelledError):
                    await wes_service._execute_nextflow(run_id, run_dir, "main.nf", {})
        await db_session.refresh(row)
        assert row.state == State.CANCELED.value


def test_run_to_run_log_task_without_id_appends_log() -> None:
    """run_to_run_log uses Log (not TaskLog) when task dict has no 'id'."""
    run = WorkflowRun(
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
        run_log={"name": "blast", "cmd": []},
        task_logs=[{"name": "step1", "cmd": [], "stdout": "", "stderr": ""}],
        request={"workflow_url": "blast", "workflow_type": "BLAST", "workflow_type_version": "1.0"},
    )
    log = wes_service.run_to_run_log(run)
    assert log.task_logs is not None
    assert len(log.task_logs) == 1
    assert log.task_logs[0].name == "step1"


@pytest.mark.asyncio
async def test_get_service_info_returns_empty_dict(db_session) -> None:
    """get_service_info returns empty dict (counts filled by endpoint)."""
    info = wes_service.get_service_info(db_session)
    assert info == {}


@pytest.mark.asyncio
async def test_cancel_run_cancels_running_task(db_session) -> None:
    """cancel_run cancels task in _run_tasks and sets state CANCELED."""
    row = WorkflowRun(
        run_id=uuid4(),
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
    db_session.add(row)
    await db_session.flush()
    run_id = str(row.run_id)
    # Register a long-running task so cancel_run has something to cancel
    long_task = asyncio.create_task(asyncio.sleep(999))
    wes_service._run_tasks[run_id] = long_task
    try:
        result = await wes_service.cancel_run(db_session, run_id)
        assert result is True
        await db_session.refresh(row)
        assert row.state == State.CANCELED.value
    finally:
        wes_service._run_tasks.pop(run_id, None)
