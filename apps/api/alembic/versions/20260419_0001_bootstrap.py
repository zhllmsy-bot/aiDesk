"""bootstrap control plane tables"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260419_0001"
down_revision = None
branch_labels = None
depends_on = None


project_status = sa.Enum("active", "archived", name="project_status", native_enum=False)
iteration_status = sa.Enum(
    "planned", "active", "completed", name="iteration_status", native_enum=False
)
plan_status = sa.Enum("draft", "ready", "archived", name="plan_status", native_enum=False)
project_role = sa.Enum(
    "admin",
    "maintainer",
    "reviewer",
    "viewer",
    name="project_role",
    native_enum=False,
)
membership_status = sa.Enum(
    "active",
    "invited",
    "suspended",
    name="membership_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("root_path", sa.String(length=1024), nullable=False),
        sa.Column("default_branch", sa.String(length=120), nullable=False, server_default="main"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", project_status, nullable=False, server_default="active"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("root_path", name="uq_projects_root_path"),
        sa.UniqueConstraint("slug", name="uq_projects_slug"),
    )
    op.create_index("ix_projects_status", "projects", ["status"], unique=False)
    op.create_index("ix_projects_slug", "projects", ["slug"], unique=True)
    op.create_index("ix_projects_root_path", "projects", ["root_path"], unique=True)

    op.create_table(
        "project_iterations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("status", iteration_status, nullable=False, server_default="planned"),
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
        sa.UniqueConstraint(
            "project_id", "sequence_number", name="uq_project_iterations_project_sequence"
        ),
    )

    op.create_table(
        "plans",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("iteration_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("status", plan_status, nullable=False, server_default="draft"),
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
        sa.ForeignKeyConstraint(["iteration_id"], ["project_iterations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plans_project_id", "plans", ["project_id"], unique=False)

    op.create_table(
        "project_memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", project_role, nullable=False),
        sa.Column("status", membership_status, nullable=False, server_default="active"),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_memberships_project_user"),
    )
    op.create_index(
        "ix_project_memberships_project_user",
        "project_memberships",
        ["project_id", "user_id"],
        unique=True,
    )

    op.create_table(
        "api_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_api_sessions_token_hash"),
    )
    op.create_index("ix_api_sessions_user_id", "api_sessions", ["user_id"], unique=False)
    op.create_index("ix_api_sessions_token_hash", "api_sessions", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_api_sessions_token_hash", table_name="api_sessions")
    op.drop_index("ix_api_sessions_user_id", table_name="api_sessions")
    op.drop_table("api_sessions")

    op.drop_index("ix_project_memberships_project_user", table_name="project_memberships")
    op.drop_table("project_memberships")

    op.drop_index("ix_plans_project_id", table_name="plans")
    op.drop_table("plans")

    op.drop_table("project_iterations")

    op.drop_index("ix_projects_root_path", table_name="projects")
    op.drop_index("ix_projects_slug", table_name="projects")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
