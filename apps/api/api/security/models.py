from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.auth.models import generate_id
from api.database import Base, utcnow


class SecretScopeDB(str, enum.Enum):
    project = "project"
    global_scope = "global"


class AuditEventTypeDB(str, enum.Enum):
    secret_resolve = "secret_resolve"
    approval_gate_hit = "approval_gate_hit"
    blocked_command = "blocked_command"
    write_execution_grant = "write_execution_grant"
    workspace_isolation_violation = "workspace_isolation_violation"
    provenance_integrity_failure = "provenance_integrity_failure"


class SecretRecord(Base):
    __tablename__ = "secrets"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    scope: Mapped[SecretScopeDB] = mapped_column(
        Enum(SecretScopeDB, native_enum=False),
        default=SecretScopeDB.project,
        index=True,
    )
    encrypted_value: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_by: Mapped[str] = mapped_column(String(120))
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    event_type: Mapped[AuditEventTypeDB] = mapped_column(
        Enum(AuditEventTypeDB, native_enum=False),
        index=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor: Mapped[str] = mapped_column(String(120), index=True)
    resource_kind: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
