from __future__ import annotations

# pyright: reportUnknownVariableType=false
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

EXECUTION_SCHEMA_VERSION = "2026-04-19.execution.v1"


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ExecutionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, use_enum_values=True)


class ExecutionApiModel(ExecutionModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        use_enum_values=True,
        alias_generator=to_camel,
    )


class WorkspaceMode(StrEnum):
    READ_ONLY = "read_only"
    WORKTREE = "worktree"
    DIRECT = "direct"


class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class FailureKind(StrEnum):
    RETRYABLE = "retryable"
    TERMINAL = "terminal"


class ArtifactType(StrEnum):
    PATCH = "patch"
    LOG = "log"
    REPORT = "report"
    SCREENSHOT = "screenshot"
    TRACE_SNAPSHOT = "trace_snapshot"
    TEST_REPORT = "test_report"
    FILE = "file"
    SUMMARY = "summary"
    EVIDENCE = "evidence"
    COMMAND_OUTPUT = "command_output"


class MemoryType(StrEnum):
    LONG_TERM_KNOWLEDGE = "long_term_knowledge"
    PROJECT_FACT = "project_fact"
    LESSON = "lesson"


class ApprovalType(StrEnum):
    WRITE_EXECUTION = "write_execution"
    SECRET_ACCESS = "secret_access"
    COMMAND_EXCEPTION = "command_exception"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ContextLevel(StrEnum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class EvidenceKind(StrEnum):
    ARTIFACT = "artifact"
    MEMORY = "memory"
    VERIFICATION = "verification"
    APPROVAL = "approval"
    PROVENANCE = "provenance"


class SecretSource(StrEnum):
    BROKER = "broker"
    OPERATOR = "operator"
    ENVIRONMENT = "environment"


class AttemptStatus(StrEnum):
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"
    CANCELLED = "cancelled"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceRef(ExecutionModel):
    kind: EvidenceKind
    ref: str
    summary: str | None = None


class ContextBlock(ExecutionModel):
    level: ContextLevel
    title: str
    body: str
    source: str
    truncated: bool = False
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ContextBundle(ExecutionModel):
    schema_version: str = EXECUTION_SCHEMA_VERSION
    task_id: str
    blocks: list[ContextBlock]
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class PermissionPolicy(ExecutionModel):
    workspace_allowlist: list[str] = Field(default_factory=list)
    allowed_write_paths: list[str] = Field(default_factory=list)
    command_allowlist: list[str] = Field(default_factory=list)
    command_denylist: list[str] = Field(default_factory=list)
    require_manual_approval_for_write: bool = True
    secret_broker_enabled: bool = False
    workspace_mode: WorkspaceMode = WorkspaceMode.READ_ONLY


class VerifyCommand(ExecutionModel):
    id: str
    command: str
    required: bool = True


class SecretUsage(ExecutionModel):
    name: str
    source: SecretSource
    scope: str
    expires_at: datetime | None = None


class TaskInfo(ExecutionModel):
    task_id: str
    run_id: str
    title: str
    description: str
    executor: str
    priority: str = "normal"
    expected_artifact_types: list[ArtifactType] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkspaceInfo(ExecutionModel):
    project_id: str
    iteration_id: str | None = None
    workspace_ref: str
    root_path: str
    base_commit_sha: str | None = None
    mode: WorkspaceMode = WorkspaceMode.READ_ONLY
    writable_paths: list[str] = Field(default_factory=list)


class DispatchControl(ExecutionModel):
    idempotency_key: str
    timeout_seconds: int = Field(default=1800, ge=1)
    heartbeat_interval_seconds: int = Field(default=30, ge=1)
    replay_of_attempt_id: str | None = None
    attempt_id: str | None = None


class ExecutorInputBundle(ExecutionModel):
    schema_version: str = EXECUTION_SCHEMA_VERSION
    task: TaskInfo
    workspace: WorkspaceInfo
    context_blocks: list[ContextBlock] = Field(default_factory=list)
    permission_policy: PermissionPolicy
    verify_commands: list[VerifyCommand] = Field(default_factory=list)
    proposed_commands: list[str] = Field(default_factory=list)
    secret_usages: list[SecretUsage] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    dispatch: DispatchControl


class LogEntry(ExecutionModel):
    stream: str
    message: str
    timestamp: datetime = Field(default_factory=utcnow)


class ExecutionProvenance(ExecutionModel):
    executor: str
    provider_request_id: str
    model: str | None = None
    attempt_id: str
    workspace_ref: str
    trigger: str
    operator: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactDescriptor(ExecutionModel):
    artifact_type: ArtifactType
    path: str
    content_hash: str
    producer: str
    workspace_ref: str
    provenance: ExecutionProvenance
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    retention_policy: str = "retain_for_run"
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ArtifactRecord(ExecutionModel):
    artifact_id: str
    project_id: str
    run_id: str
    task_id: str
    source_attempt_id: str
    source_executor: str
    artifact_type: ArtifactType
    path: str
    content_hash: str
    producer: str
    workspace_ref: str
    provenance: ExecutionProvenance
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    retention_policy: str = "retain_for_run"
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class VerificationCommandResult(ExecutionModel):
    command: str
    exit_code: int
    output: str
    passed: bool


class VerificationResult(ExecutionModel):
    passed: bool
    summary: str
    results: list[VerificationCommandResult] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class FailureInfo(ExecutionModel):
    kind: FailureKind
    category: str
    reason: str
    retry_after_seconds: int | None = Field(default=None, ge=1)
    detail: dict[str, Any] = Field(default_factory=dict)


class ExecutorResultBundle(ExecutionModel):
    schema_version: str = EXECUTION_SCHEMA_VERSION
    status: ExecutionStatus
    logs: list[LogEntry] = Field(default_factory=list)
    artifacts: list[ArtifactDescriptor] = Field(default_factory=list)
    verification: VerificationResult | None = None
    failure: FailureInfo | None = None
    provenance: ExecutionProvenance
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime = Field(default_factory=utcnow)
    heartbeat_count: int = 0


class ExecutorCapability(ExecutionModel):
    executor: str
    supports_write: bool
    supports_verify: bool
    supports_tools: bool
    supports_screenshots: bool


class RetentionPolicy(StrEnum):
    RETAIN_FOR_RUN = "retain_for_run"
    RETAIN_FOR_PROJECT = "retain_for_project"
    RETAIN_PERMANENT = "retain_permanent"
    DECAY_30D = "decay_30d"
    DECAY_90D = "decay_90d"


class MemoryWriteCandidate(ExecutionModel):
    project_id: str
    iteration_id: str | None = None
    namespace: str | None = None
    memory_type: MemoryType
    external_ref: str
    summary: str
    content_hash: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    quality_score: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    force: bool = False
    retention_policy: RetentionPolicy = RetentionPolicy.RETAIN_FOR_PROJECT
    supersedes_record_id: str | None = None


class MemoryRecord(ExecutionModel):
    record_id: str
    project_id: str
    iteration_id: str | None = None
    namespace: str
    memory_type: MemoryType
    external_ref: str
    summary: str
    content_hash: str
    score: float = Field(ge=0.0, le=1.0)
    quality_score: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    supersedes_record_id: str | None = None
    stale_at: datetime | None = None
    retention_policy: RetentionPolicy = RetentionPolicy.RETAIN_FOR_PROJECT
    last_recalled_at: datetime | None = None
    recall_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalResolutionPayload(ExecutionModel):
    decision: ApprovalStatus
    reason: str
    approved_write_paths: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalRecord(ExecutionModel):
    approval_id: str
    project_id: str
    run_id: str
    task_id: str
    approval_type: ApprovalType
    status: ApprovalStatus
    requested_by: str
    requested_at: datetime = Field(default_factory=utcnow)
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    resolution_payload: ApprovalResolutionPayload | None = None
    reason: str
    required_scope: list[str] = Field(default_factory=list)


class ProvenanceNode(ExecutionModel):
    node_id: str
    kind: EvidenceKind
    label: str
    ref: str


class ProvenanceEdge(ExecutionModel):
    source: str
    target: str
    relation: str


class ProvenanceGraph(ExecutionModel):
    nodes: list[ProvenanceNode] = Field(default_factory=list)
    edges: list[ProvenanceEdge] = Field(default_factory=list)


class EvidenceSummary(ExecutionModel):
    attempt_id: str
    artifact_ids: list[str] = Field(default_factory=list)
    memory_refs: list[MemoryRecord] = Field(default_factory=list)
    verification: VerificationResult | None = None
    verification_refs: list[EvidenceRef] = Field(default_factory=list)
    provenance_graph: ProvenanceGraph = Field(default_factory=ProvenanceGraph)


class AttemptSummary(ExecutionModel):
    attempt_id: str
    project_id: str
    task_id: str
    run_id: str
    executor_type: str
    status: AttemptStatus
    failure_category: str | None = None
    failure_reason: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None
    linked_artifact_ids: list[str] = Field(default_factory=list)
    linked_evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    verification_passed: bool | None = None
    approval_id: str | None = None
    provenance: ExecutionProvenance | None = None


class Actor(ExecutionApiModel):
    id: str
    name: str
    role: str


class Correlation(ExecutionApiModel):
    project_id: str
    run_id: str
    task_id: str
    attempt_id: str | None = None


class ProvenanceRecord(ExecutionApiModel):
    source: str
    producer: str
    created_at: str
    content_hash: str
    correlation: Correlation


class ApprovalSummaryView(ExecutionApiModel):
    schema_version: str = EXECUTION_SCHEMA_VERSION
    id: str
    type: str
    status: ApprovalStatus
    requested_by: Actor
    requested_at: str
    risk_level: RiskLevel
    title: str
    reason: str
    correlation: Correlation


class ApprovalDetailView(ApprovalSummaryView):
    resolution_note: str | None = None
    related_artifacts: list[str] = Field(default_factory=list)
    expires_at: str | None = None


class ArtifactView(ExecutionApiModel):
    schema_version: str = EXECUTION_SCHEMA_VERSION
    id: str
    type: str
    title: str
    preview: str
    mime_type: str
    content: str
    provenance: ProvenanceRecord


class VerificationCheckView(ExecutionApiModel):
    label: str
    status: str
    detail: str


class VerificationView(ExecutionApiModel):
    verdict: str
    summary: str
    checks: list[VerificationCheckView] = Field(default_factory=list)


class MemoryHitView(ExecutionApiModel):
    id: str
    namespace: str
    score: float
    summary: str
    external_ref: str | None = None
    version: int = 1
    supersedes_record_id: str | None = None
    stale_at: str | None = None
    retention_policy: str = RetentionPolicy.RETAIN_FOR_PROJECT
    recall_count: int = 0


class EvidenceRefView(ExecutionApiModel):
    id: str
    label: str
    type: EvidenceKind
    href: str


class SecuritySummaryView(ExecutionApiModel):
    write_allowed: bool
    approval_required: bool
    used_secret: bool
    scope: str


class ExecutorAttemptView(ExecutionApiModel):
    schema_version: str = EXECUTION_SCHEMA_VERSION
    id: str
    executor: str
    started_at: str
    finished_at: str
    summary: str
    verification: VerificationView
    memory_hits: list[MemoryHitView] = Field(default_factory=list)
    evidence_refs: list[EvidenceRefView] = Field(default_factory=list)
    security: SecuritySummaryView
    correlation: Correlation


class EvidenceSummaryView(ExecutionApiModel):
    schema_version: str = EXECUTION_SCHEMA_VERSION
    attempt_id: str
    artifact_ids: list[str] = Field(default_factory=list)
    memory_hits: list[MemoryHitView] = Field(default_factory=list)
    verification: VerificationView | None = None
    evidence_refs: list[EvidenceRefView] = Field(default_factory=list)


class DispatchExecutionResponse(ExecutionModel):
    result: ExecutorResultBundle | None = None
    approval: ApprovalRecord | None = None


class ExecutorCapabilitiesResponse(ExecutionModel):
    items: list[ExecutorCapability]


class ApprovalListResponse(ExecutionModel):
    items: list[ApprovalSummaryView]


class ArtifactListResponse(ExecutionModel):
    items: list[ArtifactView]


class MemoryHitsResponse(ExecutionModel):
    items: list[MemoryHitView]


class AttemptListResponse(ExecutionModel):
    items: list[ExecutorAttemptView]


def contract_snapshot() -> dict[str, Any]:
    models = {
        "ExecutorInputBundle": ExecutorInputBundle,
        "ExecutorResultBundle": ExecutorResultBundle,
        "ApprovalRecord": ApprovalRecord,
        "ArtifactRecord": ArtifactRecord,
        "AttemptSummary": AttemptSummary,
        "MemoryRecord": MemoryRecord,
        "EvidenceSummary": EvidenceSummary,
        "ContextBundle": ContextBundle,
    }
    return {
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "models": {name: model.model_json_schema() for name, model in models.items()},
    }


def approval_risk_level(record: ApprovalRecord) -> RiskLevel:
    if record.approval_type == ApprovalType.SECRET_ACCESS:
        return RiskLevel.CRITICAL
    if record.approval_type == ApprovalType.COMMAND_EXCEPTION:
        return RiskLevel.HIGH
    if len(record.required_scope) > 2:
        return RiskLevel.HIGH
    if record.required_scope:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def correlation_for(
    *,
    project_id: str,
    run_id: str,
    task_id: str,
    attempt_id: str | None = None,
) -> Correlation:
    return Correlation(
        project_id=project_id,
        run_id=run_id,
        task_id=task_id,
        attempt_id=attempt_id,
    )


def map_approval_summary(record: ApprovalRecord) -> ApprovalSummaryView:
    return ApprovalSummaryView(
        id=record.approval_id,
        type=record.approval_type,
        status=record.status,
        requested_by=Actor(id=record.requested_by, name=record.requested_by, role="operator"),
        requested_at=record.requested_at.isoformat(),
        risk_level=approval_risk_level(record),
        title=record.approval_type.replace("_", " ").title(),
        reason=record.reason,
        correlation=correlation_for(
            project_id=record.project_id,
            run_id=record.run_id,
            task_id=record.task_id,
        ),
    )


def map_approval_detail(record: ApprovalRecord, related_artifacts: list[str]) -> ApprovalDetailView:
    payload = map_approval_summary(record).model_dump()
    resolution_note = record.resolution_payload.reason if record.resolution_payload else None
    expires_at = None
    if record.status == ApprovalStatus.PENDING:
        expires_at = record.requested_at.replace(microsecond=0).isoformat()
    return ApprovalDetailView(
        **payload,
        resolution_note=resolution_note,
        related_artifacts=related_artifacts,
        expires_at=expires_at,
    )


def map_verification_view(verification: VerificationResult | None) -> VerificationView:
    if verification is None:
        return VerificationView(
            verdict="warning",
            summary="Verification was not executed for this attempt.",
            checks=[],
        )

    verdict = "passed" if verification.passed else "failed"
    checks = [
        VerificationCheckView(
            label=result.command,
            status="passed" if result.passed else "failed",
            detail=result.output,
        )
        for result in verification.results
    ]
    return VerificationView(verdict=verdict, summary=verification.summary, checks=checks)


def map_memory_hit(record: MemoryRecord) -> MemoryHitView:
    return MemoryHitView(
        id=record.record_id,
        namespace=record.namespace,
        score=record.score,
        summary=record.summary,
        external_ref=record.external_ref,
        version=record.version,
        supersedes_record_id=record.supersedes_record_id,
        stale_at=record.stale_at.isoformat() if record.stale_at else None,
        retention_policy=record.retention_policy,
        recall_count=record.recall_count,
    )


def map_evidence_ref(ref: EvidenceRef) -> EvidenceRefView:
    href = "/review"
    if ref.kind == EvidenceKind.ARTIFACT:
        href = f"/artifacts/{ref.ref}"
    elif ref.kind == EvidenceKind.MEMORY:
        href = f"/memory/hits?recordId={ref.ref}"
    elif ref.kind == EvidenceKind.VERIFICATION:
        href = f"/review/evidence/{ref.ref.replace('verify:', '')}"
    elif ref.kind == EvidenceKind.APPROVAL:
        href = f"/review/approvals/{ref.ref}"

    return EvidenceRefView(
        id=ref.ref,
        label=ref.summary or ref.kind.replace("_", " ").title(),
        type=ref.kind,
        href=href,
    )


def artifact_view_type(artifact_type: ArtifactType) -> str:
    if artifact_type == ArtifactType.PATCH:
        return ArtifactType.PATCH
    if artifact_type in {ArtifactType.LOG, ArtifactType.COMMAND_OUTPUT}:
        return ArtifactType.LOG
    if artifact_type == ArtifactType.SCREENSHOT:
        return ArtifactType.SCREENSHOT
    if artifact_type == ArtifactType.TRACE_SNAPSHOT:
        return ArtifactType.TRACE_SNAPSHOT
    return ArtifactType.REPORT


def artifact_mime_type(artifact_type: ArtifactType) -> str:
    if artifact_type == ArtifactType.PATCH:
        return "text/x-diff"
    if artifact_type in {ArtifactType.LOG, ArtifactType.COMMAND_OUTPUT}:
        return "text/plain"
    if artifact_type == ArtifactType.SCREENSHOT:
        return "image/png"
    if artifact_type == ArtifactType.TRACE_SNAPSHOT:
        return "application/json"
    return "text/markdown"


def map_artifact_view(record: ArtifactRecord) -> ArtifactView:
    preview = record.summary or record.path
    content = record.metadata.get("content")
    if not isinstance(content, str):
        content = f"Artifact stored at {record.path}"
    return ArtifactView(
        id=record.artifact_id,
        type=artifact_view_type(record.artifact_type),
        title=record.summary or record.path.rsplit("/", maxsplit=1)[-1],
        preview=preview,
        mime_type=artifact_mime_type(record.artifact_type),
        content=content,
        provenance=ProvenanceRecord(
            source=record.source_executor,
            producer=record.producer,
            created_at=record.created_at.isoformat(),
            content_hash=record.content_hash,
            correlation=correlation_for(
                project_id=record.project_id,
                run_id=record.run_id,
                task_id=record.task_id,
                attempt_id=record.source_attempt_id,
            ),
        ),
    )


def map_evidence_summary_view(summary: EvidenceSummary) -> EvidenceSummaryView:
    evidence_refs = [map_evidence_ref(ref) for ref in summary.verification_refs]
    for memory_record in summary.memory_refs:
        evidence_refs.append(
            EvidenceRefView(
                id=memory_record.record_id,
                label=memory_record.summary,
                type=EvidenceKind.MEMORY,
                href=f"/memory/hits?projectId={memory_record.project_id}",
            )
        )
    for artifact_id in summary.artifact_ids:
        evidence_refs.append(
            EvidenceRefView(
                id=artifact_id,
                label="Artifact",
                type=EvidenceKind.ARTIFACT,
                href=f"/artifacts/{artifact_id}",
            )
        )
    return EvidenceSummaryView(
        attempt_id=summary.attempt_id,
        artifact_ids=summary.artifact_ids,
        memory_hits=[map_memory_hit(record) for record in summary.memory_refs],
        verification=map_verification_view(summary.verification) if summary.verification else None,
        evidence_refs=evidence_refs,
    )


def map_attempt_view(
    attempt: AttemptSummary, evidence: EvidenceSummary | None
) -> ExecutorAttemptView:
    verification = map_verification_view(evidence.verification if evidence else None)
    memory_hits = [map_memory_hit(record) for record in evidence.memory_refs] if evidence else []
    evidence_refs = [map_evidence_ref(ref) for ref in attempt.linked_evidence_refs]
    if evidence:
        evidence_refs.extend(map_evidence_summary_view(evidence).evidence_refs)

    if attempt.status == AttemptStatus.WAITING_APPROVAL:
        summary = "Waiting for manual approval before write execution."
    elif attempt.status == AttemptStatus.COMPLETED:
        summary = "Execution completed successfully."
    else:
        summary = attempt.failure_reason or "Execution ended with a failure."

    used_secret = bool(attempt.provenance and attempt.provenance.metadata.get("secret_names"))
    write_allowed = attempt.status != AttemptStatus.WAITING_APPROVAL
    security = SecuritySummaryView(
        write_allowed=write_allowed,
        approval_required=attempt.approval_id is not None,
        used_secret=used_secret,
        scope=attempt.provenance.workspace_ref if attempt.provenance else "unknown",
    )
    finished_at = attempt.ended_at or attempt.started_at
    return ExecutorAttemptView(
        id=attempt.attempt_id,
        executor=attempt.executor_type,
        started_at=attempt.started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        summary=summary,
        verification=verification,
        memory_hits=memory_hits,
        evidence_refs=evidence_refs,
        security=security,
        correlation=correlation_for(
            project_id=attempt.project_id,
            run_id=attempt.run_id,
            task_id=attempt.task_id,
            attempt_id=attempt.attempt_id,
        ),
    )
