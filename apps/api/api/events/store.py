from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from api.events.builder import build_timeline_entry
from api.events.models import (
    AttemptHistoryReadModel,
    AttemptRecord,
    RunEventEnvelope,
    TaskGraphEdge,
    TaskGraphNode,
    TaskGraphReadModel,
    TaskTodoItem,
    TimelineReadModel,
    WorkerHealthReadModel,
)
from api.runtime_contracts import EventType, TaskStatus, WorkerHealthStatus, WorkflowName

TODO_STATUSES = {"queued", "running", "completed", "failed", "skipped"}


def _status_from_event(event: RunEventEnvelope) -> TaskStatus | None:
    to_status = event.payload.get("to_status")
    if isinstance(to_status, str):
        try:
            return TaskStatus(to_status)
        except ValueError:
            return None
    fallback = {
        EventType.TASK_CLAIMED: TaskStatus.CLAIMED,
        EventType.TASK_RUNNING: TaskStatus.RUNNING,
        EventType.TASK_VERIFYING: TaskStatus.VERIFYING,
        EventType.TASK_COMPLETED: TaskStatus.COMPLETED,
        EventType.TASK_FAILED: TaskStatus.FAILED,
        EventType.TASK_RECLAIMED: TaskStatus.RECLAIMED,
    }
    return fallback.get(event.event_type)


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
        status = raw_status if raw_status in TODO_STATUSES else "queued"
        detail = raw_item.get("detail")
        items.append(
            TaskTodoItem(
                id=item_id,
                title=title,
                status=status,
                detail=str(detail) if detail is not None else None,
            )
        )
    return items


class RuntimeProjector:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._timelines: dict[str, TimelineReadModel] = {}
        self._graphs: dict[str, TaskGraphReadModel] = {}
        self._attempts: dict[str, AttemptHistoryReadModel] = {}
        self._workers: dict[str, WorkerHealthReadModel] = {}

    def apply(self, event: RunEventEnvelope) -> None:
        workflow_run_id = event.correlation.workflow_run_id
        timeline = self._timelines.setdefault(
            workflow_run_id,
            TimelineReadModel(workflow_run_id=workflow_run_id),
        )
        timeline.entries.append(build_timeline_entry(event))

        if event.event_type == EventType.TASK_GRAPH_UPDATED:
            self._graphs[workflow_run_id] = TaskGraphReadModel(
                workflow_run_id=workflow_run_id,
                nodes=[
                    TaskGraphNode.model_validate(node) for node in event.payload.get("nodes", [])
                ],
                edges=[
                    TaskGraphEdge.model_validate(edge) for edge in event.payload.get("edges", [])
                ],
            )

        task_id = event.correlation.task_id
        graph = self._graphs.get(workflow_run_id)
        if task_id and graph is not None:
            for node in graph.nodes:
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

        attempt_id = event.correlation.attempt_id
        if task_id and attempt_id:
            history = self._attempts.setdefault(task_id, AttemptHistoryReadModel(task_id=task_id))
            attempt = next(
                (item for item in history.attempts if item.attempt_id == attempt_id), None
            )
            if attempt is None:
                attempt = AttemptRecord(attempt_id=attempt_id, task_id=task_id)
                history.attempts.append(attempt)
            attempt.event_sequence.append(event.sequence)
            if attempt.started_at is None:
                attempt.started_at = event.occurred_at
            status = _status_from_event(event)
            if status is not None:
                attempt.status = status
            if event.event_type in {
                EventType.TASK_COMPLETED,
                EventType.TASK_FAILED,
                EventType.TASK_RECLAIMED,
            }:
                attempt.ended_at = event.occurred_at

        if event.event_type == EventType.WORKER_HEALTH_REPORTED:
            payload = event.payload
            self._workers[str(payload["worker_id"])] = WorkerHealthReadModel(
                worker_id=str(payload["worker_id"]),
                task_queue=str(payload["task_queue"]),
                status=WorkerHealthStatus(str(payload["status"])),
                last_seen_at=event.occurred_at,
                active_workflow_names=[
                    WorkflowName(name) for name in payload.get("active_workflow_names", [])
                ],
                detail=str(payload["detail"]) if payload.get("detail") is not None else None,
            )

    def timeline(self, workflow_run_id: str) -> TimelineReadModel:
        return self._timelines.get(
            workflow_run_id, TimelineReadModel(workflow_run_id=workflow_run_id)
        ).model_copy(deep=True)

    def graph(self, workflow_run_id: str) -> TaskGraphReadModel:
        return self._graphs.get(
            workflow_run_id, TaskGraphReadModel(workflow_run_id=workflow_run_id)
        ).model_copy(deep=True)

    def attempts(self, task_id: str) -> AttemptHistoryReadModel:
        return self._attempts.get(task_id, AttemptHistoryReadModel(task_id=task_id)).model_copy(
            deep=True
        )

    def workers(self) -> list[WorkerHealthReadModel]:
        return [item.model_copy(deep=True) for item in self._workers.values()]


class InMemoryRuntimeEventStore:
    def __init__(self, projector: RuntimeProjector | None = None) -> None:
        self._projector = projector or RuntimeProjector()
        self.reset()

    def reset(self) -> None:
        self._events_by_run: dict[str, list[RunEventEnvelope]] = defaultdict(list)
        self._events_by_idempotency: dict[str, RunEventEnvelope] = {}
        self._projector.reset()

    def next_sequence(self, workflow_run_id: str) -> int:
        return len(self._events_by_run[workflow_run_id]) + 1

    def append(self, event: RunEventEnvelope) -> RunEventEnvelope:
        existing = self._events_by_idempotency.get(event.idempotency_key)
        if existing is not None:
            return existing
        run_events = self._events_by_run[event.correlation.workflow_run_id]
        expected = len(run_events) + 1
        if event.sequence != expected:
            workflow_run_id = event.correlation.workflow_run_id
            raise ValueError(
                f"Expected sequence {expected} for {workflow_run_id}, got {event.sequence}"
            )
        run_events.append(event)
        self._events_by_idempotency[event.idempotency_key] = event
        self._projector.apply(event)
        return event

    def list_run_events(self, workflow_run_id: str) -> list[RunEventEnvelope]:
        return [event.model_copy(deep=True) for event in self._events_by_run[workflow_run_id]]

    def event_count(self, workflow_run_id: str) -> int:
        return len(self._events_by_run[workflow_run_id])

    def get_timeline(self, workflow_run_id: str) -> TimelineReadModel:
        return self._projector.timeline(workflow_run_id)

    def get_graph(self, workflow_run_id: str) -> TaskGraphReadModel:
        return self._projector.graph(workflow_run_id)

    def get_attempts(self, task_id: str) -> AttemptHistoryReadModel:
        return self._projector.attempts(task_id)

    def get_workers_health(self) -> list[WorkerHealthReadModel]:
        return self._projector.workers()


class RuntimeEventStore(Protocol):
    def next_sequence(self, workflow_run_id: str) -> int: ...

    def append(self, event: RunEventEnvelope) -> RunEventEnvelope: ...

    def list_run_events(self, workflow_run_id: str) -> list[RunEventEnvelope]: ...

    def event_count(self, workflow_run_id: str) -> int: ...

    def get_timeline(self, workflow_run_id: str) -> TimelineReadModel: ...

    def get_graph(self, workflow_run_id: str) -> TaskGraphReadModel: ...

    def get_attempts(self, task_id: str) -> AttemptHistoryReadModel: ...

    def get_workers_health(self) -> list[WorkerHealthReadModel]: ...
