"""add attempt_summaries and evidence_summaries tables"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260419_0004"
down_revision = "20260419_0003_1"
branch_labels = None
depends_on = None

attempt_status = sa.Enum(
    "waiting_approval",
    "completed",
    "failed_retryable",
    "failed_terminal",
    "cancelled",
    name="attempt_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "attempt_summaries",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=120), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("executor_type", sa.String(length=80), nullable=False),
        sa.Column("status", attempt_status, nullable=False, server_default="waiting_approval"),
        sa.Column("failure_category", sa.String(length=120), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_id", sa.String(length=120), nullable=True),
        sa.Column("verification_passed", sa.Boolean(), nullable=True),
        sa.Column(
            "linked_artifact_ids_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "linked_evidence_refs_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column(
            "metadata_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_attempt_summaries_project_id",
        "attempt_summaries",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_attempt_summaries_status",
        "attempt_summaries",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_attempt_summaries_task_id",
        "attempt_summaries",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "ix_attempt_summaries_workflow_run_id",
        "attempt_summaries",
        ["workflow_run_id"],
        unique=False,
    )

    op.create_table(
        "evidence_summaries",
        sa.Column("attempt_id", sa.String(length=120), nullable=False),
        sa.Column(
            "artifact_ids_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("verification_json", sa.JSON(), nullable=True),
        sa.Column(
            "verification_refs_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "memory_refs_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "provenance_graph_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
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
        sa.PrimaryKeyConstraint("attempt_id"),
    )


def downgrade() -> None:
    op.drop_table("evidence_summaries")

    op.drop_index("ix_attempt_summaries_workflow_run_id", table_name="attempt_summaries")
    op.drop_index("ix_attempt_summaries_task_id", table_name="attempt_summaries")
    op.drop_index("ix_attempt_summaries_status", table_name="attempt_summaries")
    op.drop_index("ix_attempt_summaries_project_id", table_name="attempt_summaries")
    op.drop_table("attempt_summaries")
