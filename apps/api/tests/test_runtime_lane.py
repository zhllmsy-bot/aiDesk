from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.agent_runtime.models import GraphExecutionRequest
from api.agent_runtime.service import RuntimeGraphService
from api.app import create_app
from api.database import create_session_factory
from api.events.builder import RuntimeEventBuilder
from api.runtime_contracts import (
    EventType,
    GraphExecutionStatus,
    GraphKind,
    TaskStatus,
    WorkflowName,
    WorkflowRunStatus,
)
from api.runtime_persistence.service import RuntimePersistenceService
from api.workflows.lease_manager import ClaimLeaseManager
from api.workflows.state_machine import (
    InvalidTransitionError,
    transition_task_status,
    transition_workflow_run_status,
)
from tests.helpers import build_test_settings, run_migrations


def _runtime_client(tmp_path: Path) -> TestClient:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'runtime.db'}"
    run_migrations(database_url)
    settings = build_test_settings(
        database_url=database_url,
        runtime_worker_id="runtime-worker",
    )
    return TestClient(create_app(settings))


def test_state_machine_allows_expected_transitions() -> None:
    workflow_transition = transition_workflow_run_status(
        WorkflowRunStatus.RUNNING.value,
        WorkflowRunStatus.RETRYING.value,
        "retry requested",
    )
    task_transition = transition_task_status(
        TaskStatus.RUNNING.value,
        TaskStatus.VERIFYING.value,
        "begin verification",
    )
    assert workflow_transition.to_status == WorkflowRunStatus.RETRYING.value
    assert task_transition.to_status == TaskStatus.VERIFYING.value


def test_state_machine_rejects_invalid_transition() -> None:
    with pytest.raises(InvalidTransitionError):
        transition_task_status(TaskStatus.QUEUED.value, TaskStatus.COMPLETED.value, "skip ahead")


def test_claim_manager_enforces_single_active_claim_and_reclaim() -> None:
    manager = ClaimLeaseManager()
    claim = manager.claim_task(
        task_id="task-1",
        workflow_run_id="run-1",
        attempt_id="attempt-1",
        worker_id="worker-1",
        lease_timeout_seconds=30,
    )
    with pytest.raises(ValueError):
        manager.claim_task(
            task_id="task-1",
            workflow_run_id="run-1",
            attempt_id="attempt-2",
            worker_id="worker-2",
            lease_timeout_seconds=30,
        )
    reclaimed = manager.reclaim_stale_claims(
        workflow_run_id="run-1", force_claim_ids=[claim.claim_id]
    )
    assert len(reclaimed) == 1
    assert reclaimed[0].status.value == "reclaimed"


def test_event_store_projects_timeline_graph_attempts_and_worker_health() -> None:
    database_url = "sqlite+pysqlite:///:memory:"
    factory = create_session_factory(database_url)
    from api.models import register_models

    register_models()
    engine = factory.kw["bind"]
    assert engine is not None
    from api.database import Base

    Base.metadata.create_all(engine)
    store = RuntimePersistenceService(factory)
    store.ensure_workflow_run(
        workflow_run_id="run-1",
        project_id=None,
        iteration_id=None,
        workflow_name=WorkflowName.PROJECT_PLANNING.value,
        trace_id="trace-1",
        initiated_by="tests",
        objective="test run",
    )
    store.ensure_task(
        workflow_run_id="run-1",
        task_id="task-1",
        title="Task 1",
        graph_kind=GraphKind.PLANNER.value,
        executor_summary="planner",
    )
    store.ensure_attempt(
        workflow_run_id="run-1",
        task_id="task-1",
        attempt_id="attempt-1",
    )
    builder = RuntimeEventBuilder(producer="tests.runtime")
    correlation = {
        "workflow_run_id": "run-1",
        "trace_id": "trace-1",
        "task_id": "task-1",
        "attempt_id": "attempt-1",
    }
    events = [
        builder.build(
            event_type=EventType.TASK_CLAIMED,
            sequence=store.next_sequence("run-1"),
            correlation=correlation,
            payload={"to_status": TaskStatus.CLAIMED.value, "summary": "claimed"},
        ),
        builder.build(
            event_type=EventType.TASK_GRAPH_UPDATED,
            sequence=store.next_sequence("run-1") + 1,
            correlation=correlation,
            payload={
                "nodes": [
                    {
                        "task_id": "task-1",
                        "title": "Task 1",
                        "status": TaskStatus.CLAIMED.value,
                        "blocked_reason": None,
                        "executor_summary": "planner",
                    }
                ],
                "edges": [],
                "summary": "graph updated",
            },
        ),
        builder.build(
            event_type=EventType.TASK_COMPLETED,
            sequence=store.next_sequence("run-1") + 3,
            correlation=correlation,
            payload={"to_status": TaskStatus.COMPLETED.value, "summary": "completed"},
        ),
    ]
    events.insert(
        2,
        builder.build(
            event_type=EventType.TASK_TODO_UPDATED,
            sequence=store.next_sequence("run-1") + 2,
            correlation=correlation,
            payload={
                "summary": "todo updated",
                "todo_items": [
                    {
                        "id": "context",
                        "title": "Assemble context",
                        "status": "completed",
                    },
                    {
                        "id": "verify",
                        "title": "Run verification",
                        "status": "running",
                    },
                ],
            },
        ),
    )
    for event in events:
        store.append(event)

    worker_event = builder.build(
        event_type=EventType.WORKER_HEALTH_REPORTED,
        sequence=store.next_sequence("worker-health::runtime-worker"),
        correlation={
            "workflow_run_id": "worker-health::runtime-worker",
            "trace_id": "trace-worker",
        },
        payload={
            "worker_id": "runtime-worker",
            "task_queue": "ai-desk.runtime",
            "status": "healthy",
            "detail": "worker alive",
            "active_workflow_names": [WorkflowName.PROJECT_PLANNING.value],
        },
    )
    store.append(worker_event)

    timeline = store.get_timeline("run-1")
    graph = store.get_graph("run-1")
    attempts = store.get_attempts("task-1")
    workers = store.get_workers_health()

    assert len(timeline.entries) == 4
    assert graph.nodes[0].status == TaskStatus.COMPLETED
    assert graph.nodes[0].todo_items[0].title == "Assemble context"
    assert graph.nodes[0].todo_items[1].status == "running"
    assert attempts.attempts[0].ended_at is not None
    assert workers[0].worker_id == "runtime-worker"


def test_runtime_todo_event_does_not_rewrite_terminal_attempt_end_time() -> None:
    database_url = "sqlite+pysqlite:///:memory:"
    factory = create_session_factory(database_url)
    from api.models import register_models

    register_models()
    engine = factory.kw["bind"]
    assert engine is not None
    from api.database import Base

    Base.metadata.create_all(engine)
    store = RuntimePersistenceService(factory)
    store.ensure_workflow_run(
        workflow_run_id="run-1",
        project_id=None,
        iteration_id=None,
        workflow_name=WorkflowName.PROJECT_PLANNING.value,
        trace_id="trace-1",
        initiated_by="tests",
        objective="test run",
    )
    store.ensure_task(
        workflow_run_id="run-1",
        task_id="task-1",
        title="Task 1",
        graph_kind=GraphKind.PLANNER.value,
        executor_summary="planner",
    )
    store.ensure_attempt(
        workflow_run_id="run-1",
        task_id="task-1",
        attempt_id="attempt-1",
    )
    builder = RuntimeEventBuilder(producer="tests.runtime")
    correlation = {
        "workflow_run_id": "run-1",
        "trace_id": "trace-1",
        "task_id": "task-1",
        "attempt_id": "attempt-1",
    }
    store.append(
        builder.build(
            event_type=EventType.TASK_FAILED,
            sequence=store.next_sequence("run-1"),
            correlation=correlation,
            payload={"to_status": TaskStatus.FAILED.value, "summary": "failed"},
        )
    )
    ended_at = store.get_attempts("task-1").attempts[0].ended_at
    assert ended_at is not None

    store.append(
        builder.build(
            event_type=EventType.TASK_TODO_UPDATED,
            sequence=store.next_sequence("run-1"),
            correlation=correlation,
            payload={
                "summary": "todo updated after terminal event",
                "todo_items": [
                    {
                        "id": "summarize",
                        "title": "Publish failure evidence",
                        "status": "completed",
                    }
                ],
            },
        )
    )

    attempt = store.get_attempts("task-1").attempts[0]
    assert attempt.status == TaskStatus.FAILED
    assert attempt.ended_at == ended_at


def test_runtime_graph_service_supports_interrupt_and_resume() -> None:
    database_url = "sqlite+pysqlite:///:memory:"
    factory = create_session_factory(database_url)
    from api.models import register_models

    register_models()
    engine = factory.kw["bind"]
    assert engine is not None
    from api.database import Base

    Base.metadata.create_all(engine)
    persistence = RuntimePersistenceService(factory)
    persistence.ensure_workflow_run(
        workflow_run_id="run-1",
        project_id=None,
        iteration_id=None,
        workflow_name=WorkflowName.PROJECT_PLANNING.value,
        trace_id="trace-1",
        initiated_by="tests",
        objective="Plan the rollout",
    )
    service = RuntimeGraphService(checkpoint_store=persistence)
    request = GraphExecutionRequest.model_validate(
        {
            "graph_kind": GraphKind.PLANNER.value,
            "objective": "Plan the rollout",
            "correlation": {"workflow_run_id": "run-1", "trace_id": "trace-1"},
            "interrupt_before_finalize": True,
        }
    )
    interrupted = service.execute(request)
    assert interrupted.status == GraphExecutionStatus.INTERRUPTED
    checkpoint_id = interrupted.checkpoint["checkpoint_id"]
    resumed = service.execute(
        GraphExecutionRequest.model_validate(
            {
                "graph_kind": GraphKind.PLANNER.value,
                "objective": "Plan the rollout",
                "correlation": {"workflow_run_id": "run-1", "trace_id": "trace-1"},
                "checkpoint_id": checkpoint_id,
            }
        )
    )
    assert resumed.status == GraphExecutionStatus.COMPLETED
    assert resumed.structured_output["plan_steps"]


def test_runtime_graph_rejects_legacy_checkpoint_shape() -> None:
    database_url = "sqlite+pysqlite:///:memory:"
    factory = create_session_factory(database_url)
    from api.models import register_models

    register_models()
    engine = factory.kw["bind"]
    assert engine is not None
    from api.database import Base

    Base.metadata.create_all(engine)
    persistence = RuntimePersistenceService(factory)
    persistence.ensure_workflow_run(
        workflow_run_id="run-legacy",
        project_id=None,
        iteration_id=None,
        workflow_name=WorkflowName.PROJECT_PLANNING.value,
        trace_id="trace-legacy",
        initiated_by="tests",
        objective="Reject legacy checkpoint",
    )
    service = RuntimeGraphService(checkpoint_store=persistence)

    with pytest.raises(ValueError, match="thread_id"):
        service.execute(
            GraphExecutionRequest.model_validate(
                {
                    "graph_kind": GraphKind.PLANNER.value,
                    "objective": "Reject legacy checkpoint",
                    "correlation": {
                        "workflow_run_id": "run-legacy",
                        "trace_id": "trace-legacy",
                    },
                    "checkpoint": {
                        "graph_kind": GraphKind.PLANNER.value,
                        "prepared": {"summary": "legacy", "items": []},
                    },
                }
            )
        )


def test_runtime_api_bootstrap_and_read_models(tmp_path: Path) -> None:
    client = _runtime_client(tmp_path)
    bootstrap = client.post(
        "/runtime/dev/bootstrap?workflow_name=project.planning&include_retry=true&include_interrupt=true"
    )
    assert bootstrap.status_code == 202
    workflow_run_id = bootstrap.json()["workflow_run_id"]

    timeline = client.get(f"/runtime/runs/{workflow_run_id}/timeline")
    graph = client.get(f"/runtime/runs/{workflow_run_id}/graph")
    attempts = client.get("/runtime/tasks/task-1/attempts")
    workers = client.get("/runtime/workers/health")

    assert timeline.status_code == 200
    assert any(entry["event_type"] == "workflow.retrying" for entry in timeline.json()["entries"])
    assert graph.status_code == 200
    assert graph.json()["nodes"][0]["task_id"] == "task-1"
    assert attempts.status_code == 200
    assert attempts.json()["attempts"][0]["task_id"] == "task-1"
    assert workers.status_code == 200
    assert workers.json()[0]["worker_id"] == "runtime-worker"
