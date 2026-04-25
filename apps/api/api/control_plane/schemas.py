from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from api.contracts import (
    ITERATIONS_SCHEMA_VERSION,
    PLAN_SUMMARY_SCHEMA_VERSION,
    PROJECTS_SCHEMA_VERSION,
)
from api.control_plane.models import (
    IterationStatus,
    MembershipStatus,
    PlanStatus,
    ProjectRole,
    ProjectStatus,
)


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    root_path: str = Field(min_length=1, max_length=1024)
    default_branch: str = Field(default="main", min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    root_path: str | None = Field(default=None, min_length=1, max_length=1024)
    default_branch: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    status: ProjectStatus | None = None


class MembershipCountSummaryModel(BaseModel):
    admin: int
    maintainer: int
    reviewer: int
    viewer: int


class ProjectListItemModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    root_path: str
    default_branch: str
    description: str | None
    status: ProjectStatus
    current_user_role: ProjectRole | None
    active_iteration_count: int
    active_plan_count: int
    created_at: datetime
    updated_at: datetime


class ProjectPaginationModel(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    sort_by: str
    sort_order: str
    status_filter: ProjectStatus | None


class ProjectListResponse(BaseModel):
    schema_version: str = PROJECTS_SCHEMA_VERSION
    items: list[ProjectListItemModel]
    pagination: ProjectPaginationModel


class ProjectDetailResponse(ProjectListItemModel):
    membership_counts: MembershipCountSummaryModel
    can_edit: bool
    can_archive: bool


class IterationRecordModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    sequence_number: int
    status: IterationStatus
    created_at: datetime
    updated_at: datetime


class IterationListResponse(BaseModel):
    schema_version: str = ITERATIONS_SCHEMA_VERSION
    items: list[IterationRecordModel]


class PlanSummaryByStatusModel(BaseModel):
    draft: int
    ready: int
    archived: int


class PlanSummaryRecordModel(BaseModel):
    id: str
    title: str
    status: PlanStatus
    iteration_id: str | None
    created_at: datetime
    updated_at: datetime


class PlanSummaryResponse(BaseModel):
    schema_version: str = PLAN_SUMMARY_SCHEMA_VERSION
    total_plans: int
    by_status: PlanSummaryByStatusModel
    latest_plan: PlanSummaryRecordModel | None


class SessionMembershipSummaryModel(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: ProjectRole
    status: MembershipStatus
    created_at: datetime
    updated_at: datetime
