"""add security hardening tables: secrets, audit_log"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260419_0003"
down_revision = "20260419_0002"
branch_labels = None
depends_on = None

secret_scope = sa.Enum(
    "project",
    "global_scope",
    name="secret_scope",
    native_enum=False,
)

audit_event_type = sa.Enum(
    "secret_resolve",
    "approval_gate_hit",
    "blocked_command",
    "write_execution_grant",
    "workspace_isolation_violation",
    "provenance_integrity_failure",
    name="audit_event_type",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "secrets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scope", secret_scope, nullable=False, server_default="project"),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_secrets_project_id", "secrets", ["project_id"], unique=False)
    op.create_index("ix_secrets_name", "secrets", ["name"], unique=False)
    op.create_index("ix_secrets_scope", "secrets", ["scope"], unique=False)
    op.create_index("ix_secrets_expires_at", "secrets", ["expires_at"], unique=False)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", audit_event_type, nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("resource_kind", sa.String(length=80), nullable=True),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("detail_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"], unique=False)
    op.create_index("ix_audit_log_project_id", "audit_log", ["project_id"], unique=False)
    op.create_index("ix_audit_log_actor", "audit_log", ["actor"], unique=False)
    op.create_index("ix_audit_log_occurred_at", "audit_log", ["occurred_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_log_occurred_at", table_name="audit_log")
    op.drop_index("ix_audit_log_actor", table_name="audit_log")
    op.drop_index("ix_audit_log_project_id", table_name="audit_log")
    op.drop_index("ix_audit_log_event_type", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_secrets_expires_at", table_name="secrets")
    op.drop_index("ix_secrets_scope", table_name="secrets")
    op.drop_index("ix_secrets_name", table_name="secrets")
    op.drop_index("ix_secrets_project_id", table_name="secrets")
    op.drop_table("secrets")
