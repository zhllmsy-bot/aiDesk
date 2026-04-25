from __future__ import annotations

from temporalio import workflow

from api.runtime_contracts import GraphKind, WorkflowName
from api.workflows.definitions.base import WorkflowExecutionContext, execute_standard_workflow
from api.workflows.types import (
    ApprovalResolution,
    WorkflowRequest,
    WorkflowResult,
    WorkflowTaskSpec,
)

PROJECT_AUDIT_MODE_THREE_PASS = "three_pass"
PROJECT_AUDIT_THREE_PASS_TASK_IDS = (
    "audit-survey",
    "audit-counter-argument",
    "audit-roadmap",
)


def resolve_project_audit_tasks(request: WorkflowRequest) -> list[WorkflowTaskSpec]:
    if request.tasks:
        return request.tasks
    # Default to the project-maturity-audit three-pass sequence.
    return [
        WorkflowTaskSpec(
            task_id=PROJECT_AUDIT_THREE_PASS_TASK_IDS[0],
            title="Survey repository evidence and classify capability closure",
            graph_kind=GraphKind.AUDITOR.value,
        ),
        WorkflowTaskSpec(
            task_id=PROJECT_AUDIT_THREE_PASS_TASK_IDS[1],
            title="Counter-argument against optimistic conclusions",
            graph_kind=GraphKind.REVIEWER.value,
            depends_on=[PROJECT_AUDIT_THREE_PASS_TASK_IDS[0]],
        ),
        WorkflowTaskSpec(
            task_id=PROJECT_AUDIT_THREE_PASS_TASK_IDS[2],
            title="Roadmap prioritized closure plan",
            graph_kind=GraphKind.PLANNER.value,
            depends_on=[PROJECT_AUDIT_THREE_PASS_TASK_IDS[1]],
        ),
    ]


@workflow.defn(name=WorkflowName.PROJECT_AUDIT.value)
class ProjectAuditWorkflow:
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
        request.tasks = resolve_project_audit_tasks(request)
        request.metadata.setdefault("audit_mode", PROJECT_AUDIT_MODE_THREE_PASS)
        return await execute_standard_workflow(
            WorkflowExecutionContext(
                workflow_name=WorkflowName.PROJECT_AUDIT.value,
                request=request,
                approval_getter=lambda: self._approval_resolution,
                approval_reset=lambda: setattr(self, "_approval_resolution", None),
                worker_id="runtime-worker",
            )
        )
