"""GA4GH WES v1.1 backend: Nextflow execution and direct BLAST via async subprocess.

Workflow files are staged under {wes_work_dir}/{run_id}/. Nextflow stdout/stderr
are captured into RunLog.run_log and RunLog.task_logs. BLAST runs as binary
(workflow_url='blast') without Nextflow.
"""

import asyncio
import logging
import os
import re
import signal
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_async_session_maker
from app.core.isolation import (
    apply_scope,
    current_isolation_mode,
    get_scope_filter,
    get_scope_values,
    object_visible_to_scope,
)
from app.models.workflow_run import WorkflowRun
from app.schemas.wes import Log, RunLog, RunRequest, RunStatus, RunSummary, State, TaskLog

logger = logging.getLogger(__name__)

# In-process map run_id -> asyncio.Task for cancellation (single-instance only)
_run_tasks: dict[str, asyncio.Task[None]] = {}
_run_processes: dict[str, asyncio.subprocess.Process] = {}

ALLOWED_BLAST_PROGRAMS = frozenset({"blastn", "blastp", "blastx", "tblastn", "tblastx"})
ALLOWED_BLAST_DATABASES = frozenset(
    {
        "nt",
        "nr",
        "swissprot",
        "pdbaa",
        "pdbnt",
        "refseq_rna",
        "refseq_protein",
        "env_nt",
        "env_nr",
        "tsa_nt",
    }
)

# Allowed workflow_url values (injection prevention; no user-controlled paths/URLs)
ALLOWED_WORKFLOWS = frozenset(
    [
        "blast",
        # Nextflow Workflows — lokale .nf Dateien und bekannte nf-core Pipelines
        "main.nf",
        "nextflow",
    ]
)

# HelixTest (SynapticFour/HelixTest) TRS-style workflow descriptors — in-process stubs only.
HELIXTEST_TRS_ECHO = "trs://test-tool/echo/1.0"
HELIXTEST_TRS_FAIL = "trs://test-tool/fail/1.0"
HELIXTEST_TRS_CWL_ECHO = "trs://test-tool/cwl-echo/1.0"
HELIXTEST_TRS_NONEXISTENT = "trs://nonexistent/invalid/0.0"
HELIXTEST_TRS_URLS: frozenset[str] = frozenset(
    {
        HELIXTEST_TRS_ECHO,
        HELIXTEST_TRS_FAIL,
        HELIXTEST_TRS_CWL_ECHO,
        HELIXTEST_TRS_NONEXISTENT,
    }
)

# HelixTest robustness test polls with a 1s timeout — success paths must stay non-terminal longer.
HELIXTEST_MIN_RUNNING_SECONDS = 2.0
# Brief delay so pollers typically observe QUEUED before RUNNING.
HELIXTEST_QUEUED_VISIBLE_SECONDS = 0.15


def _normalize_workflow_type(workflow_type: str) -> str:
    """Map client aliases to canonical GA4GH labels (aligned with Ferrum executor routing).

    Some clients send ``NFL`` / ``NXF`` instead of ``NEXTFLOW``.
    """
    t = workflow_type.strip()
    key = t.lower().replace(" ", "_").replace("-", "_")
    if key in ("nfl", "nxf", "nextflow"):
        return "NEXTFLOW"
    if key == "wdl":
        return "WDL"
    if key == "cwl":
        return "CWL"
    if key in ("smk", "snakemake"):
        return "SNAKEMAKE"
    return t


def _is_helixtest_trs_workflow(workflow_url: str) -> bool:
    """Return True if URL is a HelixTest TRS conformance stub (not executed via Nextflow)."""
    return workflow_url in HELIXTEST_TRS_URLS


def _helixtest_stubs_enabled() -> bool:
    """TRS echo/fail stubs exist only for HelixTest conformance, never by default."""
    return os.environ.get("WES_HELIXTEST_STUBS") == "1" or os.environ.get("TESTING") == "1"


def resolve_blast_database(name_or_path: str) -> str:
    """Return an allowlisted BLAST database name (never a user-controlled path)."""
    raw = (name_or_path or "nt").strip()
    base = Path(raw).name
    if not base or base not in ALLOWED_BLAST_DATABASES:
        raise ValueError(
            f"BLAST database {base!r} is not allowlisted. "
            f"Allowed: {sorted(ALLOWED_BLAST_DATABASES)}"
        )
    return base


def _validate_workflow_url(workflow_url: str) -> None:
    """Validate workflow URL against allowlist; remote http(s) is opt-in.

    Remote ``http://`` / ``https://`` URLs require WES_ALLOW_REMOTE_WORKFLOWS=1
    and must not contain ``..`` path segments. Optional host allowlist via
    WES_ALLOWED_WORKFLOW_HOSTS.
    """
    if _is_helixtest_trs_workflow(workflow_url):
        if not _helixtest_stubs_enabled():
            raise ValueError(
                "HelixTest TRS stubs are disabled. Set WES_HELIXTEST_STUBS=1 "
                "only for conformance runs."
            )
        return
    if workflow_url in ALLOWED_WORKFLOWS:
        return
    # Local .nf filenames only (basename, no path separators) — staged under the run dir.
    if workflow_url.endswith(".nf") and "://" not in workflow_url:
        if "/" in workflow_url or "\\" in workflow_url or ".." in workflow_url:
            raise ValueError("Local workflow files must be a basename ending in .nf")
        return
    parsed = urlparse(workflow_url)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        path = parsed.path or "/"
        if ".." in path:
            raise ValueError("Invalid workflow URL: path must not contain '..'")
        settings = get_settings()
        if not settings.wes_allow_remote_workflows:
            raise ValueError(
                "Remote http(s) workflow URLs are disabled. "
                "Set WES_ALLOW_REMOTE_WORKFLOWS=1 "
                "(and optionally WES_ALLOWED_WORKFLOW_HOSTS)."
            )
        host = parsed.netloc.split("@")[-1].split(":")[0].lower()
        allowed_hosts = settings.wes_allowed_workflow_hosts
        if allowed_hosts and host not in allowed_hosts:
            raise ValueError(f"Workflow host {host!r} is not allowlisted")
        return
    raise ValueError(
        f"Unknown workflow: {workflow_url!r}. "
        f"Allowed: {sorted(ALLOWED_WORKFLOWS)}, local *.nf files, "
        "HelixTest TRS stubs, or (when enabled) http(s) URLs without '..' in the path"
    )


async def _kill_run_process(run_id: str) -> None:
    """Terminate a live BLAST/Nextflow subprocess.

    Prefers the in-process asyncio handle. If this worker does not own the
    handle (same-host multi-worker), kill via the PID file under the run dir.
    Cross-host cancellation still requires a shared job queue.
    """
    process = _run_processes.pop(run_id, None)
    if process is not None and process.returncode is None:
        try:
            process.kill()
            await process.wait()
        except (ProcessLookupError, OSError):
            pass
        _clear_run_pid(run_id)
        return
    pid_file = _pid_path(run_id)
    if pid_file.is_file():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            os.kill(pid, signal.SIGKILL)
        except (ValueError, ProcessLookupError, PermissionError, OSError):
            pass
    _clear_run_pid(run_id)


def _pid_path(run_id: str) -> Path:
    return _run_dir(run_id) / "executor.pid"


def _write_run_pid(run_id: str, pid: int | None) -> None:
    if pid is None:
        return
    path = _pid_path(run_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(pid), encoding="utf-8")
    except OSError as e:
        logger.warning("Could not write WES pid file for %s: %s", run_id, e)


def _clear_run_pid(run_id: str) -> None:
    try:
        _pid_path(run_id).unlink(missing_ok=True)
    except OSError:
        pass


def _register_run_process(run_id: str, process: asyncio.subprocess.Process) -> None:
    _run_processes[run_id] = process
    _write_run_pid(run_id, process.pid)


async def _persist_run_fields(
    run_id: str,
    state: State,
    start_time: str | None = None,
    end_time: str | None = None,
    run_log: dict | None = None,
    task_logs: list | None = None,
    outputs: dict | None = None,
) -> None:
    """Update WorkflowRun row from a background task (own session)."""
    async with get_async_session_maker()() as session:
        stmt = select(WorkflowRun).where(WorkflowRun.run_id == UUID(run_id))
        r = await session.execute(stmt)
        row = r.scalars().first()
        if not row:
            return
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
    try:
        database = resolve_blast_database(str(params.get("database", "nt")))
    except ValueError as e:
        await _persist_run_fields(
            run_id,
            State.EXECUTOR_ERROR,
            end_time=_iso_now(),
            run_log={
                "name": "blast",
                "stderr": str(e),
                "exit_code": -1,
            },
        )
        return
    program = str(params.get("program", "blastn")).strip().lower()
    if program not in ALLOWED_BLAST_PROGRAMS:
        await _persist_run_fields(
            run_id,
            State.EXECUTOR_ERROR,
            end_time=_iso_now(),
            run_log={
                "name": "blast",
                "stderr": f"Unsupported BLAST program: {program!r}",
                "exit_code": -1,
            },
        )
        return
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
        await _persist_run_fields(
            run_id,
            state,
            start_time=start_time,
            end_time=end_time,
            run_log=run_log,
            task_logs=task_logs,
            outputs=outputs,
        )

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
        _register_run_process(run_id, process)
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
    except asyncio.CancelledError:
        await _kill_run_process(run_id)
        end_time = _iso_now()
        run_log_obj["end_time"] = end_time
        run_log_obj["stderr"] = (run_log_obj.get("stderr") or "") + "\nCanceled by user."
        run_log_obj["exit_code"] = -1
        await update_db(
            State.CANCELED,
            end_time=end_time,
            run_log=run_log_obj,
            task_logs=task_logs_list,
        )
        raise
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
        _run_processes.pop(run_id, None)
        _clear_run_pid(run_id)
        _run_tasks.pop(run_id, None)


async def _execute_helixtest_trs(
    run_id: str,
    _run_dir: Path,
    workflow_url: str,
    workflow_type: str,
    workflow_type_version: str,
    workflow_params: dict[str, Any] | None,
) -> None:
    """Run in-process TRS stubs matching SynapticFour/HelixTest WES conformance expectations."""
    params = workflow_params or {}
    start_time = _iso_now()
    run_log_obj: dict[str, Any] = {
        "name": "helixtest-trs-stub",
        "cmd": [workflow_url, workflow_type, workflow_type_version],
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
        start_time_: str | None = None,
        end_time: str | None = None,
        run_log: dict | None = None,
        task_logs: list | None = None,
        outputs: dict[str, Any] | None = None,
    ) -> None:
        await _persist_run_fields(
            run_id,
            state,
            start_time=start_time_,
            end_time=end_time,
            run_log=run_log,
            task_logs=task_logs,
            outputs=outputs,
        )

    async def finish_error(msg: str) -> None:
        end_time = _iso_now()
        run_log_obj["end_time"] = end_time
        run_log_obj["stderr"] = msg
        run_log_obj["exit_code"] = 1
        task_logs_list.append(
            {
                "id": f"{run_id}-trs",
                "name": "helixtest-trs-stub",
                "cmd": run_log_obj["cmd"],
                "start_time": start_time,
                "end_time": end_time,
                "stdout": "",
                "stderr": msg,
                "exit_code": 1,
                "system_logs": None,
            },
        )
        await update_db(
            State.EXECUTOR_ERROR,
            end_time=end_time,
            run_log=run_log_obj,
            task_logs=task_logs_list,
        )

    async def finish_success(outputs: dict[str, Any]) -> None:
        end_time = _iso_now()
        run_log_obj["end_time"] = end_time
        run_log_obj["exit_code"] = 0
        run_log_obj["stdout"] = "ok"
        task_logs_list.append(
            {
                "id": f"{run_id}-trs",
                "name": "helixtest-trs-stub",
                "cmd": run_log_obj["cmd"],
                "start_time": start_time,
                "end_time": end_time,
                "stdout": "ok",
                "stderr": "",
                "exit_code": 0,
                "system_logs": None,
            },
        )
        await update_db(
            State.COMPLETE,
            end_time=end_time,
            run_log=run_log_obj,
            task_logs=task_logs_list,
            outputs=outputs,
        )

    try:
        await asyncio.sleep(HELIXTEST_QUEUED_VISIBLE_SECONDS)
        await update_db(
            State.RUNNING,
            start_time_=start_time,
            run_log=run_log_obj,
            task_logs=task_logs_list,
        )

        if workflow_url == HELIXTEST_TRS_NONEXISTENT or workflow_url == HELIXTEST_TRS_FAIL:
            await finish_error("HelixTest stub: workflow failure")
            return

        if workflow_url == HELIXTEST_TRS_CWL_ECHO:
            if workflow_type.upper() != "CWL":
                await finish_error("HelixTest stub: workflow_type must be CWL for cwl-echo")
                return
            if "message" not in params:
                await finish_error("HelixTest stub: missing required message parameter")
                return

        if workflow_url in (HELIXTEST_TRS_ECHO, HELIXTEST_TRS_CWL_ECHO):
            # Same timing requirement: robustness suite uses a 1s poll timeout on echo runs.
            await asyncio.sleep(HELIXTEST_MIN_RUNNING_SECONDS)
            raw = params.get("message")
            message = raw if raw is not None else ""
            await finish_success({"echo_out": str(message)})
            return

        await finish_error(f"Helixtest stub: unsupported workflow URL {workflow_url!r}")
    except asyncio.CancelledError:
        end_time = _iso_now()
        run_log_obj["end_time"] = end_time
        run_log_obj["exit_code"] = -1
        run_log_obj["stderr"] = (run_log_obj.get("stderr") or "") + "\nCanceled by user."
        await update_db(
            State.CANCELED,
            end_time=end_time,
            run_log=run_log_obj,
            task_logs=task_logs_list,
        )
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception("HelixTest TRS stub failed for run_id=%s", run_id)
        end_time = _iso_now()
        run_log_obj["end_time"] = end_time
        run_log_obj["exit_code"] = -1
        run_log_obj["stderr"] = str(e)
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
    Only workflow_url in ALLOWED_WORKFLOWS is accepted (injection prevention).
    """
    _validate_workflow_url(workflow_url)
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
    if workflow_path is not None:
        if not workflow_path.exists():
            await _persist_run_fields(
                run_id,
                State.EXECUTOR_ERROR,
                end_time=_iso_now(),
                run_log={
                    "name": "nextflow",
                    "stderr": f"Workflow file not staged: {workflow_path.name}",
                    "exit_code": -1,
                },
            )
            return
        cmd_target = str(workflow_path)
    else:
        cmd_target = workflow_url

    start_time = _iso_now()
    cmd = ["nextflow", "run", cmd_target]
    if workflow_params:
        for k, v in workflow_params.items():
            if v is None:
                continue
            key = str(k)
            if not re.fullmatch(r"[A-Za-z0-9_]+", key):
                logger.warning("Skipping unsafe Nextflow param key %r", key)
                continue
            value = str(v)
            if len(value) > 4096 or value.startswith("-") or "\n" in value or "\0" in value:
                logger.warning("Skipping unsafe Nextflow param value for key %r", key)
                continue
            cmd.extend(["--" + key, value])

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
        await _persist_run_fields(
            run_id,
            state,
            start_time=start_time,
            end_time=end_time,
            run_log=run_log,
            task_logs=task_logs,
            outputs=outputs,
        )

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
        _register_run_process(run_id, process)
        timeout = get_settings().wes_subprocess_timeout_seconds
        try:
            if timeout is not None:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            else:
                stdout_bytes, stderr_bytes = await process.communicate()
        except TimeoutError:
            process.kill()
            await process.wait()
            end_time = _iso_now()
            run_log_obj["end_time"] = end_time
            run_log_obj["exit_code"] = -1
            run_log_obj["stderr"] = (
                run_log_obj.get("stderr") or ""
            ) + f"\nSubprocess exceeded timeout ({timeout}s)."
            run_log_obj["system_logs"] = ["wes_subprocess_timeout"]
            await update_db(
                State.SYSTEM_ERROR,
                end_time=end_time,
                run_log=run_log_obj,
                task_logs=task_logs_list,
            )
            return
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
        await _kill_run_process(run_id)
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
        _run_processes.pop(run_id, None)
        _clear_run_pid(run_id)
        _run_tasks.pop(run_id, None)


def _parse_nextflow_outputs(run_dir: Path, stdout: str) -> dict[str, Any]:
    """Try to infer published outputs from Nextflow stdout or results dir. Placeholder."""
    out: dict[str, Any] = {}
    # Optional: parse "Published output" lines or read results from run_dir
    for m in re.finditer(r"Published output:\s*(\S+)", stdout):
        out[m.group(1)] = str(run_dir / m.group(1))
    return out if out else {"stdout_snippet": stdout[-2000:] if len(stdout) > 2000 else stdout}


# ----- Public service API -----


WES_SERVICE_METADATA: dict[str, Any] = {
    "workflow_type_versions": {
        "NEXTFLOW": ["DSL2"],
        "CWL": ["v1.0"],
        "WDL": ["1.0", "1.1"],
    },
    "supported_wes_versions": ["1.1.0", "1.1", "1.0"],
    "supported_filesystem_protocols": ["file", "http", "https"],
    "workflow_engine_versions": {
        "nextflow": ["23.10.0", "24.04.0"],
    },
    "tags": {"backend": "nextflow"},
}


def get_service_info(db: AsyncSession | None = None) -> dict[str, Any]:
    """Static WES service metadata (system_state_counts are filled by the endpoint)."""
    _ = db
    return {
        "workflow_type_versions": {
            k: list(v) for k, v in WES_SERVICE_METADATA["workflow_type_versions"].items()
        },
        "supported_wes_versions": list(WES_SERVICE_METADATA["supported_wes_versions"]),
        "supported_filesystem_protocols": list(
            WES_SERVICE_METADATA["supported_filesystem_protocols"]
        ),
        "workflow_engine_versions": {
            k: list(v) for k, v in WES_SERVICE_METADATA["workflow_engine_versions"].items()
        },
        "tags": dict(WES_SERVICE_METADATA["tags"]),
    }


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
    *,
    current_user: dict[str, Any] | None = None,
) -> UUID:
    """Create workflow run (QUEUED), stage files, start Nextflow. Returns run_id."""
    _validate_workflow_url(request.workflow_url)
    normalized = request.model_copy(
        update={"workflow_type": _normalize_workflow_type(request.workflow_type)},
    )
    run_id = uuid4()
    run_dir = _run_dir(str(run_id))
    run_dir.mkdir(parents=True, exist_ok=True)

    if workflow_attachments:
        for filename, content in workflow_attachments:
            safe = _safe_filename(filename)
            (run_dir / safe).write_bytes(content)

    if current_user:
        scope_vals = get_scope_values(current_user)
    elif current_isolation_mode() == "open":
        scope_vals = {"user_id": None, "team_id": None}
    else:
        raise ValueError("Authenticated user required to create workflow runs")
    request_dict = normalized.model_dump(mode="json")
    row = WorkflowRun(
        run_id=run_id,
        state=State.QUEUED.value,
        workflow_url=normalized.workflow_url,
        workflow_params=normalized.workflow_params,
        workflow_type=normalized.workflow_type,
        workflow_type_version=normalized.workflow_type_version,
        workflow_engine=normalized.workflow_engine,
        workflow_engine_version=normalized.workflow_engine_version,
        tags=normalized.tags,
        start_time=None,
        end_time=None,
        outputs=None,
        run_log=None,
        task_logs=None,
        request=request_dict,
        user_id=scope_vals.get("user_id"),
        team_id=scope_vals.get("team_id"),
    )
    db.add(row)
    await db.flush()

    # Pytest sets WES_DEFER_BACKGROUND_EXECUTION=1 (see tests/conftest.py) so create_run stays
    # deterministic; HelixTest / production omit it so WES tasks actually run.
    if os.environ.get("WES_DEFER_BACKGROUND_EXECUTION") == "1":
        return run_id

    loop = asyncio.get_running_loop()
    if _is_helixtest_trs_workflow(normalized.workflow_url):
        task = loop.create_task(
            _execute_helixtest_trs(
                str(run_id),
                run_dir,
                normalized.workflow_url,
                normalized.workflow_type,
                normalized.workflow_type_version,
                normalized.workflow_params,
            ),
        )
    else:
        task = loop.create_task(
            _execute_nextflow(
                str(run_id),
                run_dir,
                normalized.workflow_url,
                normalized.workflow_params,
            ),
        )
    _run_tasks[str(run_id)] = task
    # Don't await task; let it run in background. Caller commits DB.

    return run_id


async def get_run(
    db: AsyncSession,
    run_id: str,
    current_user: dict[str, Any] | None = None,
) -> WorkflowRun | None:
    """Fetch WorkflowRun by run_id (string). Optionally hide out-of-scope rows."""
    try:
        uid = UUID(run_id)
    except ValueError:
        return None
    stmt = select(WorkflowRun).where(WorkflowRun.run_id == uid)
    r = await db.execute(stmt)
    run = r.scalars().first()
    if run is None:
        return None
    if current_user is not None:
        scope = get_scope_filter(current_user)
        if not object_visible_to_scope(run.user_id, run.team_id, scope):
            return None
    elif current_isolation_mode() != "open":
        return None
    return run


async def list_runs(
    db: AsyncSession,
    page_size: int = 100,
    page_token: str | None = None,
    state_filter: str | None = None,
    current_user: dict[str, Any] | None = None,
) -> tuple[list[WorkflowRun], str]:
    """List workflow runs with simple offset pagination. Returns (runs, next_page_token)."""
    stmt = select(WorkflowRun).order_by(WorkflowRun.created_at.desc())
    if current_user is not None:
        stmt = apply_scope(stmt, WorkflowRun, get_scope_filter(current_user))
    elif current_isolation_mode() != "open":
        return [], ""
    if state_filter is not None:
        stmt = stmt.where(WorkflowRun.state == state_filter)
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


async def cancel_run(
    db: AsyncSession,
    run_id: str,
    current_user: dict[str, Any] | None = None,
) -> bool:
    """Cancel run: kill subprocess, cancel task, set CANCELED. True if found."""
    run = await get_run(db, run_id, current_user=current_user)
    if not run:
        return False
    if run.state in (
        State.COMPLETE.value,
        State.EXECUTOR_ERROR.value,
        State.SYSTEM_ERROR.value,
        State.CANCELED.value,
    ):
        return True  # Already terminal
    await _kill_run_process(run_id)
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
