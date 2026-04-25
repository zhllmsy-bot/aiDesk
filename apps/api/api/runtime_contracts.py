from __future__ import annotations

from enum import StrEnum

RUNTIME_SCHEMA_VERSION = "2026-04-19.runtime.v1"
RUNTIME_TASK_QUEUE = "ai-desk.runtime"


class WorkflowName(StrEnum):
    PROJECT_IMPORT = "project.import"
    PROJECT_AUDIT = "project.audit"
    PROJECT_PLANNING = "project.planning"
    TASK_EXECUTION = "task.execution"
    PROJECT_IMPROVEMENT = "project.improvement"


class WorkflowRunStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    VERIFYING = "verifying"
    WAITING_APPROVAL = "waiting_approval"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    RECLAIMED = "reclaimed"
    CANCELLED = "cancelled"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ClaimStatus(StrEnum):
    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"
    RECLAIMED = "reclaimed"


class GraphKind(StrEnum):
    AUDITOR = "auditor"
    PLANNER = "planner"
    DECOMPOSITION = "decomposition"
    REVIEWER = "reviewer"


class GraphExecutionStatus(StrEnum):
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


class WorkerHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class EventType(StrEnum):
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_RETRYING = "workflow.retrying"
    WORKFLOW_WAITING_APPROVAL = "workflow.waiting_approval"
    TASK_CLAIMED = "task.claimed"
    TASK_RUNNING = "task.running"
    TASK_VERIFYING = "task.verifying"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_HEARTBEAT = "task.heartbeat"
    TASK_RECLAIMED = "task.reclaimed"
    TASK_GRAPH_UPDATED = "task.graph.updated"
    TASK_TODO_UPDATED = "task.todo.updated"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_RESOLVED = "approval.resolved"
    NOTIFICATION_SENT = "notification.sent"
    ARTIFACT_LINKED = "artifact.linked"
    MEMORY_RECALLED = "memory.recalled"
    MEMORY_WRITTEN = "memory.written"
    RUNTIME_GRAPH_INTERRUPTED = "runtime.graph.interrupted"
    RUNTIME_GRAPH_COMPLETED = "runtime.graph.completed"
    WORKER_HEALTH_REPORTED = "worker.health.reported"


EVENT_LABELS: dict[EventType, str] = {
    EventType.WORKFLOW_STARTED: "Workflow started",
    EventType.WORKFLOW_COMPLETED: "Workflow completed",
    EventType.WORKFLOW_FAILED: "Workflow failed",
    EventType.WORKFLOW_RETRYING: "Workflow retrying",
    EventType.WORKFLOW_WAITING_APPROVAL: "Workflow waiting approval",
    EventType.TASK_CLAIMED: "Task claimed",
    EventType.TASK_RUNNING: "Task running",
    EventType.TASK_VERIFYING: "Task verifying",
    EventType.TASK_COMPLETED: "Task completed",
    EventType.TASK_FAILED: "Task failed",
    EventType.TASK_HEARTBEAT: "Task heartbeat",
    EventType.TASK_RECLAIMED: "Task reclaimed",
    EventType.TASK_GRAPH_UPDATED: "Task graph updated",
    EventType.TASK_TODO_UPDATED: "Task todo updated",
    EventType.APPROVAL_REQUESTED: "Approval requested",
    EventType.APPROVAL_RESOLVED: "Approval resolved",
    EventType.NOTIFICATION_SENT: "Notification sent",
    EventType.ARTIFACT_LINKED: "Artifact linked",
    EventType.MEMORY_RECALLED: "Memory recalled",
    EventType.MEMORY_WRITTEN: "Memory written",
    EventType.RUNTIME_GRAPH_INTERRUPTED: "Runtime graph interrupted",
    EventType.RUNTIME_GRAPH_COMPLETED: "Runtime graph completed",
    EventType.WORKER_HEALTH_REPORTED: "Worker health reported",
}
