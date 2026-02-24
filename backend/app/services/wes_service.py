"""GA4GH WES v1.1 backend: Nextflow execution and direct BLAST via async subprocess.

Workflow files are staged under {wes_work_dir}/{run_id}/. Nextflow stdout/stderr
are captured into RunLog.run_log and RunLog.task_logs. BLAST runs as binary
(workflow_url='blast') without Nextflow.
"""

import asyncio
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_async_session_maker
from app.models.workflow_run import WorkflowRun
from app.schemas.wes import Log, RunLog, RunRequest, RunStatus, RunSummary, State, TaskLog

logger = logging.getLogger(__name__)

# In-process map run_id -> asyncio.Task for cancellation (single-instance only)
_run_tasks: dict[str, asyncio.Task[None]] = {}


def _run_dir(run_id: str) -> Path:
    """Return the working directory for a run (e.g. /tmp/wes/{run_id})."""
    return Path(get_settings().wes_work_dir) / run_id


def _safe_filename(name: str) -> str:
    """Sanitize filename: no parent path components."""
    return Path(name).name if name else "unnamed"


def _iso_now() -> str:
    """Current time in ISO 8601 format as used by WES."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _run_blast_direct(
    run_id: str,
    run_dir: Path,
    workflow_params: dict[str, Any] | None,
) -> None:
    """Run BLAST directly as binary (no Nextflow). Writes results.xml to run_dir."""
    params = workflow_params or {}
    query_file = run_dir / "query.fasta"
    if not query_file.exists():
        logger.warning("BLAST run %s: query.fasta not found", run_id)
        return
    database = str(params.get("database", "nt"))
    program = str(params.get("program", "blastn"))
    evalue = float(params.get("evalue", 0.001))
    max_target_seqs = int(params.get("max_hits", 10))
    out_xml = run_dir / "results.xml"

    cmd = [
        program,
        "-query",
        str(query_file),
        "-db",
        database,
        "-out",
        str(out_xml),
        "-outfmt",
        "5",
        "-max_target_seqs",
        str(max_target_seqs),
        "-evalue",
        str(evalue),
    ]
    start_time = _iso_now()
    run_log_obj: dict[str, Any] = {
        "name": "blast",
        "cmd": cmd,
        "start_time": start_time,
        "end_time": None,
        "stdout": None,
        "stderr": None,
        "exit_code": None,
        "system_logs": None,
    }
    task_logs_list: list[dict[str, Any]] = []

    async def update_db(
        state: State,
        start_time: str | None = None,
        end_time: str | None = None,
        run_log: dict | None = None,
        task_logs: list | None = None,
        outputs: dict | None = None,
    ) -> None:
        async with get_async_session_maker()() as session:
            stmt = select(WorkflowRun).where(WorkflowRun.run_id == UUID(run_id))
            r = await session.execute(stmt)
            row = r.scalars().first()
            if row:
                row.state = state.value
                if start_time:
                    row.start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                if end_time:
                    row.end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                if run_log is not None:
                    row.run_log = run_log
                if task_logs is not None:
                    row.task_logs = task_logs
                if outputs is not None:
                    row.outputs = outputs
                await session.commit()

    try:
        await update_db(
            State.RUNNING,
            start_time=start_time,
            run_log=run_log_obj,
            task_logs=task_logs_list,
        )

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(run_dir),
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=300)
        end_time = _iso_now()
        exit_code = process.returncode or 0
        stdout_str = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
        stderr_str = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

        run_log_obj["end_time"] = end_time
        run_log_obj["stdout"] = stdout_str
        run_log_obj["stderr"] = stderr_str
        run_log_obj["exit_code"] = exit_code
        task_logs_list.append(
            {
                "id": run_id + "-blast",
                "name": "blast",
                "cmd": cmd,
                "start_time": start_time,
                "end_time": end_time,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "exit_code": exit_code,
                "system_logs": None,
            }
        )
        state = State.COMPLETE if exit_code == 0 and out_xml.exists() else State.EXECUTOR_ERROR
        await update_db(state, end_time=end_time, run_log=run_log_obj, task_logs=task_logs_list)
    except TimeoutError:
        end_time = _iso_now()
        run_log_obj["end_time"] = end_time
        run_log_obj["stderr"] = (run_log_obj.get("stderr") or "") + "\nBLAST timeout (300s)."
        run_log_obj["exit_code"] = -1
        await update_db(
            State.EXECUTOR_ERROR,
            end_time=end_time,
            run_log=run_log_obj,
            task_logs=task_logs_list,
        )
    except Exception as e:
        logger.exception("BLAST execution failed for run_id=%s", run_id)
        end_time = _iso_now()
        run_log_obj["end_time"] = end_time
        run_log_obj["stderr"] = (run_log_obj.get("stderr") or "") + "\n" + str(e)
        run_log_obj["exit_code"] = -1
        await update_db(
            State.SYSTEM_ERROR,
            end_time=end_time,
            run_log=run_log_obj,
            task_logs=task_logs_list,
        )
    finally:
        _run_tasks.pop(run_id, None)


async def _execute_nextflow(
    run_id: str,
    run_dir: Path,
    workflow_url: str,
    workflow_params: dict[str, Any] | None,
) -> None:
    """Run Nextflow in run_dir and update WorkflowRun state and logs.

    Uses async subprocess; stdout/stderr captured into run_log and task_logs.
    """
    if workflow_url == "blast":
        task = asyncio.create_task(
            _run_blast_direct(run_id, run_dir, workflow_params),
        )
        _run_tasks[run_id] = task
        return

    workflow_path = (
        run_dir / _safe_filename(workflow_url)
        if not workflow_url.startswith(("http://", "https://"))
        else None
    )
    cmd_target = str(workflow_path) if workflow_path and workflow_path.exists() else workflow_url

    start_time = _iso_now()
    cmd = ["nextflow", "run", cmd_target]
    if workflow_params:
        for k, v in workflow_params.items():
            if v is None:
                continue
            cmd.extend(["--" + k, str(v)])

    run_log_obj: dict[str, Any] = {
        "name": "nextflow",
        "cmd": cmd,
        "start_time": start_time,
        "end_time": None,
        "stdout": None,
        "stderr": None,
        "exit_code": None,
        "system_logs": None,
    }
    task_logs_list: list[dict[str, Any]] = []

    async def update_db(
        state: State,
        start_time: str | None = None,
        end_time: str | None = None,
        run_log: dict | None = None,
        task_logs: list | None = None,
        outputs: dict | None = None,
    ) -> None:
        async with get_async_session_maker()() as session:
            stmt = select(WorkflowRun).where(WorkflowRun.run_id == UUID(run_id))
            r = await session.execute(stmt)
            row = r.scalars().first()
            if row:
                row.state = state.value
                if start_time:
                    row.start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                if end_time:
                    row.end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                if run_log is not None:
                    row.run_log = run_log
                if task_logs is not None:
                    row.task_logs = task_logs
                if outputs is not None:
                    row.outputs = outputs
                await session.commit()

    try:
        await update_db(
            State.RUNNING, start_time=start_time, run_log=run_log_obj, task_logs=task_logs_list
        )

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(run_dir),
        )
        stdout_bytes, stderr_bytes = await process.communicate()
        stdout_str = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
        stderr_str = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
        end_time = _iso_now()
        exit_code = process.returncode or 0

        run_log_obj["end_time"] = end_time
        run_log_obj["stdout"] = stdout_str
        run_log_obj["stderr"] = stderr_str
        run_log_obj["exit_code"] = exit_code

        # One task log entry for the whole Nextflow run (spec allows task_logs for each step)
        task_logs_list.append(
            {
                "id": run_id + "-nextflow",
                "name": "nextflow",
                "cmd": cmd,
                "start_time": start_time,
                "end_time": end_time,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "exit_code": exit_code,
                "system_logs": None,
            }
        )

        if exit_code == 0:
            state = State.COMPLETE
            outputs = _parse_nextflow_outputs(run_dir, stdout_str)
        else:
            state = State.EXECUTOR_ERROR
            outputs = None

        await update_db(
            state, end_time=end_time, run_log=run_log_obj, task_logs=task_logs_list, outputs=outputs
        )
    except asyncio.CancelledError:
        end_time = _iso_now()
        run_log_obj["end_time"] = end_time
        run_log_obj["exit_code"] = -1
        run_log_obj["stderr"] = (run_log_obj.get("stderr") or "") + "\nCanceled by user."
        if task_logs_list:
            task_logs_list[0]["end_time"] = end_time
            task_logs_list[0]["exit_code"] = -1
        await update_db(
            State.CANCELED, end_time=end_time, run_log=run_log_obj, task_logs=task_logs_list
        )
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception("Nextflow execution failed for run_id=%s", run_id)
        end_time = _iso_now()
        run_log_obj["end_time"] = end_time
        run_log_obj["exit_code"] = -1
        run_log_obj["stderr"] = (run_log_obj.get("stderr") or "") + "\n" + str(e)
        run_log_obj["system_logs"] = [str(e)]
        await update_db(
            State.SYSTEM_ERROR, end_time=end_time, run_log=run_log_obj, task_logs=task_logs_list
        )
    finally:
        _run_tasks.pop(run_id, None)


def _parse_nextflow_outputs(run_dir: Path, stdout: str) -> dict[str, Any]:
    """Try to infer published outputs from Nextflow stdout or results dir. Placeholder."""
    out: dict[str, Any] = {}
    # Optional: parse "Published output" lines or read results from run_dir
    for m in re.finditer(r"Published output:\s*(\S+)", stdout):
        out[m.group(1)] = str(run_dir / m.group(1))
    return out if out else {"stdout_snippet": stdout[-2000:] if len(stdout) > 2000 else stdout}


# ----- Public service API -----


def get_service_info(db: AsyncSession) -> dict[str, Any]:
    """Build ServiceInfo with system_state_counts from DB. Caller runs query."""
    # Counts are filled by the endpoint after querying
    return {}


async def get_system_state_counts(db: AsyncSession) -> dict[str, int]:
    """Return count of workflow runs per state."""
    stmt = select(WorkflowRun.state, func.count(WorkflowRun.run_id)).group_by(WorkflowRun.state)
    r = await db.execute(stmt)
    rows = r.all()
    counts: dict[str, int] = {}
    for state, cnt in rows:
        counts[state] = cnt
    for s in State:
        if s.value not in counts:
            counts[s.value] = 0
    return counts


async def create_run(
    db: AsyncSession,
    request: RunRequest,
    workflow_attachments: list[tuple[str, bytes]] | None = None,
) -> UUID:
    """Create workflow run (QUEUED), stage files, start Nextflow. Returns run_id."""
    run_id = uuid4()
    run_dir = _run_dir(str(run_id))
    run_dir.mkdir(parents=True, exist_ok=True)

    if workflow_attachments:
        for filename, content in workflow_attachments:
            safe = _safe_filename(filename)
            (run_dir / safe).write_bytes(content)

    request_dict = request.model_dump(mode="json")
    row = WorkflowRun(
        run_id=run_id,
        state=State.QUEUED.value,
        workflow_url=request.workflow_url,
        workflow_params=request.workflow_params,
        workflow_type=request.workflow_type,
        workflow_type_version=request.workflow_type_version,
        workflow_engine=request.workflow_engine,
        workflow_engine_version=request.workflow_engine_version,
        tags=request.tags,
        start_time=None,
        end_time=None,
        outputs=None,
        run_log=None,
        task_logs=None,
        request=request_dict,
    )
    db.add(row)
    await db.flush()

    loop = asyncio.get_running_loop()
    task = loop.create_task(
        _execute_nextflow(
            str(run_id),
            run_dir,
            request.workflow_url,
            request.workflow_params,
        ),
    )
    _run_tasks[str(run_id)] = task
    # Don't await task; let it run in background. Caller commits DB.

    return run_id


async def get_run(db: AsyncSession, run_id: str) -> WorkflowRun | None:
    """Fetch WorkflowRun by run_id (string)."""
    try:
        uid = UUID(run_id)
    except ValueError:
        return None
    stmt = select(WorkflowRun).where(WorkflowRun.run_id == uid)
    r = await db.execute(stmt)
    return r.scalars().first()


async def list_runs(
    db: AsyncSession,
    page_size: int = 100,
    page_token: str | None = None,
) -> tuple[list[WorkflowRun], str]:
    """List workflow runs with simple offset pagination. Returns (runs, next_page_token)."""
    stmt = select(WorkflowRun).order_by(WorkflowRun.created_at.desc())
    offset = int(page_token) if page_token else 0
    stmt = stmt.offset(offset).limit(page_size + 1)
    r = await db.execute(stmt)
    rows = list(r.scalars().all())
    next_token = ""
    if len(rows) > page_size:
        rows = rows[:page_size]
        next_token = str(offset + page_size)
    return rows, next_token


def run_to_run_status(run: WorkflowRun) -> RunStatus:
    """Build RunStatus from WorkflowRun."""
    return RunStatus(run_id=str(run.run_id), state=State(run.state))


def run_to_run_summary(run: WorkflowRun) -> RunSummary:
    """Build RunSummary from WorkflowRun."""
    return RunSummary(
        run_id=str(run.run_id),
        state=State(run.state),
        start_time=run.start_time.isoformat().replace("+00:00", "Z") if run.start_time else None,
        end_time=run.end_time.isoformat().replace("+00:00", "Z") if run.end_time else None,
        tags=run.tags,
    )


def run_to_run_log(run: WorkflowRun) -> RunLog:
    """Build RunLog from WorkflowRun."""

    request = RunRequest(**run.request) if run.request else None
    run_log = Log(**run.run_log) if run.run_log else None
    task_logs = None
    if run.task_logs:
        task_logs = []
        for t in run.task_logs:
            if not isinstance(t, dict):
                continue
            if t.get("id") is not None:
                task_logs.append(TaskLog(**t))
            else:
                task_logs.append(Log(**t))
    return RunLog(
        run_id=str(run.run_id),
        request=request,
        state=State(run.state),
        run_log=run_log,
        task_logs_url=None,
        task_logs=task_logs,
        outputs=run.outputs,
    )


async def cancel_run(db: AsyncSession, run_id: str) -> bool:
    """Cancel run: cancel task if present, set CANCELED. True if found and canceled."""
    run = await get_run(db, run_id)
    if not run:
        return False
    if run.state in (
        State.COMPLETE.value,
        State.EXECUTOR_ERROR.value,
        State.SYSTEM_ERROR.value,
        State.CANCELED.value,
    ):
        return True  # Already terminal
    task = _run_tasks.get(run_id)
    if task and not task.done():
        task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
        except (TimeoutError, asyncio.CancelledError):
            pass
    run.state = State.CANCELED.value
    run.end_time = datetime.now(UTC)
    await db.flush()
    return True
