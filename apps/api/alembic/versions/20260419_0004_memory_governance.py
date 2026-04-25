"""add memory governance fields to memory_records"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260419_0004_memory"
down_revision = "20260419_0003_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("memory_records") as batch_op:
        batch_op.add_column(
            sa.Column("supersedes_record_id", sa.String(length=120), nullable=True),
        )
        batch_op.add_column(
            sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        )
        batch_op.add_column(
            sa.Column(
                "retention_policy",
                sa.String(length=80),
                nullable=False,
                server_default="retain_for_project",
            ),
        )
        batch_op.add_column(
            sa.Column("last_recalled_at", sa.DateTime(timezone=True), nullable=True),
        )
        batch_op.add_column(
            sa.Column("recall_count", sa.Integer(), nullable=False, server_default="0"),
        )
        batch_op.create_foreign_key(
            "fk_memory_records_supersedes_record_id_memory_records",
            "memory_records",
            ["supersedes_record_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_memory_records_supersedes_record_id",
            ["supersedes_record_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_memory_records_stale_at",
            ["stale_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("memory_records") as batch_op:
        batch_op.drop_index("ix_memory_records_stale_at")
        batch_op.drop_index("ix_memory_records_supersedes_record_id")
        batch_op.drop_constraint(
            "fk_memory_records_supersedes_record_id_memory_records",
            type_="foreignkey",
        )
        batch_op.drop_column("recall_count")
        batch_op.drop_column("last_recalled_at")
        batch_op.drop_column("retention_policy")
        batch_op.drop_column("stale_at")
        batch_op.drop_column("supersedes_record_id")
