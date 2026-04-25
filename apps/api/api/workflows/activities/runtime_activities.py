from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

from temporalio import activity

from api.agent_runtime.models import GraphExecutionRequest
from api.context.assembly import AssemblyRequest
from api.events.builder import RuntimeEventBuilder
from api.events.models import CorrelationIds
from api.executors.contracts import ExecutorInputBundle
from api.notifications.base import NotificationMessage
from api.observability.logging import get_logger, set_correlation
from api.observability.metrics import get_metrics
from api.runtime_contracts import EventType, WorkerHealthStatus
from api.workflows.dependencies import get_standalone_runtime_container
from api.workflows.state_machine import (
    transition_claim_status,
    transition_task_status,
    transition_workflow_run_status,
)

logger = get_logger("workflows.activities")


def _container():
    return get_standalone_runtime_container()


def _ensure_models_registered() -> None:
    # Worker activities can run in a process where control-plane models haven't
    # been imported yet; ensure all ORM mappings are configured before any DB IO.
    from api.models import register_models

    register_models()


@activity.defn
async def emit_runtime_event(
    event_type: str,
    correlation_payload: dict[str, Any],
    payload: dict[str, Any] | None = None,
    sequence: int | None = None,
    producer: str | None = None,
) -> dict[str, Any]:
    _ensure_models_registered()
    correlation = CorrelationIds.model_validate(correlation_payload)
    set_correlation(
        workflow_run_id=correlation.workflow_run_id,
        trace_id=correlation.trace_id,
        task_id=correlation.task_id or "",
        attempt_id=correlation.attempt_id or "",
    )
    store = _container().event_store
    builder = RuntimeEventBuilder(producer=producer or "runtime.activities")
    event = builder.build(
        event_type=event_type,
        sequence=sequence or store.next_sequence(correlation.workflow_run_id),
        correlation=correlation,
        payload=payload or {},
    )
    logger.info(
        "runtime event emitted",
        extra={"event_type": event_type, "workflow_run_id": correlation.workflow_run_id},
    )
    return store.append(event).model_dump(mode="json")


@activity.defn
async def execute_graph_activity(request_payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_models_registered()
    request = GraphExecutionRequest.model_validate(request_payload)
    correlation = request_payload.get("correlation", {})
    set_correlation(
        workflow_run_id=correlation.get("workflow_run_id", ""),
        trace_id=correlation.get("trace_id", ""),
        task_id=correlation.get("task_id", ""),
        attempt_id=correlation.get("attempt_id", ""),
    )
    logger.info(
        "graph execution started",
        extra={"graph_kind": request_payload.get("graph_kind", "")},
    )
    result = _container().agent_runtime.execute(request).model_dump(mode="json")
    logger.info(
        "graph execution completed",
        extra={"graph_kind": result.get("graph_kind", ""), "status": result.get("status", "")},
    )
    return result


@activity.defn
async def claim_task_activity(
    task_id: str,
    workflow_run_id: str,
    attempt_id: str,
    worker_id: str,
    lease_timeout_seconds: int,
) -> dict[str, Any]:
    _ensure_models_registered()
    metrics = get_metrics()
    set_correlation(workflow_run_id=workflow_run_id, task_id=task_id, attempt_id=attempt_id)
    claim = _container().persistence.claim_task(
        task_id=task_id,
        workflow_run_id=workflow_run_id,
        attempt_id=attempt_id,
        worker_id=worker_id,
        lease_timeout_seconds=lease_timeout_seconds,
    )
    metrics.inc_counter("claim_created")
    logger.info(
        "task claimed",
        extra={
            "task_id": task_id,
            "worker_id": worker_id,
            "lease_timeout_seconds": lease_timeout_seconds,
        },
    )
    return asdict(claim)


@activity.defn
async def heartbeat_claim_activity(claim_id: str) -> dict[str, Any]:
    _ensure_models_registered()
    try:
        return asdict(_container().persistence.heartbeat(claim_id))
    except ValueError:
        # Claim can be released between heartbeat scheduling and execution;
        # treat as a benign terminal condition instead of retrying the activity.
        logger.info(
            "heartbeat ignored for non-active claim",
            extra={"claim_id": claim_id},
        )
        return {"claim_id": claim_id, "status": "ignored"}


@activity.defn
async def release_claim_activity(claim_id: str) -> dict[str, Any]:
    _ensure_models_registered()
    metrics = get_metrics()
    metrics.inc_counter("claim_released")
    logger.info("claim released", extra={"claim_id": claim_id})
    return asdict(_container().persistence.release(claim_id))


@activity.defn
async def reclaim_stale_claims_activity(
    workflow_run_id: str,
    force_claim_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    _ensure_models_registered()
    metrics = get_metrics()
    claims = _container().persistence.reclaim_stale_claims(
        workflow_run_id=workflow_run_id,
        force_claim_ids=force_claim_ids,
    )
    metrics.inc_counter("claim_reclaimed", amount=len(claims))
    if claims:
        logger.warning(
            "stale claims reclaimed",
            extra={"workflow_run_id": workflow_run_id, "count": len(claims)},
        )
    return [asdict(claim) for claim in claims]


@activity.defn
async def transition_workflow_status_activity(
    current: str,
    target: str,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ensure_models_registered()
    transition = transition_workflow_run_status(current, target, reason, metadata)
    workflow_run_id = str((metadata or {}).get("workflow_run_id", ""))
    if workflow_run_id:
        _container().persistence.transition_workflow_status(
            workflow_run_id=workflow_run_id,
            target=transition.to_status,
        )
    metrics = get_metrics()
    wf_name = str((metadata or {}).get("workflow_name", ""))
    if target == "running":
        metrics.inc_counter("workflow_started", workflow_name=wf_name)
    elif target == "completed":
        metrics.inc_counter("workflow_succeeded", workflow_name=wf_name)
    elif target == "failed":
        metrics.inc_counter("workflow_failed", workflow_name=wf_name)
    logger.info(
        "workflow status transitioned",
        extra={"from": current, "to": target, "reason": reason},
    )
    return asdict(transition)


@activity.defn
async def transition_task_status_activity(
    current: str,
    target: str,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ensure_models_registered()
    transition = transition_task_status(current, target, reason, metadata)
    payload = metadata or {}
    task_id = payload.get("task_id")
    if isinstance(task_id, str):
        attempt_id = payload.get("attempt_id")
        _container().persistence.transition_task_status(
            task_id=task_id,
            attempt_id=str(attempt_id) if isinstance(attempt_id, str) else None,
            target=transition.to_status,
            metadata=payload,
        )
    logger.info(
        "task status transitioned",
        extra={"from": current, "to": target, "reason": reason, "task_id": str(task_id or "")},
    )
    return asdict(transition)


@activity.defn
async def transition_claim_status_activity(
    current: str,
    target: str,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ensure_models_registered()
    return asdict(transition_claim_status(current, target, reason, metadata))


@activity.defn
async def send_notification_activity(message_payload: dict[str, Any]) -> list[dict[str, Any]]:
    _ensure_models_registered()
    message = NotificationMessage.model_validate(message_payload)
    receipts = _container().notification_service.send(message)
    return [receipt.model_dump(mode="json") for receipt in receipts]


@activity.defn
async def report_worker_health_activity(
    worker_id: str,
    detail: str,
    active_workflow_names: list[str],
) -> dict[str, Any]:
    _ensure_models_registered()
    container = _container()
    event = RuntimeEventBuilder(producer="runtime.worker").build(
        event_type=EventType.WORKER_HEALTH_REPORTED,
        sequence=container.event_store.next_sequence(f"worker-health::{worker_id}"),
        correlation={
            "workflow_run_id": f"worker-health::{worker_id}",
            "trace_id": f"trace::{worker_id}",
        },
        payload={
            "worker_id": worker_id,
            "task_queue": container.runtime_task_queue,
            "status": WorkerHealthStatus.HEALTHY.value,
            "detail": detail,
            "active_workflow_names": active_workflow_names,
        },
    )
    return container.event_store.append(event).model_dump(mode="json")


@activity.defn
async def dispatch_executor_activity(dispatch_payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_models_registered()
    container = _container()
    settings = container.settings
    from api.executors.dependencies import configure_execution_container

    execution_container = configure_execution_container(settings)
    bundle = ExecutorInputBundle.model_validate(dispatch_payload)
    # Executor adapters may internally use asyncio runners; run provider work in
    # a worker thread to avoid nested-loop errors inside async Temporal
    # activities. Persist only after the provider returns and only if the
    # activity is still active, so late completions do not write stale attempt
    # summaries after Temporal has already timed out or cancelled the activity.
    dispatcher = execution_container.dispatcher
    dispatch_without_persistence = getattr(dispatcher, "dispatch_without_persistence", None)
    persist_response = getattr(dispatcher, "persist_response", None)

    if callable(dispatch_without_persistence) and callable(persist_response):
        response = await asyncio.to_thread(
            dispatch_without_persistence,
            bundle,
        )
        if response.result is not None and activity.is_cancelled():
            raise asyncio.CancelledError("dispatch executor activity cancelled before persistence")
        await asyncio.to_thread(persist_response, bundle, response)
    else:
        # Backward-compatible path for legacy/fake dispatchers that still expose
        # only `dispatch`, where persistence happens internally.
        response = await asyncio.to_thread(dispatcher.dispatch, bundle)
        if response.result is not None and activity.is_cancelled():
            raise asyncio.CancelledError("dispatch executor activity cancelled")
    return response.model_dump(mode="json")


@activity.defn
async def assemble_context_activity(assembly_payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_models_registered()
    container = _container()
    settings = container.settings
    from api.executors.dependencies import configure_execution_container

    execution_container = configure_execution_container(settings)
    request = AssemblyRequest.model_validate(assembly_payload)
    bundle = await asyncio.to_thread(execution_container.context_assembly.assemble, request)
    return bundle.model_dump(mode="json")


ALL_RUNTIME_ACTIVITIES = [
    emit_runtime_event,
    execute_graph_activity,
    dispatch_executor_activity,
    assemble_context_activity,
    claim_task_activity,
    heartbeat_claim_activity,
    release_claim_activity,
    reclaim_stale_claims_activity,
    transition_workflow_status_activity,
    transition_task_status_activity,
    transition_claim_status_activity,
    send_notification_activity,
    report_worker_health_activity,
]
