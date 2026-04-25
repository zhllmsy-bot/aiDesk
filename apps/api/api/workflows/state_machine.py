from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportArgumentType=false
from dataclasses import dataclass, field
from typing import Any

from api.runtime_contracts import ClaimStatus, TaskStatus, WorkflowRunStatus


class InvalidTransitionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StatusTransition:
    from_status: str
    to_status: str
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


_WORKFLOW_TRANSITIONS: dict[WorkflowRunStatus, set[WorkflowRunStatus]] = {
    WorkflowRunStatus.CREATED: {WorkflowRunStatus.QUEUED, WorkflowRunStatus.RUNNING},
    WorkflowRunStatus.QUEUED: {WorkflowRunStatus.RUNNING, WorkflowRunStatus.CANCELLED},
    WorkflowRunStatus.RUNNING: {
        WorkflowRunStatus.WAITING_APPROVAL,
        WorkflowRunStatus.PAUSED,
        WorkflowRunStatus.RETRYING,
        WorkflowRunStatus.COMPLETED,
        WorkflowRunStatus.FAILED,
        WorkflowRunStatus.CANCELLED,
    },
    WorkflowRunStatus.WAITING_APPROVAL: {
        WorkflowRunStatus.RUNNING,
        WorkflowRunStatus.FAILED,
        WorkflowRunStatus.CANCELLED,
    },
    WorkflowRunStatus.PAUSED: {WorkflowRunStatus.RUNNING, WorkflowRunStatus.CANCELLED},
    WorkflowRunStatus.RETRYING: {WorkflowRunStatus.RUNNING, WorkflowRunStatus.FAILED},
    WorkflowRunStatus.COMPLETED: set(),
    WorkflowRunStatus.FAILED: {WorkflowRunStatus.RETRYING},
    WorkflowRunStatus.CANCELLED: set(),
}

_TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.QUEUED: {TaskStatus.CLAIMED, TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.CLAIMED: {TaskStatus.RUNNING, TaskStatus.RECLAIMED, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {
        TaskStatus.VERIFYING,
        TaskStatus.WAITING_APPROVAL,
        TaskStatus.RETRYING,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.RECLAIMED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.VERIFYING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.RETRYING},
    TaskStatus.WAITING_APPROVAL: {
        TaskStatus.RUNNING,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.RETRYING: {
        TaskStatus.QUEUED,
        TaskStatus.CLAIMED,
        TaskStatus.RUNNING,
        TaskStatus.FAILED,
    },
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: {TaskStatus.RETRYING},
    TaskStatus.RECLAIMED: {TaskStatus.CLAIMED, TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.CANCELLED: set(),
}

_CLAIM_TRANSITIONS: dict[ClaimStatus, set[ClaimStatus]] = {
    ClaimStatus.ACTIVE: {ClaimStatus.RELEASED, ClaimStatus.EXPIRED, ClaimStatus.RECLAIMED},
    ClaimStatus.EXPIRED: {ClaimStatus.RECLAIMED},
    ClaimStatus.RELEASED: set(),
    ClaimStatus.RECLAIMED: set(),
}


def _transition(
    *,
    current: str,
    target: str,
    reason: str,
    metadata: dict[str, Any] | None,
    enum_type: type[WorkflowRunStatus] | type[TaskStatus] | type[ClaimStatus],
    allowed: dict[WorkflowRunStatus, set[WorkflowRunStatus]]
    | dict[TaskStatus, set[TaskStatus]]
    | dict[ClaimStatus, set[ClaimStatus]],
) -> StatusTransition:
    current_status = enum_type(current)
    target_status = enum_type(target)
    if current_status != target_status and target_status not in allowed[current_status]:
        raise InvalidTransitionError(
            f"Invalid transition from {current_status.value} to {target_status.value}: {reason}"
        )
    return StatusTransition(
        from_status=current_status.value,
        to_status=target_status.value,
        reason=reason,
        metadata=metadata or {},
    )


def transition_workflow_run_status(
    current: str,
    target: str,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> StatusTransition:
    return _transition(
        current=current,
        target=target,
        reason=reason,
        metadata=metadata,
        enum_type=WorkflowRunStatus,
        allowed=_WORKFLOW_TRANSITIONS,
    )


def transition_task_status(
    current: str,
    target: str,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> StatusTransition:
    return _transition(
        current=current,
        target=target,
        reason=reason,
        metadata=metadata,
        enum_type=TaskStatus,
        allowed=_TASK_TRANSITIONS,
    )


def transition_claim_status(
    current: str,
    target: str,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> StatusTransition:
    return _transition(
        current=current,
        target=target,
        reason=reason,
        metadata=metadata,
        enum_type=ClaimStatus,
        allowed=_CLAIM_TRANSITIONS,
    )
