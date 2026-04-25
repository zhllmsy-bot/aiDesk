from __future__ import annotations

from datetime import timedelta

from api.executors.contracts import (
    ArtifactDescriptor,
    ArtifactType,
    DispatchControl,
    ExecutionProvenance,
    ExecutorInputBundle,
    PermissionPolicy,
    SecretSource,
    SecretUsage,
    TaskInfo,
    WorkspaceInfo,
    WorkspaceMode,
    utcnow,
)
from api.security.models import AuditEventTypeDB
from api.security.service import (
    ApprovalClass,
    AuditLogService,
    CommandFamily,
    SecretBroker,
    SecurityPolicyService,
    classify_command,
    compute_provenance_hash,
    validate_provenance_integrity,
)


def _bundle(
    *,
    workspace_mode: WorkspaceMode = WorkspaceMode.WORKTREE,
    root_path: str = "/repo/project",
    writable_paths: list[str] | None = None,
    proposed_commands: list[str] | None = None,
    secret_usages: list[SecretUsage] | None = None,
    workspace_allowlist: list[str] | None = None,
    command_allowlist: list[str] | None = None,
    command_denylist: list[str] | None = None,
    secret_broker_enabled: bool = False,
    require_manual_approval_for_write: bool = True,
) -> ExecutorInputBundle:
    wp = writable_paths
    if wp is None:
        wp = ["/repo/project/apps"] if workspace_mode != WorkspaceMode.READ_ONLY else []
    return ExecutorInputBundle(
        task=TaskInfo(
            task_id="task-1",
            run_id="run-1",
            title="Test task",
            description="desc",
            executor="codex",
        ),
        workspace=WorkspaceInfo(
            project_id="project-1",
            iteration_id="iter-1",
            workspace_ref="ws-1",
            root_path=root_path,
            mode=workspace_mode,
            writable_paths=wp,
        ),
        context_blocks=[],
        permission_policy=PermissionPolicy(
            workspace_allowlist=workspace_allowlist or ["/repo"],
            allowed_write_paths=wp,
            command_allowlist=command_allowlist or ["pytest", "python"],
            command_denylist=command_denylist or ["rm -rf", "curl "],
            require_manual_approval_for_write=require_manual_approval_for_write,
            secret_broker_enabled=secret_broker_enabled,
            workspace_mode=workspace_mode,
        ),
        verify_commands=[],
        proposed_commands=proposed_commands or ["pytest -q"],
        secret_usages=secret_usages or [],
        evidence_refs=[],
        dispatch=DispatchControl(idempotency_key="dispatch-test"),
    )


def test_secret_broker_in_memory_basic() -> None:
    broker = SecretBroker()
    broker.enable()
    broker.register("API_KEY", "secret-123")
    usage = SecretUsage(name="API_KEY", source=SecretSource.BROKER, scope="executor")
    assert broker.resolve(usage) == "secret-123"


def test_secret_broker_in_memory_with_audit() -> None:
    audit = AuditLogService()
    broker = SecretBroker(audit=audit)
    broker.enable()
    broker.register("DB_PASSWORD", "pass-456")
    usage = SecretUsage(name="DB_PASSWORD", source=SecretSource.BROKER, scope="executor")
    broker.resolve(usage, actor="test_user")
    entries = audit.query(event_type=AuditEventTypeDB.secret_resolve)
    assert len(entries) == 1
    assert entries[0]["actor"] == "test_user"
    assert entries[0]["resource_id"] == "DB_PASSWORD"


def test_secret_broker_expired_secret_rejected() -> None:
    audit = AuditLogService()
    broker = SecretBroker(audit=audit)
    broker.enable()
    expired_at = utcnow() - timedelta(seconds=1)
    broker.register("EXPIRED_KEY", "old-value", expires_at=expired_at)
    usage = SecretUsage(name="EXPIRED_KEY", source=SecretSource.BROKER, scope="executor")
    try:
        broker.resolve(usage)
        raise AssertionError("Should have raised PermissionError")
    except PermissionError as e:
        assert "expired" in str(e)
    entries = audit.query(event_type=AuditEventTypeDB.secret_resolve)
    assert len(entries) == 1
    detail: dict[str, object] = entries[0]["detail"]  # type: ignore[index]
    assert detail.get("error") == "expired"


def test_workspace_isolation_blocks_cross_project_path() -> None:
    service = SecurityPolicyService()
    bundle = _bundle(
        root_path="/repo/project-a",
        writable_paths=["/repo/project-b/apps"],
    )
    decision = service.evaluate(bundle)
    assert decision.needs_approval is True
    assert "isolation violation" in (decision.reason or "")


def test_workspace_isolation_blocks_path_outside_allowlist() -> None:
    service = SecurityPolicyService()
    bundle = _bundle(
        root_path="/repo/project",
        writable_paths=["/other/project/apps"],
        workspace_allowlist=["/repo"],
    )
    decision = service.evaluate(bundle)
    assert decision.needs_approval is True
    assert "isolation violation" in (decision.reason or "")


def test_workspace_isolation_allows_valid_paths() -> None:
    service = SecurityPolicyService()
    bundle = _bundle(
        workspace_mode=WorkspaceMode.READ_ONLY,
        writable_paths=[],
        require_manual_approval_for_write=False,
    )
    decision = service.evaluate(bundle)
    assert decision.needs_approval is False


def test_classify_command_families() -> None:
    assert classify_command("pytest -q").family == CommandFamily.TEST
    assert classify_command("python main.py").family == CommandFamily.BUILD
    assert classify_command("curl http://example.com").family == CommandFamily.NETWORK
    assert classify_command("rm -rf /tmp").family == CommandFamily.SYSTEM
    assert classify_command("docker build .").family == CommandFamily.DEPLOY
    assert classify_command("ruff check .").family == CommandFamily.LINT
    assert classify_command("unknown_cmd").family == CommandFamily.UNKNOWN


def test_classify_command_approval_classes() -> None:
    assert classify_command("pytest -q").approval_class == ApprovalClass.AUTO
    assert classify_command("curl http://x").approval_class == ApprovalClass.ESCALATED
    assert classify_command("rm file").approval_class == ApprovalClass.ESCALATED
    assert classify_command("unknown_cmd").approval_class == ApprovalClass.MANUAL


def test_blocked_command_audited() -> None:
    service = SecurityPolicyService()
    bundle = _bundle(
        workspace_mode=WorkspaceMode.READ_ONLY,
        writable_paths=[],
        proposed_commands=["rm -rf /"],
        require_manual_approval_for_write=False,
    )
    decision = service.evaluate(bundle)
    assert decision.needs_approval is True
    assert "blocked commands" in (decision.reason or "")
    entries = service.audit.query(event_type=AuditEventTypeDB.blocked_command)
    assert len(entries) == 1
    assert entries[0]["resource_id"] == "rm -rf /"
    detail: dict[str, object] = entries[0]["detail"]  # type: ignore[index]
    assert str(detail.get("family", "")) == CommandFamily.SYSTEM


def test_approval_gate_hit_audited() -> None:
    service = SecurityPolicyService()
    bundle = _bundle(
        workspace_mode=WorkspaceMode.WORKTREE,
        writable_paths=["/repo/project/apps"],
        require_manual_approval_for_write=True,
    )
    decision = service.evaluate(bundle)
    assert decision.needs_approval is True
    entries = service.audit.query(event_type=AuditEventTypeDB.approval_gate_hit)
    assert len(entries) == 1
    assert entries[0]["resource_kind"] == "write_execution"


def test_write_execution_grant_audited() -> None:
    service = SecurityPolicyService()
    bundle = _bundle(
        workspace_mode=WorkspaceMode.WORKTREE,
        writable_paths=["/repo/project/apps"],
        require_manual_approval_for_write=False,
    )
    decision = service.evaluate(bundle)
    assert decision.needs_approval is False
    entries = service.audit.query(event_type=AuditEventTypeDB.write_execution_grant)
    assert len(entries) == 1
    assert entries[0]["resource_kind"] == "write_execution"


def test_security_gate_no_longer_supports_global_full_access_bypass() -> None:
    service = SecurityPolicyService()
    bundle = _bundle(
        root_path="/outside",
        writable_paths=["/outside/apps"],
        workspace_allowlist=["/repo"],
        proposed_commands=["rm -rf /"],
        require_manual_approval_for_write=True,
    )
    decision = service.evaluate(bundle)
    assert decision.needs_approval is True
    assert "workspace root is outside allowlist" in (decision.reason or "")


def test_workspace_isolation_violation_audited() -> None:
    service = SecurityPolicyService()
    bundle = _bundle(
        root_path="/repo/project-a",
        writable_paths=["/repo/project-b/apps"],
    )
    service.evaluate(bundle)
    entries = service.audit.query(event_type=AuditEventTypeDB.workspace_isolation_violation)
    assert len(entries) == 1
    assert entries[0]["resource_kind"] == "workspace"


def test_compute_provenance_hash_deterministic() -> None:
    provenance = ExecutionProvenance(
        executor="codex",
        provider_request_id="req-1",
        attempt_id="attempt-1",
        workspace_ref="ws-1",
        trigger="manual",
    )
    artifacts = [
        ArtifactDescriptor(
            artifact_type=ArtifactType.PATCH,
            path="a.diff",
            content_hash="sha256:aaa",
            producer="codex",
            workspace_ref="ws-1",
            provenance=provenance,
        ),
    ]
    hash1 = compute_provenance_hash(artifacts, provenance)
    hash2 = compute_provenance_hash(artifacts, provenance)
    assert hash1 == hash2
    assert len(hash1) == 64


def test_validate_provenance_integrity_catches_missing_fields() -> None:
    provenance = ExecutionProvenance(
        executor="",
        provider_request_id="req-1",
        attempt_id="",
        workspace_ref="",
        trigger="manual",
    )
    artifacts = [
        ArtifactDescriptor(
            artifact_type=ArtifactType.PATCH,
            path="a.diff",
            content_hash="",
            producer="",
            workspace_ref="ws-1",
            provenance=provenance,
        ),
    ]
    errors = validate_provenance_integrity(artifacts, provenance)
    assert any("missing executor" in e for e in errors)
    assert any("missing attempt_id" in e for e in errors)
    assert any("missing workspace_ref" in e for e in errors)
    assert any("missing content_hash" in e for e in errors)
    assert any("missing producer" in e for e in errors)


def test_validate_provenance_integrity_catches_executor_mismatch() -> None:
    provenance = ExecutionProvenance(
        executor="codex",
        provider_request_id="req-1",
        attempt_id="attempt-1",
        workspace_ref="ws-1",
        trigger="manual",
    )
    other_provenance = ExecutionProvenance(
        executor="openhands",
        provider_request_id="req-2",
        attempt_id="attempt-1",
        workspace_ref="ws-1",
        trigger="manual",
    )
    artifacts = [
        ArtifactDescriptor(
            artifact_type=ArtifactType.PATCH,
            path="a.diff",
            content_hash="sha256:aaa",
            producer="codex",
            workspace_ref="ws-1",
            provenance=other_provenance,
        ),
    ]
    errors = validate_provenance_integrity(artifacts, provenance)
    assert any("executor mismatch" in e for e in errors)


def test_validate_provenance_integrity_passes_for_valid() -> None:
    provenance = ExecutionProvenance(
        executor="codex",
        provider_request_id="req-1",
        attempt_id="attempt-1",
        workspace_ref="ws-1",
        trigger="manual",
    )
    artifacts = [
        ArtifactDescriptor(
            artifact_type=ArtifactType.PATCH,
            path="a.diff",
            content_hash="sha256:aaa",
            producer="codex",
            workspace_ref="ws-1",
            provenance=provenance,
        ),
    ]
    errors = validate_provenance_integrity(artifacts, provenance)
    assert len(errors) == 0


def test_audit_log_query_filters() -> None:
    audit = AuditLogService()
    audit.record(
        event_type=AuditEventTypeDB.blocked_command,
        project_id="project-1",
        actor="system",
        resource_kind="command",
        resource_id="rm -rf /",
    )
    audit.record(
        event_type=AuditEventTypeDB.secret_resolve,
        project_id="project-2",
        actor="user-1",
        resource_kind="secret",
        resource_id="API_KEY",
    )
    assert len(audit.query(event_type=AuditEventTypeDB.blocked_command)) == 1
    assert len(audit.query(project_id="project-1")) == 1
    assert len(audit.query(actor="user-1")) == 1
    assert len(audit.query()) == 2


def test_secret_broker_disabled_raises() -> None:
    broker = SecretBroker()
    usage = SecretUsage(name="KEY", source=SecretSource.BROKER, scope="executor")
    try:
        broker.resolve(usage)
        raise AssertionError("Should have raised PermissionError")
    except PermissionError:
        pass


def test_secret_broker_unknown_key_raises() -> None:
    broker = SecretBroker()
    broker.enable()
    usage = SecretUsage(name="NONEXISTENT", source=SecretSource.BROKER, scope="executor")
    try:
        broker.resolve(usage)
        raise AssertionError("Should have raised KeyError")
    except KeyError:
        pass
