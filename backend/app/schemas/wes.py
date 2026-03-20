"""GA4GH Workflow Execution Service (WES) v1.1 Pydantic schemas.

Reference: https://ga4gh.github.io/workflow-execution-service-schemas/
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class State(str, Enum):
    """Workflow/task state per WES State schema."""

    UNKNOWN = "UNKNOWN"
    QUEUED = "QUEUED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETE = "COMPLETE"
    EXECUTOR_ERROR = "EXECUTOR_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    CANCELED = "CANCELED"
    CANCELING = "CANCELING"
    PREEMPTED = "PREEMPTED"


# ----- Service Info -----


class ServiceType(BaseModel):
    """Type of a GA4GH service (group, artifact, version)."""

    group: str = Field(..., description="Namespace in reverse domain name format, e.g. org.ga4gh")
    artifact: str = Field(..., description="Name of the API or GA4GH specification")
    version: str = Field(..., description="Version of the API or specification")


class ServiceOrganization(BaseModel):
    """Organization providing the service."""

    name: str
    url: str = Field(..., description="URL of the organization (RFC 3986)")


class Service(BaseModel):
    """GA4GH service base (id, name, type, organization, version)."""

    id: str = Field(..., description="Unique ID of this service, e.g. org.ga4gh.myservice")
    name: str = Field(..., description="Human-readable name")
    type: ServiceType
    organization: ServiceOrganization
    version: str = Field(..., description="Version of the service")
    description: str | None = None
    # GA4GH Service JSON Schema expects strings (not null) when fields are present.
    contactUrl: str = Field(default="", description="Contact URL (RFC 3986)")
    documentationUrl: str = Field(default="", description="Documentation URL (RFC 3986)")
    createdAt: str = Field(
        default="2024-01-01T00:00:00Z",
        description="RFC 3339 timestamp when the service was created",
    )
    updatedAt: str = Field(
        default="2024-01-01T00:00:00Z",
        description="RFC 3339 timestamp when the service was last updated",
    )
    environment: str = Field(default="", description="Deployment environment identifier")


class WorkflowTypeVersion(BaseModel):
    """Available workflow type versions supported by the service."""

    workflow_type_version: list[str] = Field(
        ...,
        description="Array of acceptable versions for the workflow_type",
    )


class WorkflowEngineVersion(BaseModel):
    """Available workflow engine versions supported by the service."""

    workflow_engine_version: list[str] = Field(
        ...,
        description="Array of acceptable engine versions for the workflow_engine",
    )


class DefaultWorkflowEngineParameter(BaseModel):
    """Default parameter for a workflow engine."""

    name: str | None = None
    type: str | None = None
    default_value: str | None = None


class ServiceInfo(Service):
    """WES service info response (GetServiceInfo)."""

    workflow_type_versions: dict[str, WorkflowTypeVersion] = Field(
        ...,
        description="Supported workflow types and their versions",
    )
    supported_wes_versions: list[str] = Field(
        ...,
        description="WES schema versions supported by this service",
    )
    supported_filesystem_protocols: list[str] = Field(
        ...,
        description="Protocols supported, e.g. http, https, file, s3, gs",
    )
    workflow_engine_versions: dict[str, WorkflowEngineVersion] = Field(
        ...,
        description="Supported workflow engines and their versions",
    )
    default_workflow_engine_parameters: list[DefaultWorkflowEngineParameter] = Field(
        default_factory=list,
        description="Default parameters for each workflow engine",
    )
    system_state_counts: dict[str, int] = Field(
        ...,
        description="Count of runs per state",
    )
    auth_instructions_url: str = Field(
        ...,
        description="URL with instructions on how to get an authorization token",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Useful information about the service",
    )


# ----- Run request & identifiers -----


class RunRequest(BaseModel):
    """Request body for RunWorkflow (POST /runs)."""

    workflow_params: dict[str, Any] | None = Field(
        default=None,
        description="Workflow run parameterizations (JSON), including input/output file locations",
    )
    workflow_type: str = Field(..., description="Workflow descriptor type, e.g. CWL, WDL, NEXTFLOW")
    workflow_type_version: str = Field(..., description="Workflow descriptor type version")
    tags: dict[str, str] | None = Field(default=None, description="Arbitrary key/value tags")
    workflow_engine_parameters: dict[str, str] | None = Field(default=None)
    workflow_engine: str | None = Field(default=None, description="Engine, e.g. nextflow")
    workflow_engine_version: str | None = Field(default=None)
    workflow_url: str = Field(
        ...,
        description="URL or path to workflow file (absolute or relative to workflow_attachment)",
    )


class RunId(BaseModel):
    """Response containing the workflow run ID (POST /runs, POST /runs/{run_id}/cancel)."""

    run_id: str = Field(..., description="Workflow run ID")


# ----- Run status & list -----


class RunStatus(BaseModel):
    """State information of a workflow run (GetRunStatus)."""

    run_id: str
    state: State


class RunSummary(RunStatus):
    """Summary of a workflow run (includes start_time, end_time, tags)."""

    start_time: str | None = Field(
        default=None,
        description='When the run started, ISO 8601 "%Y-%m-%dT%H:%M:%SZ"',
    )
    end_time: str | None = Field(
        default=None,
        description='When the run stopped, ISO 8601 "%Y-%m-%dT%H:%M:%SZ"',
    )
    tags: dict[str, str] | None = Field(default=None, description="Tags from run creation")


class RunListResponse(BaseModel):
    """Response for ListRuns (GET /runs)."""

    runs: list[RunStatus | RunSummary] = Field(
        ...,
        description="List of workflow runs the caller has permission to see",
    )
    next_page_token: str = Field(
        default="",
        description="Token for next page of results; empty string if no more items",
    )


# ----- Logs -----


class Log(BaseModel):
    """Log and other info for a workflow run or task."""

    name: str | None = Field(default=None, description="Task or workflow name")
    cmd: list[str] | None = Field(default=None, description="Command line that was executed")
    start_time: str | None = Field(
        default=None,
        description='When the command started, ISO 8601 "%Y-%m-%dT%H:%M:%SZ"',
    )
    end_time: str | None = Field(
        default=None,
        description='When the command stopped, ISO 8601 "%Y-%m-%dT%H:%M:%SZ"',
    )
    stdout: str | None = Field(
        default=None,
        description="URL or inline content for standard output logs",
    )
    stderr: str | None = Field(
        default=None,
        description="URL or inline content for standard error logs",
    )
    exit_code: int | None = Field(default=None, description="Exit code of the program")
    system_logs: list[str] | None = Field(
        default=None,
        description="System logs not tied directly to the workflow",
    )


class TaskLog(Log):
    """Runtime information for a given task (extends Log with id)."""

    id: str = Field(..., description="Unique identifier for the task")
    name: str = Field(..., description="Task name")
    tes_uri: str | None = Field(
        default=None,
        description="Optional URL to extended task definition (TES API)",
    )


class RunLog(BaseModel):
    """Detailed information about a workflow run (GetRunLog)."""

    run_id: str
    request: RunRequest | None = Field(default=None, description="Original run request")
    state: State
    run_log: Log | None = Field(default=None, description="Main run log")
    task_logs_url: str | None = Field(
        default=None,
        description="URL to paginated list of task logs",
    )
    task_logs: list[Log | TaskLog] | None = Field(
        default=None,
        description="Logs for each step (deprecated in spec, still supported)",
    )
    outputs: dict[str, Any] | None = Field(
        default=None, description="Outputs from the workflow run"
    )


# ----- Error -----


class ErrorResponse(BaseModel):
    """Error response body."""

    msg: str = Field(..., description="Detailed error message")
    status_code: int | None = Field(default=None, description="HTTP status code")
