from __future__ import annotations

from api.workflows.definitions.base import WorkflowExecutionContext
from api.workflows.execution_policy import WorkflowExecutionPolicy
from api.workflows.types import (
    BreakGlassKind,
    BreakGlassReason,
    RequestOptions,
    WorkflowRequest,
)


def test_resolve_notification_metadata_defaults() -> None:
    metadata = WorkflowExecutionContext._resolve_notification_metadata(
        request_metadata={},
        workflow_name="project.improvement",
    )
    assert metadata == {"workflow_name": "project.improvement"}


def test_resolve_notification_metadata_includes_feishu_receive_id_and_type() -> None:
    metadata = WorkflowExecutionContext._resolve_notification_metadata(
        request_metadata={
            "notification": {
                "feishu": {
                    "receive_id": "oc_123",
                    "receive_id_type": "open_id",
                }
            }
        },
        workflow_name="project.improvement",
    )
    assert metadata["workflow_name"] == "project.improvement"
    assert metadata["receive_id"] == "oc_123"
    assert metadata["receive_id_type"] == "open_id"


def test_resolve_runtime_full_access_defaults_to_false() -> None:
    enabled = WorkflowExecutionContext._resolve_runtime_full_access({})
    assert enabled is False


def test_resolve_runtime_full_access_accepts_bool_and_truthy_string() -> None:
    assert WorkflowExecutionContext._resolve_runtime_full_access({"runtime_full_access": True})
    assert WorkflowExecutionContext._resolve_runtime_full_access({"runtime_full_access": "true"})
    assert WorkflowExecutionContext._resolve_runtime_full_access({"runtime_full_access": "1"})
    assert WorkflowExecutionContext._resolve_runtime_full_access({"runtime_full_access": "yes"})


def test_request_options_full_access_becomes_break_glass_reason() -> None:
    request = WorkflowRequest(
        workflow_run_id="run-break-glass",
        project_id="project-break-glass",
        initiated_by="operator",
        trace_id="trace-break-glass",
        objective="test break-glass",
        request_options=RequestOptions(
            full_access=BreakGlassReason(
                kind=BreakGlassKind.INCIDENT_RESPONSE,
                reason="restore stuck runtime",
                approved_by="lead-operator",
                ticket_id="INC-42",
            )
        ),
    )

    reason = WorkflowExecutionPolicy.resolve_request_full_access(request)

    assert reason is not None
    assert reason.kind == BreakGlassKind.INCIDENT_RESPONSE
    assert reason.ticket_id == "INC-42"
