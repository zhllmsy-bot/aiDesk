"""add runtime durable backbone tables"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260419_0002"
down_revision = "20260419_0001"
branch_labels = None
depends_on = None


workflow_run_status = sa.Enum(
    "created",
    "queued",
    "running",
    "waiting_approval",
    "paused",
    "retrying",
    "completed",
    "failed",
    "cancelled",
    name="workflow_run_status",
    native_enum=False,
)
task_status = sa.Enum(
    "queued",
    "claimed",
    "running",
    "verifying",
    "waiting_approval",
    "retrying",
    "completed",
    "failed",
    "reclaimed",
    "cancelled",
    name="task_status",
    native_enum=False,
)
claim_status = sa.Enum(
    "active",
    "released",
    "expired",
    "reclaimed",
    name="claim_status",
    native_enum=False,
)
runtime_approval_status = sa.Enum(
    "pending",
    "approved",
    "rejected",
    "expired",
    "cancelled",
    name="runtime_approval_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("iteration_id", sa.String(length=36), nullable=True),
        sa.Column("workflow_name", sa.String(length=120), nullable=False),
        sa.Column("temporal_workflow_id", sa.String(length=255), nullable=False),
        sa.Column("temporal_run_id", sa.String(length=255), nullable=True),
        sa.Column("trace_id", sa.String(length=120), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("initiated_by", sa.String(length=120), nullable=False),
        sa.Column("status", workflow_run_status, nullable=False, server_default="created"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["iteration_id"], ["project_iterations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("temporal_workflow_id", name="uq_workflow_runs_temporal_workflow_id"),
    )
    op.create_index("ix_workflow_runs_project_id", "workflow_runs", ["project_id"], unique=False)
    op.create_index(
        "ix_workflow_runs_iteration_id", "workflow_runs", ["iteration_id"], unique=False
    )
    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"], unique=False)
    op.create_index("ix_workflow_runs_trace_id", "workflow_runs", ["trace_id"], unique=False)
    op.create_index(
        "ix_workflow_runs_workflow_name", "workflow_runs", ["workflow_name"], unique=False
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("graph_kind", sa.String(length=80), nullable=False),
        sa.Column("executor", sa.String(length=80), nullable=True),
        sa.Column("depends_on", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("status", task_status, nullable=False, server_default="queued"),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("executor_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_status", "tasks", ["status"], unique=False)
    op.create_index("ix_tasks_workflow_run_id", "tasks", ["workflow_run_id"], unique=False)

    op.create_table(
        "task_attempts",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("task_id", sa.String(length=120), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("executor", sa.String(length=80), nullable=True),
        sa.Column("status", task_status, nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_attempts_status", "task_attempts", ["status"], unique=False)
    op.create_index("ix_task_attempts_task_id", "task_attempts", ["task_id"], unique=False)
    op.create_index(
        "ix_task_attempts_workflow_run_id", "task_attempts", ["workflow_run_id"], unique=False
    )

    op.create_table(
        "task_claims",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("task_id", sa.String(length=120), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("attempt_id", sa.String(length=120), nullable=False),
        sa.Column("worker_id", sa.String(length=120), nullable=False),
        sa.Column("lease_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("status", claim_status, nullable=False, server_default="active"),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "heartbeat_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reclaimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["attempt_id"], ["task_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_claims_attempt_id", "task_claims", ["attempt_id"], unique=False)
    op.create_index("ix_task_claims_status", "task_claims", ["status"], unique=False)
    op.create_index("ix_task_claims_task_id", "task_claims", ["task_id"], unique=False)
    op.create_index("ix_task_claims_worker_id", "task_claims", ["worker_id"], unique=False)
    op.create_index(
        "ix_task_claims_workflow_run_id", "task_claims", ["workflow_run_id"], unique=False
    )

    op.create_table(
        "run_events",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=120), nullable=False),
        sa.Column("workflow_id", sa.String(length=255), nullable=True),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("task_id", sa.String(length=120), nullable=True),
        sa.Column("attempt_id", sa.String(length=120), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("payload_version", sa.String(length=40), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("producer", sa.String(length=120), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["attempt_id"], ["task_attempts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_run_events_idempotency_key"),
        sa.UniqueConstraint("workflow_run_id", "sequence", name="uq_run_events_workflow_sequence"),
    )
    op.create_index("ix_run_events_attempt_id", "run_events", ["attempt_id"], unique=False)
    op.create_index("ix_run_events_event_type", "run_events", ["event_type"], unique=False)
    op.create_index("ix_run_events_project_id", "run_events", ["project_id"], unique=False)
    op.create_index("ix_run_events_task_id", "run_events", ["task_id"], unique=False)
    op.create_index("ix_run_events_trace_id", "run_events", ["trace_id"], unique=False)
    op.create_index(
        "ix_run_events_workflow_run_id", "run_events", ["workflow_run_id"], unique=False
    )

    op.create_table(
        "approvals",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=120), nullable=False),
        sa.Column("approval_type", sa.String(length=80), nullable=False),
        sa.Column("status", runtime_approval_status, nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("required_scope", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("resolved_by", sa.String(length=120), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approvals_project_id", "approvals", ["project_id"], unique=False)
    op.create_index("ix_approvals_status", "approvals", ["status"], unique=False)
    op.create_index("ix_approvals_task_id", "approvals", ["task_id"], unique=False)
    op.create_index("ix_approvals_workflow_run_id", "approvals", ["workflow_run_id"], unique=False)
    op.create_index("ix_approvals_approval_type", "approvals", ["approval_type"], unique=False)

    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=120), nullable=False),
        sa.Column("source_attempt_id", sa.String(length=120), nullable=False),
        sa.Column("source_executor", sa.String(length=80), nullable=False),
        sa.Column("artifact_type", sa.String(length=80), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("content_hash", sa.String(length=255), nullable=False),
        sa.Column("producer", sa.String(length=120), nullable=False),
        sa.Column("workspace_ref", sa.String(length=255), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "retention_policy",
            sa.String(length=80),
            nullable=False,
            server_default="retain_for_run",
        ),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_attempt_id"], ["task_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_artifacts_artifact_type", "artifacts", ["artifact_type"], unique=False)
    op.create_index("ix_artifacts_project_id", "artifacts", ["project_id"], unique=False)
    op.create_index(
        "ix_artifacts_source_attempt_id", "artifacts", ["source_attempt_id"], unique=False
    )
    op.create_index("ix_artifacts_task_id", "artifacts", ["task_id"], unique=False)
    op.create_index("ix_artifacts_workflow_run_id", "artifacts", ["workflow_run_id"], unique=False)

    op.create_table(
        "memory_records",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("iteration_id", sa.String(length=36), nullable=True),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=True),
        sa.Column("task_id", sa.String(length=120), nullable=True),
        sa.Column("source_attempt_id", sa.String(length=120), nullable=True),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("memory_type", sa.String(length=80), nullable=False),
        sa.Column("external_ref", sa.String(length=1024), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default="openviking"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["iteration_id"], ["project_iterations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_attempt_id"], ["task_attempts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "namespace",
            "content_hash",
            name="uq_memory_records_namespace_hash",
        ),
    )
    op.create_index(
        "ix_memory_records_iteration_id", "memory_records", ["iteration_id"], unique=False
    )
    op.create_index(
        "ix_memory_records_memory_type", "memory_records", ["memory_type"], unique=False
    )
    op.create_index("ix_memory_records_namespace", "memory_records", ["namespace"], unique=False)
    op.create_index("ix_memory_records_project_id", "memory_records", ["project_id"], unique=False)
    op.create_index(
        "ix_memory_records_source_attempt_id", "memory_records", ["source_attempt_id"], unique=False
    )
    op.create_index("ix_memory_records_task_id", "memory_records", ["task_id"], unique=False)
    op.create_index(
        "ix_memory_records_workflow_run_id", "memory_records", ["workflow_run_id"], unique=False
    )

    op.create_table(
        "runtime_graph_checkpoints",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=120), nullable=True),
        sa.Column("attempt_id", sa.String(length=120), nullable=True),
        sa.Column("trace_id", sa.String(length=120), nullable=False),
        sa.Column("graph_kind", sa.String(length=80), nullable=False),
        sa.Column("state_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("resumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["attempt_id"], ["task_attempts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_runtime_graph_checkpoints_attempt_id",
        "runtime_graph_checkpoints",
        ["attempt_id"],
        unique=False,
    )
    op.create_index(
        "ix_runtime_graph_checkpoints_task_id",
        "runtime_graph_checkpoints",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "ix_runtime_graph_checkpoints_trace_id",
        "runtime_graph_checkpoints",
        ["trace_id"],
        unique=False,
    )
    op.create_index(
        "ix_runtime_graph_checkpoints_workflow_run_id",
        "runtime_graph_checkpoints",
        ["workflow_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_runtime_graph_checkpoints_workflow_run_id", table_name="runtime_graph_checkpoints"
    )
    op.drop_index("ix_runtime_graph_checkpoints_trace_id", table_name="runtime_graph_checkpoints")
    op.drop_index("ix_runtime_graph_checkpoints_task_id", table_name="runtime_graph_checkpoints")
    op.drop_index("ix_runtime_graph_checkpoints_attempt_id", table_name="runtime_graph_checkpoints")
    op.drop_table("runtime_graph_checkpoints")

    op.drop_index("ix_memory_records_workflow_run_id", table_name="memory_records")
    op.drop_index("ix_memory_records_task_id", table_name="memory_records")
    op.drop_index("ix_memory_records_source_attempt_id", table_name="memory_records")
    op.drop_index("ix_memory_records_project_id", table_name="memory_records")
    op.drop_index("ix_memory_records_namespace", table_name="memory_records")
    op.drop_index("ix_memory_records_memory_type", table_name="memory_records")
    op.drop_index("ix_memory_records_iteration_id", table_name="memory_records")
    op.drop_table("memory_records")

    op.drop_index("ix_artifacts_workflow_run_id", table_name="artifacts")
    op.drop_index("ix_artifacts_task_id", table_name="artifacts")
    op.drop_index("ix_artifacts_source_attempt_id", table_name="artifacts")
    op.drop_index("ix_artifacts_project_id", table_name="artifacts")
    op.drop_index("ix_artifacts_artifact_type", table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index("ix_approvals_approval_type", table_name="approvals")
    op.drop_index("ix_approvals_workflow_run_id", table_name="approvals")
    op.drop_index("ix_approvals_task_id", table_name="approvals")
    op.drop_index("ix_approvals_status", table_name="approvals")
    op.drop_index("ix_approvals_project_id", table_name="approvals")
    op.drop_table("approvals")

    op.drop_index("ix_run_events_workflow_run_id", table_name="run_events")
    op.drop_index("ix_run_events_trace_id", table_name="run_events")
    op.drop_index("ix_run_events_task_id", table_name="run_events")
    op.drop_index("ix_run_events_project_id", table_name="run_events")
    op.drop_index("ix_run_events_event_type", table_name="run_events")
    op.drop_index("ix_run_events_attempt_id", table_name="run_events")
    op.drop_table("run_events")

    op.drop_index("ix_task_claims_workflow_run_id", table_name="task_claims")
    op.drop_index("ix_task_claims_worker_id", table_name="task_claims")
    op.drop_index("ix_task_claims_task_id", table_name="task_claims")
    op.drop_index("ix_task_claims_status", table_name="task_claims")
    op.drop_index("ix_task_claims_attempt_id", table_name="task_claims")
    op.drop_table("task_claims")

    op.drop_index("ix_task_attempts_workflow_run_id", table_name="task_attempts")
    op.drop_index("ix_task_attempts_task_id", table_name="task_attempts")
    op.drop_index("ix_task_attempts_status", table_name="task_attempts")
    op.drop_table("task_attempts")

    op.drop_index("ix_tasks_workflow_run_id", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("ix_workflow_runs_workflow_name", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_trace_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_status", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_project_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_iteration_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")
