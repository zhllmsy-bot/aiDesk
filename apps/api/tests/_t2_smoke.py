import sys

sys.path.insert(0, ".")

from fastapi import FastAPI

from api.database import Base, create_session_factory
from api.events.builder import RuntimeEventBuilder
from api.models import register_models
from api.runtime_contracts import EventType, TaskStatus, WorkflowName
from api.runtime_persistence.service import RuntimePersistenceService
from api.workflows.recovery import RecoveryDecision, RecoveryResult
from api.workflows.router import router

register_models()
factory = create_session_factory("sqlite+pysqlite:///:memory:")
engine = factory.kw["bind"]
Base.metadata.create_all(engine)

persistence = RuntimePersistenceService(factory)
persistence.ensure_workflow_run(
    workflow_run_id="run-1",
    project_id=None,
    iteration_id=None,
    workflow_name=WorkflowName.PROJECT_PLANNING.value,
    trace_id="trace-1",
    initiated_by="tests",
    objective="test",
)
persistence.ensure_task(
    workflow_run_id="run-1",
    task_id="task-1",
    title="Task 1",
    graph_kind="planner",
    executor_summary="planner",
)
persistence.ensure_attempt(
    workflow_run_id="run-1",
    task_id="task-1",
    attempt_id="attempt-1",
)

# Test heartbeat
claim = persistence.claim_task(
    task_id="task-1",
    workflow_run_id="run-1",
    attempt_id="attempt-1",
    worker_id="worker-1",
    lease_timeout_seconds=30,
)
print(f"Claim created: {claim.claim_id}")
assert claim.claim_id is not None

updated = persistence.heartbeat(claim.claim_id)
print(f"Heartbeat updated: {updated.heartbeat_at}")
assert updated.heartbeat_at >= claim.heartbeat_at

# Test multiple heartbeats
hb_times = [claim.heartbeat_at]
for _ in range(3):
    updated = persistence.heartbeat(claim.claim_id)
    hb_times.append(updated.heartbeat_at)
for i in range(1, len(hb_times)):
    assert hb_times[i] >= hb_times[i - 1], f"Heartbeat not monotonic: {hb_times}"
print("Multiple heartbeats: OK")

# Test stale claim scan
stale = persistence.scan_all_stale_claims()
assert len(stale) == 0, f"Expected 0 stale, got {len(stale)}"
print("Stale scan (no stale): OK")

# Test force reclaim
reclaimed = persistence.reclaim_stale_claims(
    workflow_run_id="run-1",
    force_claim_ids=[claim.claim_id],
)
assert len(reclaimed) == 1, f"Expected 1 reclaimed, got {len(reclaimed)}"
print(f"Force reclaim: OK ({reclaimed[0].status.value})")

# Test projector - timeline
persistence2 = RuntimePersistenceService(create_session_factory("sqlite+pysqlite:///:memory:"))
register_models()
factory2 = create_session_factory("sqlite+pysqlite:///:memory:")
engine2 = factory2.kw["bind"]
Base.metadata.create_all(engine2)
ps = RuntimePersistenceService(factory2)
ps.ensure_workflow_run(
    workflow_run_id="run-2",
    project_id=None,
    iteration_id=None,
    workflow_name=WorkflowName.PROJECT_PLANNING.value,
    trace_id="trace-2",
    initiated_by="tests",
    objective="test projector",
)
ps.ensure_task(
    workflow_run_id="run-2",
    task_id="task-2",
    title="Task 2",
    graph_kind="planner",
    executor_summary="planner",
)
ps.ensure_attempt(
    workflow_run_id="run-2",
    task_id="task-2",
    attempt_id="attempt-2",
)

builder = RuntimeEventBuilder(producer="tests.t2")
correlation = {
    "workflow_run_id": "run-2",
    "trace_id": "trace-2",
    "task_id": "task-2",
    "attempt_id": "attempt-2",
}
event1 = builder.build(
    event_type=EventType.TASK_CLAIMED,
    sequence=ps.next_sequence("run-2"),
    correlation=correlation,
    payload={"to_status": TaskStatus.CLAIMED.value, "summary": "claimed"},
)
ps.append(event1)
event2 = builder.build(
    event_type=EventType.TASK_COMPLETED,
    sequence=ps.next_sequence("run-2"),
    correlation=correlation,
    payload={"to_status": TaskStatus.COMPLETED.value, "summary": "completed"},
)
ps.append(event2)

timeline = ps.projector.get_timeline("run-2")
assert len(timeline.entries) == 2, f"Expected 2 timeline entries, got {len(timeline.entries)}"
print(f"Timeline projector: OK ({len(timeline.entries)} entries)")

attempts = ps.projector.get_attempts("task-2")
assert len(attempts.attempts) == 1, f"Expected 1 attempt, got {len(attempts.attempts)}"
print(f"Attempt projector: OK ({len(attempts.attempts)} attempts)")

result = RecoveryResult(
    claim_id="test-claim",
    task_id="test-task",
    workflow_run_id="test-run",
    decision=RecoveryDecision.REQUEUE,
    detail="test",
)
assert result.decision == RecoveryDecision.REQUEUE
print("Recovery module: OK")

app = FastAPI()
app.include_router(router)
found = False
for route in app.routes:
    if hasattr(route, "path") and route.path == "/runtime/dev/bootstrap":
        assert getattr(route, "deprecated", False) is True, "Bootstrap should be deprecated"
        found = True
        break
assert found, "Bootstrap route not found"
print("Bootstrap deprecation: OK")

print("\n=== All T2 core checks passed! ===")
