import sys

sys.path.insert(0, ".")
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

broker = SecretBroker()
broker.enable()
broker.register("API_KEY", "secret-123")
usage = SecretUsage(name="API_KEY", source=SecretSource.BROKER, scope="executor")
assert broker.resolve(usage) == "secret-123"
print("1. Secret broker basic: PASS")

audit = AuditLogService()
broker2 = SecretBroker(audit=audit)
broker2.enable()
broker2.register("DB_PASSWORD", "pass-456")
usage2 = SecretUsage(name="DB_PASSWORD", source=SecretSource.BROKER, scope="executor")
broker2.resolve(usage2, actor="test_user")
entries = audit.query(event_type=AuditEventTypeDB.secret_resolve)
assert len(entries) == 1
print("2. Secret broker with audit: PASS")

audit3 = AuditLogService()
broker3 = SecretBroker(audit=audit3)
broker3.enable()
expired_at = utcnow() - timedelta(seconds=1)
broker3.register("EXPIRED_KEY", "old-value", expires_at=expired_at)
usage3 = SecretUsage(name="EXPIRED_KEY", source=SecretSource.BROKER, scope="executor")
try:
    broker3.resolve(usage3)
    raise AssertionError("Expected PermissionError for expired secret")
except PermissionError as e:
    assert "expired" in str(e)
print("3. Expired secret rejected: PASS")

service = SecurityPolicyService()
bundle = ExecutorInputBundle(
    task=TaskInfo(
        task_id="task-1", run_id="run-1", title="Test", description="d", executor="codex"
    ),
    workspace=WorkspaceInfo(
        project_id="p1",
        iteration_id="i1",
        workspace_ref="ws",
        root_path="/repo/a",
        mode=WorkspaceMode.WORKTREE,
        writable_paths=["/repo/b/apps"],
    ),
    context_blocks=[],
    permission_policy=PermissionPolicy(
        workspace_allowlist=["/repo"],
        command_allowlist=["pytest"],
        command_denylist=["rm"],
        require_manual_approval_for_write=False,
        secret_broker_enabled=False,
        workspace_mode=WorkspaceMode.WORKTREE,
    ),
    verify_commands=[],
    proposed_commands=["pytest"],
    secret_usages=[],
    evidence_refs=[],
    dispatch=DispatchControl(idempotency_key="d1"),
)
decision = service.evaluate(bundle)
assert decision.needs_approval is True
assert "isolation violation" in (decision.reason or "")
print("4. Workspace isolation: PASS")

assert classify_command("pytest -q").family == CommandFamily.TEST
assert classify_command("curl http://x").approval_class == ApprovalClass.ESCALATED
print("5. Command classification: PASS")

provenance = ExecutionProvenance(
    executor="codex",
    provider_request_id="r1",
    attempt_id="a1",
    workspace_ref="ws",
    trigger="manual",
)
artifacts = [
    ArtifactDescriptor(
        artifact_type=ArtifactType.PATCH,
        path="a.diff",
        content_hash="sha256:aaa",
        producer="codex",
        workspace_ref="ws",
        provenance=provenance,
    )
]
h = compute_provenance_hash(artifacts, provenance)
assert len(h) == 64
errors = validate_provenance_integrity(artifacts, provenance)
assert len(errors) == 0
print("6. Provenance integrity: PASS")

audit7 = AuditLogService()
audit7.record(
    event_type=AuditEventTypeDB.blocked_command,
    project_id="p1",
    actor="system",
    resource_kind="command",
    resource_id="rm -rf /",
)
audit7.record(
    event_type=AuditEventTypeDB.secret_resolve,
    project_id="p2",
    actor="user-1",
    resource_kind="secret",
    resource_id="API_KEY",
)
assert len(audit7.query(event_type=AuditEventTypeDB.blocked_command)) == 1
assert len(audit7.query()) == 2
print("7. Audit log: PASS")

print()
print("ALL 7 CORE SECURITY TESTS PASSED")
