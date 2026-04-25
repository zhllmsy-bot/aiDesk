from __future__ import annotations

from api.config import Settings
from api.executors.contracts import (
    ArtifactType,
    DispatchControl,
    EvidenceKind,
    EvidenceRef,
    ExecutionStatus,
    ExecutorInputBundle,
    PermissionPolicy,
    TaskInfo,
    VerifyCommand,
    WorkspaceInfo,
    WorkspaceMode,
)
from api.executors.providers.claude_agent import ClaudeAgentExecutorAdapter
from api.integrations.llm.base import CapabilityFlag
from api.integrations.llm.factory import create_llm_provider


def _bundle() -> ExecutorInputBundle:
    return ExecutorInputBundle(
        task=TaskInfo(
            task_id="task-agent",
            run_id="run-agent",
            title="Use agent harness",
            description="Exercise the SDK executor boundary.",
            executor="claude_agent",
            expected_artifact_types=[ArtifactType.REPORT],
            metadata={"simulate_success": True},
        ),
        workspace=WorkspaceInfo(
            project_id="project-agent",
            workspace_ref="ws-agent",
            root_path="/repo/project",
            mode=WorkspaceMode.WORKTREE,
            writable_paths=["/repo/project"],
        ),
        context_blocks=[],
        permission_policy=PermissionPolicy(
            workspace_allowlist=["/repo"],
            allowed_write_paths=["/repo/project"],
            command_allowlist=["pytest"],
            command_denylist=["rm -rf"],
            require_manual_approval_for_write=False,
            workspace_mode=WorkspaceMode.WORKTREE,
        ),
        verify_commands=[VerifyCommand(id="verify-agent", command="pytest -q")],
        proposed_commands=["pytest -q"],
        evidence_refs=[
            EvidenceRef(kind=EvidenceKind.VERIFICATION, ref="smoke", summary="seed")
        ],
        dispatch=DispatchControl(idempotency_key="dispatch-agent", attempt_id="attempt-agent"),
    )


def test_litellm_factory_exposes_single_llm_boundary() -> None:
    provider = create_llm_provider(Settings(llm_default_model="openai/gpt-5.4"))

    assert provider.capabilities.provider == "litellm"
    assert provider.capabilities.models == ["openai/gpt-5.4"]
    assert CapabilityFlag.TOOL_CALLING in provider.capabilities.flags


def test_agent_harness_executor_uses_standard_execution_contract() -> None:
    adapter = ClaudeAgentExecutorAdapter(model="claude-sonnet-4-5")
    result = adapter.execute(_bundle())

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.provenance.executor == "claude_agent"
    assert result.verification is not None
    assert result.verification.passed is True
