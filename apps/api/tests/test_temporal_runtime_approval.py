from __future__ import annotations

from dataclasses import asdict

import pytest
from httpx import ASGITransport, AsyncClient
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from api.app import create_app
from api.executors.contracts import (
    ContextBundle,
    DispatchExecutionResponse,
    ExecutionProvenance,
    ExecutionStatus,
    ExecutorResultBundle,
    LogEntry,
    VerificationResult,
)
from api.runtime_contracts import EventType, GraphKind, TaskStatus, WorkflowName, WorkflowRunStatus
from api.runtime_persistence.models import RuntimeTask, RuntimeWorkflowRun
from api.workflows.activities.runtime_activities import ALL_RUNTIME_ACTIVITIES
from api.workflows.types import WorkflowRequest, WorkflowResult, WorkflowTaskSpec
from api.workflows.workers.runtime_worker import ALL_RUNTIME_WORKFLOWS
from tests.helpers import build_test_settings
from tests.temporal_helpers import initialize_database, seed_project, wait_for_timeline_event

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_temporal_runtime_approval_signal_resumes_and_completes(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'temporal-runtime.db'}"
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    async with await WorkflowEnvironment.start_time_skipping() as env:
        settings = build_test_settings(
            database_url=database_url,
            temporal_address=env.client.service_client.config.target_host,
            temporal_namespace=env.client.namespace,
            runtime_worker_id="temporal-test-worker",
        )
        app = create_app(settings, include_runtime_surface=True, include_execution_surface=False)
        initialize_database(app.state.session_factory)
        seed_project(
            app.state.session_factory,
            project_id="project-temporal-approval",
            root_path=workspace_root,
        )

        async with Worker(
            env.client,
            task_queue=settings.runtime_task_queue,
            workflows=ALL_RUNTIME_WORKFLOWS,
            activities=ALL_RUNTIME_ACTIVITIES,
            workflow_runner=UnsandboxedWorkflowRunner(),
        ), AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            workflow_run_id = "run-temporal-approval-1"
            raw_task_id = "approval-task"
            payload = WorkflowRequest(
                workflow_run_id=workflow_run_id,
                project_id="project-temporal-approval",
                initiated_by="temporal-harness",
                trace_id="trace-temporal-approval-1",
                objective="Validate Temporal approval signal bridge",
                tasks=[
                    WorkflowTaskSpec(
                        task_id=raw_task_id,
                        title="Wait for approval then complete",
                        graph_kind=GraphKind.PLANNER.value,
                        requires_approval=True,
                    )
                ],
                signal_timeout_seconds=60,
                metadata={
                    "workflow_name": WorkflowName.PROJECT_PLANNING.value,
                    "workspace_root_path": str(workspace_root),
                    "workspace_writable_paths": [str(workspace_root)],
                    "workspace_allowlist": [str(workspace_root)],
                },
            )

            start_response = await client.post("/runtime/runs/start", json=asdict(payload))
            assert start_response.status_code == 202, start_response.text
            temporal_workflow_id = start_response.json()["temporal_workflow_id"]

            waiting_entries = await wait_for_timeline_event(
                client,
                workflow_run_id,
                EventType.WORKFLOW_WAITING_APPROVAL.value,
            )
            assert any(
                entry["event_type"] == EventType.WORKFLOW_STARTED.value
                for entry in waiting_entries
            )

            approval_response = await client.post(
                f"/runtime/runs/{workflow_run_id}/approval",
                params={
                    "approved": True,
                    "actor": "temporal-harness",
                    "comment": "approved by temporal test env",
                },
            )
            assert approval_response.status_code == 202, approval_response.text

            handle = env.client.get_workflow_handle(
                temporal_workflow_id,
                result_type=WorkflowResult,
            )
            result = await handle.result()
            assert result.status == WorkflowRunStatus.COMPLETED.value

            full_task_id = f"{workflow_run_id}::{raw_task_id}"
            assert full_task_id in result.outputs

            final_entries = await wait_for_timeline_event(
                client,
                workflow_run_id,
                EventType.WORKFLOW_COMPLETED.value,
            )
            event_types = {entry["event_type"] for entry in final_entries}
            assert EventType.APPROVAL_RESOLVED.value in event_types
            assert EventType.TASK_COMPLETED.value in event_types

            attempts_response = await client.get(f"/runtime/tasks/{full_task_id}/attempts")
            assert attempts_response.status_code == 200, attempts_response.text
            attempts = attempts_response.json()["attempts"]
            assert len(attempts) == 1
            assert attempts[0]["status"] == TaskStatus.COMPLETED.value

            graph_response = await client.get(f"/runtime/runs/{workflow_run_id}/graph")
            assert graph_response.status_code == 200, graph_response.text
            nodes = graph_response.json()["nodes"]
            assert len(nodes) == 1
            assert nodes[0]["task_id"] == full_task_id
            assert nodes[0]["status"] == TaskStatus.COMPLETED.value


async def test_goofish_query_triggers_self_driven_temporal_iterations(
    tmp_path,
    monkeypatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'temporal-goofish-self-driven.db'}"
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    class _FakeContextAssembly:
        def assemble(self, request):
            return ContextBundle(task_id=request.task_id, blocks=[], evidence_refs=[])

    class _FakeDispatcher:
        def dispatch(self, bundle):
            attempt_id = bundle.dispatch.attempt_id or "attempt"
            result = ExecutorResultBundle(
                status=ExecutionStatus.SUCCEEDED,
                logs=[
                    LogEntry(
                        stream="stdout",
                        message=f"simulated self-driven execution for {bundle.task.task_id}",
                    )
                ],
                verification=VerificationResult(
                    passed=True,
                    summary="simulated verification passed",
                    results=[],
                ),
                provenance=ExecutionProvenance(
                    executor=bundle.task.executor,
                    provider_request_id=f"fake-{attempt_id}",
                    model="fake-codex",
                    attempt_id=attempt_id,
                    workspace_ref=bundle.workspace.workspace_ref,
                    trigger="test-harness",
                    metadata={"task_id": bundle.task.task_id},
                ),
                heartbeat_count=1,
            )
            return DispatchExecutionResponse(result=result, approval=None)

    class _FakeExecutionContainer:
        def __init__(self) -> None:
            self.context_assembly = _FakeContextAssembly()
            self.dispatcher = _FakeDispatcher()

    monkeypatch.setattr(
        "api.executors.dependencies.configure_execution_container",
        lambda _settings: _FakeExecutionContainer(),
    )

    async with await WorkflowEnvironment.start_time_skipping() as env:
        settings = build_test_settings(
            database_url=database_url,
            temporal_address=env.client.service_client.config.target_host,
            temporal_namespace=env.client.namespace,
            runtime_worker_id="temporal-self-driven-worker",
        )
        app = create_app(settings, include_runtime_surface=True, include_execution_surface=False)
        initialize_database(app.state.session_factory)
        seed_project(
            app.state.session_factory,
            project_id="project-goofish-self-driven",
            root_path=workspace_root,
            name="Goofish Insight",
            slug="goofish-insight",
        )

        async with Worker(
            env.client,
            task_queue=settings.runtime_task_queue,
            workflows=ALL_RUNTIME_WORKFLOWS,
            activities=ALL_RUNTIME_ACTIVITIES,
            workflow_runner=UnsandboxedWorkflowRunner(),
        ), AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            workflow_run_id = "run-goofish-self-driven-1"
            payload = WorkflowRequest(
                workflow_run_id=workflow_run_id,
                project_id="project-goofish-self-driven",
                initiated_by="goofish-insight query",
                trace_id="trace-goofish-self-driven-1",
                objective="验证 goofish-insight query 能触发 self_driven 自迭代",
                signal_timeout_seconds=60,
                metadata={
                    "workflow_name": WorkflowName.PROJECT_IMPROVEMENT.value,
                    "workspace_root_path": str(workspace_root),
                    "workspace_writable_paths": [str(workspace_root)],
                    "workspace_allowlist": [str(workspace_root)],
                    "context_blocks": [
                        {
                            "level": "L0",
                            "title": "Task Core",
                            "body": "验证 goofish-insight query 能触发 self_driven 自迭代",
                            "source": "test",
                        }
                    ],
                },
            )

            start_response = await client.post("/runtime/runs/start", json=asdict(payload))
            assert start_response.status_code == 202, start_response.text
            temporal_workflow_id = start_response.json()["temporal_workflow_id"]

            handle = env.client.get_workflow_handle(
                temporal_workflow_id,
                result_type=WorkflowResult,
            )
            result = await handle.result()
            assert result.status == WorkflowRunStatus.COMPLETED.value

            expected_output_keys = {
                f"{workflow_run_id}::loop-1-survey",
                f"{workflow_run_id}::loop-1-counter-argument",
                f"{workflow_run_id}::loop-1-roadmap",
                f"{workflow_run_id}::loop-1-execution",
                f"{workflow_run_id}::loop-1-review",
                f"{workflow_run_id}::loop-2-survey",
                f"{workflow_run_id}::loop-2-counter-argument",
                f"{workflow_run_id}::loop-2-roadmap",
                f"{workflow_run_id}::loop-2-execution",
                f"{workflow_run_id}::loop-2-review",
            }
            assert set(result.outputs) == expected_output_keys

            final_entries = await wait_for_timeline_event(
                client,
                workflow_run_id,
                EventType.WORKFLOW_COMPLETED.value,
            )
            event_types = {entry["event_type"] for entry in final_entries}
            assert EventType.WORKFLOW_STARTED.value in event_types
            assert EventType.WORKFLOW_COMPLETED.value in event_types
            assert EventType.TASK_COMPLETED.value in event_types

            graph_response = await client.get(f"/runtime/runs/{workflow_run_id}/graph")
            assert graph_response.status_code == 200, graph_response.text
            graph = graph_response.json()
            assert len(graph["nodes"]) == 10
            assert len(graph["edges"]) == 9
            node_ids = {node["task_id"] for node in graph["nodes"]}
            assert f"{workflow_run_id}::loop-1-survey" in node_ids
            assert f"{workflow_run_id}::loop-2-review" in node_ids
            edge_pairs = {
                (edge["source_task_id"], edge["target_task_id"])
                for edge in graph["edges"]
            }
            assert (
                f"{workflow_run_id}::loop-1-review",
                f"{workflow_run_id}::loop-2-survey",
            ) in edge_pairs

            attempts_response = await client.get(
                f"/runtime/tasks/{workflow_run_id}::loop-2-execution/attempts"
            )
            assert attempts_response.status_code == 200, attempts_response.text
            attempts = attempts_response.json()["attempts"]
            assert len(attempts) == 1
            assert attempts[0]["status"] == TaskStatus.COMPLETED.value

        with app.state.session_factory() as session:
            run_row = session.get(RuntimeWorkflowRun, workflow_run_id)
            assert run_row is not None
            assert run_row.initiated_by == "goofish-insight query"
            assert run_row.metadata_json["drive_mode"] == "self_driven"
            assert run_row.metadata_json["loop_iterations"] == 2
            assert (
                run_row.metadata_json["evaluation_pattern"]
                == "project_maturity_audit.three_pass"
            )

            loop_1_execution = session.get(RuntimeTask, f"{workflow_run_id}::loop-1-execution")
            assert loop_1_execution is not None
            assert loop_1_execution.executor == "codex"
            assert loop_1_execution.executor_summary == "codex self-iteration"

            loop_2_survey = session.get(RuntimeTask, f"{workflow_run_id}::loop-2-survey")
            assert loop_2_survey is not None
            assert loop_2_survey.depends_on == [f"{workflow_run_id}::loop-1-review"]
