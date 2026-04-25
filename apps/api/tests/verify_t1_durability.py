from __future__ import annotations

import os
import tempfile

from api.database import create_session_factory
from api.executors.contracts import (
    ApprovalType,
    ArtifactType,
    AttemptStatus,
    DispatchControl,
    EvidenceKind,
    EvidenceRef,
    ExecutionProvenance,
    ExecutorInputBundle,
    PermissionPolicy,
    TaskInfo,
    VerifyCommand,
    WorkspaceInfo,
    WorkspaceMode,
)
from api.review.service import ApprovalService, AttemptStore, EvidenceService
from tests.helpers import run_migrations


def sample_bundle():
    return ExecutorInputBundle(
        task=TaskInfo(
            task_id="task-1",
            run_id="run-1",
            title="Implement feature",
            description="Make a change",
            executor="codex",
            expected_artifact_types=[ArtifactType.PATCH],
        ),
        workspace=WorkspaceInfo(
            project_id="project-1",
            iteration_id="iter-1",
            workspace_ref="ws-1",
            root_path="/repo/project",
            mode=WorkspaceMode.WORKTREE,
            writable_paths=["/repo/project/apps/api"],
        ),
        context_blocks=[],
        permission_policy=PermissionPolicy(
            workspace_allowlist=["/repo"],
            allowed_write_paths=["/repo/project/apps/api"],
            command_allowlist=["pytest", "python"],
            command_denylist=["rm -rf", "curl "],
            require_manual_approval_for_write=True,
            workspace_mode=WorkspaceMode.WORKTREE,
        ),
        verify_commands=[VerifyCommand(id="verify-1", command="pytest -q")],
        proposed_commands=["pytest -q"],
        secret_usages=[],
        evidence_refs=[
            EvidenceRef(kind=EvidenceKind.ARTIFACT, ref="artifact-seed", summary="seed")
        ],
        dispatch=DispatchControl(idempotency_key="dispatch-1", attempt_id="attempt-1"),
    )


def main():
    db_path = os.path.join(tempfile.mkdtemp(), "test.db")
    database_url = f"sqlite+pysqlite:///{db_path}"
    run_migrations(database_url)

    session_factory = create_session_factory(database_url)

    approvals = ApprovalService(session_factory=session_factory)
    approval = approvals.request_approval(
        project_id="project-1",
        run_id="run-1",
        task_id="task-1",
        approval_type=ApprovalType.WRITE_EXECUTION,
        requested_by="system",
        reason="test",
        required_scope=["/repo"],
    )

    attempts = AttemptStore(session_factory=session_factory)
    bundle = sample_bundle()
    summary = attempts.record_waiting_approval(bundle, approval)
    print(f"Attempt recorded: {summary.attempt_id}, status: {summary.status}")

    retrieved = attempts.get_attempt("attempt-1")
    print(f"Attempt retrieved: {retrieved.attempt_id}, status: {retrieved.status}")
    assert retrieved.attempt_id == "attempt-1"
    assert retrieved.status == AttemptStatus.WAITING_APPROVAL

    evidence = EvidenceService(session_factory=session_factory)
    provenance = ExecutionProvenance(
        executor="codex",
        provider_request_id="req-1",
        attempt_id="attempt-1",
        workspace_ref="ws-1",
        trigger="manual",
    )
    evidence.record_execution(
        attempt_id="attempt-1",
        artifact_ids=["artifact-1"],
        verification=None,
        provenance=provenance,
    )
    ev_summary = evidence.get_summary("attempt-1")
    print(f"Evidence recorded: {ev_summary.attempt_id}, artifacts: {ev_summary.artifact_ids}")
    assert ev_summary.attempt_id == "attempt-1"

    attempts2 = AttemptStore(session_factory=session_factory)
    evidence2 = EvidenceService(session_factory=session_factory)
    retrieved2 = attempts2.get_attempt("attempt-1")
    ev2 = evidence2.get_summary("attempt-1")
    print(f"Durability check - attempt: {retrieved2.attempt_id}, evidence: {ev2.attempt_id}")
    assert retrieved2.attempt_id == "attempt-1"
    assert ev2.attempt_id == "attempt-1"

    print("ALL DURABILITY TESTS PASSED!")


if __name__ == "__main__":
    main()
