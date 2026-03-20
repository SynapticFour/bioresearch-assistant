"""HelixTest TRS stub workflows (in-process conformance helpers)."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.workflow_run import WorkflowRun
from app.schemas.wes import State
from app.services import wes_service


@pytest.mark.asyncio
async def test_helixtest_trs_echo_completes_with_echo_out(db_session) -> None:
    """TRS echo stub writes echo_out and reaches COMPLETE."""
    row = WorkflowRun(
        run_id=uuid4(),
        state=State.QUEUED.value,
        workflow_url=wes_service.HELIXTEST_TRS_ECHO,
        workflow_params={"message": "hello-ga4gh"},
        workflow_type="CWL",
        workflow_type_version="v1.2",
        workflow_engine=None,
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

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=db_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_cm)

    with (
        patch(
            "app.services.wes_service.get_async_session_maker",
            return_value=mock_factory,
        ),
        patch.object(wes_service, "HELIXTEST_MIN_RUNNING_SECONDS", 0.01),
        patch.object(wes_service, "HELIXTEST_QUEUED_VISIBLE_SECONDS", 0.01),
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            await wes_service._execute_helixtest_trs(
                run_id,
                Path(tmpdir),
                wes_service.HELIXTEST_TRS_ECHO,
                "CWL",
                "v1.2",
                {"message": "hello-ga4gh"},
            )

    await db_session.refresh(row)
    assert row.state == State.COMPLETE.value
    assert row.outputs is not None
    assert row.outputs.get("echo_out") == "hello-ga4gh"


@pytest.mark.asyncio
async def test_helixtest_trs_fail_reaches_executor_error(db_session) -> None:
    """TRS fail stub ends in EXECUTOR_ERROR."""
    row = WorkflowRun(
        run_id=uuid4(),
        state=State.QUEUED.value,
        workflow_url=wes_service.HELIXTEST_TRS_FAIL,
        workflow_params={},
        workflow_type="CWL",
        workflow_type_version="v1.2",
        workflow_engine=None,
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

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=db_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_cm)

    with (
        patch(
            "app.services.wes_service.get_async_session_maker",
            return_value=mock_factory,
        ),
        patch.object(wes_service, "HELIXTEST_QUEUED_VISIBLE_SECONDS", 0.01),
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            await wes_service._execute_helixtest_trs(
                run_id,
                Path(tmpdir),
                wes_service.HELIXTEST_TRS_FAIL,
                "CWL",
                "v1.2",
                {},
            )

    await db_session.refresh(row)
    assert row.state == State.EXECUTOR_ERROR.value


@pytest.mark.asyncio
async def test_helixtest_cwl_echo_rejects_wrong_workflow_type(db_session) -> None:
    """cwl-echo with WDL type must fail (HelixTest incompatible-type case)."""
    row = WorkflowRun(
        run_id=uuid4(),
        state=State.QUEUED.value,
        workflow_url=wes_service.HELIXTEST_TRS_CWL_ECHO,
        workflow_params={"message": "x"},
        workflow_type="WDL",
        workflow_type_version="1.0",
        workflow_engine=None,
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

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=db_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_cm)

    with (
        patch(
            "app.services.wes_service.get_async_session_maker",
            return_value=mock_factory,
        ),
        patch.object(wes_service, "HELIXTEST_QUEUED_VISIBLE_SECONDS", 0.01),
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            await wes_service._execute_helixtest_trs(
                run_id,
                Path(tmpdir),
                wes_service.HELIXTEST_TRS_CWL_ECHO,
                "WDL",
                "1.0",
                {"message": "x"},
            )

    await db_session.refresh(row)
    assert row.state == State.EXECUTOR_ERROR.value
