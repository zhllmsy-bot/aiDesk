from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.executors.contracts import (
    ApprovalResolutionPayload,
    ApprovalStatus,
    ArtifactType,
    DispatchControl,
    EvidenceKind,
    EvidenceRef,
    ExecutorInputBundle,
    PermissionPolicy,
    TaskInfo,
    VerifyCommand,
    WorkspaceInfo,
    WorkspaceMode,
)
from tests.e2e.conftest import register_user

pytestmark = pytest.mark.e2e


def _write_bundle(
    *,
    task_id: str = "task-approval-1",
    run_id: str = "run-approval-1",
    attempt_id: str = "attempt-approval-1",
    dispatch_key: str = "dispatch-approval-1",
) -> ExecutorInputBundle:
    return ExecutorInputBundle(
        task=TaskInfo(
            task_id=task_id,
            run_id=run_id,
            title="Write task needing approval",
            description="Requires write approval",
            executor="codex",
            expected_artifact_types=[ArtifactType.PATCH],
        ),
        workspace=WorkspaceInfo(
            project_id="project-approval",
            iteration_id="iter-approval",
            workspace_ref="ws-approval",
            root_path="/repo/project",
            mode=WorkspaceMode.WORKTREE,
            writable_paths=["/repo/project/apps/api"],
        ),
        context_blocks=[],
        permission_policy=PermissionPolicy(
            workspace_allowlist=["/repo"],
            allowed_write_paths=["/repo/project/apps/api"],
            command_allowlist=["pytest", "python"],
            command_denylist=["rm -rf"],
            require_manual_approval_for_write=True,
            workspace_mode=WorkspaceMode.WORKTREE,
        ),
        verify_commands=[VerifyCommand(id="verify-approval", command="pytest -q")],
        proposed_commands=["pytest -q"],
        secret_usages=[],
        evidence_refs=[
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                ref="artifact-approval-seed",
                summary="approval seed",
            )
        ],
        dispatch=DispatchControl(
            idempotency_key=dispatch_key,
            attempt_id=attempt_id,
        ),
    )


def test_approval_required_then_resolve_then_complete(
    e2e_client: TestClient,
) -> None:
    headers = register_user(e2e_client, "e2e-approval@example.com")

    dispatch_response = e2e_client.post(
        "/executors/dispatch",
        json=_write_bundle().model_dump(mode="json"),
        headers=headers,
    )
    assert dispatch_response.status_code == 200
    payload = dispatch_response.json()
    assert payload["result"] is None
    assert payload["approval"] is not None
    approval_id = payload["approval"]["approval_id"]
    assert payload["approval"]["status"] == "pending"

    approvals_list = e2e_client.get("/review/approvals", headers=headers)
    assert approvals_list.status_code == 200
    items = approvals_list.json()["items"]
    assert any(item["id"] == approval_id for item in items)

    approval_detail = e2e_client.get(f"/review/approvals/{approval_id}", headers=headers)
    assert approval_detail.status_code == 200
    detail = approval_detail.json()
    assert detail["status"] == "pending"
    assert detail["type"] == "write_execution"

    resolve_response = e2e_client.post(
        f"/review/approvals/{approval_id}/resolve",
        json=ApprovalResolutionPayload(
            decision=ApprovalStatus.APPROVED,
            reason="E2E test approval",
            approved_write_paths=["/repo/project/apps/api"],
        ).model_dump(mode="json"),
        headers=headers,
    )
    assert resolve_response.status_code == 200
    resolved = resolve_response.json()
    assert resolved["status"] == "approved"

    resolved_detail = e2e_client.get(f"/review/approvals/{approval_id}", headers=headers)
    assert resolved_detail.status_code == 200
    assert resolved_detail.json()["status"] == "approved"

    attempt_id = _write_bundle().dispatch.attempt_id
    attempt_response = e2e_client.get(f"/review/attempts/{attempt_id}", headers=headers)
    assert attempt_response.status_code == 200
    assert attempt_response.json()["id"] == "attempt-approval-1"


def test_approval_rejected_blocks_execution(e2e_client: TestClient) -> None:
    headers = register_user(e2e_client, "e2e-rejection@example.com")

    dispatch_response = e2e_client.post(
        "/executors/dispatch",
        json=_write_bundle(
            task_id="task-reject-1",
            run_id="run-reject-1",
            attempt_id="attempt-reject-1",
            dispatch_key="dispatch-reject-1",
        ).model_dump(mode="json"),
        headers=headers,
    )
    assert dispatch_response.status_code == 200
    approval_id = dispatch_response.json()["approval"]["approval_id"]

    resolve_response = e2e_client.post(
        f"/review/approvals/{approval_id}/resolve",
        json=ApprovalResolutionPayload(
            decision=ApprovalStatus.REJECTED,
            reason="E2E test rejection",
        ).model_dump(mode="json"),
        headers=headers,
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "rejected"

    resolved_detail = e2e_client.get(f"/review/approvals/{approval_id}", headers=headers)
    assert resolved_detail.status_code == 200
    assert resolved_detail.json()["status"] == "rejected"
