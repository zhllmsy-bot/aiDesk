from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.auth.models import generate_id
from api.database import Base, utcnow


class WorkflowRunStatusDB(str, enum.Enum):
    created = "created"
    queued = "queued"
    running = "running"
    waiting_approval = "waiting_approval"
    paused = "paused"
    retrying = "retrying"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaskStatusDB(str, enum.Enum):
    queued = "queued"
    claimed = "claimed"
    running = "running"
    verifying = "verifying"
    waiting_approval = "waiting_approval"
    retrying = "retrying"
    completed = "completed"
    failed = "failed"
    reclaimed = "reclaimed"
    cancelled = "cancelled"


class ClaimStatusDB(str, enum.Enum):
    active = "active"
    released = "released"
    expired = "expired"
    reclaimed = "reclaimed"


class ApprovalStatusDB(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"
    cancelled = "cancelled"


class RuntimeWorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    iteration_id: Mapped[str | None] = mapped_column(
        ForeignKey("project_iterations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workflow_name: Mapped[str] = mapped_column(String(120), index=True)
    temporal_workflow_id: Mapped[str] = mapped_column(String(255), unique=True)
    temporal_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trace_id: Mapped[str] = mapped_column(String(120), index=True)
    objective: Mapped[str] = mapped_column(Text)
    initiated_by: Mapped[str] = mapped_column(String(120))
    status: Mapped[WorkflowRunStatusDB] = mapped_column(
        Enum(WorkflowRunStatusDB, native_enum=False),
        default=WorkflowRunStatusDB.created,
        index=True,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RuntimeTask(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    graph_kind: Mapped[str] = mapped_column(String(80))
    executor: Mapped[str | None] = mapped_column(String(80), nullable=True)
    depends_on: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[TaskStatusDB] = mapped_column(
        Enum(TaskStatusDB, native_enum=False),
        default=TaskStatusDB.queued,
        index=True,
    )
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    executor_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RuntimeTaskAttempt(Base):
    __tablename__ = "task_attempts"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        index=True,
    )
    executor: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[TaskStatusDB] = mapped_column(
        Enum(TaskStatusDB, native_enum=False),
        default=TaskStatusDB.queued,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class RuntimeTaskClaim(Base):
    __tablename__ = "task_claims"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        index=True,
    )
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("task_attempts.id", ondelete="CASCADE"),
        index=True,
    )
    worker_id: Mapped[str] = mapped_column(String(120), index=True)
    lease_timeout_seconds: Mapped[int] = mapped_column(Integer)
    status: Mapped[ClaimStatusDB] = mapped_column(
        Enum(ClaimStatusDB, native_enum=False),
        default=ClaimStatusDB.active,
        index=True,
    )
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reclaimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RuntimeRunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "sequence", name="uq_run_events_workflow_sequence"),
        UniqueConstraint("idempotency_key", name="uq_run_events_idempotency_key"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        index=True,
    )
    trace_id: Mapped[str] = mapped_column(String(120), index=True)
    workflow_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey("task_attempts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    schema_version: Mapped[str] = mapped_column(String(40))
    payload_version: Mapped[str] = mapped_column(String(40))
    sequence: Mapped[int] = mapped_column(Integer)
    producer: Mapped[str] = mapped_column(String(120))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(255))
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RuntimeApproval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(120), primary_key=True, default=generate_id)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        index=True,
    )
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    approval_type: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[ApprovalStatusDB] = mapped_column(
        Enum(ApprovalStatusDB, native_enum=False),
        default=ApprovalStatusDB.pending,
        index=True,
    )
    requested_by: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text)
    required_scope: Mapped[list[str]] = mapped_column(JSON, default=list)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)


class RuntimeArtifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(120), primary_key=True, default=generate_id)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        index=True,
    )
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    source_attempt_id: Mapped[str] = mapped_column(
        ForeignKey("task_attempts.id", ondelete="CASCADE"),
        index=True,
    )
    source_executor: Mapped[str] = mapped_column(String(80))
    artifact_type: Mapped[str] = mapped_column(String(80), index=True)
    path: Mapped[str] = mapped_column(String(1024))
    content_hash: Mapped[str] = mapped_column(String(255))
    producer: Mapped[str] = mapped_column(String(120))
    workspace_ref: Mapped[str] = mapped_column(String(255))
    provenance_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    retention_policy: Mapped[str] = mapped_column(String(80), default="retain_for_run")
    evidence_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RuntimeNotificationDelivery(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint("receipt_id", name="uq_notification_deliveries_receipt_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        index=True,
    )
    trace_id: Mapped[str] = mapped_column(String(120), index=True)
    source_channel: Mapped[str] = mapped_column(String(80), index=True)
    delivery_channel: Mapped[str] = mapped_column(String(80), index=True)
    delivery_status: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    receipt_id: Mapped[str] = mapped_column(String(120), index=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RetentionPolicyDB(str, enum.Enum):
    retain_for_run = "retain_for_run"
    retain_for_project = "retain_for_project"
    retain_permanent = "retain_permanent"
    decay_30d = "decay_30d"
    decay_90d = "decay_90d"


class RuntimeMemoryRecord(Base):
    __tablename__ = "memory_records"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "namespace", "content_hash", name="uq_memory_records_namespace_hash"
        ),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True, default=generate_id)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    iteration_id: Mapped[str | None] = mapped_column(
        ForeignKey("project_iterations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workflow_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey("task_attempts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    namespace: Mapped[str] = mapped_column(String(255), index=True)
    memory_type: Mapped[str] = mapped_column(String(80), index=True)
    external_ref: Mapped[str] = mapped_column(String(1024))
    summary: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(255))
    score: Mapped[float] = mapped_column()
    quality_score: Mapped[float] = mapped_column()
    version: Mapped[int] = mapped_column(Integer, default=1)
    supersedes_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("memory_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    stale_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    retention_policy: Mapped[str] = mapped_column(
        String(80),
        default=RetentionPolicyDB.retain_for_project,
    )
    last_recalled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recall_count: Mapped[int] = mapped_column(Integer, default=0)
    provider: Mapped[str] = mapped_column(String(80), default="openviking")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    evidence_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AttemptStatusDB(str, enum.Enum):
    waiting_approval = "waiting_approval"
    completed = "completed"
    failed_retryable = "failed_retryable"
    failed_terminal = "failed_terminal"
    cancelled = "cancelled"


class RuntimeAttemptSummary(Base):
    __tablename__ = "attempt_summaries"

    id: Mapped[str] = mapped_column(String(120), primary_key=True, default=generate_id)
    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        index=True,
    )
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    executor_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[AttemptStatusDB] = mapped_column(
        Enum(AttemptStatusDB, native_enum=False),
        default=AttemptStatusDB.waiting_approval,
        index=True,
    )
    failure_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    verification_passed: Mapped[bool | None] = mapped_column(nullable=True)
    linked_artifact_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    linked_evidence_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    provenance_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class RuntimeEvidenceSummary(Base):
    __tablename__ = "evidence_summaries"

    attempt_id: Mapped[str] = mapped_column(
        String(120),
        primary_key=True,
    )
    artifact_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    verification_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    verification_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    memory_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    provenance_graph_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class RuntimeGraphCheckpoint(Base):
    __tablename__ = "runtime_graph_checkpoints"

    id: Mapped[str] = mapped_column(String(120), primary_key=True, default=generate_id)
    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        index=True,
    )
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey("task_attempts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    trace_id: Mapped[str] = mapped_column(String(120), index=True)
    graph_kind: Mapped[str] = mapped_column(String(80))
    state_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
