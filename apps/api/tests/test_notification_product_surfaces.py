from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from api.control_plane.models import IterationStatus, Project, ProjectIteration
from api.events.models import CorrelationIds, RunEventEnvelope
from api.notifications.base import NotificationMessage
from api.notifications.service import (
    InMemoryNotificationAdapter,
    NotificationHistoryService,
    NotificationService,
    PersistentNotificationRecorder,
)
from api.runtime_contracts import EventType
from api.runtime_persistence.service import RuntimePersistenceService


def _seed_project(client: TestClient, project_id: str) -> None:
    session_factory = client.app.state.session_factory
    with session_factory() as session:
        session.add(
            Project(
                id=project_id,
                name="AI Desk",
                slug=f"{project_id}-slug",
                root_path=f"/tmp/{project_id}",
                default_branch="main",
            )
        )
        session.commit()


def _seed_iteration(client: TestClient, project_id: str, iteration_id: str) -> None:
    session_factory = client.app.state.session_factory
    with session_factory() as session:
        session.add(
            ProjectIteration(
                id=iteration_id,
                project_id=project_id,
                title="Sprint 1",
                sequence_number=1,
                status=IterationStatus.active,
            )
        )
        session.commit()


def test_notifications_deliveries_endpoint_returns_persisted_rows(
    client: TestClient,
    maintainer_headers: dict[str, str],
) -> None:
    project_id = "proj-notify"
    workflow_run_id = "run-notify-product"
    trace_id = "trace-notify-product"
    _seed_project(client, project_id)

    persistence = RuntimePersistenceService(client.app.state.session_factory)
    persistence.ensure_workflow_run(
        workflow_run_id=workflow_run_id,
        project_id=project_id,
        iteration_id=None,
        workflow_name="project.improvement",
        trace_id=trace_id,
        initiated_by="tests",
        objective="verify notifications api",
    )
    history = NotificationHistoryService(client.app.state.session_factory)
    NotificationService(
        adapters=[InMemoryNotificationAdapter()],
        recorders=[PersistentNotificationRecorder(history)],
    ).send(
        NotificationMessage(
            channel="runtime",
            title="workflow completed",
            body="notification body",
            correlation=CorrelationIds(
                workflow_run_id=workflow_run_id,
                trace_id=trace_id,
                project_id=project_id,
            ),
            metadata={"receive_id": "oc_surface"},
        )
    )

    response = client.get(
        "/notifications/deliveries",
        params={"project_id": project_id, "delivery_channel": "runtime"},
        headers=maintainer_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["workflow_run_id"] == workflow_run_id
    assert item["source_channel"] == "runtime"
    assert item["delivery_channel"] == "runtime"
    assert item["delivery_status"] == "sent"
    receipt_id = item["receipt_id"]
    assert item["metadata"]["message"]["receive_id"] == "oc_surface"

    updated = client.post(
        f"/notifications/deliveries/{receipt_id}/status",
        headers=maintainer_headers,
        json={
            "delivery_status": "delivered",
            "provider_message_id": "msg-runtime-1",
            "metadata_patch": {"webhook": "ack"},
        },
    )
    assert updated.status_code == 200
    updated_payload = updated.json()
    assert updated_payload["delivery_status"] == "delivered"
    assert updated_payload["provider_message_id"] == "msg-runtime-1"
    assert updated_payload["metadata"]["provider_update"]["webhook"] == "ack"


def test_runtime_sla_endpoint_returns_snapshot_with_notifications(client: TestClient) -> None:
    project_id = "proj-sla-scope"
    iteration_id = "iter-sla-scope"
    workflow_run_id = "run-observability-sla"
    trace_id = "trace-observability-sla"
    _seed_project(client, project_id)
    _seed_iteration(client, project_id, iteration_id)
    persistence = RuntimePersistenceService(client.app.state.session_factory)
    persistence.ensure_workflow_run(
        workflow_run_id=workflow_run_id,
        project_id=project_id,
        iteration_id=iteration_id,
        workflow_name="project.improvement",
        trace_id=trace_id,
        initiated_by="tests",
        objective="verify runtime sla endpoint",
    )
    base = datetime.now(UTC) - timedelta(minutes=5)
    events: list[tuple[EventType, str, datetime]] = [
        (EventType.APPROVAL_REQUESTED, "task-approval", base + timedelta(seconds=0)),
        (EventType.APPROVAL_RESOLVED, "task-approval", base + timedelta(seconds=20)),
        (EventType.WORKFLOW_RETRYING, "task-retry", base + timedelta(seconds=30)),
        (EventType.TASK_CLAIMED, "task-retry", base + timedelta(seconds=45)),
    ]
    for index, (event_type, task_id, occurred_at) in enumerate(events, start=1):
        persistence.append_event(
            RunEventEnvelope(
                event_id=f"evt-observability-{index}",
                event_type=event_type,
                schema_version="1.0.0",
                payload_version="1.0.0",
                sequence=index,
                producer="tests",
                occurred_at=occurred_at.isoformat(),
                idempotency_key=f"observability-{index}",
                correlation=CorrelationIds(
                    workflow_run_id=workflow_run_id,
                    trace_id=trace_id,
                    task_id=task_id,
                    attempt_id=f"attempt-{task_id}",
                ),
                payload={"summary": event_type.value},
            )
        )
    history = NotificationHistoryService(client.app.state.session_factory)
    NotificationService(
        adapters=[InMemoryNotificationAdapter()],
        recorders=[PersistentNotificationRecorder(history)],
    ).send(
        NotificationMessage(
            channel="runtime",
            title="done",
            body="done",
            correlation=CorrelationIds(workflow_run_id=workflow_run_id, trace_id=trace_id),
            metadata={},
        )
    )

    response = client.get(
        "/observability/runtime-sla",
        params={
            "window_hours": 24,
            "project_id": project_id,
            "iteration_id": iteration_id,
            "bucket_minutes": 15,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"]["project_id"] == project_id
    assert payload["scope"]["iteration_id"] == iteration_id
    assert payload["trend"]["bucket_minutes"] == 15
    assert len(payload["trend"]["points"]) >= 1
    assert payload["run_count"] >= 1
    assert payload["approval_resolution"]["count"] == 1
    assert payload["retry_recovery"]["count"] == 1
    assert payload["notifications"]["total"] == 1
    assert "runtime" in payload["notifications"]["channels"]
