from __future__ import annotations

from api.executors.contracts import (
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
from api.executors.providers.codex import CodexExecutorAdapter
from api.executors.transports import CodexSessionConfig


def _bundle() -> ExecutorInputBundle:
    return ExecutorInputBundle(
        task=TaskInfo(
            task_id="provider-task-1",
            run_id="provider-run-1",
            title="Provider artifact test",
            description="Verify Codex artifact metadata",
            executor="codex",
            metadata={"simulate_success": True},
        ),
        workspace=WorkspaceInfo(
            project_id="provider-project",
            workspace_ref="provider-workspace",
            root_path="/tmp",
            mode=WorkspaceMode.READ_ONLY,
            writable_paths=[],
        ),
        context_blocks=[],
        permission_policy=PermissionPolicy(
            workspace_allowlist=["/tmp"],
            allowed_write_paths=[],
            command_allowlist=["pytest"],
            command_denylist=["rm -rf"],
            require_manual_approval_for_write=False,
            workspace_mode=WorkspaceMode.READ_ONLY,
        ),
        verify_commands=[VerifyCommand(id="verify-1", command="pytest -q")],
        proposed_commands=["pytest -q"],
        secret_usages=[],
        evidence_refs=[
            EvidenceRef(kind=EvidenceKind.ARTIFACT, ref="seed-artifact", summary="seed")
        ],
        dispatch=DispatchControl(
            idempotency_key="provider-dispatch-1",
            attempt_id="provider-attempt-1",
            timeout_seconds=60,
        ),
    )


def _adapter() -> CodexExecutorAdapter:
    return CodexExecutorAdapter(
        CodexSessionConfig(
            transport="stdio",
            url="ws://127.0.0.1:8321",
            command="/Applications/Codex.app/Contents/Resources/codex",
            args=["app-server", "--listen", "stdio://"],
            model="gpt-5.4",
            reasoning_effort="medium",
            reasoning_summary="concise",
            startup_timeout_seconds=20.0,
            turn_timeout_seconds=300.0,
        )
    )


def test_codex_verification_artifact_carries_structured_results() -> None:
    result = _adapter().execute(_bundle())
    verification_artifacts = [
        artifact
        for artifact in result.artifacts
        if artifact.path == "artifacts/codex/verification.json"
    ]
    assert len(verification_artifacts) == 1
    metadata = verification_artifacts[0].metadata
    verification = metadata["verification"]
    assert metadata["verification_source"] == "command_execution"
    assert verification["passed"] is True
    assert verification["results"][0]["command"] == "pytest -q"


def test_codex_transcript_artifact_includes_turn_metadata() -> None:
    result = _adapter().execute(_bundle())
    transcript_artifacts = [
        artifact for artifact in result.artifacts if artifact.artifact_type == ArtifactType.LOG
    ]
    assert len(transcript_artifacts) == 1
    metadata = transcript_artifacts[0].metadata
    assert metadata["thread_id"] == "simulated-thread"
    assert metadata["turn_id"] == "simulated-turn"
    assert any(
        item.get("command") == "pytest -q"
        for item in metadata["completed_items"]
    )
