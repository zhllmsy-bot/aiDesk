from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from temporalio.client import Client

from api.control_plane.models import Project
from api.events.builder import RuntimeEventBuilder
from api.events.models import (
    AttemptHistoryReadModel,
    TaskGraphReadModel,
    TimelineReadModel,
    WorkerHealthReadModel,
)
from api.runtime_contracts import EventType, TaskStatus, WorkflowName
from api.workflows.approval_bridge import signal_runtime_approval
from api.workflows.definitions.project_audit import resolve_project_audit_tasks
from api.workflows.definitions.project_import import resolve_project_import_tasks
from api.workflows.definitions.project_improvement import resolve_project_improvement_tasks
from api.workflows.definitions.project_planning import resolve_project_planning_tasks
from api.workflows.definitions.task_execution import resolve_task_execution_tasks
from api.workflows.dependencies import RuntimeContainer
from api.workflows.recovery import recover_stale_claims
from api.workflows.types import WorkflowRequest

router = APIRouter(prefix="/runtime", tags=["runtime"])


def get_runtime_container(request: Request) -> RuntimeContainer:
    return request.app.state.runtime_container


async def _temporal_client(request: Request) -> Client:
    settings = request.app.state.settings
    return await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        identity=f"{settings.runtime_worker_id}-control-plane",
    )


def _resolve_workflow_tasks(workflow_name: WorkflowName, payload: WorkflowRequest) -> None:
    if payload.tasks:
        return
    if workflow_name == WorkflowName.PROJECT_AUDIT:
        payload.tasks = resolve_project_audit_tasks(payload)
        return
    if workflow_name == WorkflowName.PROJECT_IMPORT:
        payload.tasks = resolve_project_import_tasks(payload)
        return
    if workflow_name == WorkflowName.PROJECT_PLANNING:
        payload.tasks = resolve_project_planning_tasks(payload)
        return
    if workflow_name == WorkflowName.TASK_EXECUTION:
        payload.tasks = resolve_task_execution_tasks(payload)
        return
    if workflow_name == WorkflowName.PROJECT_IMPROVEMENT:
        payload.tasks = resolve_project_improvement_tasks(payload)
        return


def _normalize_runtime_workspace_metadata(payload: WorkflowRequest, request: Request) -> None:
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        project = session.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project_id not found")

    metadata = payload.metadata
    raw_root = metadata.get("workspace_root_path")
    if not isinstance(raw_root, str) or not raw_root.strip():
        metadata["workspace_root_path"] = project.root_path
        raw_root = project.root_path

    root = Path(str(raw_root)).expanduser()
    if not root.is_absolute():
        raise HTTPException(status_code=422, detail="metadata.workspace_root_path must be absolute")
    if not root.exists() or not root.is_dir():
        raise HTTPException(
            status_code=422,
            detail=f"metadata.workspace_root_path does not exist: {root}",
        )
    resolved_root = str(root.resolve())
    metadata["workspace_root_path"] = resolved_root

    writable = metadata.get("workspace_writable_paths")
    if not isinstance(writable, list) or not writable:
        metadata["workspace_writable_paths"] = [resolved_root]

    allowlist = metadata.get("workspace_allowlist")
    if not isinstance(allowlist, list) or not allowlist:
        metadata["workspace_allowlist"] = [resolved_root]
    else:
        normalized_allowlist = [str(Path(str(item)).expanduser()) for item in allowlist]
        if resolved_root not in normalized_allowlist:
            normalized_allowlist.append(resolved_root)
        metadata["workspace_allowlist"] = normalized_allowlist


@router.post(
    "/dev/bootstrap",
    status_code=status.HTTP_202_ACCEPTED,
    deprecated=True,
    summary="DEV ONLY: bootstrap runtime fixtures",
)
def bootstrap_runtime_dev(
    request: Request,
    response: Response,
    workflow_name: Annotated[WorkflowName, Query()],
    include_retry: Annotated[bool, Query()] = False,
    include_interrupt: Annotated[bool, Query()] = False,
) -> dict[str, str]:
    container = get_runtime_container(request)
    workflow_run_id = f"run-{uuid4().hex[:8]}"
    trace_id = f"trace-{uuid4().hex[:8]}"
    task_id = "task-1"
    attempt_id = "attempt-1"
    builder = RuntimeEventBuilder(producer="runtime.dev.bootstrap")

    container.persistence.ensure_workflow_run(
        workflow_run_id=workflow_run_id,
        project_id=None,
        iteration_id=None,
        workflow_name=workflow_name.value,
        trace_id=trace_id,
        initiated_by="runtime.dev.bootstrap",
        objective=f"{workflow_name.value} bootstrap",
    )
    container.persistence.ensure_task(
        workflow_run_id=workflow_run_id,
        task_id=task_id,
        title="Task 1",
        graph_kind="planner",
        executor_summary="planner",
    )
    container.persistence.ensure_attempt(
        workflow_run_id=workflow_run_id,
        task_id=task_id,
        attempt_id=attempt_id,
        status=TaskStatus.CLAIMED.value,
    )

    def emit(
        event_type: EventType, payload: dict[str, object], *, task_scoped: bool = True
    ) -> None:
        event = builder.build(
            event_type=event_type,
            sequence=container.event_store.next_sequence(workflow_run_id),
            correlation={
                "workflow_run_id": workflow_run_id,
                "trace_id": trace_id,
                "workflow_id": workflow_run_id,
                "task_id": task_id if task_scoped else None,
                "attempt_id": attempt_id if task_scoped else None,
            },
            payload=payload,
            occurred_at=datetime.now(UTC),
        )
        container.event_store.append(event)

    emit(
        EventType.WORKFLOW_STARTED,
        {"workflow_name": workflow_name.value, "summary": f"{workflow_name.value} started"},
        task_scoped=False,
    )
    emit(EventType.TASK_CLAIMED, {"to_status": TaskStatus.CLAIMED.value, "summary": "claimed"})
    emit(
        EventType.TASK_GRAPH_UPDATED,
        {
            "nodes": [
                {
                    "task_id": task_id,
                    "title": "Task 1",
                    "status": TaskStatus.CLAIMED.value,
                    "blocked_reason": None,
                    "executor_summary": "planner",
                }
            ],
            "edges": [],
            "summary": "graph updated",
        },
    )
    emit(EventType.TASK_RUNNING, {"to_status": TaskStatus.RUNNING.value, "summary": "running"})
    if include_retry:
        emit(EventType.WORKFLOW_RETRYING, {"summary": "workflow retrying"}, task_scoped=False)
    if include_interrupt:
        emit(EventType.RUNTIME_GRAPH_INTERRUPTED, {"summary": "graph interrupted"})
    emit(
        EventType.TASK_COMPLETED, {"to_status": TaskStatus.COMPLETED.value, "summary": "completed"}
    )
    emit(
        EventType.WORKFLOW_COMPLETED,
        {"summary": f"{workflow_name.value} completed"},
        task_scoped=False,
    )
    worker_event = builder.build(
        event_type=EventType.WORKER_HEALTH_REPORTED,
        sequence=container.event_store.next_sequence(f"worker-health::{container.worker_id}"),
        correlation={
            "workflow_run_id": f"worker-health::{container.worker_id}",
            "trace_id": f"trace::{container.worker_id}",
        },
        payload={
            "worker_id": container.worker_id,
            "task_queue": container.task_queue,
            "status": "healthy",
            "detail": "worker alive",
            "active_workflow_names": [workflow_name.value],
        },
        occurred_at=datetime.now(UTC),
    )
    container.event_store.append(worker_event)
    response.status_code = status.HTTP_202_ACCEPTED
    return {"workflow_run_id": workflow_run_id}


@router.post(
    "/runs/start",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Production entry: start a runtime workflow via Temporal",
)
async def start_runtime_workflow(
    payload: WorkflowRequest,
    request: Request,
) -> dict[str, str]:
    container = get_runtime_container(request)
    workflow_name_raw = payload.metadata.get("workflow_name")
    if not isinstance(workflow_name_raw, str):
        raise HTTPException(status_code=422, detail="metadata.workflow_name is required")
    workflow_name = WorkflowName(workflow_name_raw)
    _resolve_workflow_tasks(workflow_name, payload)
    _normalize_runtime_workspace_metadata(payload, request)

    client = await _temporal_client(request)
    workflow_id = f"{workflow_name.value}:{payload.workflow_run_id}"
    container.persistence.ensure_workflow_run(
        workflow_run_id=payload.workflow_run_id,
        project_id=payload.project_id,
        iteration_id=str(payload.metadata.get("iteration_id"))
        if payload.metadata.get("iteration_id")
        else None,
        workflow_name=workflow_name.value,
        trace_id=payload.trace_id,
        initiated_by=payload.initiated_by,
        objective=payload.objective,
        temporal_workflow_id=workflow_id,
        metadata=payload.metadata,
    )
    # Task IDs are global primary keys in runtime persistence. Prefix with run_id
    # so repeated workflow templates across runs do not overwrite previous rows.
    # Keep raw ids in metadata for API/UI readability.
    if payload.tasks:
        for task in payload.tasks:
            original_task_id = task.task_id
            task.task_id = f"{payload.workflow_run_id}::{original_task_id}"
            task.depends_on = [
                f"{payload.workflow_run_id}::{dependency}" for dependency in task.depends_on
            ]
            payload.metadata.setdefault("task_id_aliases", {})
            aliases = payload.metadata["task_id_aliases"]
            if isinstance(aliases, dict):
                aliases[task.task_id] = original_task_id
                aliases[original_task_id] = task.task_id

    for task in payload.tasks:
        container.persistence.ensure_task(
            workflow_run_id=payload.workflow_run_id,
            task_id=task.task_id,
            title=task.title,
            graph_kind=task.graph_kind,
            executor=task.executor_name,
            executor_summary=task.executor_summary,
            depends_on=task.depends_on,
            metadata={"requires_approval": task.requires_approval},
        )

    try:
        handle = await client.start_workflow(
            workflow_name.value,
            payload,
            id=workflow_id,
            task_queue=container.runtime_task_queue,
            run_timeout=timedelta(seconds=max(payload.signal_timeout_seconds, 600)),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Temporal start failed: {exc}") from exc

    container.persistence.ensure_workflow_run(
        workflow_run_id=payload.workflow_run_id,
        project_id=payload.project_id,
        iteration_id=str(payload.metadata.get("iteration_id"))
        if payload.metadata.get("iteration_id")
        else None,
        workflow_name=workflow_name.value,
        trace_id=payload.trace_id,
        initiated_by=payload.initiated_by,
        objective=payload.objective,
        temporal_workflow_id=handle.id,
        temporal_run_id=handle.run_id,
        metadata=payload.metadata,
    )
    return {"workflow_run_id": payload.workflow_run_id, "temporal_workflow_id": handle.id}


@router.post("/runs/{workflow_run_id}/approval", status_code=status.HTTP_202_ACCEPTED)
async def resolve_runtime_approval(
    workflow_run_id: str,
    approved: Annotated[bool, Query()],
    actor: Annotated[str, Query(min_length=1)],
    comment: Annotated[str | None, Query()] = None,
    approval_id: Annotated[str | None, Query()] = None,
    request: Request = None,  # type: ignore[assignment]
) -> dict[str, str]:
    assert request is not None
    settings = request.app.state.settings
    session_factory = request.app.state.session_factory
    try:
        signaled = await signal_runtime_approval(
            settings=settings,
            session_factory=session_factory,
            workflow_run_id=workflow_run_id,
            approved=approved,
            actor=actor,
            comment=comment,
            approval_id=approval_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"approval signal failed: {exc}") from exc
    if not signaled:
        raise HTTPException(status_code=404, detail="workflow handle not found")
    return {"workflow_run_id": workflow_run_id, "status": "signaled"}


@router.get("/runs/{workflow_run_id}/timeline", response_model=TimelineReadModel)
def get_runtime_timeline(workflow_run_id: str, request: Request) -> TimelineReadModel:
    return get_runtime_container(request).event_store.get_timeline(workflow_run_id)


@router.get("/runs/{workflow_run_id}/graph", response_model=TaskGraphReadModel)
def get_runtime_graph(workflow_run_id: str, request: Request) -> TaskGraphReadModel:
    return get_runtime_container(request).event_store.get_graph(workflow_run_id)


@router.get("/tasks/{task_id}/attempts", response_model=AttemptHistoryReadModel)
def list_runtime_attempts(task_id: str, request: Request) -> AttemptHistoryReadModel:
    return get_runtime_container(request).event_store.get_attempts(task_id)


@router.get("/workers/health", response_model=list[WorkerHealthReadModel])
def worker_health(request: Request) -> list[WorkerHealthReadModel]:
    return get_runtime_container(request).event_store.get_workers_health()


@router.post("/recovery/reclaim-stale")
def reclaim_stale_claims_endpoint(request: Request) -> dict[str, Any]:
    results = recover_stale_claims()
    return {
        "reclaimed_count": len(results),
        "results": [
            {
                "claim_id": r.claim_id,
                "task_id": r.task_id,
                "workflow_run_id": r.workflow_run_id,
                "decision": r.decision.value,
                "detail": r.detail,
            }
            for r in results
        ],
    }


@router.post("/recovery/reconcile-terminal")
def reconcile_terminal_runs_endpoint(request: Request) -> dict[str, Any]:
    container = get_runtime_container(request)
    summary = container.persistence.reconcile_terminal_runs()
    return summary
