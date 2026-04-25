from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.events.builder import build_timeline_entry
from api.events.models import (
    AttemptHistoryReadModel,
    AttemptRecord,
    CorrelationIds,
    RunEventEnvelope,
    TaskGraphEdge,
    TaskGraphNode,
    TaskGraphReadModel,
    TaskTodoItem,
    TimelineReadModel,
    WorkerHealthReadModel,
)
from api.runtime_contracts import EventType, TaskStatus, WorkerHealthStatus, WorkflowName
from api.runtime_persistence.models import (
    RuntimeRunEvent,
    RuntimeTask,
    RuntimeTaskAttempt,
)


def _to_task_status(value: str | None) -> TaskStatus | None:
    if value is None:
        return None
    try:
        return TaskStatus(value)
    except ValueError:
        return None


def _status_from_event(event: RunEventEnvelope) -> TaskStatus | None:
    to_status = event.payload.get("to_status")
    if isinstance(to_status, str):
        return _to_task_status(to_status)
    fallback = {
        EventType.TASK_CLAIMED: TaskStatus.CLAIMED,
        EventType.TASK_RUNNING: TaskStatus.RUNNING,
        EventType.TASK_VERIFYING: TaskStatus.VERIFYING,
        EventType.TASK_COMPLETED: TaskStatus.COMPLETED,
        EventType.TASK_FAILED: TaskStatus.FAILED,
        EventType.TASK_RECLAIMED: TaskStatus.RECLAIMED,
    }
    return fallback.get(event.event_type)


TODO_STATUSES = {"queued", "running", "completed", "failed", "skipped"}


def _normalize_todo_items(raw_items: object) -> list[TaskTodoItem]:
    if not isinstance(raw_items, list):
        return []

    items: list[TaskTodoItem] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        item_id = str(raw_item.get("id") or "").strip()
        title = str(raw_item.get("title") or "").strip()
        if not item_id or not title:
            continue
        raw_status = str(raw_item.get("status") or "queued").strip()
        detail = raw_item.get("detail")
        items.append(
            TaskTodoItem(
                id=item_id,
                title=title,
                status=raw_status if raw_status in TODO_STATUSES else "queued",
                detail=str(detail) if detail is not None else None,
            )
        )
    return items


def _to_event_envelope(row: RuntimeRunEvent) -> RunEventEnvelope:
    return RunEventEnvelope(
        event_id=row.id,
        event_type=EventType(row.event_type),
        schema_version=row.schema_version,
        payload_version=row.payload_version,
        sequence=row.sequence,
        producer=row.producer,
        occurred_at=row.occurred_at.isoformat(),
        idempotency_key=row.idempotency_key,
        correlation=CorrelationIds(
            workflow_run_id=row.workflow_run_id,
            trace_id=row.trace_id,
            workflow_id=row.workflow_id,
            project_id=row.project_id,
            task_id=row.task_id,
            attempt_id=row.attempt_id,
        ),
        payload=dict(row.payload_json),
    )


def _list_run_events(
    session_factory: Callable[[], Session], workflow_run_id: str
) -> list[RunEventEnvelope]:
    with session_factory() as session:
        rows = session.scalars(
            select(RuntimeRunEvent)
            .where(RuntimeRunEvent.workflow_run_id == workflow_run_id)
            .order_by(RuntimeRunEvent.sequence.asc())
        ).all()
        return [_to_event_envelope(row) for row in rows]


@dataclass(slots=True)
class TimelineProjector:
    session_factory: Callable[[], Session]

    def project(self, workflow_run_id: str) -> TimelineReadModel:
        events = _list_run_events(self.session_factory, workflow_run_id)
        return TimelineReadModel(
            workflow_run_id=workflow_run_id,
            entries=[build_timeline_entry(event) for event in events],
        )


@dataclass(slots=True)
class TaskGraphProjector:
    session_factory: Callable[[], Session]

    def project(self, workflow_run_id: str) -> TaskGraphReadModel:
        events = _list_run_events(self.session_factory, workflow_run_id)
        graph = TaskGraphReadModel(workflow_run_id=workflow_run_id)
        latest_graph: TaskGraphReadModel | None = None
        for event in events:
            if event.event_type == EventType.TASK_GRAPH_UPDATED:
                latest_graph = TaskGraphReadModel(
                    workflow_run_id=workflow_run_id,
                    nodes=[
                        TaskGraphNode.model_validate(node)
                        for node in event.payload.get("nodes", [])
                    ],
                    edges=[
                        TaskGraphEdge.model_validate(edge)
                        for edge in event.payload.get("edges", [])
                    ],
                )
        if latest_graph is None:
            with self.session_factory() as session:
                tasks = session.scalars(
                    select(RuntimeTask)
                    .where(RuntimeTask.workflow_run_id == workflow_run_id)
                    .order_by(RuntimeTask.id.asc())
                ).all()
                if not tasks:
                    return graph
                nodes = [
                    TaskGraphNode(
                        task_id=task.id,
                        title=task.title,
                        status=_to_task_status(task.status.value),
                        blocked_reason=task.blocked_reason,
                        executor_summary=task.executor_summary,
                        todo_items=[],
                    )
                    for task in tasks
                ]
                edges = [
                    TaskGraphEdge(
                        source_task_id=dependency, target_task_id=task.id, kind="depends_on"
                    )
                    for task in tasks
                    for dependency in task.depends_on
                ]
                return TaskGraphReadModel(workflow_run_id=workflow_run_id, nodes=nodes, edges=edges)
            return graph

        for event in events:
            task_id = event.correlation.task_id
            if task_id is None:
                continue
            for node in latest_graph.nodes:
                if node.task_id != task_id:
                    continue
                status = _status_from_event(event)
                if status is not None:
                    node.status = status
                blocked_reason = event.payload.get("blocked_reason")
                if isinstance(blocked_reason, str):
                    node.blocked_reason = blocked_reason
                executor_summary = event.payload.get("executor_summary")
                if isinstance(executor_summary, str):
                    node.executor_summary = executor_summary
                if event.event_type == EventType.TASK_TODO_UPDATED:
                    todo_items = _normalize_todo_items(event.payload.get("todo_items"))
                    if todo_items:
                        node.todo_items = todo_items
        return latest_graph


@dataclass(slots=True)
class AttemptHistoryProjector:
    session_factory: Callable[[], Session]

    def project(self, task_id: str) -> AttemptHistoryReadModel:
        with self.session_factory() as session:
            attempts = session.scalars(
                select(RuntimeTaskAttempt)
                .where(RuntimeTaskAttempt.task_id == task_id)
                .order_by(RuntimeTaskAttempt.created_at.asc())
            ).all()
            items = [
                AttemptRecord(
                    attempt_id=attempt.id,
                    task_id=attempt.task_id,
                    status=_to_task_status(attempt.status.value),
                    started_at=attempt.started_at.isoformat() if attempt.started_at else None,
                    ended_at=attempt.ended_at.isoformat() if attempt.ended_at else None,
                    event_sequence=[
                        row.sequence
                        for row in session.scalars(
                            select(RuntimeRunEvent)
                            .where(RuntimeRunEvent.attempt_id == attempt.id)
                            .order_by(RuntimeRunEvent.sequence.asc())
                        ).all()
                    ],
                )
                for attempt in attempts
            ]
            return AttemptHistoryReadModel(task_id=task_id, attempts=items)


@dataclass(slots=True)
class WorkerHealthProjector:
    session_factory: Callable[[], Session]

    def project(self) -> list[WorkerHealthReadModel]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(RuntimeRunEvent)
                .where(RuntimeRunEvent.event_type == EventType.WORKER_HEALTH_REPORTED.value)
                .order_by(RuntimeRunEvent.occurred_at.desc())
            ).all()
            latest_by_worker: dict[str, WorkerHealthReadModel] = {}
            for row in rows:
                worker_id = str(row.payload_json["worker_id"])
                if worker_id in latest_by_worker:
                    continue
                raw_active_names = row.payload_json.get("active_workflow_names")
                active_names = raw_active_names if isinstance(raw_active_names, list) else []
                latest_by_worker[worker_id] = WorkerHealthReadModel(
                    worker_id=worker_id,
                    task_queue=str(row.payload_json["task_queue"]),
                    status=WorkerHealthStatus(str(row.payload_json["status"])),
                    last_seen_at=row.occurred_at.isoformat(),
                    active_workflow_names=[
                        WorkflowName(name)
                        for name in active_names
                    ],
                    detail=str(row.payload_json["detail"])
                    if row.payload_json.get("detail") is not None
                    else None,
                )
            return list(latest_by_worker.values())


@dataclass(slots=True)
class RuntimeProjectorService:
    timeline: TimelineProjector
    task_graph: TaskGraphProjector
    attempt_history: AttemptHistoryProjector
    worker_health: WorkerHealthProjector

    def get_timeline(self, workflow_run_id: str) -> TimelineReadModel:
        return self.timeline.project(workflow_run_id)

    def get_graph(self, workflow_run_id: str) -> TaskGraphReadModel:
        return self.task_graph.project(workflow_run_id)

    def get_attempts(self, task_id: str) -> AttemptHistoryReadModel:
        return self.attempt_history.project(task_id)

    def get_workers_health(self) -> list[WorkerHealthReadModel]:
        return self.worker_health.project()
