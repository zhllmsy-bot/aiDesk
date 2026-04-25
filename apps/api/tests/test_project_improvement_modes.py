from __future__ import annotations

from api.workflows.definitions.project_improvement import (
    DEFAULT_SELF_DRIVEN_LOOP_ITERATIONS,
    DRIVE_MODE_EXTERNAL_REQUIREMENT,
    DRIVE_MODE_SELF_DRIVEN,
    resolve_project_improvement_mode,
    resolve_project_improvement_tasks,
    resolve_self_driven_loop_iterations,
)
from api.workflows.types import WorkflowRequest, WorkflowTaskSpec


def _request(metadata: dict[str, object] | None = None) -> WorkflowRequest:
    return WorkflowRequest(
        workflow_run_id="run-improvement-mode",
        project_id="project-improvement-mode",
        initiated_by="tests",
        trace_id="trace-improvement-mode",
        objective="Improve project maturity",
        metadata=dict(metadata or {}),
    )


def test_resolve_project_improvement_mode_defaults_to_self_driven() -> None:
    request = _request()
    assert resolve_project_improvement_mode(request.metadata) == DRIVE_MODE_SELF_DRIVEN


def test_resolve_self_driven_loop_iterations_uses_bounds() -> None:
    assert resolve_self_driven_loop_iterations({}) == DEFAULT_SELF_DRIVEN_LOOP_ITERATIONS
    assert resolve_self_driven_loop_iterations({"loop_iterations": 0}) == 1
    assert resolve_self_driven_loop_iterations({"loop_iterations": 12}) == 5
    assert resolve_self_driven_loop_iterations({"loop_iterations": "3"}) == 3


def test_project_improvement_self_driven_builds_iterative_loop_tasks() -> None:
    request = _request({"drive_mode": DRIVE_MODE_SELF_DRIVEN, "loop_iterations": 2})
    tasks = resolve_project_improvement_tasks(request)

    assert request.metadata["drive_mode"] == DRIVE_MODE_SELF_DRIVEN
    assert request.metadata["loop_iterations"] == 2
    assert request.metadata["evaluation_pattern"] == "project_maturity_audit.three_pass"
    assert [task.task_id for task in tasks] == [
        "loop-1-survey",
        "loop-1-counter-argument",
        "loop-1-roadmap",
        "loop-1-execution",
        "loop-1-review",
        "loop-2-survey",
        "loop-2-counter-argument",
        "loop-2-roadmap",
        "loop-2-execution",
        "loop-2-review",
    ]
    loop_1_execution = next(task for task in tasks if task.task_id == "loop-1-execution")
    assert loop_1_execution.executor_name == "codex"
    assert loop_1_execution.executor_summary == "codex self-iteration"
    loop_2_survey = next(task for task in tasks if task.task_id == "loop-2-survey")
    assert loop_2_survey.depends_on == ["loop-1-review"]


def test_project_improvement_external_requirement_mode_builds_requirement_tasks() -> None:
    request = _request({"drive_mode": DRIVE_MODE_EXTERNAL_REQUIREMENT})
    tasks = resolve_project_improvement_tasks(request)

    assert request.metadata["drive_mode"] == DRIVE_MODE_EXTERNAL_REQUIREMENT
    assert request.metadata["evaluation_pattern"] == "external_requirement.delivery"
    assert [task.task_id for task in tasks] == [
        "req-clarify",
        "req-execution",
        "req-review",
    ]
    assert tasks[1].executor_name == "codex"
    assert tasks[1].executor_summary == "codex requirement delivery"
    assert tasks[1].depends_on == ["req-clarify"]
    assert tasks[2].depends_on == ["req-execution"]


def test_project_improvement_keeps_explicit_tasks() -> None:
    explicit = [
        WorkflowTaskSpec(task_id="custom-1", title="custom", graph_kind="planner"),
    ]
    request = _request({"drive_mode": DRIVE_MODE_EXTERNAL_REQUIREMENT})
    request.tasks = explicit
    assert resolve_project_improvement_tasks(request) == explicit
