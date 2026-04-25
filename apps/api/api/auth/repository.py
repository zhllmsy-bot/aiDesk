from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from api.auth.models import ApiSession, User
from api.control_plane.models import MembershipStatus, Project, ProjectMembership


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def count_users(self) -> int:
        return self.session.query(User).count()

    def get_user_by_email(self, email: str) -> User | None:
        return self.session.execute(
            select(User).where(User.email == email.lower())
        ).scalar_one_or_none()

    def add_user(self, user: User) -> None:
        self.session.add(user)

    def add_api_session(self, api_session: ApiSession) -> None:
        self.session.add(api_session)

    def get_api_session_by_token_hash(self, token_hash: str) -> ApiSession | None:
        statement = select(ApiSession).where(ApiSession.token_hash == token_hash).options()
        return self.session.execute(statement).scalar_one_or_none()

    def list_active_memberships_for_user(
        self, user_id: str
    ) -> Sequence[tuple[ProjectMembership, Project]]:
        statement: Select[tuple[ProjectMembership, Project]] = (
            select(ProjectMembership, Project)
            .join(Project, Project.id == ProjectMembership.project_id)
            .where(
                ProjectMembership.user_id == user_id,
                ProjectMembership.status == MembershipStatus.active,
            )
            .order_by(Project.name.asc())
        )
        rows: Sequence[Row[tuple[ProjectMembership, Project]]] = self.session.execute(
            statement
        ).all()
        return [(membership, project) for membership, project in rows]
