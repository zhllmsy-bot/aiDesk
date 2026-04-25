from __future__ import annotations

from api.workflows.definitions.project_audit import (
    PROJECT_AUDIT_MODE_THREE_PASS,
    resolve_project_audit_tasks,
)
from api.workflows.types import WorkflowRequest


def _base_request() -> WorkflowRequest:
    return WorkflowRequest(
        workflow_run_id="run-audit-mode",
        project_id="project-audit-mode",
        initiated_by="tests",
        trace_id="trace-audit-mode",
        objective="Assess project maturity",
    )


def test_project_audit_defaults_to_three_pass_sequence() -> None:
    request = _base_request()
    tasks = resolve_project_audit_tasks(request)

    assert [task.task_id for task in tasks] == [
        "audit-survey",
        "audit-counter-argument",
        "audit-roadmap",
    ]
    assert tasks[0].graph_kind == "auditor"
    assert tasks[1].graph_kind == "reviewer"
    assert tasks[1].depends_on == ["audit-survey"]
    assert tasks[2].graph_kind == "planner"
    assert tasks[2].depends_on == ["audit-counter-argument"]


def test_project_audit_keeps_explicit_tasks() -> None:
    request = _base_request()
    request.tasks = resolve_project_audit_tasks(request)
    request.metadata["audit_mode"] = PROJECT_AUDIT_MODE_THREE_PASS

    resolved = resolve_project_audit_tasks(request)
    assert resolved == request.tasks
