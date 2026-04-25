from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from api.config import get_settings
from api.workflows.activities.runtime_activities import ALL_RUNTIME_ACTIVITIES
from api.workflows.definitions.project_audit import ProjectAuditWorkflow
from api.workflows.definitions.project_import import ProjectImportWorkflow
from api.workflows.definitions.project_improvement import ProjectImprovementWorkflow
from api.workflows.definitions.project_planning import ProjectPlanningWorkflow
from api.workflows.definitions.task_execution import TaskExecutionWorkflow

ALL_RUNTIME_WORKFLOWS = [
    ProjectImportWorkflow,
    ProjectAuditWorkflow,
    ProjectPlanningWorkflow,
    TaskExecutionWorkflow,
    ProjectImprovementWorkflow,
]


async def run_worker() -> None:
    settings = get_settings()
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        identity=settings.runtime_worker_id,
    )
    worker = Worker(
        client,
        task_queue=settings.runtime_task_queue,
        workflows=ALL_RUNTIME_WORKFLOWS,
        activities=ALL_RUNTIME_ACTIVITIES,
        # Runtime workflows import SDK/integration stacks (e.g. OpenHands) that
        # rely on import-time instrumentation and can fail sandbox validation.
        # Temporal's official unsandboxed runner keeps workflow determinism while
        # avoiding those import-hook incompatibilities.
        workflow_runner=UnsandboxedWorkflowRunner(),
    )
    await worker.run()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
