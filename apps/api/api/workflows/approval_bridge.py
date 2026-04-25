from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session
from temporalio.client import Client

from api.config import Settings
from api.runtime_contracts import WorkflowName
from api.runtime_persistence.models import RuntimeWorkflowRun


async def signal_runtime_approval(
    *,
    settings: Settings,
    session_factory: Callable[[], Session],
    workflow_run_id: str,
    approved: bool,
    actor: str,
    comment: str | None = None,
    approval_id: str | None = None,
    approved_write_paths: list[str] | None = None,
) -> bool:
    temporal_workflow_id: str | None = None
    with session_factory() as session:
        row = session.get(RuntimeWorkflowRun, workflow_run_id)
        if row is not None and row.temporal_workflow_id:
            temporal_workflow_id = row.temporal_workflow_id

    if temporal_workflow_id is None:
        return False

    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        identity=f"{settings.runtime_worker_id}-approval-bridge",
    )

    async def _signal(workflow_id: str) -> None:
        handle = client.get_workflow_handle(
            workflow_id,
            result_type=dict[str, object],
        )
        await handle.signal(
            "resolve_approval",
            args=[
                approved,
                actor,
                comment,
                approval_id,
                list(approved_write_paths or []),
            ],
        )

    if temporal_workflow_id:
        try:
            await _signal(temporal_workflow_id)
            return True
        except Exception:
            pass

    last_error: Exception | None = None
    for candidate in WorkflowName:
        workflow_id = f"{candidate.value}:{workflow_run_id}"
        try:
            await _signal(workflow_id)
            return True
        except Exception as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    return False
