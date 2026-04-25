from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api.control_plane.models import Project
from api.events.models import (
    AttemptHistoryReadModel,
    CorrelationIds,
    RunEventEnvelope,
    TaskGraphReadModel,
    TimelineReadModel,
    WorkerHealthReadModel,
)
from api.runtime_contracts import ClaimStatus, EventType, TaskStatus
from api.runtime_persistence.models import (
    ClaimStatusDB,
    RuntimeGraphCheckpoint,
    RuntimeNotificationDelivery,
    RuntimeRunEvent,
    RuntimeTask,
    RuntimeTaskAttempt,
    RuntimeTaskClaim,
    RuntimeWorkflowRun,
    TaskStatusDB,
    WorkflowRunStatusDB,
)
from api.runtime_persistence.projectors import RuntimeProjectorService
from api.workflows.lease_manager import TaskClaim


def _utcnow() -> datetime:
    return datetime.now(UTC)


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


def _task_status_db(status: str) -> TaskStatusDB:
    return TaskStatusDB(status)


def _workflow_status_db(status: str) -> WorkflowRunStatusDB:
    return WorkflowRunStatusDB(status)


_INFLIGHT_TASK_STATUSES: tuple[TaskStatusDB, ...] = (
    TaskStatusDB.queued,
    TaskStatusDB.claimed,
    TaskStatusDB.running,
    TaskStatusDB.verifying,
    TaskStatusDB.waiting_approval,
    TaskStatusDB.retrying,
)


def _terminal_task_status_for_workflow(status: WorkflowRunStatusDB) -> TaskStatusDB:
    if status == WorkflowRunStatusDB.failed:
        return TaskStatusDB.failed
    if status == WorkflowRunStatusDB.cancelled:
        return TaskStatusDB.cancelled
    # A completed workflow should not have inflight tasks; when it happens,
    # close them explicitly as cancelled to avoid stale "running" rows.
    return TaskStatusDB.cancelled


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = max(1, ceil((p / 100.0) * len(ordered)))
    return ordered[min(rank - 1, len(ordered) - 1)]


def _duration_stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "avg_seconds": None, "p50_seconds": None, "p95_seconds": None}
    avg = sum(values) / len(values)
    return {
        "count": len(values),
        "avg_seconds": round(avg, 3),
        "p50_seconds": _percentile(values, 50.0),
        "p95_seconds": _percentile(values, 95.0),
    }


@dataclass(slots=True)
class RuntimePersistenceService:
    session_factory: Callable[[], Session]
    projector: RuntimeProjectorService | None = field(default=None)

    def __post_init__(self) -> None:
        if self.projector is None:
            from api.runtime_persistence.projectors import (
                AttemptHistoryProjector,
                TaskGraphProjector,
                TimelineProjector,
                WorkerHealthProjector,
            )

            self.projector = RuntimeProjectorService(
                timeline=TimelineProjector(session_factory=self.session_factory),
                task_graph=TaskGraphProjector(session_factory=self.session_factory),
                attempt_history=AttemptHistoryProjector(session_factory=self.session_factory),
                worker_health=WorkerHealthProjector(session_factory=self.session_factory),
            )

    def require_projector(self) -> RuntimeProjectorService:
        if self.projector is None:
            raise RuntimeError("runtime projector was not configured")
        return self.projector

    def ensure_workflow_run(
        self,
        *,
        workflow_run_id: str,
        project_id: str | None,
        iteration_id: str | None,
        workflow_name: str | None,
        trace_id: str,
        initiated_by: str,
        objective: str,
        temporal_workflow_id: str | None = None,
        temporal_run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        effective_workflow_name = workflow_name or "runtime.unknown"
        with self.session_factory() as session:
            record = session.get(RuntimeWorkflowRun, workflow_run_id)
            if record is None:
                session.add(
                    RuntimeWorkflowRun(
                        id=workflow_run_id,
                        project_id=project_id,
                        iteration_id=iteration_id,
                        workflow_name=effective_workflow_name,
                        temporal_workflow_id=temporal_workflow_id or workflow_run_id,
                        temporal_run_id=temporal_run_id,
                        trace_id=trace_id,
                        initiated_by=initiated_by,
                        objective=objective,
                        metadata_json=dict(metadata or {}),
                    )
                )
            else:
                if project_id is not None and record.project_id is None:
                    record.project_id = project_id
                record.temporal_run_id = temporal_run_id or record.temporal_run_id
                if workflow_name:
                    record.workflow_name = workflow_name
                record.metadata_json = {**record.metadata_json, **dict(metadata or {})}
            session.commit()

    def ensure_task(
        self,
        *,
        workflow_run_id: str,
        task_id: str,
        title: str,
        graph_kind: str,
        executor: str | None = None,
        depends_on: list[str] | None = None,
        executor_summary: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.session_factory() as session:
            task = session.get(RuntimeTask, task_id)
            if task is None:
                session.add(
                    RuntimeTask(
                        id=task_id,
                        workflow_run_id=workflow_run_id,
                        title=title,
                        graph_kind=graph_kind,
                        executor=executor,
                        depends_on=list(depends_on or []),
                        executor_summary=executor_summary,
                        metadata_json=dict(metadata or {}),
                    )
                )
            else:
                task.title = title
                task.graph_kind = graph_kind
                task.executor = executor
                task.depends_on = list(depends_on or [])
                task.executor_summary = executor_summary
                task.metadata_json = {**task.metadata_json, **dict(metadata or {})}
            session.commit()

    def ensure_attempt(
        self,
        *,
        workflow_run_id: str,
        task_id: str,
        attempt_id: str,
        executor: str | None = None,
        status: str = TaskStatus.QUEUED.value,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.session_factory() as session:
            attempt = session.get(RuntimeTaskAttempt, attempt_id)
            if attempt is None:
                session.add(
                    RuntimeTaskAttempt(
                        id=attempt_id,
                        task_id=task_id,
                        workflow_run_id=workflow_run_id,
                        executor=executor,
                        status=_task_status_db(status),
                        metadata_json=dict(metadata or {}),
                    )
                )
            else:
                attempt.executor = executor or attempt.executor
                attempt.status = _task_status_db(status)
                attempt.metadata_json = {**attempt.metadata_json, **dict(metadata or {})}
            session.commit()

    def append_event(self, event: RunEventEnvelope) -> RunEventEnvelope:
        with self.session_factory() as session:
            existing = session.scalar(
                select(RuntimeRunEvent).where(
                    RuntimeRunEvent.idempotency_key == event.idempotency_key
                )
            )
            if existing is not None:
                return self._to_event_envelope(existing)

            safe_project_id = self._resolve_existing_project_id(
                session, event.correlation.project_id
            )
            self._ensure_minimum_records(session, event, safe_project_id)
            self._validate_sequence(session, event)
            row = RuntimeRunEvent(
                id=event.event_id,
                workflow_run_id=event.correlation.workflow_run_id,
                trace_id=event.correlation.trace_id,
                workflow_id=event.correlation.workflow_id,
                project_id=safe_project_id,
                task_id=event.correlation.task_id,
                attempt_id=event.correlation.attempt_id,
                event_type=str(event.event_type),
                schema_version=event.schema_version,
                payload_version=event.payload_version,
                sequence=event.sequence,
                producer=event.producer,
                occurred_at=datetime.fromisoformat(event.occurred_at),
                idempotency_key=event.idempotency_key,
                payload_json=event.payload,
            )
            session.add(row)
            self._apply_event_side_effects(session, event)
            session.commit()
            return event

    def append(self, event: RunEventEnvelope) -> RunEventEnvelope:
        return self.append_event(event)

    def next_sequence(self, workflow_run_id: str) -> int:
        with self.session_factory() as session:
            count = (
                session.query(RuntimeRunEvent).filter_by(workflow_run_id=workflow_run_id).count()
            )
            return count + 1

    def list_run_events(self, workflow_run_id: str) -> list[RunEventEnvelope]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(RuntimeRunEvent)
                .where(RuntimeRunEvent.workflow_run_id == workflow_run_id)
                .order_by(RuntimeRunEvent.sequence.asc())
            ).all()
            return [self._to_event_envelope(row) for row in rows]

    def list_notification_deliveries(
        self,
        *,
        workflow_run_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 500))
        with self.session_factory() as session:
            statement = select(RuntimeNotificationDelivery).order_by(
                RuntimeNotificationDelivery.sent_at.desc()
            )
            if workflow_run_id:
                statement = statement.where(
                    RuntimeNotificationDelivery.workflow_run_id == workflow_run_id
                )
            rows = session.scalars(statement.limit(safe_limit)).all()
            return [
                {
                    "id": row.id,
                    "workflow_run_id": row.workflow_run_id,
                    "trace_id": row.trace_id,
                    "source_channel": row.source_channel,
                    "delivery_channel": row.delivery_channel,
                    "delivery_status": row.delivery_status,
                    "title": row.title,
                    "body": row.body,
                    "receipt_id": row.receipt_id,
                    "provider_message_id": row.provider_message_id,
                    "metadata": dict(row.metadata_json),
                    "sent_at": row.sent_at.isoformat(),
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]

    def runtime_sla_snapshot(
        self,
        *,
        window_hours: int = 24 * 7,
        project_id: str | None = None,
        iteration_id: str | None = None,
        bucket_minutes: int = 60,
    ) -> dict[str, Any]:
        safe_window_hours = max(1, min(window_hours, 24 * 90))
        safe_bucket_minutes = max(5, min(bucket_minutes, 24 * 60))
        now = _utcnow()
        cutoff = now - timedelta(hours=safe_window_hours)
        retry_recovery_seconds: list[float] = []
        approval_resolution_seconds: list[float] = []
        failure_recovery_seconds: list[float] = []

        def _empty_snapshot() -> dict[str, Any]:
            return {
                "generated_at": now.isoformat(),
                "window_hours": safe_window_hours,
                "scope": {
                    "project_id": project_id,
                    "iteration_id": iteration_id,
                },
                "run_count": 0,
                "event_count": 0,
                "retry_recovery": _duration_stats([]),
                "approval_resolution": _duration_stats([]),
                "failure_recovery": _duration_stats([]),
                "notifications": {
                    "total": 0,
                    "delivered": 0,
                    "failed": 0,
                    "channels": [],
                },
                "trend": {"bucket_minutes": safe_bucket_minutes, "points": []},
            }

        try:
            with self.session_factory() as session:
                scoped_run_ids: set[str] | None = None
                if project_id or iteration_id:
                    scoped_runs_statement = select(RuntimeWorkflowRun.id)
                    if project_id:
                        scoped_runs_statement = scoped_runs_statement.where(
                            RuntimeWorkflowRun.project_id == project_id
                        )
                    if iteration_id:
                        scoped_runs_statement = scoped_runs_statement.where(
                            RuntimeWorkflowRun.iteration_id == iteration_id
                        )
                    scoped_run_ids = set(session.scalars(scoped_runs_statement).all())
                    if not scoped_run_ids:
                        return _empty_snapshot()

                event_statement = (
                    select(RuntimeRunEvent)
                    .where(RuntimeRunEvent.occurred_at >= cutoff)
                    .order_by(RuntimeRunEvent.workflow_run_id.asc(), RuntimeRunEvent.sequence.asc())
                )
                if scoped_run_ids is not None:
                    event_statement = event_statement.where(
                        RuntimeRunEvent.workflow_run_id.in_(scoped_run_ids)
                    )
                event_rows = session.scalars(
                    event_statement
                ).all()

                runs_statement = select(RuntimeWorkflowRun.id).where(
                    RuntimeWorkflowRun.created_at >= cutoff
                )
                if project_id:
                    runs_statement = runs_statement.where(
                        RuntimeWorkflowRun.project_id == project_id
                    )
                if iteration_id:
                    runs_statement = runs_statement.where(
                        RuntimeWorkflowRun.iteration_id == iteration_id
                    )
                runs = set(session.scalars(runs_statement).all())

                deliveries_statement = select(RuntimeNotificationDelivery).where(
                    RuntimeNotificationDelivery.sent_at >= cutoff
                )
                if scoped_run_ids is not None:
                    deliveries_statement = deliveries_statement.where(
                        RuntimeNotificationDelivery.workflow_run_id.in_(scoped_run_ids)
                    )
                deliveries = session.scalars(deliveries_statement).all()
        except SQLAlchemyError:
            return _empty_snapshot()

        def _bucket_start(value: datetime) -> datetime:
            effective = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
            bucket_seconds = safe_bucket_minutes * 60
            bucket_epoch = int(effective.timestamp()) // bucket_seconds * bucket_seconds
            return datetime.fromtimestamp(bucket_epoch, tz=UTC)

        trend_buckets: dict[datetime, dict[str, Any]] = {}

        def _trend_row(bucket_start: datetime) -> dict[str, Any]:
            row = trend_buckets.get(bucket_start)
            if row is not None:
                return row
            row = {
                "bucket_start": bucket_start.isoformat(),
                "event_count": 0,
                "workflow_retrying_count": 0,
                "approval_resolved_count": 0,
                "retry_recovered_count": 0,
                "failure_recovered_count": 0,
                "notifications_total": 0,
                "notifications_failed": 0,
            }
            trend_buckets[bucket_start] = row
            return row

        pending_retry_by_task: dict[tuple[str, str], list[datetime]] = {}
        pending_failure_by_task: dict[tuple[str, str], list[datetime]] = {}
        pending_approval_by_task: dict[tuple[str, str], list[datetime]] = {}

        for row in event_rows:
            run_id = row.workflow_run_id
            task_id = row.task_id or ""
            key = (run_id, task_id)
            event_type = row.event_type
            occurred_at = row.occurred_at
            trend_row = _trend_row(_bucket_start(occurred_at))
            trend_row["event_count"] += 1

            if event_type == EventType.WORKFLOW_RETRYING.value and task_id:
                trend_row["workflow_retrying_count"] += 1
                pending_retry_by_task.setdefault(key, []).append(occurred_at)
                continue

            if event_type == EventType.TASK_FAILED.value and task_id:
                pending_failure_by_task.setdefault(key, []).append(occurred_at)
                continue

            if event_type == EventType.APPROVAL_REQUESTED.value and task_id:
                pending_approval_by_task.setdefault(key, []).append(occurred_at)
                continue

            if event_type == EventType.TASK_CLAIMED.value and task_id:
                retry_pending = pending_retry_by_task.get(key)
                if retry_pending:
                    started_at = retry_pending.pop(0)
                    retry_recovery_seconds.append((occurred_at - started_at).total_seconds())
                    trend_row["retry_recovered_count"] += 1
                failed_pending = pending_failure_by_task.get(key)
                if failed_pending:
                    failed_at = failed_pending.pop(0)
                    failure_recovery_seconds.append((occurred_at - failed_at).total_seconds())
                    trend_row["failure_recovered_count"] += 1
                continue

            if event_type == EventType.APPROVAL_RESOLVED.value and task_id:
                trend_row["approval_resolved_count"] += 1
                approval_pending = pending_approval_by_task.get(key)
                if approval_pending:
                    requested_at = approval_pending.pop(0)
                    approval_resolution_seconds.append((occurred_at - requested_at).total_seconds())
                continue

        for delivery in deliveries:
            trend_row = _trend_row(_bucket_start(delivery.sent_at))
            trend_row["notifications_total"] += 1
            if delivery.delivery_status.lower() != "sent":
                trend_row["notifications_failed"] += 1

        notification_total = len(deliveries)
        notification_failed = sum(
            1 for item in deliveries if item.delivery_status.lower() != "sent"
        )
        notification_delivered = notification_total - notification_failed
        channels = sorted(
            {item.delivery_channel for item in deliveries if item.delivery_channel}
        )
        trend_points = [
            trend_buckets[key] for key in sorted(trend_buckets.keys())
        ]

        return {
            "generated_at": now.isoformat(),
            "window_hours": safe_window_hours,
            "scope": {
                "project_id": project_id,
                "iteration_id": iteration_id,
            },
            "run_count": len(runs),
            "event_count": len(event_rows),
            "retry_recovery": _duration_stats(retry_recovery_seconds),
            "approval_resolution": _duration_stats(approval_resolution_seconds),
            "failure_recovery": _duration_stats(failure_recovery_seconds),
            "notifications": {
                "total": notification_total,
                "delivered": notification_delivered,
                "failed": notification_failed,
                "channels": channels,
            },
            "trend": {
                "bucket_minutes": safe_bucket_minutes,
                "points": trend_points,
            },
        }

    def event_count(self, workflow_run_id: str) -> int:
        with self.session_factory() as session:
            return session.query(RuntimeRunEvent).filter_by(workflow_run_id=workflow_run_id).count()

    def get_timeline(self, workflow_run_id: str) -> TimelineReadModel:
        return self.require_projector().get_timeline(workflow_run_id)

    def get_graph(self, workflow_run_id: str) -> TaskGraphReadModel:
        return self.require_projector().get_graph(workflow_run_id)

    def get_attempts(self, task_id: str) -> AttemptHistoryReadModel:
        return self.require_projector().get_attempts(task_id)

    def get_workers_health(self) -> list[WorkerHealthReadModel]:
        return self.require_projector().get_workers_health()

    def claim_task(
        self,
        *,
        task_id: str,
        workflow_run_id: str,
        attempt_id: str,
        worker_id: str,
        lease_timeout_seconds: int,
    ) -> TaskClaim:
        with self.session_factory() as session:
            active = session.scalar(
                select(RuntimeTaskClaim)
                .where(RuntimeTaskClaim.task_id == task_id)
                .where(RuntimeTaskClaim.workflow_run_id == workflow_run_id)
                .where(RuntimeTaskClaim.status == ClaimStatusDB.active)
            )
            if active is not None:
                raise ValueError(f"Task {task_id} already has an active claim")
            now = _utcnow()
            existing_claim = session.get(RuntimeTaskClaim, f"claim-{attempt_id}")
            if existing_claim is not None:
                return self._to_claim(existing_claim)
            attempt = session.get(RuntimeTaskAttempt, attempt_id)
            if attempt is None:
                attempt = RuntimeTaskAttempt(
                    id=attempt_id,
                    task_id=task_id,
                    workflow_run_id=workflow_run_id,
                    status=TaskStatusDB.claimed,
                    started_at=now,
                )
                session.add(attempt)
            else:
                attempt.started_at = attempt.started_at or now
                attempt.status = TaskStatusDB.claimed
            # Ensure FK target exists before claim insert regardless of flush ordering.
            session.flush()
            claim = RuntimeTaskClaim(
                id=f"claim-{attempt_id}",
                task_id=task_id,
                workflow_run_id=workflow_run_id,
                attempt_id=attempt_id,
                worker_id=worker_id,
                lease_timeout_seconds=lease_timeout_seconds,
                status=ClaimStatusDB.active,
                claimed_at=now,
                heartbeat_at=now,
            )
            session.add(claim)
            task = session.get(RuntimeTask, task_id)
            if task is not None:
                task.status = TaskStatusDB.claimed
            session.commit()
            return self._to_claim(claim)

    def heartbeat(self, claim_id: str) -> TaskClaim:
        with self.session_factory() as session:
            claim = session.get(RuntimeTaskClaim, claim_id)
            if claim is None:
                raise KeyError(claim_id)
            if claim.status != ClaimStatusDB.active:
                raise ValueError(
                    f"Cannot heartbeat claim {claim_id} in status {claim.status.value}"
                )
            claim.heartbeat_at = _utcnow()
            session.commit()
            return self._to_claim(claim)

    def release(self, claim_id: str) -> TaskClaim:
        with self.session_factory() as session:
            claim = session.get(RuntimeTaskClaim, claim_id)
            if claim is None:
                raise KeyError(claim_id)
            claim.status = ClaimStatusDB.released
            claim.released_at = _utcnow()
            session.commit()
            return self._to_claim(claim)

    def reclaim_stale_claims(
        self,
        *,
        workflow_run_id: str,
        force_claim_ids: list[str] | None = None,
    ) -> list[TaskClaim]:
        force_ids = set(force_claim_ids or [])
        now = _utcnow()
        with self.session_factory() as session:
            claims = session.scalars(
                select(RuntimeTaskClaim)
                .where(RuntimeTaskClaim.workflow_run_id == workflow_run_id)
                .where(RuntimeTaskClaim.status == ClaimStatusDB.active)
            ).all()
            reclaimed: list[TaskClaim] = []
            for claim in claims:
                heartbeat_at = claim.heartbeat_at
                if heartbeat_at.tzinfo is None:
                    heartbeat_at = heartbeat_at.replace(tzinfo=UTC)
                stale = claim.id in force_ids or now >= heartbeat_at + timedelta(
                    seconds=claim.lease_timeout_seconds
                )
                if not stale:
                    continue
                claim.status = ClaimStatusDB.reclaimed
                claim.expired_at = now
                claim.reclaimed_at = now
                task = session.get(RuntimeTask, claim.task_id)
                if task is not None:
                    task.status = TaskStatusDB.reclaimed
                attempt = session.get(RuntimeTaskAttempt, claim.attempt_id)
                if attempt is not None:
                    attempt.status = TaskStatusDB.reclaimed
                    attempt.ended_at = now
                reclaimed.append(self._to_claim(claim))
            session.commit()
            return reclaimed

    def scan_all_stale_claims(self) -> list[TaskClaim]:
        now = _utcnow()
        with self.session_factory() as session:
            claims = session.scalars(
                select(RuntimeTaskClaim).where(RuntimeTaskClaim.status == ClaimStatusDB.active)
            ).all()
            stale: list[TaskClaim] = []
            for claim in claims:
                heartbeat_at = claim.heartbeat_at
                if heartbeat_at.tzinfo is None:
                    heartbeat_at = heartbeat_at.replace(tzinfo=UTC)
                if now >= heartbeat_at + timedelta(seconds=claim.lease_timeout_seconds):
                    stale.append(self._to_claim(claim))
            return stale

    def transition_workflow_status(
        self,
        *,
        workflow_run_id: str,
        target: str,
    ) -> None:
        with self.session_factory() as session:
            workflow_run = session.get(RuntimeWorkflowRun, workflow_run_id)
            if workflow_run is None:
                return
            workflow_run.status = _workflow_status_db(target)
            now = _utcnow()
            if target == WorkflowRunStatusDB.running.value and workflow_run.started_at is None:
                workflow_run.started_at = now
            if target in {
                WorkflowRunStatusDB.completed.value,
                WorkflowRunStatusDB.failed.value,
                WorkflowRunStatusDB.cancelled.value,
            }:
                workflow_run.completed_at = now
                self._finalize_inflight_records_on_workflow_terminal(
                    session=session,
                    workflow_run_id=workflow_run_id,
                    workflow_status=_workflow_status_db(target),
                    occurred_at=now,
                )
            session.commit()

    def reconcile_terminal_runs(
        self,
        *,
        workflow_run_ids: list[str] | None = None,
    ) -> dict[str, int]:
        terminal_statuses = {
            WorkflowRunStatusDB.completed,
            WorkflowRunStatusDB.failed,
            WorkflowRunStatusDB.cancelled,
        }
        summary = {
            "runs_scanned": 0,
            "runs_reconciled": 0,
            "tasks_reconciled": 0,
            "attempts_reconciled": 0,
            "claims_reconciled": 0,
        }
        with self.session_factory() as session:
            query = select(RuntimeWorkflowRun).where(
                RuntimeWorkflowRun.status.in_(terminal_statuses)
            )
            if workflow_run_ids:
                query = query.where(RuntimeWorkflowRun.id.in_(workflow_run_ids))
            runs = session.scalars(query).all()
            summary["runs_scanned"] = len(runs)
            for run in runs:
                counters = self._finalize_inflight_records_on_workflow_terminal(
                    session=session,
                    workflow_run_id=run.id,
                    workflow_status=run.status,
                    occurred_at=run.completed_at or _utcnow(),
                )
                if any(value > 0 for value in counters.values()):
                    summary["runs_reconciled"] += 1
                summary["tasks_reconciled"] += counters["tasks"]
                summary["attempts_reconciled"] += counters["attempts"]
                summary["claims_reconciled"] += counters["claims"]
            session.commit()
        return summary

    def transition_task_status(
        self,
        *,
        task_id: str,
        attempt_id: str | None,
        target: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.session_factory() as session:
            task = session.get(RuntimeTask, task_id)
            now = _utcnow()
            if task is not None:
                task.status = _task_status_db(target)
                if metadata and "blocked_reason" in metadata:
                    task.blocked_reason = str(metadata["blocked_reason"])
                if target in {
                    TaskStatusDB.completed.value,
                    TaskStatusDB.failed.value,
                    TaskStatusDB.reclaimed.value,
                    TaskStatusDB.cancelled.value,
                }:
                    task.completed_at = now
            if attempt_id:
                attempt = session.get(RuntimeTaskAttempt, attempt_id)
                if attempt is not None:
                    if attempt.started_at is None:
                        attempt.started_at = now
                    attempt.status = _task_status_db(target)
                    attempt.metadata_json = {**attempt.metadata_json, **dict(metadata or {})}
                    if target in {
                        TaskStatusDB.completed.value,
                        TaskStatusDB.failed.value,
                        TaskStatusDB.reclaimed.value,
                        TaskStatusDB.cancelled.value,
                    }:
                        attempt.ended_at = now
            session.commit()

    def save_graph_checkpoint(
        self,
        *,
        workflow_run_id: str,
        task_id: str | None,
        attempt_id: str | None,
        trace_id: str,
        graph_kind: str,
        state: dict[str, Any],
    ) -> str:
        with self.session_factory() as session:
            row = RuntimeGraphCheckpoint(
                workflow_run_id=workflow_run_id,
                task_id=task_id,
                attempt_id=attempt_id,
                trace_id=trace_id,
                graph_kind=graph_kind,
                state_json=dict(state),
            )
            session.add(row)
            session.commit()
            return row.id

    def load_graph_checkpoint(self, checkpoint_id: str) -> dict[str, Any]:
        with self.session_factory() as session:
            row = session.get(RuntimeGraphCheckpoint, checkpoint_id)
            if row is None:
                raise KeyError(checkpoint_id)
            return dict(row.state_json)

    def mark_graph_checkpoint_resumed(self, checkpoint_id: str) -> None:
        with self.session_factory() as session:
            row = session.get(RuntimeGraphCheckpoint, checkpoint_id)
            if row is None:
                return
            row.resumed_at = _utcnow()
            session.commit()

    def _ensure_minimum_records(
        self,
        session: Session,
        event: RunEventEnvelope,
        project_id: str | None = None,
    ) -> None:
        workflow_run = session.get(RuntimeWorkflowRun, event.correlation.workflow_run_id)
        if workflow_run is None:
            workflow_name = event.payload.get("workflow_name")
            objective = (
                event.payload.get("objective")
                or event.payload.get("summary")
                or event.correlation.workflow_run_id
            )
            safe_project_id = project_id
            if safe_project_id is None:
                safe_project_id = self._resolve_existing_project_id(
                    session, event.correlation.project_id
                )
            session.add(
                RuntimeWorkflowRun(
                    id=event.correlation.workflow_run_id,
                    project_id=safe_project_id,
                    iteration_id=None,
                    workflow_name=str(workflow_name or "runtime.unknown"),
                    temporal_workflow_id=event.correlation.workflow_id
                    or event.correlation.workflow_run_id,
                    temporal_run_id=None,
                    trace_id=event.correlation.trace_id,
                    initiated_by="runtime",
                    objective=str(objective),
                    metadata_json={},
                )
            )
        if event.correlation.task_id is not None:
            task = session.get(RuntimeTask, event.correlation.task_id)
            if task is None:
                session.add(
                    RuntimeTask(
                        id=event.correlation.task_id,
                        workflow_run_id=event.correlation.workflow_run_id,
                        title=str(event.payload.get("task_title") or event.correlation.task_id),
                        graph_kind=str(event.payload.get("graph_kind") or "unknown"),
                        executor_summary=str(event.payload.get("executor_summary"))
                        if event.payload.get("executor_summary") is not None
                        else None,
                    )
                )
        if event.correlation.attempt_id is not None and event.correlation.task_id is not None:
            attempt = session.get(RuntimeTaskAttempt, event.correlation.attempt_id)
            if attempt is None:
                session.add(
                    RuntimeTaskAttempt(
                        id=event.correlation.attempt_id,
                        task_id=event.correlation.task_id,
                        workflow_run_id=event.correlation.workflow_run_id,
                    )
                )
        session.flush()

    @staticmethod
    def _resolve_existing_project_id(session: Session, project_id: str | None) -> str | None:
        if project_id is None:
            return None
        return project_id if session.get(Project, project_id) is not None else None

    def _validate_sequence(self, session: Session, event: RunEventEnvelope) -> None:
        current = (
            session.query(RuntimeRunEvent)
            .filter_by(workflow_run_id=event.correlation.workflow_run_id)
            .count()
        )
        expected = current + 1
        if event.sequence != expected:
            workflow_run_id = event.correlation.workflow_run_id
            raise ValueError(
                f"Expected sequence {expected} for {workflow_run_id}, got {event.sequence}"
            )

    def _apply_event_side_effects(self, session: Session, event: RunEventEnvelope) -> None:
        if event.event_type == EventType.WORKFLOW_STARTED:
            workflow_run = session.get(RuntimeWorkflowRun, event.correlation.workflow_run_id)
            if workflow_run is not None:
                workflow_run.status = WorkflowRunStatusDB.running
                workflow_run.started_at = workflow_run.started_at or datetime.fromisoformat(
                    event.occurred_at
                )
                workflow_name = event.payload.get("workflow_name")
                if isinstance(workflow_name, str):
                    workflow_run.workflow_name = workflow_name
        elif event.event_type == EventType.WORKFLOW_COMPLETED:
            workflow_run = session.get(RuntimeWorkflowRun, event.correlation.workflow_run_id)
            if workflow_run is not None:
                occurred_at = datetime.fromisoformat(event.occurred_at)
                workflow_run.status = WorkflowRunStatusDB.completed
                workflow_run.completed_at = occurred_at
                self._finalize_inflight_records_on_workflow_terminal(
                    session=session,
                    workflow_run_id=workflow_run.id,
                    workflow_status=WorkflowRunStatusDB.completed,
                    occurred_at=occurred_at,
                )
        elif event.event_type == EventType.WORKFLOW_FAILED:
            workflow_run = session.get(RuntimeWorkflowRun, event.correlation.workflow_run_id)
            if workflow_run is not None:
                occurred_at = datetime.fromisoformat(event.occurred_at)
                workflow_run.status = WorkflowRunStatusDB.failed
                workflow_run.completed_at = occurred_at
                self._finalize_inflight_records_on_workflow_terminal(
                    session=session,
                    workflow_run_id=workflow_run.id,
                    workflow_status=WorkflowRunStatusDB.failed,
                    occurred_at=occurred_at,
                )
        elif event.event_type == EventType.WORKFLOW_RETRYING:
            workflow_run = session.get(RuntimeWorkflowRun, event.correlation.workflow_run_id)
            if workflow_run is not None:
                workflow_run.status = WorkflowRunStatusDB.retrying
        elif event.event_type == EventType.WORKFLOW_WAITING_APPROVAL:
            workflow_run = session.get(RuntimeWorkflowRun, event.correlation.workflow_run_id)
            if workflow_run is not None:
                workflow_run.status = WorkflowRunStatusDB.waiting_approval

        task_id = event.correlation.task_id
        attempt_id = event.correlation.attempt_id
        status = _status_from_event(event)
        terminal_statuses = {
            TaskStatusDB.completed,
            TaskStatusDB.failed,
            TaskStatusDB.reclaimed,
            TaskStatusDB.cancelled,
        }
        if task_id is not None:
            task = session.get(RuntimeTask, task_id)
            if task is not None:
                if status is not None:
                    task.status = _task_status_db(status.value)
                blocked_reason = event.payload.get("blocked_reason")
                if isinstance(blocked_reason, str):
                    task.blocked_reason = blocked_reason
                executor_summary = event.payload.get("executor_summary")
                if isinstance(executor_summary, str):
                    task.executor_summary = executor_summary
                if status is not None and _task_status_db(status.value) in terminal_statuses:
                    task.completed_at = datetime.fromisoformat(event.occurred_at)
        if attempt_id is not None:
            attempt = session.get(RuntimeTaskAttempt, attempt_id)
            if attempt is not None:
                if attempt.started_at is None:
                    attempt.started_at = datetime.fromisoformat(event.occurred_at)
                if status is not None:
                    attempt.status = _task_status_db(status.value)
                if status is not None and _task_status_db(status.value) in terminal_statuses:
                    attempt.ended_at = datetime.fromisoformat(event.occurred_at)

    def _finalize_inflight_records_on_workflow_terminal(
        self,
        *,
        session: Session,
        workflow_run_id: str,
        workflow_status: WorkflowRunStatusDB,
        occurred_at: datetime,
    ) -> dict[str, int]:
        terminal_task_status = _terminal_task_status_for_workflow(workflow_status)
        tasks = session.scalars(
            select(RuntimeTask)
            .where(RuntimeTask.workflow_run_id == workflow_run_id)
            .where(RuntimeTask.status.in_(_INFLIGHT_TASK_STATUSES))
        ).all()
        for task in tasks:
            task.status = terminal_task_status
            task.completed_at = task.completed_at or occurred_at
            if task.blocked_reason is None:
                task.blocked_reason = (
                    f"workflow {workflow_status.value} before task reached terminal state"
                )

        attempts = session.scalars(
            select(RuntimeTaskAttempt)
            .where(RuntimeTaskAttempt.workflow_run_id == workflow_run_id)
            .where(RuntimeTaskAttempt.status.in_(_INFLIGHT_TASK_STATUSES))
        ).all()
        for attempt in attempts:
            attempt.status = terminal_task_status
            attempt.ended_at = attempt.ended_at or occurred_at
            attempt.metadata_json = {
                **attempt.metadata_json,
                "workflow_terminal_status": workflow_status.value,
            }

        active_claims = session.scalars(
            select(RuntimeTaskClaim)
            .where(RuntimeTaskClaim.workflow_run_id == workflow_run_id)
            .where(RuntimeTaskClaim.status == ClaimStatusDB.active)
        ).all()
        for claim in active_claims:
            claim.status = ClaimStatusDB.reclaimed
            claim.reclaimed_at = claim.reclaimed_at or occurred_at
            claim.expired_at = claim.expired_at or occurred_at
        return {
            "tasks": len(tasks),
            "attempts": len(attempts),
            "claims": len(active_claims),
        }

    def _to_event_envelope(self, row: RuntimeRunEvent) -> RunEventEnvelope:
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

    def _to_claim(self, row: RuntimeTaskClaim) -> TaskClaim:
        return TaskClaim(
            claim_id=row.id,
            task_id=row.task_id,
            workflow_run_id=row.workflow_run_id,
            attempt_id=row.attempt_id,
            worker_id=row.worker_id,
            lease_timeout_seconds=row.lease_timeout_seconds,
            status=ClaimStatus(row.status.value),
            claimed_at=row.claimed_at.isoformat(),
            heartbeat_at=row.heartbeat_at.isoformat(),
            expired_at=row.expired_at.isoformat() if row.expired_at else None,
            reclaimed_at=row.reclaimed_at.isoformat() if row.reclaimed_at else None,
            released_at=row.released_at.isoformat() if row.released_at else None,
        )
