from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from api.config import Settings
from api.domain.security.hooks import ToolHookContext, ToolHookPhase, ToolHookPipeline
from api.executors.contracts import (
    ArtifactDescriptor,
    ExecutionProvenance,
    ExecutorInputBundle,
    SecretUsage,
    WorkspaceMode,
    utcnow,
)
from api.security.models import (
    AuditEventTypeDB,
    AuditLogEntry,
    SecretRecord,
    SecretScopeDB,
)
from api.security.opa import OpaPolicyEngine


@dataclass(slots=True)
class SecurityGateDecision:
    needs_approval: bool
    reason: str | None
    required_scope: list[str]


class CommandFamily(StrEnum):
    BUILD = "build"
    TEST = "test"
    LINT = "lint"
    DEPLOY = "deploy"
    NETWORK = "network"
    FILE_WRITE = "file_write"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ApprovalClass(StrEnum):
    NONE = "none"
    AUTO = "auto"
    MANUAL = "manual"
    ESCALATED = "escalated"


@dataclass(slots=True)
class CommandPolicyEntry:
    family: CommandFamily
    network_required: bool
    write_required: bool
    approval_class: ApprovalClass


COMMAND_FAMILY_RULES: dict[str, CommandFamily] = {
    "pytest": CommandFamily.TEST,
    "python": CommandFamily.BUILD,
    "pip": CommandFamily.BUILD,
    "npm": CommandFamily.BUILD,
    "cargo": CommandFamily.BUILD,
    "make": CommandFamily.BUILD,
    "curl": CommandFamily.NETWORK,
    "wget": CommandFamily.NETWORK,
    "ssh": CommandFamily.NETWORK,
    "scp": CommandFamily.NETWORK,
    "rm": CommandFamily.SYSTEM,
    "chmod": CommandFamily.SYSTEM,
    "chown": CommandFamily.SYSTEM,
    "sudo": CommandFamily.SYSTEM,
    "docker": CommandFamily.DEPLOY,
    "kubectl": CommandFamily.DEPLOY,
    "git push": CommandFamily.DEPLOY,
    "git commit": CommandFamily.FILE_WRITE,
    "cp": CommandFamily.FILE_WRITE,
    "mv": CommandFamily.FILE_WRITE,
    "mkdir": CommandFamily.FILE_WRITE,
    "ruff": CommandFamily.LINT,
    "flake8": CommandFamily.LINT,
    "eslint": CommandFamily.LINT,
    "mypy": CommandFamily.LINT,
    "pyright": CommandFamily.LINT,
}

NETWORK_FAMILIES = {CommandFamily.NETWORK, CommandFamily.DEPLOY}
WRITE_FAMILIES = {CommandFamily.FILE_WRITE, CommandFamily.SYSTEM, CommandFamily.DEPLOY}

APPROVAL_CLASS_MAP: dict[CommandFamily, ApprovalClass] = {
    CommandFamily.TEST: ApprovalClass.AUTO,
    CommandFamily.LINT: ApprovalClass.AUTO,
    CommandFamily.BUILD: ApprovalClass.AUTO,
    CommandFamily.UNKNOWN: ApprovalClass.MANUAL,
    CommandFamily.FILE_WRITE: ApprovalClass.MANUAL,
    CommandFamily.NETWORK: ApprovalClass.ESCALATED,
    CommandFamily.SYSTEM: ApprovalClass.ESCALATED,
    CommandFamily.DEPLOY: ApprovalClass.ESCALATED,
}


def classify_command(command: str) -> CommandPolicyEntry:
    family = CommandFamily.UNKNOWN
    stripped = command.strip()
    for prefix, fam in COMMAND_FAMILY_RULES.items():
        if stripped.startswith(prefix):
            family = fam
            break
    return CommandPolicyEntry(
        family=family,
        network_required=family in NETWORK_FAMILIES,
        write_required=family in WRITE_FAMILIES,
        approval_class=APPROVAL_CLASS_MAP.get(family, ApprovalClass.MANUAL),
    )


class AuditLogService:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory
        self._entries: list[dict[str, object]] = []

    def record(
        self,
        *,
        event_type: AuditEventTypeDB,
        project_id: str | None = None,
        actor: str,
        resource_kind: str | None = None,
        resource_id: str | None = None,
        detail: dict[str, object] | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        if self._session_factory is None:
            self._entries.append(
                {
                    "event_type": event_type,
                    "project_id": project_id,
                    "actor": actor,
                    "resource_kind": resource_kind,
                    "resource_id": resource_id,
                    "detail": detail or {},
                    "occurred_at": (occurred_at or utcnow()).isoformat(),
                }
            )
            return
        with self._session_factory() as session:
            row = AuditLogEntry(
                event_type=event_type,
                project_id=project_id,
                actor=actor,
                resource_kind=resource_kind,
                resource_id=resource_id,
                detail_json=detail or {},
                occurred_at=occurred_at or utcnow(),
            )
            session.add(row)
            session.commit()

    def query(
        self,
        *,
        event_type: AuditEventTypeDB | None = None,
        project_id: str | None = None,
        actor: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        if self._session_factory is None:
            results = list(self._entries)
            if event_type:
                results = [e for e in results if e["event_type"] == event_type]
            if project_id:
                results = [e for e in results if e.get("project_id") == project_id]
            if actor:
                results = [e for e in results if e.get("actor") == actor]
            return results[-limit:]
        with self._session_factory() as session:
            stmt = select(AuditLogEntry).order_by(AuditLogEntry.occurred_at.desc()).limit(limit)
            if event_type:
                stmt = stmt.where(AuditLogEntry.event_type == event_type)
            if project_id:
                stmt = stmt.where(AuditLogEntry.project_id == project_id)
            if actor:
                stmt = stmt.where(AuditLogEntry.actor == actor)
            rows = session.scalars(stmt).all()
            return [
                {
                    "event_type": row.event_type,
                    "project_id": row.project_id,
                    "actor": row.actor,
                    "resource_kind": row.resource_kind,
                    "resource_id": row.resource_id,
                    "detail": dict(row.detail_json),
                    "occurred_at": row.occurred_at.isoformat(),
                }
                for row in rows
            ]


class _SecretMeta:
    __slots__ = ("project_id", "scope", "expires_at", "created_by")

    def __init__(
        self,
        project_id: str | None,
        scope: SecretScopeDB,
        expires_at: datetime | None,
        created_by: str,
    ) -> None:
        self.project_id = project_id
        self.scope = scope
        self.expires_at = expires_at
        self.created_by = created_by


class SecretBroker:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        audit: AuditLogService | None = None,
    ) -> None:
        self._enabled = False
        self._secrets: dict[str, str] = {}
        self._secret_meta: dict[str, _SecretMeta] = {}
        self._session_factory = session_factory
        self._audit = audit

    def enable(self) -> None:
        self._enabled = True

    def register(
        self,
        name: str,
        value: str,
        *,
        project_id: str | None = None,
        scope: SecretScopeDB = SecretScopeDB.project,
        created_by: str = "system",
        expires_at: datetime | None = None,
    ) -> None:
        if self._session_factory is None:
            self._secrets[name] = value
            self._secret_meta[name] = _SecretMeta(
                project_id=project_id,
                scope=scope,
                expires_at=expires_at,
                created_by=created_by,
            )
            return
        with self._session_factory() as session:
            row = SecretRecord(
                project_id=project_id,
                name=name,
                scope=scope,
                encrypted_value=value,
                expires_at=expires_at,
                created_by=created_by,
            )
            session.add(row)
            session.commit()

    def resolve(self, usage: SecretUsage, *, actor: str = "system") -> str:
        if not self._enabled:
            raise PermissionError("secret broker is disabled")
        if self._session_factory is None:
            return self._resolve_in_memory(usage, actor)
        return self._resolve_db(usage, actor)

    def _resolve_in_memory(self, usage: SecretUsage, actor: str) -> str:
        try:
            value = self._secrets[usage.name]
        except KeyError as exc:
            if self._audit:
                self._audit.record(
                    event_type=AuditEventTypeDB.secret_resolve,
                    project_id=None,
                    actor=actor,
                    resource_kind="secret",
                    resource_id=usage.name,
                    detail={"error": "not_found"},
                )
            raise KeyError(f"unknown secret: {usage.name}") from exc
        meta = self._secret_meta.get(usage.name)
        if meta and meta.expires_at and meta.expires_at < utcnow():
            if self._audit:
                self._audit.record(
                    event_type=AuditEventTypeDB.secret_resolve,
                    project_id=meta.project_id,
                    actor=actor,
                    resource_kind="secret",
                    resource_id=usage.name,
                    detail={"error": "expired", "expires_at": meta.expires_at.isoformat()},
                )
            raise PermissionError(f"secret {usage.name} has expired")
        if self._audit:
            self._audit.record(
                event_type=AuditEventTypeDB.secret_resolve,
                project_id=meta.project_id if meta else None,
                actor=actor,
                resource_kind="secret",
                resource_id=usage.name,
                detail={"scope": usage.scope, "source": usage.source},
            )
        return value

    def _resolve_db(self, usage: SecretUsage, actor: str) -> str:
        assert self._session_factory is not None
        with self._session_factory() as session:
            stmt = select(SecretRecord).where(SecretRecord.name == usage.name)
            if usage.scope and usage.scope != "executor":
                stmt = stmt.where(SecretRecord.scope == SecretScopeDB(usage.scope))
            row = session.scalars(stmt).first()
            if row is None:
                if self._audit:
                    self._audit.record(
                        event_type=AuditEventTypeDB.secret_resolve,
                        project_id=None,
                        actor=actor,
                        resource_kind="secret",
                        resource_id=usage.name,
                        detail={"error": "not_found"},
                    )
                raise KeyError(f"unknown secret: {usage.name}")
            if row.expires_at and row.expires_at < utcnow():
                if self._audit:
                    self._audit.record(
                        event_type=AuditEventTypeDB.secret_resolve,
                        project_id=row.project_id,
                        actor=actor,
                        resource_kind="secret",
                        resource_id=usage.name,
                        detail={"error": "expired", "expires_at": row.expires_at.isoformat()},
                    )
                raise PermissionError(f"secret {usage.name} has expired")
            if self._audit:
                self._audit.record(
                    event_type=AuditEventTypeDB.secret_resolve,
                    project_id=row.project_id,
                    actor=actor,
                    resource_kind="secret",
                    resource_id=usage.name,
                    detail={"scope": usage.scope, "source": usage.source},
                )
            return row.encrypted_value

    def list_secrets(
        self,
        *,
        project_id: str | None = None,
    ) -> list[dict[str, str | None]]:
        if self._session_factory is None:
            results: list[dict[str, str | None]] = [
                {"name": k, "scope": "in_memory"} for k in self._secrets
            ]
            if project_id:
                results = []
            return results
        with self._session_factory() as session:
            stmt = select(SecretRecord)
            if project_id:
                stmt = stmt.where(SecretRecord.project_id == project_id)
            rows = session.scalars(stmt).all()
            return [
                {
                    "id": row.id,
                    "name": row.name,
                    "project_id": row.project_id,
                    "scope": row.scope,
                    "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                    "created_by": row.created_by,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]


def _is_path_under_root(path: str, root: str) -> bool:
    normalized_path = path.rstrip("/")
    normalized_root = root.rstrip("/")
    return normalized_path == normalized_root or normalized_path.startswith(normalized_root + "/")


def _check_workspace_isolation(bundle: ExecutorInputBundle) -> str | None:
    root_path = bundle.workspace.root_path
    for wp in bundle.workspace.writable_paths:
        if not _is_path_under_root(wp, root_path):
            return f"writable path {wp} is outside workspace root {root_path}"
    for wp in bundle.workspace.writable_paths:
        for allowed in bundle.permission_policy.workspace_allowlist:
            if _is_path_under_root(wp, allowed):
                break
        else:
            if bundle.permission_policy.workspace_allowlist:
                return f"writable path {wp} is outside workspace allowlist"
    return None


def compute_provenance_hash(
    artifacts: list[ArtifactDescriptor],
    provenance: ExecutionProvenance,
) -> str:
    manifest = {
        "executor": provenance.executor,
        "provider_request_id": provenance.provider_request_id,
        "attempt_id": provenance.attempt_id,
        "workspace_ref": provenance.workspace_ref,
        "trigger": provenance.trigger,
        "artifacts": sorted(
            [
                {
                    "path": a.path,
                    "content_hash": a.content_hash,
                    "producer": a.producer,
                }
                for a in artifacts
            ],
            key=lambda x: x["path"],
        ),
    }
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def validate_provenance_integrity(
    artifacts: list[ArtifactDescriptor],
    provenance: ExecutionProvenance,
) -> list[str]:
    errors: list[str] = []
    if not provenance.executor:
        errors.append("provenance missing executor")
    if not provenance.attempt_id:
        errors.append("provenance missing attempt_id")
    if not provenance.workspace_ref:
        errors.append("provenance missing workspace_ref")
    for artifact in artifacts:
        if not artifact.content_hash:
            errors.append(f"artifact {artifact.path} missing content_hash")
        if not artifact.producer:
            errors.append(f"artifact {artifact.path} missing producer")
        if artifact.provenance.executor != provenance.executor:
            errors.append(
                f"artifact {artifact.path} provenance executor mismatch: "
                f"{artifact.provenance.executor} != {provenance.executor}"
            )
    return errors


class SecurityPolicyService:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        audit: AuditLogService | None = None,
        settings: Settings | None = None,
        hook_pipeline: ToolHookPipeline | None = None,
        opa: OpaPolicyEngine | None = None,
    ) -> None:
        self._secret_broker = SecretBroker(session_factory=session_factory, audit=audit)
        self._audit = audit or AuditLogService()
        self._session_factory = session_factory
        self._settings = settings
        self._hook_pipeline = hook_pipeline or ToolHookPipeline()
        self._opa = opa or OpaPolicyEngine(
            policy_dir=settings.opa_policy_dir if settings else "infra/policies",
            enabled=settings.opa_enabled if settings else False,
        )

    @property
    def secret_broker(self) -> SecretBroker:
        return self._secret_broker

    @property
    def audit(self) -> AuditLogService:
        return self._audit

    def evaluate(self, bundle: ExecutorInputBundle) -> SecurityGateDecision:
        hook_decision = self._hook_pipeline.run(
            ToolHookContext(
                phase=ToolHookPhase.BEFORE_TOOL,
                tool_name="command",
                run_id=bundle.task.run_id,
                task_id=bundle.task.task_id,
                attempt_id=bundle.dispatch.attempt_id,
                payload={"commands": list(bundle.proposed_commands)},
            )
        )
        if not hook_decision.allowed:
            return SecurityGateDecision(
                True,
                hook_decision.reason or f"tool hook {hook_decision.hook_id} rejected call",
                [hook_decision.hook_id],
            )

        opa_decision = self._opa.evaluate("execution", _opa_input(bundle))
        if not opa_decision.allowed:
            return SecurityGateDecision(
                True,
                opa_decision.reason,
                opa_decision.required_scope,
            )

        if not any(
            bundle.workspace.root_path.startswith(root)
            for root in bundle.permission_policy.workspace_allowlist
        ):
            self._audit.record(
                event_type=AuditEventTypeDB.workspace_isolation_violation,
                project_id=bundle.workspace.project_id,
                actor="system",
                resource_kind="workspace",
                resource_id=bundle.workspace.root_path,
                detail={"reason": "workspace root outside allowlist"},
            )
            return SecurityGateDecision(
                True,
                "workspace root is outside allowlist",
                [bundle.workspace.root_path],
            )

        isolation_violation = _check_workspace_isolation(bundle)
        if isolation_violation:
            self._audit.record(
                event_type=AuditEventTypeDB.workspace_isolation_violation,
                project_id=bundle.workspace.project_id,
                actor="system",
                resource_kind="workspace",
                resource_id=bundle.workspace.root_path,
                detail={"reason": isolation_violation},
            )
            return SecurityGateDecision(
                True,
                f"workspace isolation violation: {isolation_violation}",
                [bundle.workspace.root_path],
            )

        blocked = [
            command
            for command in bundle.proposed_commands
            if self._is_command_blocked(command, bundle)
        ]
        if blocked:
            for cmd in blocked:
                policy = classify_command(cmd)
                self._audit.record(
                    event_type=AuditEventTypeDB.blocked_command,
                    project_id=bundle.workspace.project_id,
                    actor="system",
                    resource_kind="command",
                    resource_id=cmd,
                    detail={
                        "family": policy.family,
                        "approval_class": policy.approval_class,
                        "network_required": policy.network_required,
                        "write_required": policy.write_required,
                    },
                )
            return SecurityGateDecision(
                True,
                f"blocked commands require approval: {', '.join(blocked)}",
                blocked,
            )

        if bundle.permission_policy.require_manual_approval_for_write and self._is_write_execution(
            bundle
        ):
            self._audit.record(
                event_type=AuditEventTypeDB.approval_gate_hit,
                project_id=bundle.workspace.project_id,
                actor="system",
                resource_kind="write_execution",
                resource_id=bundle.task.task_id,
                detail={"writable_paths": bundle.workspace.writable_paths},
            )
            return SecurityGateDecision(
                True,
                "write execution requires approval",
                bundle.workspace.writable_paths,
            )

        if bundle.secret_usages and not bundle.permission_policy.secret_broker_enabled:
            self._audit.record(
                event_type=AuditEventTypeDB.approval_gate_hit,
                project_id=bundle.workspace.project_id,
                actor="system",
                resource_kind="secret_access",
                resource_id=",".join(u.name for u in bundle.secret_usages),
                detail={"reason": "secret broker disabled"},
            )
            return SecurityGateDecision(
                True,
                "secret broker is disabled",
                [usage.name for usage in bundle.secret_usages],
            )

        if self._is_write_execution(bundle):
            self._audit.record(
                event_type=AuditEventTypeDB.write_execution_grant,
                project_id=bundle.workspace.project_id,
                actor="system",
                resource_kind="write_execution",
                resource_id=bundle.task.task_id,
                detail={"writable_paths": bundle.workspace.writable_paths},
            )

        return SecurityGateDecision(False, None, [])

    def resolve_secrets(self, bundle: ExecutorInputBundle) -> dict[str, str]:
        return {
            usage.name: self._secret_broker.resolve(usage, actor="dispatch_service")
            for usage in bundle.secret_usages
        }

    def _is_write_execution(self, bundle: ExecutorInputBundle) -> bool:
        return bundle.workspace.mode in {WorkspaceMode.WORKTREE, WorkspaceMode.DIRECT} and bool(
            bundle.workspace.writable_paths
        )

    @staticmethod
    def _is_command_blocked(command: str, bundle: ExecutorInputBundle) -> bool:
        allowlist = bundle.permission_policy.command_allowlist
        denylist = bundle.permission_policy.command_denylist
        if any(command.startswith(prefix) for prefix in denylist):
            return True
        return bool(allowlist and not any(command.startswith(prefix) for prefix in allowlist))


def _opa_input(bundle: ExecutorInputBundle) -> dict[str, Any]:
    return {
        "task": {
            "task_id": bundle.task.task_id,
            "run_id": bundle.task.run_id,
            "executor": bundle.task.executor,
        },
        "workspace": {
            "root_path": bundle.workspace.root_path,
            "writable_paths": list(bundle.workspace.writable_paths),
            "mode": bundle.workspace.mode,
        },
        "permission": bundle.permission_policy.model_dump(mode="json"),
        "commands": list(bundle.proposed_commands),
    }
