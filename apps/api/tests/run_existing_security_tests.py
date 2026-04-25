from api.executors.contracts import (
    ArtifactType,
    DispatchControl,
    EvidenceKind,
    EvidenceRef,
    ExecutorInputBundle,
    PermissionPolicy,
    SecretSource,
    SecretUsage,
    TaskInfo,
    VerifyCommand,
    WorkspaceInfo,
    WorkspaceMode,
)
from api.security.service import SecurityPolicyService


def sample_bundle(
    *, executor="codex", workspace_mode=WorkspaceMode.WORKTREE, metadata=None, secret_enabled=False
):
    return ExecutorInputBundle(
        task=TaskInfo(
            task_id="task-1",
            run_id="run-1",
            title="Implement feature",
            description="Make a change",
            executor=executor,
            expected_artifact_types=[ArtifactType.PATCH],
            metadata=metadata or {},
        ),
        workspace=WorkspaceInfo(
            project_id="project-1",
            iteration_id="iter-1",
            workspace_ref="ws-1",
            root_path="/repo/project",
            mode=workspace_mode,
            writable_paths=["/repo/project/apps/api"]
            if workspace_mode != WorkspaceMode.READ_ONLY
            else [],
        ),
        context_blocks=[],
        permission_policy=PermissionPolicy(
            workspace_allowlist=["/repo"],
            allowed_write_paths=["/repo/project/apps/api"],
            command_allowlist=["pytest", "python"],
            command_denylist=["rm -rf", "curl "],
            require_manual_approval_for_write=True,
            secret_broker_enabled=secret_enabled,
            workspace_mode=workspace_mode,
        ),
        verify_commands=[VerifyCommand(id="verify-1", command="pytest -q")],
        proposed_commands=["pytest -q"],
        secret_usages=[],
        evidence_refs=[
            EvidenceRef(kind=EvidenceKind.ARTIFACT, ref="artifact-seed", summary="seed")
        ],
        dispatch=DispatchControl(idempotency_key="dispatch-1", attempt_id="attempt-1"),
    )


service = SecurityPolicyService()
decision = service.evaluate(sample_bundle())
assert decision.needs_approval is True
assert "write execution" in (decision.reason or "")
print("test_security_policy_requires_write_approval: PASS")

service2 = SecurityPolicyService()
bundle = sample_bundle(workspace_mode=WorkspaceMode.READ_ONLY).model_copy(
    update={
        "permission_policy": PermissionPolicy(
            workspace_allowlist=["/repo"],
            command_allowlist=["pytest", "python"],
            command_denylist=["rm -rf"],
            require_manual_approval_for_write=False,
            secret_broker_enabled=False,
            workspace_mode=WorkspaceMode.READ_ONLY,
        ),
        "secret_usages": [
            SecretUsage(name="API_KEY", source=SecretSource.BROKER, scope="executor")
        ],
    }
)
decision2 = service2.evaluate(bundle)
assert decision2.needs_approval is True
assert "secret broker is disabled" in (decision2.reason or "")
print("test_security_policy_blocks_secret_when_broker_disabled: PASS")

print("EXISTING SECURITY TESTS: PASS")
