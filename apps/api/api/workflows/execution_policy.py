from __future__ import annotations

from typing import Any

from api.executors.contracts import ArtifactType, WorkspaceMode
from api.workflows.types import ApprovalResolution, WorkflowRequest, WorkflowTaskSpec


def normalize_context_blocks(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    raw_blocks = metadata.get("context_blocks", [])
    if not isinstance(raw_blocks, list):
        return []
    blocks: list[dict[str, Any]] = []
    for index, item in enumerate(raw_blocks, start=1):
        if isinstance(item, dict):
            block = dict(item)
            block.setdefault("level", "L1")
            block.setdefault("title", f"runtime-context-{index}")
            block.setdefault("body", "")
            block.setdefault("source", "runtime.metadata")
            block.setdefault("truncated", False)
            block.setdefault("evidence_refs", [])
            blocks.append(block)
            continue
        if isinstance(item, str):
            body = item.strip()
            if not body:
                continue
            blocks.append(
                {
                    "level": "L1",
                    "title": f"runtime-context-{index}",
                    "body": body,
                    "source": "runtime.metadata",
                    "truncated": False,
                    "evidence_refs": [],
                }
            )
    return blocks


def serialize_evidence_refs(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    raw_refs = metadata.get("evidence_refs", [])
    if not isinstance(raw_refs, list):
        return []
    serialized: list[dict[str, Any]] = []
    for item in raw_refs:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip()
        ref = str(item.get("ref") or "").strip()
        if not kind or not ref:
            continue
        serialized.append(
            {
                "kind": kind,
                "ref": ref,
                "summary": str(item.get("summary")) if item.get("summary") is not None else None,
            }
        )
    return serialized


def normalize_verify_commands(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    raw_commands = metadata.get("verify_commands", [])
    if not isinstance(raw_commands, list):
        return []
    commands: list[dict[str, Any]] = []
    for index, item in enumerate(raw_commands, start=1):
        if isinstance(item, dict):
            command = str(item.get("command") or "").strip()
            if not command:
                continue
            commands.append(
                {
                    "id": str(item.get("id") or f"verify-{index}"),
                    "command": command,
                    "required": bool(item.get("required", True)),
                }
            )
            continue
        if isinstance(item, str):
            command = item.strip()
            if not command:
                continue
            commands.append(
                {
                    "id": f"verify-{index}",
                    "command": command,
                    "required": True,
                }
            )
    return commands


def resolve_notification_metadata(
    request_metadata: dict[str, Any],
    workflow_name: str,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {"workflow_name": workflow_name}
    notification = request_metadata.get("notification")
    if not isinstance(notification, dict):
        return metadata
    feishu = notification.get("feishu")
    if not isinstance(feishu, dict):
        return metadata

    receive_id = feishu.get("receive_id")
    if isinstance(receive_id, str) and receive_id.strip():
        metadata["receive_id"] = receive_id.strip()

    receive_id_type = feishu.get("receive_id_type")
    if isinstance(receive_id_type, str) and receive_id_type.strip():
        metadata["receive_id_type"] = receive_id_type.strip()
    return metadata


def resolve_runtime_full_access(metadata: dict[str, Any]) -> bool:
    value = metadata.get("runtime_full_access")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "on"}
    return False


def workspace_root_path(metadata: dict[str, Any]) -> str:
    return str(metadata.get("workspace_root_path", "/tmp/ai-desk-workspace"))


def workspace_writable_paths(
    metadata: dict[str, Any],
    approval_resolution: ApprovalResolution | None = None,
) -> list[str]:
    if approval_resolution is not None and approval_resolution.approved_write_paths:
        return list(approval_resolution.approved_write_paths)
    raw = metadata.get("workspace_writable_paths", [])
    return list(raw) if isinstance(raw, list) else []


def workspace_allowlist(metadata: dict[str, Any], resolved_root_path: str) -> list[str]:
    raw = metadata.get("workspace_allowlist")
    if isinstance(raw, list) and raw:
        return list(raw)
    return [resolved_root_path]


def build_executor_dispatch_payload(
    *,
    request: WorkflowRequest,
    task: WorkflowTaskSpec,
    attempt_id: str,
    executor_dispatch_timeout_seconds: int,
    normalized_verify_commands: list[dict[str, Any]],
    normalized_context_blocks: list[dict[str, Any]],
    approval_resolution: ApprovalResolution | None = None,
) -> dict[str, Any]:
    resolved_workspace_root_path = workspace_root_path(request.metadata)
    writable_paths = workspace_writable_paths(request.metadata, approval_resolution)
    full_access = resolve_runtime_full_access(request.metadata)
    permission_policy: dict[str, Any]
    if full_access:
        permission_policy = {
            "workspace_allowlist": [resolved_workspace_root_path],
            "allowed_write_paths": writable_paths or [resolved_workspace_root_path],
            "command_allowlist": [],
            "command_denylist": [],
            "require_manual_approval_for_write": False,
            "secret_broker_enabled": True,
            "workspace_mode": WorkspaceMode.WORKTREE,
        }
    else:
        permission_policy = {
            "workspace_allowlist": workspace_allowlist(
                request.metadata,
                resolved_workspace_root_path,
            ),
            "allowed_write_paths": writable_paths,
            "command_allowlist": request.metadata.get("command_allowlist", []),
            "command_denylist": request.metadata.get("command_denylist", []),
            "require_manual_approval_for_write": (
                False if approval_resolution is not None else task.requires_approval
            ),
            "secret_broker_enabled": bool(request.metadata.get("secret_broker_enabled", False)),
            "workspace_mode": WorkspaceMode.WORKTREE,
        }
    return {
        "task": {
            "task_id": task.task_id,
            "run_id": request.workflow_run_id,
            "title": task.title,
            "description": request.objective,
            "executor": task.executor_name,
            "expected_artifact_types": [ArtifactType.LOG],
        },
        "workspace": {
            "project_id": request.project_id,
            "workspace_ref": request.workflow_run_id,
            "root_path": resolved_workspace_root_path,
            "mode": WorkspaceMode.WORKTREE,
            "writable_paths": writable_paths,
        },
        "permission_policy": permission_policy,
        "dispatch": {
            "idempotency_key": f"{request.workflow_run_id}-{task.task_id}",
            "attempt_id": attempt_id,
            "timeout_seconds": executor_dispatch_timeout_seconds,
        },
        "verify_commands": normalized_verify_commands,
        "context_blocks": normalized_context_blocks,
        "evidence_refs": request.metadata.get("evidence_refs", []),
    }


class WorkflowExecutionPolicy:
    def __init__(self, request: WorkflowRequest) -> None:
        self._request = request

    @staticmethod
    def normalize_context_blocks(metadata: dict[str, Any]) -> list[dict[str, Any]]:
        return normalize_context_blocks(metadata)

    @staticmethod
    def serialize_evidence_refs(metadata: dict[str, Any]) -> list[dict[str, Any]]:
        return serialize_evidence_refs(metadata)

    @staticmethod
    def normalize_verify_commands(metadata: dict[str, Any]) -> list[dict[str, Any]]:
        return normalize_verify_commands(metadata)

    @staticmethod
    def resolve_notification_metadata(
        request_metadata: dict[str, Any],
        workflow_name: str,
    ) -> dict[str, Any]:
        return resolve_notification_metadata(request_metadata, workflow_name)

    @staticmethod
    def resolve_runtime_full_access(metadata: dict[str, Any]) -> bool:
        return resolve_runtime_full_access(metadata)

    def workspace_root_path(self) -> str:
        return workspace_root_path(self._request.metadata)

    def workspace_writable_paths(
        self,
        approval_resolution: ApprovalResolution | None = None,
    ) -> list[str]:
        return workspace_writable_paths(self._request.metadata, approval_resolution)

    def workspace_allowlist(self, resolved_root_path: str) -> list[str]:
        return workspace_allowlist(self._request.metadata, resolved_root_path)

    def build_executor_dispatch_payload(
        self,
        *,
        task: WorkflowTaskSpec,
        attempt_id: str,
        executor_dispatch_timeout_seconds: int,
        normalized_verify_commands: list[dict[str, Any]],
        normalized_context_blocks: list[dict[str, Any]],
        approval_resolution: ApprovalResolution | None = None,
    ) -> dict[str, Any]:
        return build_executor_dispatch_payload(
            request=self._request,
            task=task,
            attempt_id=attempt_id,
            executor_dispatch_timeout_seconds=executor_dispatch_timeout_seconds,
            normalized_verify_commands=normalized_verify_commands,
            normalized_context_blocks=normalized_context_blocks,
            approval_resolution=approval_resolution,
        )
