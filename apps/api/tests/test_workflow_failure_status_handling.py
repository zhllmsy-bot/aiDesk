from __future__ import annotations

from api.runtime_contracts import TaskStatus, WorkflowRunStatus
from api.workflows.definitions.base import WorkflowExecutionContext
from api.workflows.types import WorkflowRequest, WorkflowTaskSpec


def _context() -> WorkflowExecutionContext:
    request = WorkflowRequest(
        workflow_run_id="run-workflow-failure-status",
        project_id="project-workflow-failure-status",
        initiated_by="tests",
        trace_id="trace-workflow-failure-status",
        objective="Verify workflow failure status propagation",
        tasks=[
            WorkflowTaskSpec(
                task_id="execute-1",
                title="Execute",
                graph_kind="decomposition",
                executor_name="codex",
            )
        ],
    )
    return WorkflowExecutionContext(
        workflow_name="project.improvement",
        request=request,
        approval_getter=lambda: None,
        approval_reset=lambda: None,
        worker_id="runtime-worker",
    )


def test_execute_task_keeps_workflow_status_when_task_returns_failure(
    monkeypatch,
) -> None:
    context = _context()
    task = context.request.tasks[0]

    async def _fake_execute_task_once(
        _self: WorkflowExecutionContext,
        _task: WorkflowTaskSpec,
        workflow_status: str,
        attempt_no: int,
    ) -> tuple[str, dict[str, str]]:
        if attempt_no == 1:
            return workflow_status, {
                "status": TaskStatus.FAILED.value,
                "attempt_id": "att-1",
                "error": "provider timeout",
            }
        return workflow_status, {
            "status": TaskStatus.COMPLETED.value,
            "attempt_id": "att-2",
        }

    monkeypatch.setattr(WorkflowExecutionContext, "_execute_task_once", _fake_execute_task_once)
    
    async def _fake_transition_workflow(
        _self: WorkflowExecutionContext,
        _current: str,
        target: str,
        reason: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, str]:
        _ = (reason, metadata)
        return {"to_status": target}

    monkeypatch.setattr(
        WorkflowExecutionContext,
        "transition_workflow",
        _fake_transition_workflow,
    )
    monkeypatch.setattr(
        WorkflowExecutionContext,
        "emit_event",
        lambda *_args, **_kwargs: _async_result({}),
    )
    monkeypatch.setattr(
        "api.workflows.definitions.base.workflow.sleep",
        lambda *_args, **_kwargs: _async_result(None),
    )

    async def _run() -> tuple[str, dict[str, str]]:
        return await context.execute_task(task, WorkflowRunStatus.RUNNING.value)

    import asyncio

    workflow_status, result = asyncio.run(_run())
    assert workflow_status == WorkflowRunStatus.RUNNING.value
    assert result["status"] == TaskStatus.COMPLETED.value


async def _async_result(value):
    return value
