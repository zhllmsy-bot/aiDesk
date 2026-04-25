from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from api.contracts import AUTH_SCHEMA_VERSION
from api.control_plane.models import MembershipStatus, ProjectRole


class RegisterUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    display_name: str = Field(min_length=1, max_length=120)


class CreateSessionRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class AuthenticatedUserModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    is_platform_admin: bool
    created_at: datetime
    updated_at: datetime


class SessionRecordModel(BaseModel):
    id: str
    expires_at: datetime
    token: str


class SessionMembershipModel(BaseModel):
    project_id: str
    project_name: str
    role: ProjectRole
    status: MembershipStatus


class SessionContextResponse(BaseModel):
    schema_version: str = AUTH_SCHEMA_VERSION
    session: SessionRecordModel
    user: AuthenticatedUserModel
    memberships: list[SessionMembershipModel]
