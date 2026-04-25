from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from api.auth.models import User
from api.control_plane.models import (
    IterationStatus,
    MembershipStatus,
    Plan,
    PlanStatus,
    Project,
    ProjectIteration,
    ProjectMembership,
    ProjectRole,
    ProjectStatus,
)


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_project(self, project: Project) -> None:
        self.session.add(project)

    def add_membership(self, membership: ProjectMembership) -> None:
        self.session.add(membership)

    def get_project_by_id(self, project_id: str) -> Project | None:
        return self.session.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()

    def get_project_by_slug(self, slug: str) -> Project | None:
        return self.session.execute(
            select(Project).where(Project.slug == slug)
        ).scalar_one_or_none()

    def get_project_by_root_path(self, root_path: str) -> Project | None:
        return self.session.execute(
            select(Project).where(Project.root_path == root_path)
        ).scalar_one_or_none()

    def get_membership_for_user(self, project_id: str, user_id: str) -> ProjectMembership | None:
        statement = select(ProjectMembership).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user_id,
            ProjectMembership.status == MembershipStatus.active,
        )
        return self.session.execute(statement).scalar_one_or_none()

    def list_projects(
        self,
        *,
        user: User,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        status_filter: ProjectStatus | None,
    ) -> tuple[Sequence[tuple[Project, ProjectRole | None, int, int]], int]:
        project_rows: list[tuple[Project, ProjectRole | None, int, int]] = []
        membership_alias = aliased(ProjectMembership)

        active_iteration_counts = (
            select(
                ProjectIteration.project_id.label("project_id"),
                func.count(ProjectIteration.id).label("active_iteration_count"),
            )
            .where(ProjectIteration.status == IterationStatus.active)
            .group_by(ProjectIteration.project_id)
            .subquery()
        )

        active_plan_counts = (
            select(
                Plan.project_id.label("project_id"),
                func.count(Plan.id).label("active_plan_count"),
            )
            .where(Plan.status != PlanStatus.archived)
            .group_by(Plan.project_id)
            .subquery()
        )

        statement = (
            select(
                Project,
                membership_alias.role,
                func.coalesce(active_iteration_counts.c.active_iteration_count, 0),
                func.coalesce(active_plan_counts.c.active_plan_count, 0),
            )
            .outerjoin(
                active_iteration_counts,
                active_iteration_counts.c.project_id == Project.id,
            )
            .outerjoin(
                active_plan_counts,
                active_plan_counts.c.project_id == Project.id,
            )
        )

        count_statement = select(func.count(Project.id))

        if user.is_platform_admin:
            statement = statement.outerjoin(
                membership_alias,
                (membership_alias.project_id == Project.id)
                & (membership_alias.user_id == user.id)
                & (membership_alias.status == MembershipStatus.active),
            )
        else:
            statement = statement.join(
                membership_alias,
                (membership_alias.project_id == Project.id)
                & (membership_alias.user_id == user.id)
                & (membership_alias.status == MembershipStatus.active),
            )
            count_statement = count_statement.join(
                membership_alias,
                (membership_alias.project_id == Project.id)
                & (membership_alias.user_id == user.id)
                & (membership_alias.status == MembershipStatus.active),
            )

        if status_filter is not None:
            statement = statement.where(Project.status == status_filter)
            count_statement = count_statement.where(Project.status == status_filter)

        sort_mapping = {
            "created_at": Project.created_at,
            "updated_at": Project.updated_at,
            "name": Project.name,
        }
        sort_column = sort_mapping[sort_by]
        ordered = sort_column.asc() if sort_order == "asc" else sort_column.desc()

        statement = (
            statement.order_by(ordered, Project.id.asc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )

        rows = self.session.execute(statement).all()
        for project, role, active_iteration_count, active_plan_count in rows:
            project_rows.append(
                (
                    project,
                    role,
                    cast(int, active_iteration_count),
                    cast(int, active_plan_count),
                )
            )
        total_items = self.session.execute(count_statement).scalar_one()
        return project_rows, total_items

    def membership_counts(self, project_id: str) -> dict[ProjectRole, int]:
        statement = (
            select(ProjectMembership.role, func.count(ProjectMembership.id))
            .where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.status == MembershipStatus.active,
            )
            .group_by(ProjectMembership.role)
        )
        rows = self.session.execute(statement).all()
        pairs: list[tuple[ProjectRole, int]] = [(role, count) for role, count in rows]
        return dict(pairs)

    def list_iterations(self, project_id: str) -> Sequence[ProjectIteration]:
        statement = (
            select(ProjectIteration)
            .where(ProjectIteration.project_id == project_id)
            .order_by(ProjectIteration.sequence_number.asc(), ProjectIteration.created_at.asc())
        )
        return self.session.execute(statement).scalars().all()

    def get_plan_summary(self, project_id: str) -> tuple[dict[PlanStatus, int], Plan | None]:
        count_statement = (
            select(Plan.status, func.count(Plan.id))
            .where(Plan.project_id == project_id)
            .group_by(Plan.status)
        )
        count_rows = self.session.execute(count_statement).all()
        pairs: list[tuple[PlanStatus, int]] = [(status, count) for status, count in count_rows]
        counts = dict(pairs)
        latest_plan = self.session.execute(
            select(Plan)
            .where(Plan.project_id == project_id)
            .order_by(Plan.updated_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        return counts, latest_plan
