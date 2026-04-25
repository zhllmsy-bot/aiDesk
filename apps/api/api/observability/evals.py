from __future__ import annotations

# pyright: reportUnknownVariableType=false
import asyncio
import json
from contextlib import suppress
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from api.agent_runtime.models import GraphExecutionRequest
from api.agent_runtime.service import RuntimeGraphService
from api.config import Settings
from api.database import Base, create_session_factory
from api.executors.contracts import (
    ApprovalResolutionPayload,
    ApprovalStatus,
    ArtifactType,
    DispatchControl,
    EvidenceKind,
    EvidenceRef,
    ExecutorInputBundle,
    MemoryType,
    MemoryWriteCandidate,
    PermissionPolicy,
    TaskInfo,
    VerifyCommand,
    WorkspaceInfo,
    WorkspaceMode,
)
from api.executors.openhands_runtime import (
    OpenHandsWorkspaceConfig,
    describe_openhands_runtime,
)
from api.models import register_models
from api.observability.metrics import get_metrics
from api.runtime_contracts import GraphExecutionStatus, GraphKind, WorkflowName
from api.runtime_persistence.service import RuntimePersistenceService
from api.security.service import SecurityPolicyService
from api.workflows.definitions.base import WorkflowExecutionContext
from api.workflows.types import ApprovalResolution, WorkflowRequest

SUITE_PATH = Path(__file__).with_name("runtime_regression_suite.json")


class EvalCase(BaseModel):
    case_id: str
    kind: str
    params: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)


class EvalSuite(BaseModel):
    suite_id: str
    title: str
    cases: list[EvalCase] = Field(default_factory=list)


class EvalCaseResult(BaseModel):
    case_id: str
    kind: str
    passed: bool
    actual: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)
    message: str


class EvalSuiteResult(BaseModel):
    suite_id: str
    title: str
    passed: bool
    passed_count: int
    failed_count: int
    results: list[EvalCaseResult] = Field(default_factory=list)


def load_runtime_regression_suite() -> EvalSuite:
    payload = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    return EvalSuite.model_validate(payload)


def run_runtime_regression_suite() -> EvalSuiteResult:
    suite = load_runtime_regression_suite()
    metrics = get_metrics()
    metrics.inc_counter("eval_suite_run", suite=suite.suite_id)

    results = [_run_case(case) for case in suite.cases]
    for result in results:
        metric_name = "eval_case_passed" if result.passed else "eval_case_failed"
        metrics.inc_counter(metric_name, suite=suite.suite_id, case_id=result.case_id)

    passed_count = sum(1 for result in results if result.passed)
    failed_count = len(results) - passed_count
    return EvalSuiteResult(
        suite_id=suite.suite_id,
        title=suite.title,
        passed=failed_count == 0,
        passed_count=passed_count,
        failed_count=failed_count,
        results=results,
    )


def _status_value(value: GraphExecutionStatus | str) -> str:
    if isinstance(value, GraphExecutionStatus):
        return value.value
    return str(value)


def _run_case(case: EvalCase) -> EvalCaseResult:
    if case.kind == "runtime_graph":
        return _run_runtime_graph_case(case)
    if case.kind == "security_gate":
        return _run_security_gate_case(case)
    if case.kind == "openhands_runtime":
        return _run_openhands_runtime_case(case)
    if case.kind == "workflow_approval_resume":
        return _run_workflow_approval_resume_case(case)
    if case.kind == "restart_durability":
        return _run_restart_durability_case(case)
    return EvalCaseResult(
        case_id=case.case_id,
        kind=case.kind,
        passed=False,
        actual={},
        expected=case.expected,
        message=f"Unsupported eval case kind: {case.kind}",
    )


def _run_runtime_graph_case(case: EvalCase) -> EvalCaseResult:
    database_url = "sqlite+pysqlite:///:memory:"
    register_models()
    factory = create_session_factory(database_url)
    engine = factory.kw["bind"]
    assert engine is not None
    Base.metadata.create_all(engine)
    persistence = RuntimePersistenceService(factory)
    workflow_run_id = f"eval::{case.case_id}"
    trace_id = f"trace::{case.case_id}"
    persistence.ensure_workflow_run(
        workflow_run_id=workflow_run_id,
        project_id=None,
        iteration_id=None,
        workflow_name=WorkflowName.PROJECT_PLANNING.value,
        trace_id=trace_id,
        initiated_by="eval_harness",
        objective=str(case.params.get("objective", "Eval objective")),
    )
    service = RuntimeGraphService(checkpoint_store=persistence)
    graph_kind = GraphKind(str(case.params.get("graph_kind", GraphKind.PLANNER.value)))
    objective = str(case.params.get("objective", "Eval objective"))

    interrupted = service.execute(
        GraphExecutionRequest.model_validate(
            {
                "graph_kind": graph_kind.value,
                "objective": objective,
                "correlation": {
                    "workflow_run_id": workflow_run_id,
                    "trace_id": trace_id,
                },
                "interrupt_before_finalize": True,
            }
        )
    )
    if interrupted.checkpoint is None:
        raise RuntimeError("interrupted graph did not return a checkpoint")
    resumed = service.execute(
        GraphExecutionRequest.model_validate(
            {
                "graph_kind": graph_kind.value,
                "objective": objective,
                "correlation": {
                    "workflow_run_id": workflow_run_id,
                    "trace_id": trace_id,
                },
                "checkpoint_id": interrupted.checkpoint["checkpoint_id"],
            }
        )
    )

    output_key = str(case.expected.get("output_key", "plan_steps"))
    interrupted_status = _status_value(interrupted.status)
    resumed_status = _status_value(resumed.status)
    actual = {
        "status": resumed_status,
        "output_keys": sorted(resumed.structured_output.keys()),
        "checkpoint_id": interrupted.checkpoint.get("checkpoint_id"),
    }
    passed = (
        interrupted_status == GraphExecutionStatus.INTERRUPTED.value
        and resumed_status == GraphExecutionStatus.COMPLETED.value
        and output_key in resumed.structured_output
    )
    return EvalCaseResult(
        case_id=case.case_id,
        kind=case.kind,
        passed=passed,
        actual=actual,
        expected=case.expected,
        message=(
            "LangGraph interrupt/resume completed"
            if passed
            else "LangGraph interrupt/resume regression detected"
        ),
    )


def _run_security_gate_case(case: EvalCase) -> EvalCaseResult:
    workspace_root = str(case.params.get("workspace_root", "/repo/project"))
    writable_path = str(case.params.get("writable_path", workspace_root))
    proposed_command = str(case.params.get("proposed_command", "pytest -q"))
    bundle = ExecutorInputBundle(
        task=TaskInfo(
            task_id=f"eval::{case.case_id}",
            run_id="eval-run",
            title="Eval security gate",
            description="Validate write approval policy",
            executor="codex",
            expected_artifact_types=[ArtifactType.LOG],
        ),
        workspace=WorkspaceInfo(
            project_id="eval-project",
            workspace_ref="eval-workspace",
            root_path=workspace_root,
            mode=WorkspaceMode.WORKTREE,
            writable_paths=[writable_path],
        ),
        context_blocks=[],
        permission_policy=PermissionPolicy(
            workspace_allowlist=[workspace_root],
            allowed_write_paths=[writable_path],
            command_allowlist=["pytest"],
            command_denylist=[],
            require_manual_approval_for_write=True,
            secret_broker_enabled=False,
            workspace_mode=WorkspaceMode.WORKTREE,
        ),
        verify_commands=[],
        proposed_commands=[proposed_command],
        secret_usages=[],
        evidence_refs=[],
        dispatch=DispatchControl(idempotency_key=f"eval::{case.case_id}"),
    )
    decision = SecurityPolicyService().evaluate(bundle)
    actual = {
        "needs_approval": decision.needs_approval,
        "reason": decision.reason,
        "required_scope": decision.required_scope,
    }
    reason_contains = str(case.expected.get("reason_contains", ""))
    passed = decision.needs_approval and reason_contains in (decision.reason or "")
    return EvalCaseResult(
        case_id=case.case_id,
        kind=case.kind,
        passed=passed,
        actual=actual,
        expected=case.expected,
        message=(
            "Security gate still requires manual approval for writes"
            if passed
            else "Security approval gate regressed"
        ),
    )


def _run_openhands_runtime_case(case: EvalCase) -> EvalCaseResult:
    status = describe_openhands_runtime(
        OpenHandsWorkspaceConfig(
            host=case.params.get("host"),
            allow_local_workspace=bool(case.params.get("allow_local_workspace", False)),
        )
    )
    expected_status = str(case.expected.get("status", "not_configured"))
    passed = status.get("status") == expected_status
    return EvalCaseResult(
        case_id=case.case_id,
        kind=case.kind,
        passed=passed,
        actual=status,
        expected=case.expected,
        message=(
            "OpenHands runtime requires explicit remote or local opt-in"
            if passed
            else "OpenHands runtime default safety regressed"
        ),
    )


def _run_workflow_approval_resume_case(case: EvalCase) -> EvalCaseResult:
    actual = asyncio.run(_await_workflow_approval_resolution(case))
    expected_approval_id = str(case.expected.get("approval_id", "approval-eval"))
    expected_actor = str(case.expected.get("actor", "eval-approver"))
    expected_path = str(case.expected.get("approved_write_path", "/repo/project/apps/api"))
    passed = (
        actual["approval_id"] == expected_approval_id
        and actual["approved"] is True
        and actual["actor"] == expected_actor
        and actual["approved_write_paths"] == [expected_path]
        and actual["reset_count"] == 1
    )
    return EvalCaseResult(
        case_id=case.case_id,
        kind=case.kind,
        passed=passed,
        actual=actual,
        expected=case.expected,
        message=(
            "Workflow approval wait/resume semantics remain intact"
            if passed
            else "Workflow approval wait/resume regression detected"
        ),
    )


async def _await_workflow_approval_resolution(case: EvalCase) -> dict[str, Any]:
    approval_slot: dict[str, ApprovalResolution | None] = {"value": None}
    reset_count = 0
    signal_delay_seconds = float(case.params.get("signal_delay_seconds", 0.01))
    approval_id = str(case.expected.get("approval_id", "approval-eval"))
    actor = str(case.expected.get("actor", "eval-approver"))
    approved_write_path = str(
        case.expected.get("approved_write_path", "/repo/project/apps/api")
    )

    async def fake_wait_condition(
        predicate: Any,
        *,
        timeout: Any,
        timeout_summary: str | None = None,
    ) -> None:
        deadline = asyncio.get_running_loop().time() + timeout.total_seconds()
        while asyncio.get_running_loop().time() < deadline:
            if predicate():
                return
            await asyncio.sleep(0.001)
        raise TimeoutError(timeout_summary or "timed out waiting for approval")

    def approval_getter() -> ApprovalResolution | None:
        return approval_slot["value"]

    def approval_reset() -> None:
        nonlocal reset_count
        approval_slot["value"] = None
        reset_count += 1

    context = WorkflowExecutionContext(
        workflow_name=WorkflowName.PROJECT_PLANNING.value,
        request=WorkflowRequest(
            workflow_run_id=f"eval::{case.case_id}",
            project_id="project-eval",
            initiated_by="eval_harness",
            trace_id=f"trace::{case.case_id}",
            objective="Validate workflow approval resume semantics",
            signal_timeout_seconds=max(int(case.params.get("signal_timeout_seconds", 1)), 1),
        ),
        approval_getter=approval_getter,
        approval_reset=approval_reset,
        worker_id="eval-worker",
    )

    async def resolve_later() -> None:
        await asyncio.sleep(signal_delay_seconds)
        approval_slot["value"] = ApprovalResolution(
            approved=True,
            actor=actor,
            comment="approved in eval harness",
            approval_id=approval_id,
            approved_write_paths=[approved_write_path],
        )

    resolver = asyncio.create_task(resolve_later())
    try:
        with patch(
            "api.workflows.definitions.base.workflow.wait_condition",
            new=fake_wait_condition,
        ):
            resolution = await context.wait_for_approval(approval_id)
    finally:
        resolver.cancel()
        with suppress(asyncio.CancelledError):
            await resolver
    return {
        "approved": resolution.approved,
        "actor": resolution.actor,
        "approval_id": resolution.approval_id,
        "approved_write_paths": resolution.approved_write_paths,
        "reset_count": reset_count,
    }


def _run_restart_durability_case(case: EvalCase) -> EvalCaseResult:
    with TemporaryDirectory(prefix="ai-desk-eval-") as temp_dir:
        database_url = f"sqlite+pysqlite:///{Path(temp_dir) / 'restart-eval.db'}"
        _initialize_eval_database(database_url)
        bootstrap_run_id = _bootstrap_runtime_run(database_url)
        approval_id, memory_summary = _seed_review_memory_state(database_url)
        actual = _verify_state_after_restart(
            database_url=database_url,
            workflow_run_id=bootstrap_run_id,
            approval_id=approval_id,
            project_id="project-restart",
            expected_memory_summary=memory_summary,
        )

    expected_approval = str(case.expected.get("approval_status", "approved"))
    expected_event_types = sorted(case.expected.get("event_types", []))
    passed = (
        actual["approval_status"] == expected_approval
        and sorted(actual["timeline_event_types"]) == expected_event_types
        and actual["memory_summary_found"] is True
        and actual["graph_node_count"] >= 1
    )
    return EvalCaseResult(
        case_id=case.case_id,
        kind=case.kind,
        passed=passed,
        actual=actual,
        expected=case.expected,
        message=(
            "Restart durability preserved runtime, review, and memory state"
            if passed
            else "Restart durability regression detected"
        ),
    )


def _initialize_eval_database(database_url: str) -> None:
    register_models()
    factory = create_session_factory(database_url)
    engine = factory.kw["bind"]
    assert engine is not None
    Base.metadata.create_all(engine)
    engine.dispose()


def _eval_settings(database_url: str) -> Settings:
    return Settings(
        app_name="AI Desk Eval Harness",
        database_url=database_url,
        web_origin="http://localhost:3000",
        temporal_address="localhost:7233",
        temporal_namespace="eval",
        runtime_task_queue="ai-desk.runtime",
        runtime_worker_id="eval-worker",
        runtime_signal_timeout_seconds=60,
        runtime_lease_timeout_seconds=30,
    )


def _register_eval_user(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "super-secure-password",
            "display_name": "Eval Harness",
        },
    )
    response.raise_for_status()
    token = response.json()["session"]["token"]
    return {"Authorization": f"Bearer {token}"}


def _approval_bundle(case_id: str) -> ExecutorInputBundle:
    return ExecutorInputBundle(
        task=TaskInfo(
            task_id=f"task::{case_id}",
            run_id="run-restart-1",
            title="Restart durability approval task",
            description="Requires manual approval before execution",
            executor="codex",
            expected_artifact_types=[ArtifactType.PATCH],
        ),
        workspace=WorkspaceInfo(
            project_id="project-restart",
            iteration_id="iter-restart",
            workspace_ref="ws-restart",
            root_path="/repo/project",
            mode=WorkspaceMode.WORKTREE,
            writable_paths=["/repo/project/apps/api"],
        ),
        context_blocks=[],
        permission_policy=PermissionPolicy(
            workspace_allowlist=["/repo"],
            allowed_write_paths=["/repo/project/apps/api"],
            command_allowlist=["pytest"],
            command_denylist=["rm -rf"],
            require_manual_approval_for_write=True,
            workspace_mode=WorkspaceMode.WORKTREE,
        ),
        verify_commands=[VerifyCommand(id="verify-restart", command="pytest -q")],
        proposed_commands=["pytest -q"],
        secret_usages=[],
        evidence_refs=[
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                ref="artifact-restart-seed",
                summary="restart seed",
            )
        ],
        dispatch=DispatchControl(
            idempotency_key=f"dispatch::{case_id}",
            attempt_id=f"attempt::{case_id}",
        ),
    )


def _bootstrap_runtime_run(database_url: str) -> str:
    from api.app import create_app

    with TestClient(create_app(_eval_settings(database_url))) as client:
        response = client.post("/runtime/dev/bootstrap?workflow_name=project.planning")
        response.raise_for_status()
        return str(response.json()["workflow_run_id"])


def _seed_review_memory_state(database_url: str) -> tuple[str, str]:
    from api.app import create_app

    memory_summary = "Project uses modular FastAPI architecture"
    with TestClient(create_app(_eval_settings(database_url))) as client:
        headers = _register_eval_user(
            client,
            f"restart-seed-{uuid4().hex[:8]}@example.com",
        )
        dispatch_response = client.post(
            "/executors/dispatch",
            json=_approval_bundle("restart_durability").model_dump(mode="json"),
            headers=headers,
        )
        dispatch_response.raise_for_status()
        approval_id = str(dispatch_response.json()["approval"]["approval_id"])

        resolve_response = client.post(
            f"/review/approvals/{approval_id}/resolve",
            json=ApprovalResolutionPayload(
                decision=ApprovalStatus.APPROVED,
                reason="Eval harness approval before restart",
                approved_write_paths=["/repo/project/apps/api"],
            ).model_dump(mode="json"),
            headers=headers,
        )
        resolve_response.raise_for_status()

        memory_response = client.post(
            "/memory/writes",
            json=MemoryWriteCandidate(
                project_id="project-restart",
                iteration_id="iter-restart",
                memory_type=MemoryType.PROJECT_FACT,
                external_ref="doc://project-restart/facts/structure",
                summary=memory_summary,
                content_hash="hash-restart-fact",
                quality_score=0.88,
            ).model_dump(mode="json"),
            headers=headers,
        )
        memory_response.raise_for_status()
        return approval_id, memory_summary


def _verify_state_after_restart(
    *,
    database_url: str,
    workflow_run_id: str,
    approval_id: str,
    project_id: str,
    expected_memory_summary: str,
) -> dict[str, Any]:
    from api.app import create_app

    with TestClient(create_app(_eval_settings(database_url))) as client:
        timeline = client.get(f"/runtime/runs/{workflow_run_id}/timeline")
        timeline.raise_for_status()
        graph = client.get(f"/runtime/runs/{workflow_run_id}/graph")
        graph.raise_for_status()

        headers = _register_eval_user(
            client,
            f"restart-verify-{uuid4().hex[:8]}@example.com",
        )
        approval_detail = client.get(f"/review/approvals/{approval_id}", headers=headers)
        approval_detail.raise_for_status()
        memory_hits = client.get(f"/memory/hits?project_id={project_id}", headers=headers)
        memory_hits.raise_for_status()

    entries = timeline.json()["entries"]
    memory_items = memory_hits.json()["items"]
    return {
        "timeline_event_types": sorted({entry["event_type"] for entry in entries}),
        "graph_node_count": len(graph.json()["nodes"]),
        "approval_status": approval_detail.json()["status"],
        "memory_summary_found": any(
            item["summary"] == expected_memory_summary for item in memory_items
        ),
    }
