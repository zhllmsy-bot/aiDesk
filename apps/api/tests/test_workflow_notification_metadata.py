from __future__ import annotations

from api.workflows.definitions.base import WorkflowExecutionContext


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
