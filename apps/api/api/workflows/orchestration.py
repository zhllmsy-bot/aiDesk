from __future__ import annotations

from collections.abc import Callable
from typing import Any

from api.context.assembly import AssemblyRequest
from api.executors.contracts import WorkspaceMode
from api.workflows.types import WorkflowRequest, WorkflowTaskSpec


def build_context_assembly_payload(
    *,
    request: WorkflowRequest,
    task: WorkflowTaskSpec,
    metadata_int_resolver: Callable[[str, int], int],
    evidence_serializer: Callable[[dict[str, Any]], list[dict[str, Any]]],
) -> dict[str, Any]:
    return AssemblyRequest(
        project_id=request.project_id,
        task_id=task.task_id,
        iteration_id=(
            str(request.metadata.get("iteration_id"))
            if request.metadata.get("iteration_id") is not None
            else None
        ),
        workspace_mode=WorkspaceMode.WORKTREE.value,
        require_approval=task.requires_approval,
        secret_broker_enabled=bool(request.metadata.get("secret_broker_enabled", False)),
        namespace_prefix=(
            str(request.metadata.get("memory_namespace_prefix"))
            if request.metadata.get("memory_namespace_prefix") is not None
            else None
        ),
        memory_limit=max(metadata_int_resolver("memory_limit", 5), 1),
        attempt_limit=max(metadata_int_resolver("attempt_limit", 3), 1),
        fact_limit=max(metadata_int_resolver("fact_limit", 5), 1),
        token_budget=max(metadata_int_resolver("context_token_budget", 4000), 100),
        max_blocks_per_level=max(metadata_int_resolver("context_blocks_per_level", 5), 1),
        extra_evidence_refs=evidence_serializer(request.metadata),
    ).model_dump(mode="json")


def summarize_notification_receipts(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    delivered_count = sum(1 for receipt in receipts if receipt.get("status") == "sent")
    failed_count = len(receipts) - delivered_count
    channels: dict[str, dict[str, int]] = {}
    for receipt in receipts:
        channel = str(receipt.get("channel") or "unknown")
        state = "sent" if receipt.get("status") == "sent" else "failed"
        channel_stats = channels.setdefault(channel, {"sent": 0, "failed": 0})
        channel_stats[state] += 1
    return {
        "delivered_count": delivered_count,
        "failed_count": failed_count,
        "channels": channels,
    }
