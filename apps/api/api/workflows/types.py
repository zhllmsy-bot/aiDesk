from __future__ import annotations

# pyright: reportUnknownVariableType=false
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


@dataclass(slots=True)
class WorkflowTaskSpec:
    task_id: str
    title: str
    graph_kind: str
    depends_on: list[str] = field(default_factory=list)
    requires_approval: bool = False
    executor_summary: str | None = None
    executor_name: str | None = None


@dataclass(slots=True)
class WorkflowSimulationOptions:
    retry_task_ids: list[str] = field(default_factory=list)
    terminal_failure_task_ids: list[str] = field(default_factory=list)
    reclaim_task_ids: list[str] = field(default_factory=list)
    approval_task_ids: list[str] = field(default_factory=list)
    interrupt_task_ids: list[str] = field(default_factory=list)


class BreakGlassKind(StrEnum):
    INCIDENT_RESPONSE = "incident_response"
    MAINTENANCE = "maintenance"
    OPERATOR_OVERRIDE = "operator_override"


@dataclass(slots=True)
class BreakGlassReason:
    kind: BreakGlassKind
    reason: str
    approved_by: str
    ticket_id: str | None = None
    expires_at: str | None = None


@dataclass(slots=True)
class RequestOptions:
    full_access: BreakGlassReason | None = None


@dataclass(slots=True)
class WorkflowRequest:
    workflow_run_id: str
    project_id: str
    initiated_by: str
    trace_id: str
    objective: str
    tasks: list[WorkflowTaskSpec] = field(default_factory=list)
    require_manual_approval: bool = False
    max_attempts: int = 2
    signal_timeout_seconds: int = 300
    lease_timeout_seconds: int = 30
    metadata: dict[str, Any] = field(default_factory=dict)
    request_options: RequestOptions = field(default_factory=RequestOptions)
    simulation: WorkflowSimulationOptions = field(default_factory=WorkflowSimulationOptions)


@dataclass(slots=True)
class ApprovalResolution:
    approved: bool
    actor: str
    comment: str | None = None
    approval_id: str | None = None
    approved_write_paths: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowResult:
    workflow_run_id: str
    workflow_name: str
    status: str
    outputs: dict[str, Any]
    event_count: int
    approval_state: str | None = None
