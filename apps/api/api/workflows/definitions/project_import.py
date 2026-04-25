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


def resolve_project_import_tasks(request: WorkflowRequest) -> list[WorkflowTaskSpec]:
    if request.tasks:
        return request.tasks
    return [
        WorkflowTaskSpec(
            task_id="import-audit",
            title="Audit imported repository",
            graph_kind=GraphKind.AUDITOR.value,
        ),
        WorkflowTaskSpec(
            task_id="import-plan",
            title="Draft import remediation plan",
            graph_kind=GraphKind.PLANNER.value,
            depends_on=["import-audit"],
        ),
    ]


@workflow.defn(name=WorkflowName.PROJECT_IMPORT.value)
class ProjectImportWorkflow:
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
        request.tasks = resolve_project_import_tasks(request)
        return await execute_standard_workflow(
            WorkflowExecutionContext(
                workflow_name=WorkflowName.PROJECT_IMPORT.value,
                request=request,
                approval_getter=lambda: self._approval_resolution,
                approval_reset=lambda: setattr(self, "_approval_resolution", None),
                worker_id="runtime-worker",
            )
        )
