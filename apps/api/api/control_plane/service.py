from __future__ import annotations

import math
import re
from pathlib import Path

from sqlalchemy.orm import Session

from api.auth.models import User
from api.control_plane.models import (
    MembershipStatus,
    PlanStatus,
    Project,
    ProjectMembership,
    ProjectRole,
    ProjectStatus,
)
from api.control_plane.repository import ProjectRepository
from api.control_plane.schemas import (
    CreateProjectRequest,
    IterationListResponse,
    IterationRecordModel,
    MembershipCountSummaryModel,
    PlanSummaryByStatusModel,
    PlanSummaryRecordModel,
    PlanSummaryResponse,
    ProjectDetailResponse,
    ProjectListItemModel,
    ProjectListResponse,
    ProjectPaginationModel,
    UpdateProjectRequest,
)
from api.errors import bad_request, conflict, forbidden, not_found

ROLE_LEVELS = {
    ProjectRole.viewer: 0,
    ProjectRole.reviewer: 1,
    ProjectRole.maintainer: 2,
    ProjectRole.admin: 3,
}


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if normalized:
        return normalized
    return "project"


class ProjectService:
    def __init__(self, session: Session, current_user: User) -> None:
        self.session = session
        self.current_user = current_user
        self.repository = ProjectRepository(session)

    def create_project(self, payload: CreateProjectRequest) -> ProjectDetailResponse:
        root_path = self._validate_root_path(payload.root_path)
        slug = slugify(payload.name)

        if self.repository.get_project_by_root_path(root_path) is not None:
            raise conflict("A project with that root path already exists.")

        if self.repository.get_project_by_slug(slug) is not None:
            raise conflict("A project with that name already exists.")

        project = Project(
            name=payload.name,
            slug=slug,
            root_path=root_path,
            default_branch=payload.default_branch,
            description=payload.description,
            status=ProjectStatus.active,
        )
        membership = ProjectMembership(
            project=project,
            user_id=self.current_user.id,
            role=ProjectRole.admin,
            status=MembershipStatus.active,
        )
        self.repository.add_project(project)
        self.repository.add_membership(membership)
        self.session.commit()
        self.session.refresh(project)
        return self.get_project_detail(project.id)

    def list_projects(
        self,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        status_filter: ProjectStatus | None,
    ) -> ProjectListResponse:
        rows, total_items = self.repository.list_projects(
            user=self.current_user,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            status_filter=status_filter,
        )
        items = [
            ProjectListItemModel(
                id=project.id,
                name=project.name,
                slug=project.slug,
                root_path=project.root_path,
                default_branch=project.default_branch,
                description=project.description,
                status=project.status,
                current_user_role=role,
                active_iteration_count=active_iteration_count,
                active_plan_count=active_plan_count,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
            for project, role, active_iteration_count, active_plan_count in rows
        ]
        total_pages = max(1, math.ceil(total_items / page_size)) if total_items else 1
        return ProjectListResponse(
            items=items,
            pagination=ProjectPaginationModel(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                sort_by=sort_by,
                sort_order=sort_order,
                status_filter=status_filter,
            ),
        )

    def get_project_detail(self, project_id: str) -> ProjectDetailResponse:
        project = self.repository.get_project_by_id(project_id)
        if project is None:
            raise not_found("Project not found.")

        role = self._require_project_access(project_id, minimum_role=ProjectRole.viewer)
        counts = self.repository.membership_counts(project_id)
        active_iteration_count = sum(
            1 for iteration in project.iterations if iteration.status.value == "active"
        )
        active_plan_count = sum(1 for plan in project.plans if plan.status != PlanStatus.archived)
        return ProjectDetailResponse(
            id=project.id,
            name=project.name,
            slug=project.slug,
            root_path=project.root_path,
            default_branch=project.default_branch,
            description=project.description,
            status=project.status,
            current_user_role=role,
            active_iteration_count=active_iteration_count,
            active_plan_count=active_plan_count,
            created_at=project.created_at,
            updated_at=project.updated_at,
            membership_counts=MembershipCountSummaryModel(
                admin=counts.get(ProjectRole.admin, 0),
                maintainer=counts.get(ProjectRole.maintainer, 0),
                reviewer=counts.get(ProjectRole.reviewer, 0),
                viewer=counts.get(ProjectRole.viewer, 0),
            ),
            can_edit=self._has_role(role, ProjectRole.maintainer),
            can_archive=self._has_role(role, ProjectRole.admin),
        )

    def update_project(
        self, project_id: str, payload: UpdateProjectRequest
    ) -> ProjectDetailResponse:
        project = self.repository.get_project_by_id(project_id)
        if project is None:
            raise not_found("Project not found.")

        self._require_project_access(project_id, minimum_role=ProjectRole.maintainer)

        if payload.name is not None and payload.name != project.name:
            next_slug = slugify(payload.name)
            existing = self.repository.get_project_by_slug(next_slug)
            if existing is not None and existing.id != project_id:
                raise conflict("A project with that name already exists.")
            project.name = payload.name
            project.slug = next_slug

        if payload.root_path is not None and payload.root_path != project.root_path:
            root_path = self._validate_root_path(payload.root_path)
            existing = self.repository.get_project_by_root_path(root_path)
            if existing is not None and existing.id != project_id:
                raise conflict("A project with that root path already exists.")
            project.root_path = root_path

        if payload.default_branch is not None:
            project.default_branch = payload.default_branch

        if "description" in payload.model_fields_set:
            project.description = payload.description

        if payload.status is not None:
            project.status = payload.status

        self.session.commit()
        self.session.refresh(project)
        return self.get_project_detail(project_id)

    def archive_project(self, project_id: str) -> ProjectDetailResponse:
        project = self.repository.get_project_by_id(project_id)
        if project is None:
            raise not_found("Project not found.")

        self._require_project_access(project_id, minimum_role=ProjectRole.admin)
        project.status = ProjectStatus.archived
        self.session.commit()
        self.session.refresh(project)
        return self.get_project_detail(project_id)

    def list_iterations(self, project_id: str) -> IterationListResponse:
        self._require_project_access(project_id, minimum_role=ProjectRole.viewer)
        iterations = self.repository.list_iterations(project_id)
        return IterationListResponse(
            items=[IterationRecordModel.model_validate(iteration) for iteration in iterations]
        )

    def get_plan_summary(self, project_id: str) -> PlanSummaryResponse:
        self._require_project_access(project_id, minimum_role=ProjectRole.viewer)
        counts, latest_plan = self.repository.get_plan_summary(project_id)
        return PlanSummaryResponse(
            total_plans=sum(counts.values()),
            by_status=PlanSummaryByStatusModel(
                draft=counts.get(PlanStatus.draft, 0),
                ready=counts.get(PlanStatus.ready, 0),
                archived=counts.get(PlanStatus.archived, 0),
            ),
            latest_plan=(
                PlanSummaryRecordModel(
                    id=latest_plan.id,
                    title=latest_plan.title,
                    status=latest_plan.status,
                    iteration_id=latest_plan.iteration_id,
                    created_at=latest_plan.created_at,
                    updated_at=latest_plan.updated_at,
                )
                if latest_plan is not None
                else None
            ),
        )

    def _validate_root_path(self, raw_path: str) -> str:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            raise bad_request("Project root_path must be an absolute path.")
        if not path.exists():
            raise bad_request("Project root_path does not exist.")
        if not path.is_dir():
            raise bad_request("Project root_path must point to a directory.")
        return str(path.resolve())

    def _require_project_access(
        self, project_id: str, minimum_role: ProjectRole
    ) -> ProjectRole | None:
        if self.current_user.is_platform_admin:
            return ProjectRole.admin

        membership = self.repository.get_membership_for_user(project_id, self.current_user.id)
        if membership is None:
            raise forbidden("You do not have access to this project.")

        if not self._has_role(membership.role, minimum_role):
            raise forbidden("You do not have the required role for this action.")
        return membership.role

    def _has_role(self, current_role: ProjectRole | None, minimum_role: ProjectRole) -> bool:
        if current_role is None:
            return False
        return ROLE_LEVELS[current_role] >= ROLE_LEVELS[minimum_role]
