from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from api.auth.models import User
from api.control_plane.dependencies import get_current_user
from api.control_plane.models import ProjectStatus
from api.control_plane.schemas import (
    CreateProjectRequest,
    IterationListResponse,
    PlanSummaryResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    UpdateProjectRequest,
)
from api.control_plane.service import ProjectService
from api.database import get_db_session

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProjectService:
    return ProjectService(session=session, current_user=current_user)


@router.post("", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: CreateProjectRequest,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectDetailResponse:
    return service.create_project(payload)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    service: Annotated[ProjectService, Depends(get_project_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort_by: Annotated[str, Query(pattern="^(created_at|updated_at|name)$")] = "updated_at",
    sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    status_filter: Annotated[ProjectStatus | None, Query(alias="status")] = None,
) -> ProjectListResponse:
    return service.list_projects(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        status_filter=status_filter,
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectDetailResponse:
    return service.get_project_detail(project_id)


@router.patch("/{project_id}", response_model=ProjectDetailResponse)
def update_project(
    project_id: str,
    payload: UpdateProjectRequest,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectDetailResponse:
    return service.update_project(project_id, payload)


@router.post("/{project_id}/archive", response_model=ProjectDetailResponse)
def archive_project(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectDetailResponse:
    return service.archive_project(project_id)


@router.get("/{project_id}/iterations", response_model=IterationListResponse)
def list_iterations(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> IterationListResponse:
    return service.list_iterations(project_id)


@router.get("/{project_id}/plan-summary", response_model=PlanSummaryResponse)
def get_plan_summary(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> PlanSummaryResponse:
    return service.get_plan_summary(project_id)
