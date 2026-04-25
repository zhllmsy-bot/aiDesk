"""add persistent notification delivery ledger"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260423_0005"
down_revision = "20260419_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=120), nullable=False),
        sa.Column("source_channel", sa.String(length=80), nullable=False),
        sa.Column("delivery_channel", sa.String(length=80), nullable=False),
        sa.Column("delivery_status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("receipt_id", sa.String(length=120), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column(
            "metadata_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "sent_at",
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
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_id", name="uq_notification_deliveries_receipt_id"),
    )
    op.create_index(
        "ix_notification_deliveries_workflow_run_id",
        "notification_deliveries",
        ["workflow_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_deliveries_trace_id",
        "notification_deliveries",
        ["trace_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_deliveries_source_channel",
        "notification_deliveries",
        ["source_channel"],
        unique=False,
    )
    op.create_index(
        "ix_notification_deliveries_delivery_channel",
        "notification_deliveries",
        ["delivery_channel"],
        unique=False,
    )
    op.create_index(
        "ix_notification_deliveries_delivery_status",
        "notification_deliveries",
        ["delivery_status"],
        unique=False,
    )
    op.create_index(
        "ix_notification_deliveries_sent_at",
        "notification_deliveries",
        ["sent_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_deliveries_sent_at", table_name="notification_deliveries")
    op.drop_index(
        "ix_notification_deliveries_delivery_status",
        table_name="notification_deliveries",
    )
    op.drop_index(
        "ix_notification_deliveries_delivery_channel",
        table_name="notification_deliveries",
    )
    op.drop_index(
        "ix_notification_deliveries_source_channel",
        table_name="notification_deliveries",
    )
    op.drop_index("ix_notification_deliveries_trace_id", table_name="notification_deliveries")
    op.drop_index(
        "ix_notification_deliveries_workflow_run_id",
        table_name="notification_deliveries",
    )
    op.drop_table("notification_deliveries")
