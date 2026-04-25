from __future__ import annotations

from api.domain.context.skills import ContextSkill, ContextSkillLedger, skill_context_block
from api.domain.security.hooks import (
    ToolHook,
    ToolHookContext,
    ToolHookDecision,
    ToolHookPhase,
    ToolHookPipeline,
)
from api.executors.contracts import (
    DispatchControl,
    EvidenceKind,
    EvidenceRef,
    ExecutorInputBundle,
    PermissionPolicy,
    TaskInfo,
    WorkspaceInfo,
    WorkspaceMode,
)
from api.security.service import SecurityPolicyService


def _bundle() -> ExecutorInputBundle:
    return ExecutorInputBundle(
        task=TaskInfo(
            task_id="task-hook",
            run_id="run-hook",
            title="Run guarded tool",
            description="Validate hook rejection.",
            executor="codex",
        ),
        workspace=WorkspaceInfo(
            project_id="project-hook",
            workspace_ref="ws-hook",
            root_path="/repo/project",
            mode=WorkspaceMode.WORKTREE,
            writable_paths=["/repo/project"],
        ),
        context_blocks=[],
        permission_policy=PermissionPolicy(
            workspace_allowlist=["/repo"],
            allowed_write_paths=["/repo/project"],
            command_allowlist=["pytest"],
            command_denylist=[],
            require_manual_approval_for_write=False,
            workspace_mode=WorkspaceMode.WORKTREE,
        ),
        proposed_commands=["pytest -q"],
        dispatch=DispatchControl(idempotency_key="dispatch-hook", attempt_id="attempt-hook"),
    )


def test_context_skill_injection_writes_auditable_ledger_entry() -> None:
    ledger = ContextSkillLedger()
    evidence = EvidenceRef(kind=EvidenceKind.PROVENANCE, ref="skill-source")
    skill = ContextSkill(
        skill_id="repo-map",
        title="Repository map",
        body="Use the current package boundaries when assembling context.",
        evidence_refs=[evidence],
    )

    entry = ledger.record(task_id="task-1", skill=skill)
    block = skill_context_block(skill, entry)

    assert ledger.entries() == [entry]
    assert entry.skill_id == "repo-map"
    assert block.source.endswith(entry.ledger_id)
    assert block.evidence_refs == [evidence]


def test_tool_hook_pipeline_rejects_failed_hook() -> None:
    pipeline = ToolHookPipeline()
    pipeline.register(
        ToolHook(hook_id="before-command", phase=ToolHookPhase.BEFORE_TOOL, idempotent=True),
        lambda _context: (_ for _ in ()).throw(RuntimeError("policy unavailable")),
    )

    decision = pipeline.run(
        ToolHookContext(
            phase=ToolHookPhase.BEFORE_TOOL,
            tool_name="command",
            run_id="run-hook",
            task_id="task-hook",
        )
    )

    assert decision.allowed is False
    assert "policy unavailable" in str(decision.reason)


def test_security_gate_denies_when_tool_hook_rejects() -> None:
    pipeline = ToolHookPipeline()
    pipeline.register(
        ToolHook(
            hook_id="deny-command",
            phase=ToolHookPhase.BEFORE_TOOL,
            idempotent=True,
            tool_allowlist=["command"],
        ),
        lambda context: ToolHookDecision(
            allowed=False,
            hook_id="deny-command",
            reason=f"blocked {context.tool_name}",
        ),
    )

    decision = SecurityPolicyService(hook_pipeline=pipeline).evaluate(_bundle())

    assert decision.needs_approval is True
    assert decision.required_scope == ["deny-command"]
