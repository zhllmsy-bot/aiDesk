from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from api.executors.contracts import (
    ApprovalResolutionPayload,
    ApprovalStatus,
    ArtifactType,
    DispatchControl,
    EvidenceKind,
    EvidenceRef,
    ExecutorInputBundle,
    MemoryType,
    MemoryWriteCandidate,
    PermissionPolicy,
    TaskInfo,
    VerifyCommand,
    WorkspaceInfo,
    WorkspaceMode,
)
from tests.helpers import build_test_settings, run_migrations

pytestmark = pytest.mark.e2e


def _settings_for(database_url: str):
    return build_test_settings(
        database_url=database_url,
        runtime_worker_id="restart-worker",
    )


def _register_user(client: TestClient, email: str = "restart-user@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "super-secure-password",
            "display_name": "Restart User",
        },
    )
    token = response.json()["session"]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_runtime_data_survives_app_restart(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'restart.db'}"
    run_migrations(database_url)

    workflow_run_id: str | None = None

    settings = _settings_for(database_url)
    app = create_app(settings)
    with TestClient(app) as client:
        bootstrap = client.post("/runtime/dev/bootstrap?workflow_name=project.planning")
        assert bootstrap.status_code == 202
        workflow_run_id = bootstrap.json()["workflow_run_id"]

        timeline = client.get(f"/runtime/runs/{workflow_run_id}/timeline")
        assert timeline.status_code == 200
        assert len(timeline.json()["entries"]) >= 2

        graph = client.get(f"/runtime/runs/{workflow_run_id}/graph")
        assert graph.status_code == 200
        assert len(graph.json()["nodes"]) >= 1

    restarted_settings = _settings_for(database_url)
    restarted_app = create_app(restarted_settings)
    with TestClient(restarted_app) as client2:
        timeline2 = client2.get(f"/runtime/runs/{workflow_run_id}/timeline")
        assert timeline2.status_code == 200
        assert len(timeline2.json()["entries"]) >= 2
        event_types = {e["event_type"] for e in timeline2.json()["entries"]}
        assert "workflow.started" in event_types
        assert "task.completed" in event_types

        graph2 = client2.get(f"/runtime/runs/{workflow_run_id}/graph")
        assert graph2.status_code == 200
        assert len(graph2.json()["nodes"]) >= 1

        attempts2 = client2.get("/runtime/tasks/task-1/attempts")
        assert attempts2.status_code == 200
        assert len(attempts2.json()["attempts"]) >= 1

        workers2 = client2.get("/runtime/workers/health")
        assert workers2.status_code == 200
        assert len(workers2.json()) >= 1


def test_review_and_memory_data_survives_app_restart(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'restart-review.db'}"
    run_migrations(database_url)

    approval_id: str | None = None
    memory_id: str | None = None

    settings = _settings_for(database_url)
    app = create_app(settings)
    with TestClient(app) as client:
        headers = _register_user(client)

        dispatch_response = client.post(
            "/executors/dispatch",
            json=ExecutorInputBundle(
                task=TaskInfo(
                    task_id="task-restart-1",
                    run_id="run-restart-1",
                    title="Restart test task",
                    description="Needs approval",
                    executor="codex",
                    expected_artifact_types=[ArtifactType.PATCH],
                ),
                workspace=WorkspaceInfo(
                    project_id="project-restart",
                    iteration_id="iter-restart",
                    workspace_ref="ws-restart",
                    root_path="/repo/project",
                    mode=WorkspaceMode.WORKTREE,
                    writable_paths=["/repo/project/apps/api"],
                ),
                context_blocks=[],
                permission_policy=PermissionPolicy(
                    workspace_allowlist=["/repo"],
                    allowed_write_paths=["/repo/project/apps/api"],
                    command_allowlist=["pytest"],
                    command_denylist=["rm -rf"],
                    require_manual_approval_for_write=True,
                    workspace_mode=WorkspaceMode.WORKTREE,
                ),
                verify_commands=[VerifyCommand(id="verify-restart", command="pytest -q")],
                proposed_commands=["pytest -q"],
                secret_usages=[],
                evidence_refs=[
                    EvidenceRef(
                        kind=EvidenceKind.ARTIFACT,
                        ref="artifact-restart-seed",
                        summary="restart seed",
                    )
                ],
                dispatch=DispatchControl(
                    idempotency_key="dispatch-restart-1",
                    attempt_id="attempt-restart-1",
                ),
            ).model_dump(mode="json"),
            headers=headers,
        )
        assert dispatch_response.status_code == 200
        approval_id = dispatch_response.json()["approval"]["approval_id"]

        resolve_response = client.post(
            f"/review/approvals/{approval_id}/resolve",
            json=ApprovalResolutionPayload(
                decision=ApprovalStatus.APPROVED,
                reason="Pre-restart approval",
                approved_write_paths=["/repo/project/apps/api"],
            ).model_dump(mode="json"),
            headers=headers,
        )
        assert resolve_response.status_code == 200

        memory_response = client.post(
            "/memory/writes",
            json=MemoryWriteCandidate(
                project_id="project-restart",
                iteration_id="iter-restart",
                memory_type=MemoryType.PROJECT_FACT,
                external_ref="doc://project-restart/facts/structure",
                summary="Project uses modular FastAPI architecture",
                content_hash="hash-restart-fact",
                quality_score=0.88,
            ).model_dump(mode="json"),
            headers=headers,
        )
        assert memory_response.status_code == 201
        memory_id = memory_response.json()["items"][0]["id"]

    restarted_settings = _settings_for(database_url)
    restarted_app = create_app(restarted_settings)
    with TestClient(restarted_app) as client2:
        headers2 = _register_user(client2, "restart-user2@example.com")

        approval_detail = client2.get(f"/review/approvals/{approval_id}", headers=headers2)
        assert approval_detail.status_code == 200
        assert approval_detail.json()["status"] == "approved"
        assert approval_detail.json()["id"] == approval_id

        approvals_list = client2.get("/review/approvals", headers=headers2)
        assert approvals_list.status_code == 200
        assert any(a["id"] == approval_id for a in approvals_list.json()["items"])

        memory_recall = client2.get(
            "/memory/hits?project_id=project-restart",
            headers=headers2,
        )
        assert memory_recall.status_code == 200
        items = memory_recall.json()["items"]
        assert len(items) >= 1
        assert any(item["id"] == memory_id for item in items)
        assert any(item["summary"] == "Project uses modular FastAPI architecture" for item in items)
