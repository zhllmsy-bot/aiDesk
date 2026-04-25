from __future__ import annotations

from dataclasses import asdict

from api.database import create_session_factory
from api.events.builder import RuntimeEventBuilder
from api.runtime_contracts import EventType, TaskStatus, WorkflowName
from api.runtime_persistence.models import ClaimStatusDB, TaskStatusDB
from api.runtime_persistence.service import RuntimePersistenceService


def _init_db(database_url: str) -> RuntimePersistenceService:
    factory = create_session_factory(database_url)
    from api.models import register_models

    register_models()
    engine = factory.kw["bind"]
    assert engine is not None
    from api.database import Base

    Base.metadata.create_all(engine)
    return RuntimePersistenceService(factory)


def _seed_run(persistence: RuntimePersistenceService, workflow_run_id: str = "run-1") -> None:
    persistence.ensure_workflow_run(
        workflow_run_id=workflow_run_id,
        project_id=None,
        iteration_id=None,
        workflow_name=WorkflowName.PROJECT_PLANNING.value,
        trace_id="trace-1",
        initiated_by="tests",
        objective="test run",
    )
    persistence.ensure_task(
        workflow_run_id=workflow_run_id,
        task_id="task-1",
        title="Task 1",
        graph_kind="planner",
        executor_summary="planner",
    )
    persistence.ensure_attempt(
        workflow_run_id=workflow_run_id,
        task_id="task-1",
        attempt_id="attempt-1",
    )


def _seed_events(persistence: RuntimePersistenceService, workflow_run_id: str = "run-1") -> None:
    builder = RuntimeEventBuilder(producer="tests.t2")
    correlation = {
        "workflow_run_id": workflow_run_id,
        "trace_id": "trace-1",
        "task_id": "task-1",
        "attempt_id": "attempt-1",
    }
    event1 = builder.build(
        event_type=EventType.TASK_CLAIMED,
        sequence=persistence.next_sequence(workflow_run_id),
        correlation=correlation,
        payload={"to_status": TaskStatus.CLAIMED.value, "summary": "claimed"},
    )
    persistence.append(event1)
    event2 = builder.build(
        event_type=EventType.TASK_GRAPH_UPDATED,
        sequence=persistence.next_sequence(workflow_run_id),
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
    )
    persistence.append(event2)
    event3 = builder.build(
        event_type=EventType.TASK_COMPLETED,
        sequence=persistence.next_sequence(workflow_run_id),
        correlation=correlation,
        payload={"to_status": TaskStatus.COMPLETED.value, "summary": "completed"},
    )
    persistence.append(event3)


def test_heartbeat_updates_claim_lease() -> None:
    persistence = _init_db("sqlite+pysqlite:///:memory:")
    _seed_run(persistence)
    claim = persistence.claim_task(
        task_id="task-1",
        workflow_run_id="run-1",
        attempt_id="attempt-1",
        worker_id="worker-1",
        lease_timeout_seconds=30,
    )
    original_heartbeat = claim.heartbeat_at
    updated = persistence.heartbeat(claim.claim_id)
    assert updated.heartbeat_at >= original_heartbeat


def test_heartbeat_multiple_times_extends_lease() -> None:
    persistence = _init_db("sqlite+pysqlite:///:memory:")
    _seed_run(persistence)
    claim = persistence.claim_task(
        task_id="task-1",
        workflow_run_id="run-1",
        attempt_id="attempt-1",
        worker_id="worker-1",
        lease_timeout_seconds=30,
    )
    heartbeats = [claim.heartbeat_at]
    for _ in range(3):
        updated = persistence.heartbeat(claim.claim_id)
        heartbeats.append(updated.heartbeat_at)
    for i in range(1, len(heartbeats)):
        assert heartbeats[i] >= heartbeats[i - 1]


def test_recovery_job_reclaims_stale_claims() -> None:
    persistence = _init_db("sqlite+pysqlite:///:memory:")
    _seed_run(persistence)
    claim = persistence.claim_task(
        task_id="task-1",
        workflow_run_id="run-1",
        attempt_id="attempt-1",
        worker_id="worker-1",
        lease_timeout_seconds=1,
    )
    stale = persistence.scan_all_stale_claims()
    assert len(stale) == 0
    reclaimed = persistence.reclaim_stale_claims(
        workflow_run_id="run-1",
        force_claim_ids=[claim.claim_id],
    )
    assert len(reclaimed) == 1
    assert reclaimed[0].status.value == "reclaimed"


def test_recovery_job_scans_all_stale_claims() -> None:
    persistence = _init_db("sqlite+pysqlite:///:memory:")
    _seed_run(persistence, "run-1")
    _seed_run(persistence, "run-2")
    persistence.ensure_task(
        workflow_run_id="run-2",
        task_id="task-2",
        title="Task 2",
        graph_kind="planner",
        executor_summary="planner",
    )
    persistence.ensure_attempt(
        workflow_run_id="run-2",
        task_id="task-2",
        attempt_id="attempt-2",
    )
    persistence.claim_task(
        task_id="task-1",
        workflow_run_id="run-1",
        attempt_id="attempt-1",
        worker_id="worker-1",
        lease_timeout_seconds=1,
    )
    persistence.claim_task(
        task_id="task-2",
        workflow_run_id="run-2",
        attempt_id="attempt-2",
        worker_id="worker-1",
        lease_timeout_seconds=1,
    )
    stale = persistence.scan_all_stale_claims()
    assert len(stale) == 0
    claim1 = persistence.reclaim_stale_claims(
        workflow_run_id="run-1",
        force_claim_ids=["claim-attempt-1"],
    )
    claim2 = persistence.reclaim_stale_claims(
        workflow_run_id="run-2",
        force_claim_ids=["claim-attempt-2"],
    )
    assert len(claim1) == 1
    assert len(claim2) == 1


def test_projector_service_builds_timeline() -> None:
    persistence = _init_db("sqlite+pysqlite:///:memory:")
    _seed_run(persistence)
    _seed_events(persistence)
    timeline = persistence.projector.get_timeline("run-1")
    assert len(timeline.entries) == 3
    assert timeline.entries[0].event_type == EventType.TASK_CLAIMED


def test_projector_service_builds_graph() -> None:
    persistence = _init_db("sqlite+pysqlite:///:memory:")
    _seed_run(persistence)
    _seed_events(persistence)
    graph = persistence.projector.get_graph("run-1")
    assert len(graph.nodes) == 1
    assert graph.nodes[0].status == TaskStatus.COMPLETED


def test_projector_service_builds_attempts() -> None:
    persistence = _init_db("sqlite+pysqlite:///:memory:")
    _seed_run(persistence)
    _seed_events(persistence)
    attempts = persistence.projector.get_attempts("task-1")
    assert len(attempts.attempts) == 1
    assert attempts.attempts[0].attempt_id == "attempt-1"


def test_projector_service_builds_worker_health() -> None:
    persistence = _init_db("sqlite+pysqlite:///:memory:")
    _seed_run(persistence)
    builder = RuntimeEventBuilder(producer="tests.t2")
    worker_event = builder.build(
        event_type=EventType.WORKER_HEALTH_REPORTED,
        sequence=persistence.next_sequence("worker-health::w1"),
        correlation={"workflow_run_id": "worker-health::w1", "trace_id": "trace-w1"},
        payload={
            "worker_id": "w1",
            "task_queue": "ai-desk.runtime",
            "status": "healthy",
            "detail": "alive",
            "active_workflow_names": [WorkflowName.PROJECT_PLANNING.value],
        },
    )
    persistence.append(worker_event)
    workers = persistence.projector.get_workers_health()
    assert len(workers) == 1
    assert workers[0].worker_id == "w1"


def test_standalone_projectors_match_persistence_service() -> None:
    persistence = _init_db("sqlite+pysqlite:///:memory:")
    _seed_run(persistence)
    _seed_events(persistence)
    builder = RuntimeEventBuilder(producer="tests.t2")
    worker_event = builder.build(
        event_type=EventType.WORKER_HEALTH_REPORTED,
        sequence=persistence.next_sequence("worker-health::w1"),
        correlation={"workflow_run_id": "worker-health::w1", "trace_id": "trace-w1"},
        payload={
            "worker_id": "w1",
            "task_queue": "ai-desk.runtime",
            "status": "healthy",
            "detail": "alive",
            "active_workflow_names": [WorkflowName.PROJECT_PLANNING.value],
        },
    )
    persistence.append(worker_event)
    assert persistence.get_timeline("run-1") == persistence.projector.get_timeline("run-1")
    assert persistence.get_workers_health() == persistence.projector.get_workers_health()


def test_recovery_api_endpoint() -> None:
    persistence = _init_db("sqlite+pysqlite:///:memory:")
    _seed_run(persistence)
    persistence.claim_task(
        task_id="task-1",
        workflow_run_id="run-1",
        attempt_id="attempt-1",
        worker_id="worker-1",
        lease_timeout_seconds=30,
    )
    stale = persistence.scan_all_stale_claims()
    assert len(stale) == 0
    reclaimed = persistence.reclaim_stale_claims(
        workflow_run_id="run-1",
        force_claim_ids=["claim-attempt-1"],
    )
    assert len(reclaimed) == 1
    from api.workflows.recovery import RecoveryDecision, RecoveryResult

    result = RecoveryResult(
        claim_id=reclaimed[0].claim_id,
        task_id=reclaimed[0].task_id,
        workflow_run_id=reclaimed[0].workflow_run_id,
        decision=RecoveryDecision.REQUEUE,
        detail="test",
    )
    assert result.decision == RecoveryDecision.REQUEUE


def test_workflow_terminal_event_finalizes_inflight_task_attempt_and_claim() -> None:
    persistence = _init_db("sqlite+pysqlite:///:memory:")
    _seed_run(persistence)
    claim = persistence.claim_task(
        task_id="task-1",
        workflow_run_id="run-1",
        attempt_id="attempt-1",
        worker_id="worker-1",
        lease_timeout_seconds=30,
    )
    persistence.transition_task_status(
        task_id="task-1",
        attempt_id="attempt-1",
        target=TaskStatus.RUNNING.value,
    )
    builder = RuntimeEventBuilder(producer="tests.t2")
    failed_event = builder.build(
        event_type=EventType.WORKFLOW_FAILED,
        sequence=persistence.next_sequence("run-1"),
        correlation={"workflow_run_id": "run-1", "trace_id": "trace-1"},
        payload={"summary": "run failed in test"},
    )
    persistence.append(failed_event)

    with persistence.session_factory() as session:
        from api.runtime_persistence.models import RuntimeTask, RuntimeTaskAttempt, RuntimeTaskClaim

        task = session.get(RuntimeTask, "task-1")
        attempt = session.get(RuntimeTaskAttempt, "attempt-1")
        persisted_claim = session.get(RuntimeTaskClaim, claim.claim_id)
        assert task is not None
        assert attempt is not None
        assert persisted_claim is not None
        assert task.status == TaskStatusDB.failed
        assert task.completed_at is not None
        assert attempt.status == TaskStatusDB.failed
        assert attempt.ended_at is not None
        assert persisted_claim.status == ClaimStatusDB.reclaimed
        assert persisted_claim.reclaimed_at is not None


def test_bootstrap_endpoint_is_deprecated() -> None:
    from fastapi import FastAPI

    from api.workflows.router import router

    app = FastAPI()
    app.include_router(router)
    for route in app.routes:
        if hasattr(route, "path") and route.path == "/runtime/dev/bootstrap":
            assert getattr(route, "deprecated", False) is True
            break
    else:
        raise AssertionError("bootstrap route not found")


def test_start_runtime_workflow_preserves_explicit_runtime_full_access_metadata(
    monkeypatch,
    tmp_path,
) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.control_plane.models import Project
    from api.workflows.dependencies import configure_runtime_container
    from api.workflows.router import router
    from api.workflows.types import WorkflowRequest
    from tests.helpers import build_test_settings

    app = FastAPI()
    database_url = f"sqlite+pysqlite:///{tmp_path / 'runtime-full-access.db'}"
    settings = build_test_settings(
        database_url=database_url,
    )
    runtime_container = configure_runtime_container(settings)
    app.state.settings = settings
    app.state.runtime_container = runtime_container
    app.state.session_factory = runtime_container.persistence.session_factory

    from api.models import register_models

    register_models()
    engine = runtime_container.persistence.session_factory.kw["bind"]
    assert engine is not None
    from api.database import Base

    Base.metadata.create_all(engine)

    with runtime_container.persistence.session_factory() as session:
        session.add(
            Project(
                id="project-full-access-1",
                name="Full Access Project",
                slug="full-access-project",
                root_path="/tmp",
                default_branch="main",
            )
        )
        session.commit()

    # Mock Temporal client path so endpoint can proceed without a real Temporal cluster.
    class _Handle:
        id = "wf-id"
        run_id = "wf-run-id"

    class _Client:
        async def start_workflow(self, *args, **kwargs):  # pragma: no cover - test stub
            _ = (args, kwargs)
            return _Handle()

    async def _fake_temporal_client(_request):
        return _Client()

    monkeypatch.setattr("api.workflows.router._temporal_client", _fake_temporal_client)

    app.include_router(router)
    client = TestClient(app)

    payload = WorkflowRequest(
        workflow_run_id="run-full-access-1",
        project_id="project-full-access-1",
        initiated_by="tests",
        trace_id="trace-full-access-1",
        objective="validate full access metadata injection",
        metadata={
            "workflow_name": WorkflowName.PROJECT_IMPROVEMENT.value,
            "workspace_root_path": "/tmp",
            "workspace_writable_paths": ["/tmp"],
            "runtime_full_access": True,
        },
    )

    response = client.post("/runtime/runs/start", json=asdict(payload))
    assert response.status_code == 202, response.text

    with runtime_container.persistence.session_factory() as session:
        from api.runtime_persistence.models import RuntimeWorkflowRun

        row = session.get(RuntimeWorkflowRun, "run-full-access-1")
        assert row is not None
        assert bool(row.metadata_json.get("runtime_full_access")) is True


def test_start_runtime_workflow_rejects_oversized_workflow_run_id() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.workflows.router import MAX_WORKFLOW_RUN_ID_LENGTH, router
    from api.workflows.types import WorkflowRequest

    app = FastAPI()
    app.state.runtime_container = object()
    app.include_router(router)
    client = TestClient(app)

    payload = WorkflowRequest(
        workflow_run_id="r" * (MAX_WORKFLOW_RUN_ID_LENGTH + 1),
        project_id="project-too-long",
        initiated_by="tests",
        trace_id="trace-too-long",
        objective="validate run id length",
        metadata={"workflow_name": WorkflowName.PROJECT_IMPROVEMENT.value},
    )

    response = client.post("/runtime/runs/start", json=asdict(payload))

    assert response.status_code == 422
    assert "workflow_run_id must be 36 characters or fewer" in response.text


def test_start_runtime_workflow_defaults_project_improvement_to_self_driven_loops(
    monkeypatch,
    tmp_path,
) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.control_plane.models import Project
    from api.runtime_persistence.models import RuntimeTask, RuntimeWorkflowRun
    from api.workflows.dependencies import configure_runtime_container
    from api.workflows.router import router
    from api.workflows.types import WorkflowRequest
    from tests.helpers import build_test_settings

    app = FastAPI()
    database_url = f"sqlite+pysqlite:///{tmp_path / 'runtime-self-driven.db'}"
    settings = build_test_settings(
        database_url=database_url,
    )
    runtime_container = configure_runtime_container(settings)
    app.state.settings = settings
    app.state.runtime_container = runtime_container
    app.state.session_factory = runtime_container.persistence.session_factory

    from api.models import register_models

    register_models()
    engine = runtime_container.persistence.session_factory.kw["bind"]
    assert engine is not None
    from api.database import Base

    Base.metadata.create_all(engine)

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    with runtime_container.persistence.session_factory() as session:
        session.add(
            Project(
                id="project-self-driven-1",
                name="Self Driven Project",
                slug="self-driven-project",
                root_path=str(workspace_root),
                default_branch="main",
            )
        )
        session.commit()

    class _Handle:
        id = "wf-id"
        run_id = "wf-run-id"

    class _Client:
        async def start_workflow(self, *args, **kwargs):  # pragma: no cover - test stub
            _ = (args, kwargs)
            return _Handle()

    async def _fake_temporal_client(_request):
        return _Client()

    monkeypatch.setattr("api.workflows.router._temporal_client", _fake_temporal_client)

    app.include_router(router)
    client = TestClient(app)

    payload = WorkflowRequest(
        workflow_run_id="run-self-driven-1",
        project_id="project-self-driven-1",
        initiated_by="tests",
        trace_id="trace-self-driven-1",
        objective="verify query/start triggers self-driven improvement loops",
        metadata={
            "workflow_name": WorkflowName.PROJECT_IMPROVEMENT.value,
            "workspace_root_path": str(workspace_root),
        },
    )

    response = client.post("/runtime/runs/start", json=asdict(payload))
    assert response.status_code == 202, response.text

    with runtime_container.persistence.session_factory() as session:
        row = session.get(RuntimeWorkflowRun, "run-self-driven-1")
        assert row is not None
        assert row.metadata_json["workflow_name"] == WorkflowName.PROJECT_IMPROVEMENT.value
        assert row.metadata_json["drive_mode"] == "self_driven"
        assert row.metadata_json["loop_iterations"] == 2
        assert row.metadata_json["evaluation_pattern"] == "project_maturity_audit.three_pass"

        task_rows = (
            session.query(RuntimeTask)
            .filter(RuntimeTask.workflow_run_id == "run-self-driven-1")
            .order_by(RuntimeTask.id.asc())
            .all()
        )
        assert [task.id for task in task_rows] == [
            "run-self-driven-1::loop-1-counter-argument",
            "run-self-driven-1::loop-1-execution",
            "run-self-driven-1::loop-1-review",
            "run-self-driven-1::loop-1-roadmap",
            "run-self-driven-1::loop-1-survey",
            "run-self-driven-1::loop-2-counter-argument",
            "run-self-driven-1::loop-2-execution",
            "run-self-driven-1::loop-2-review",
            "run-self-driven-1::loop-2-roadmap",
            "run-self-driven-1::loop-2-survey",
        ]

        loop_1_execution = session.get(RuntimeTask, "run-self-driven-1::loop-1-execution")
        assert loop_1_execution is not None
        assert loop_1_execution.executor == "codex"
        assert loop_1_execution.executor_summary == "codex self-iteration"
        assert loop_1_execution.depends_on == ["run-self-driven-1::loop-1-roadmap"]

        loop_2_survey = session.get(RuntimeTask, "run-self-driven-1::loop-2-survey")
        assert loop_2_survey is not None
        assert loop_2_survey.depends_on == ["run-self-driven-1::loop-1-review"]


def test_reconcile_terminal_runs_closes_stale_running_rows() -> None:
    persistence = _init_db("sqlite+pysqlite:///:memory:")
    _seed_run(persistence)
    claim = persistence.claim_task(
        task_id="task-1",
        workflow_run_id="run-1",
        attempt_id="attempt-1",
        worker_id="worker-1",
        lease_timeout_seconds=30,
    )
    persistence.transition_task_status(
        task_id="task-1",
        attempt_id="attempt-1",
        target=TaskStatus.RUNNING.value,
    )
    persistence.transition_workflow_status(workflow_run_id="run-1", target="failed")

    with persistence.session_factory() as session:
        from api.runtime_persistence.models import RuntimeTask, RuntimeTaskAttempt, RuntimeTaskClaim

        task = session.get(RuntimeTask, "task-1")
        attempt = session.get(RuntimeTaskAttempt, "attempt-1")
        persisted_claim = session.get(RuntimeTaskClaim, claim.claim_id)
        assert task is not None
        assert attempt is not None
        assert persisted_claim is not None
        task.status = TaskStatusDB.running
        task.completed_at = None
        attempt.status = TaskStatusDB.running
        attempt.ended_at = None
        persisted_claim.status = ClaimStatusDB.active
        persisted_claim.reclaimed_at = None
        persisted_claim.expired_at = None
        session.commit()

    summary = persistence.reconcile_terminal_runs(workflow_run_ids=["run-1"])
    assert summary["runs_scanned"] == 1
    assert summary["runs_reconciled"] == 1
    assert summary["tasks_reconciled"] == 1
    assert summary["attempts_reconciled"] == 1
    assert summary["claims_reconciled"] == 1

    with persistence.session_factory() as session:
        from api.runtime_persistence.models import RuntimeTask, RuntimeTaskAttempt, RuntimeTaskClaim

        task = session.get(RuntimeTask, "task-1")
        attempt = session.get(RuntimeTaskAttempt, "attempt-1")
        persisted_claim = session.get(RuntimeTaskClaim, claim.claim_id)
        assert task is not None
        assert attempt is not None
        assert persisted_claim is not None
        assert task.status == TaskStatusDB.failed
        assert attempt.status == TaskStatusDB.failed
        assert persisted_claim.status == ClaimStatusDB.reclaimed
