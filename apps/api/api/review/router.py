from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.auth.models import User
from api.control_plane.dependencies import get_current_user
from api.errors import not_found
from api.executors.contracts import (
    ApprovalDetailView,
    ApprovalListResponse,
    ApprovalResolutionPayload,
    ApprovalStatus,
    ArtifactListResponse,
    ArtifactView,
    AttemptListResponse,
    EvidenceSummaryView,
    ExecutorAttemptView,
    map_approval_detail,
    map_approval_summary,
    map_artifact_view,
    map_attempt_view,
    map_evidence_summary_view,
)
from api.executors.dependencies import ExecutionContainer, get_execution_container
from api.workflows.approval_bridge import signal_runtime_approval

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/approvals", response_model=ApprovalListResponse)
def list_approvals(
    _: Annotated[User, Depends(get_current_user)],
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
) -> ApprovalListResponse:
    items = [map_approval_summary(record) for record in container.approvals.list_approvals()]
    return ApprovalListResponse(items=items)


@router.get("/approvals/{approval_id}", response_model=ApprovalDetailView)
def get_approval_detail(
    approval_id: str,
    _: Annotated[User, Depends(get_current_user)],
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
) -> ApprovalDetailView:
    try:
        record = container.approvals.get_approval(approval_id)
    except KeyError as exc:
        raise not_found(str(exc)) from exc
    related_artifacts = [
        artifact.artifact_id
        for artifact in container.artifacts.list_artifacts(
            project_id=record.project_id,
            run_id=record.run_id,
            task_id=record.task_id,
        )
    ]
    return map_approval_detail(record, related_artifacts)


@router.post("/approvals/{approval_id}/resolve", response_model=ApprovalDetailView)
async def resolve_approval(
    approval_id: str,
    payload: ApprovalResolutionPayload,
    current_user: Annotated[User, Depends(get_current_user)],
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
    request: Request,
) -> ApprovalDetailView:
    try:
        record = container.approvals.resolve_approval(
            approval_id,
            resolved_by=current_user.email,
            payload=payload,
        )
    except KeyError as exc:
        raise not_found(str(exc)) from exc
    settings = request.app.state.settings
    session_factory = request.app.state.session_factory
    try:
        await signal_runtime_approval(
            settings=settings,
            session_factory=session_factory,
            workflow_run_id=record.run_id,
            approved=payload.decision == ApprovalStatus.APPROVED,
            actor=current_user.email,
            comment=payload.reason,
            approval_id=approval_id,
            approved_write_paths=payload.approved_write_paths,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"runtime approval signal failed: {exc}",
        ) from exc
    related_artifacts = [
        artifact.artifact_id
        for artifact in container.artifacts.list_artifacts(
            project_id=record.project_id,
            run_id=record.run_id,
            task_id=record.task_id,
        )
    ]
    return map_approval_detail(record, related_artifacts)


@router.get("/artifacts", response_model=ArtifactListResponse)
def list_artifacts(
    _: Annotated[User, Depends(get_current_user)],
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
    project_id: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
) -> ArtifactListResponse:
    records = container.artifacts.list_artifacts(
        project_id=project_id, run_id=run_id, task_id=task_id
    )
    return ArtifactListResponse(items=[map_artifact_view(record) for record in records])


@router.get("/artifacts/{artifact_id}", response_model=ArtifactView)
def get_artifact_detail(
    artifact_id: str,
    _: Annotated[User, Depends(get_current_user)],
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
) -> ArtifactView:
    try:
        record = container.artifacts.get_artifact(artifact_id)
    except KeyError as exc:
        raise not_found(str(exc)) from exc
    return map_artifact_view(record)


@router.get("/evidence/{attempt_id}", response_model=EvidenceSummaryView)
def get_evidence_summary(
    attempt_id: str,
    _: Annotated[User, Depends(get_current_user)],
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
) -> EvidenceSummaryView:
    try:
        summary = container.evidence.get_summary(attempt_id)
    except KeyError as exc:
        raise not_found(str(exc)) from exc
    return map_evidence_summary_view(summary)


@router.get("/attempts", response_model=AttemptListResponse)
def list_attempts(
    _: Annotated[User, Depends(get_current_user)],
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
    project_id: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
) -> AttemptListResponse:
    attempts = container.attempts.list_attempts(
        project_id=project_id, run_id=run_id, task_id=task_id
    )
    items: list[ExecutorAttemptView] = []
    for attempt in attempts:
        try:
            evidence = container.evidence.get_summary(attempt.attempt_id)
        except KeyError:
            evidence = None
        items.append(map_attempt_view(attempt, evidence))
    return AttemptListResponse(items=items)


@router.get("/attempts/{attempt_id}", response_model=ExecutorAttemptView)
def get_attempt_detail(
    attempt_id: str,
    _: Annotated[User, Depends(get_current_user)],
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
) -> ExecutorAttemptView:
    try:
        attempt = container.attempts.get_attempt(attempt_id)
    except KeyError as exc:
        raise not_found(str(exc)) from exc
    try:
        evidence = container.evidence.get_summary(attempt_id)
    except KeyError:
        evidence = None
    return map_attempt_view(attempt, evidence)
