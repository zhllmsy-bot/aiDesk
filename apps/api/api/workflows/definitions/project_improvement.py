from __future__ import annotations

from typing import Any

from temporalio import workflow

from api.runtime_contracts import GraphKind, WorkflowName
from api.workflows.definitions.base import WorkflowExecutionContext, execute_standard_workflow
from api.workflows.types import (
    ApprovalResolution,
    WorkflowRequest,
    WorkflowResult,
    WorkflowTaskSpec,
)

DRIVE_MODE_SELF_DRIVEN = "self_driven"
DRIVE_MODE_EXTERNAL_REQUIREMENT = "external_requirement"
PROJECT_IMPROVEMENT_DRIVE_MODES = {
    DRIVE_MODE_SELF_DRIVEN,
    DRIVE_MODE_EXTERNAL_REQUIREMENT,
}
DEFAULT_SELF_DRIVEN_LOOP_ITERATIONS = 2
MAX_SELF_DRIVEN_LOOP_ITERATIONS = 5


def resolve_project_improvement_mode(metadata: dict[str, Any]) -> str:
    raw_mode = metadata.get("drive_mode")
    if isinstance(raw_mode, str) and raw_mode in PROJECT_IMPROVEMENT_DRIVE_MODES:
        return raw_mode
    return DRIVE_MODE_SELF_DRIVEN


def resolve_self_driven_loop_iterations(metadata: dict[str, Any]) -> int:
    raw_iterations = metadata.get("loop_iterations", DEFAULT_SELF_DRIVEN_LOOP_ITERATIONS)
    if isinstance(raw_iterations, bool):
        return DEFAULT_SELF_DRIVEN_LOOP_ITERATIONS
    if isinstance(raw_iterations, str):
        raw_iterations = raw_iterations.strip()
    try:
        iterations = int(raw_iterations)
    except (TypeError, ValueError):
        return DEFAULT_SELF_DRIVEN_LOOP_ITERATIONS
    return max(1, min(iterations, MAX_SELF_DRIVEN_LOOP_ITERATIONS))


def _build_self_driven_tasks(loop_iterations: int) -> list[WorkflowTaskSpec]:
    tasks: list[WorkflowTaskSpec] = []
    previous_review_task_id: str | None = None

    for index in range(1, loop_iterations + 1):
        prefix = f"loop-{index}"
        survey_task_id = f"{prefix}-survey"
        counter_task_id = f"{prefix}-counter-argument"
        roadmap_task_id = f"{prefix}-roadmap"
        execute_task_id = f"{prefix}-execution"
        review_task_id = f"{prefix}-review"

        survey_dependencies = [previous_review_task_id] if previous_review_task_id else []
        tasks.append(
            WorkflowTaskSpec(
                task_id=survey_task_id,
                title=f"Loop {index}: survey repository evidence and closure signals",
                graph_kind=GraphKind.AUDITOR.value,
                depends_on=survey_dependencies,
            )
        )
        tasks.append(
            WorkflowTaskSpec(
                task_id=counter_task_id,
                title=f"Loop {index}: counter-argument against optimistic assumptions",
                graph_kind=GraphKind.REVIEWER.value,
                depends_on=[survey_task_id],
            )
        )
        tasks.append(
            WorkflowTaskSpec(
                task_id=roadmap_task_id,
                title=f"Loop {index}: roadmap and priority closure plan",
                graph_kind=GraphKind.PLANNER.value,
                depends_on=[counter_task_id],
            )
        )
        tasks.append(
            WorkflowTaskSpec(
                task_id=execute_task_id,
                title=f"Loop {index}: execute highest-priority closure items",
                graph_kind=GraphKind.DECOMPOSITION.value,
                depends_on=[roadmap_task_id],
                executor_summary="codex self-iteration",
                executor_name="codex",
            )
        )
        tasks.append(
            WorkflowTaskSpec(
                task_id=review_task_id,
                title=f"Loop {index}: review execution outcome and residual risk",
                graph_kind=GraphKind.REVIEWER.value,
                depends_on=[execute_task_id],
            )
        )
        previous_review_task_id = review_task_id

    return tasks


def _build_external_requirement_tasks() -> list[WorkflowTaskSpec]:
    return [
        WorkflowTaskSpec(
            task_id="req-clarify",
            title="Clarify explicit requirement and acceptance criteria",
            graph_kind=GraphKind.PLANNER.value,
        ),
        WorkflowTaskSpec(
            task_id="req-execution",
            title="Implement requirement-aligned execution plan",
            graph_kind=GraphKind.DECOMPOSITION.value,
            depends_on=["req-clarify"],
            executor_summary="codex requirement delivery",
            executor_name="codex",
        ),
        WorkflowTaskSpec(
            task_id="req-review",
            title="Review delivery result against explicit requirement",
            graph_kind=GraphKind.REVIEWER.value,
            depends_on=["req-execution"],
        ),
    ]


def resolve_project_improvement_tasks(request: WorkflowRequest) -> list[WorkflowTaskSpec]:
    if request.tasks:
        return request.tasks

    mode = resolve_project_improvement_mode(request.metadata)
    request.metadata.setdefault("drive_mode", mode)
    if mode == DRIVE_MODE_SELF_DRIVEN:
        iterations = resolve_self_driven_loop_iterations(request.metadata)
        request.metadata["loop_iterations"] = iterations
        request.metadata.setdefault("evaluation_pattern", "project_maturity_audit.three_pass")
        return _build_self_driven_tasks(iterations)

    request.metadata.setdefault("evaluation_pattern", "external_requirement.delivery")
    return _build_external_requirement_tasks()


@workflow.defn(name=WorkflowName.PROJECT_IMPROVEMENT.value)
class ProjectImprovementWorkflow:
    def __init__(self) -> None:
        self._approval_resolution: ApprovalResolution | None = None

    @workflow.signal(name="resolve_approval")
    def resolve_approval(
        self,
        approved: bool,
        actor: str,
        comment: str | None = None,
        approval_id: str | None = None,
        approved_write_paths: list[str] | None = None,
    ) -> None:
        self._approval_resolution = ApprovalResolution(
            approved=approved,
            actor=actor,
            comment=comment,
            approval_id=approval_id,
            approved_write_paths=list(approved_write_paths or []),
        )

    @workflow.run
    async def run(self, request: WorkflowRequest) -> WorkflowResult:
        request.tasks = resolve_project_improvement_tasks(request)
        return await execute_standard_workflow(
            WorkflowExecutionContext(
                workflow_name=WorkflowName.PROJECT_IMPROVEMENT.value,
                request=request,
                approval_getter=lambda: self._approval_resolution,
                approval_reset=lambda: setattr(self, "_approval_resolution", None),
                worker_id="runtime-worker",
            )
        )
