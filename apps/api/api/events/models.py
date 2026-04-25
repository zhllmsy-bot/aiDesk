from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.runtime_contracts import (
    EventType,
    GraphExecutionStatus,
    GraphKind,
    TaskStatus,
    WorkerHealthStatus,
    WorkflowName,
)


class RuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, use_enum_values=True)


class CorrelationIds(RuntimeModel):
    workflow_run_id: str
    trace_id: str
    workflow_id: str | None = None
    project_id: str | None = None
    task_id: str | None = None
    attempt_id: str | None = None


class RunEventEnvelope(RuntimeModel):
    event_id: str
    event_type: EventType
    schema_version: str
    payload_version: str
    sequence: int
    producer: str
    occurred_at: str
    idempotency_key: str
    correlation: CorrelationIds
    payload: dict[str, Any] = Field(default_factory=dict)


class TimelineEntry(RuntimeModel):
    sequence: int
    event_type: EventType
    occurred_at: str
    label: str
    trace_id: str
    task_id: str | None = None
    attempt_id: str | None = None
    summary: str | None = None


class TimelineReadModel(RuntimeModel):
    workflow_run_id: str
    entries: list[TimelineEntry] = Field(default_factory=list)


class TaskTodoItem(RuntimeModel):
    id: str
    title: str
    status: str = "queued"
    detail: str | None = None


class TaskGraphNode(RuntimeModel):
    task_id: str
    title: str
    status: TaskStatus | None = None
    blocked_reason: str | None = None
    executor_summary: str | None = None
    todo_items: list[TaskTodoItem] = Field(default_factory=list)


class TaskGraphEdge(RuntimeModel):
    source_task_id: str
    target_task_id: str
    kind: str


class TaskGraphReadModel(RuntimeModel):
    workflow_run_id: str
    nodes: list[TaskGraphNode] = Field(default_factory=list)
    edges: list[TaskGraphEdge] = Field(default_factory=list)


class AttemptRecord(RuntimeModel):
    attempt_id: str
    task_id: str
    status: TaskStatus | None = None
    started_at: str | None = None
    ended_at: str | None = None
    event_sequence: list[int] = Field(default_factory=list)


class AttemptHistoryReadModel(RuntimeModel):
    task_id: str
    attempts: list[AttemptRecord] = Field(default_factory=list)


class WorkerHealthReadModel(RuntimeModel):
    worker_id: str
    task_queue: str
    status: WorkerHealthStatus
    last_seen_at: str
    active_workflow_names: list[WorkflowName] = Field(default_factory=list)
    detail: str | None = None


class GraphArtifact(RuntimeModel):
    artifact_id: str
    artifact_type: str
    title: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphExecutionResult(RuntimeModel):
    graph_kind: GraphKind
    status: GraphExecutionStatus
    trace_id: str
    structured_output: dict[str, Any] = Field(default_factory=dict)
    checkpoint: dict[str, Any] | None = None
    artifacts: list[GraphArtifact] = Field(default_factory=list)
    step_log: list[str] = Field(default_factory=list)
