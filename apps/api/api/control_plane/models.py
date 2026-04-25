from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.auth.models import generate_id
from api.database import Base, utcnow


class ProjectStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class IterationStatus(str, enum.Enum):
    planned = "planned"
    active = "active"
    completed = "completed"


class PlanStatus(str, enum.Enum):
    draft = "draft"
    ready = "ready"
    archived = "archived"


class ProjectRole(str, enum.Enum):
    admin = "admin"
    maintainer = "maintainer"
    reviewer = "reviewer"
    viewer = "viewer"


class MembershipStatus(str, enum.Enum):
    active = "active"
    invited = "invited"
    suspended = "suspended"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    root_path: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    default_branch: Mapped[str] = mapped_column(String(120), default="main")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False),
        default=ProjectStatus.active,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    iterations = relationship(
        "ProjectIteration", back_populates="project", cascade="all, delete-orphan"
    )
    plans = relationship("Plan", back_populates="project", cascade="all, delete-orphan")
    memberships = relationship(
        "ProjectMembership", back_populates="project", cascade="all, delete-orphan"
    )


class ProjectIteration(Base):
    __tablename__ = "project_iterations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(160))
    sequence_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[IterationStatus] = mapped_column(
        Enum(IterationStatus, native_enum=False),
        default=IterationStatus.planned,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    project = relationship("Project", back_populates="iterations")
    plans = relationship("Plan", back_populates="iteration")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    iteration_id: Mapped[str | None] = mapped_column(
        ForeignKey("project_iterations.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(160))
    status: Mapped[PlanStatus] = mapped_column(
        Enum(PlanStatus, native_enum=False),
        default=PlanStatus.draft,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    project = relationship("Project", back_populates="plans")
    iteration = relationship("ProjectIteration", back_populates="plans")


class ProjectMembership(Base):
    __tablename__ = "project_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[ProjectRole] = mapped_column(Enum(ProjectRole, native_enum=False))
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, native_enum=False),
        default=MembershipStatus.active,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    project = relationship("Project", back_populates="memberships")
    user = relationship("User", back_populates="memberships")
