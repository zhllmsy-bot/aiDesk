from __future__ import annotations

from datetime import UTC, datetime, timedelta

from api.control_plane.models import IterationStatus, Project, ProjectIteration
from api.database import Base, create_session_factory
from api.events.models import CorrelationIds, RunEventEnvelope
from api.models import register_models
from api.notifications.base import NotificationMessage
from api.notifications.service import (
    InMemoryNotificationAdapter,
    NotificationHistoryService,
    NotificationService,
    PersistentNotificationRecorder,
)
from api.runtime_contracts import EventType
from api.runtime_persistence.service import RuntimePersistenceService


def _init_persistence() -> RuntimePersistenceService:
    session_factory = create_session_factory("sqlite+pysqlite:///:memory:")
    register_models()
    engine = session_factory.kw["bind"]
    assert engine is not None
    Base.metadata.create_all(engine)
    return RuntimePersistenceService(session_factory=session_factory)


def _seed_scope(
    persistence: RuntimePersistenceService,
    *,
    project_id: str,
    iteration_id: str,
) -> None:
    with persistence.session_factory() as session:
        session.add(
            Project(
                id=project_id,
                name=f"Project {project_id}",
                slug=f"{project_id}-slug",
                root_path=f"/tmp/{project_id}",
                default_branch="main",
            )
        )
        session.add(
            ProjectIteration(
                id=iteration_id,
                project_id=project_id,
                title="Iteration 1",
                sequence_number=1,
                status=IterationStatus.active,
            )
        )
        session.commit()


def test_notification_service_records_delivery_row_durably() -> None:
    persistence = _init_persistence()
    workflow_run_id = "run-notification-persist"
    persistence.ensure_workflow_run(
        workflow_run_id=workflow_run_id,
        project_id=None,
        iteration_id=None,
        workflow_name="project.improvement",
        trace_id="trace-notification-persist",
        initiated_by="tests",
        objective="verify notification persistence",
    )
    history = NotificationHistoryService(persistence.session_factory)
    service = NotificationService(
        adapters=[InMemoryNotificationAdapter()],
        recorders=[PersistentNotificationRecorder(history)],
    )
    message = NotificationMessage(
        channel="runtime",
        title="workflow completed",
        body="notification body",
        correlation=CorrelationIds(
            workflow_run_id=workflow_run_id,
            trace_id="trace-notification-persist",
        ),
        metadata={"receive_id": "oc_xxx"},
    )
    receipts = service.send(message)
    assert len(receipts) == 1
    receipt = receipts[0]
    assert receipt.status == "sent"

    rows = history.list_deliveries(workflow_run_id=workflow_run_id, limit=10)
    assert len(rows) == 1
    row = rows[0]
    assert row.workflow_run_id == workflow_run_id
    assert row.source_channel == "runtime"
    assert row.delivery_channel == "runtime"
    assert row.delivery_status == "sent"
    assert row.receipt_id == receipt.receipt_id
    assert row.metadata["message"]["receive_id"] == "oc_xxx"
    updated = history.update_delivery_status(
        receipt_id=receipt.receipt_id,
        delivery_status="delivered",
        provider_message_id="msg-1",
        metadata_patch={"provider": "runtime"},
    )
    assert updated is not None
    assert updated.delivery_status == "delivered"
    assert updated.provider_message_id == "msg-1"
    assert updated.metadata["provider_update"]["provider"] == "runtime"


def test_runtime_sla_snapshot_reports_retries_approvals_recovery_and_notifications() -> None:
    persistence = _init_persistence()
    workflow_run_id = "run-sla-snapshot"
    trace_id = "trace-sla-snapshot"
    persistence.ensure_workflow_run(
        workflow_run_id=workflow_run_id,
        project_id=None,
        iteration_id=None,
        workflow_name="project.improvement",
        trace_id=trace_id,
        initiated_by="tests",
        objective="verify runtime sla snapshot",
    )

    base = datetime.now(UTC) - timedelta(minutes=5)
    events: list[tuple[EventType, str, datetime]] = [
        (EventType.APPROVAL_REQUESTED, "task-approval", base + timedelta(seconds=0)),
        (EventType.APPROVAL_RESOLVED, "task-approval", base + timedelta(seconds=30)),
        (EventType.TASK_FAILED, "task-failure", base + timedelta(seconds=40)),
        (EventType.TASK_CLAIMED, "task-failure", base + timedelta(seconds=70)),
        (EventType.WORKFLOW_RETRYING, "task-retry", base + timedelta(seconds=80)),
        (EventType.TASK_CLAIMED, "task-retry", base + timedelta(seconds=95)),
    ]
    for index, (event_type, task_id, occurred_at) in enumerate(events, start=1):
        payload: dict[str, object] = {"summary": event_type.value}
        if event_type == EventType.APPROVAL_REQUESTED:
            payload["approval_id"] = "approval-1"
        if event_type == EventType.APPROVAL_RESOLVED:
            payload["approval_id"] = "approval-1"
            payload["approved"] = True
        persistence.append_event(
            RunEventEnvelope(
                event_id=f"evt-sla-{index}",
                event_type=event_type,
                schema_version="1.0.0",
                payload_version="1.0.0",
                sequence=index,
                producer="tests",
                occurred_at=occurred_at.isoformat(),
                idempotency_key=f"sla-{index}",
                correlation=CorrelationIds(
                    workflow_run_id=workflow_run_id,
                    trace_id=trace_id,
                    task_id=task_id,
                    attempt_id=f"attempt-{task_id}",
                ),
                payload=payload,
            )
        )

    history = NotificationHistoryService(persistence.session_factory)
    service = NotificationService(
        adapters=[InMemoryNotificationAdapter()],
        recorders=[PersistentNotificationRecorder(history)],
    )
    service.send(
        NotificationMessage(
            channel="runtime",
            title="done",
            body="done",
            correlation=CorrelationIds(workflow_run_id=workflow_run_id, trace_id=trace_id),
            metadata={},
        )
    )

    snapshot = persistence.runtime_sla_snapshot(window_hours=24)
    assert snapshot["run_count"] >= 1
    assert snapshot["retry_recovery"]["count"] == 1
    assert snapshot["approval_resolution"]["count"] == 1
    assert snapshot["failure_recovery"]["count"] == 1
    assert snapshot["retry_recovery"]["avg_seconds"] == 15.0
    assert snapshot["approval_resolution"]["avg_seconds"] == 30.0
    assert snapshot["failure_recovery"]["avg_seconds"] == 30.0
    assert snapshot["notifications"]["total"] == 1
    assert snapshot["notifications"]["delivered"] == 1
    assert "runtime" in snapshot["notifications"]["channels"]


def test_runtime_sla_snapshot_supports_scope_and_trend() -> None:
    persistence = _init_persistence()
    _seed_scope(
        persistence,
        project_id="project-sla-a",
        iteration_id="iter-sla-a",
    )
    _seed_scope(
        persistence,
        project_id="project-sla-b",
        iteration_id="iter-sla-b",
    )

    base = datetime.now(UTC) - timedelta(minutes=10)
    runs = [
        ("run-scope-a", "trace-scope-a", "project-sla-a", "iter-sla-a"),
        ("run-scope-b", "trace-scope-b", "project-sla-b", "iter-sla-b"),
    ]
    for run_id, trace_id, project_id, iteration_id in runs:
        persistence.ensure_workflow_run(
            workflow_run_id=run_id,
            project_id=project_id,
            iteration_id=iteration_id,
            workflow_name="project.improvement",
            trace_id=trace_id,
            initiated_by="tests",
            objective="scope test",
        )
        persistence.append_event(
            RunEventEnvelope(
                event_id=f"evt-{run_id}-1",
                event_type=EventType.WORKFLOW_RETRYING,
                schema_version="1.0.0",
                payload_version="1.0.0",
                sequence=1,
                producer="tests",
                occurred_at=(base + timedelta(seconds=10)).isoformat(),
                idempotency_key=f"{run_id}-1",
                correlation=CorrelationIds(
                    workflow_run_id=run_id,
                    trace_id=trace_id,
                    task_id="task-1",
                    attempt_id="attempt-1",
                ),
                payload={"summary": "retrying"},
            )
        )
        persistence.append_event(
            RunEventEnvelope(
                event_id=f"evt-{run_id}-2",
                event_type=EventType.TASK_CLAIMED,
                schema_version="1.0.0",
                payload_version="1.0.0",
                sequence=2,
                producer="tests",
                occurred_at=(base + timedelta(seconds=30)).isoformat(),
                idempotency_key=f"{run_id}-2",
                correlation=CorrelationIds(
                    workflow_run_id=run_id,
                    trace_id=trace_id,
                    task_id="task-1",
                    attempt_id="attempt-1",
                ),
                payload={"summary": "claimed"},
            )
        )
        history = NotificationHistoryService(persistence.session_factory)
        NotificationService(
            adapters=[InMemoryNotificationAdapter()],
            recorders=[PersistentNotificationRecorder(history)],
        ).send(
            NotificationMessage(
                channel="runtime",
                title="done",
                body="done",
                correlation=CorrelationIds(workflow_run_id=run_id, trace_id=trace_id),
                metadata={},
            )
        )

    snapshot = persistence.runtime_sla_snapshot(
        window_hours=24,
        project_id="project-sla-a",
        iteration_id="iter-sla-a",
        bucket_minutes=15,
    )
    assert snapshot["scope"]["project_id"] == "project-sla-a"
    assert snapshot["scope"]["iteration_id"] == "iter-sla-a"
    assert snapshot["trend"]["bucket_minutes"] == 15
    assert snapshot["run_count"] == 1
    assert snapshot["retry_recovery"]["count"] == 1
    assert snapshot["notifications"]["total"] == 1
    assert len(snapshot["trend"]["points"]) >= 1
