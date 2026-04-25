from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import timedelta
from graphlib import CycleError, TopologicalSorter
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from api.executors.contracts import ExecutionStatus
    from api.runtime_contracts import EventType, GraphExecutionStatus, TaskStatus, WorkflowRunStatus
    from api.workflows.activities import runtime_activities
    from api.workflows.execution_policy import WorkflowExecutionPolicy
    from api.workflows.orchestration import (
        build_context_assembly_payload,
        summarize_notification_receipts,
    )
    from api.workflows.types import (
        ApprovalResolution,
        WorkflowRequest,
        WorkflowResult,
        WorkflowTaskSpec,
    )


class ApprovalTimeoutError(RuntimeError):
    pass


class TaskDependencyError(RuntimeError):
    pass


def resolve_task_execution_order(tasks: list[WorkflowTaskSpec]) -> list[str]:
    task_by_id = {task.task_id: task for task in tasks}
    dag: dict[str, set[str]] = {}
    for task in tasks:
        unknown = [dep for dep in task.depends_on if dep not in task_by_id]
        if unknown:
            raise TaskDependencyError(
                f"{task.task_id} depends on unknown task(s): {', '.join(unknown)}"
            )
        dag[task.task_id] = set(task.depends_on)
    try:
        sorter = TopologicalSorter(dag)
        return [str(task_id) for task_id in sorter.static_order()]
    except CycleError as exc:
        cycle_nodes = [str(node) for node in exc.args[1]] if len(exc.args) > 1 else []
        reason = (
            f"task dependency cycle detected: {', '.join(cycle_nodes)}"
            if cycle_nodes
            else "task dependency cycle detected"
        )
        raise TaskDependencyError(reason) from exc


@dataclass(slots=True)
class WorkflowExecutionContext:
    workflow_name: str
    request: WorkflowRequest
    approval_getter: Callable[[], ApprovalResolution | None]
    approval_reset: Callable[[], None]
    worker_id: str
    outputs: dict[str, Any] = field(default_factory=dict)
    execution_policy: WorkflowExecutionPolicy = field(init=False)

    def __post_init__(self) -> None:
        self.execution_policy = WorkflowExecutionPolicy(self.request)

    @property
    def base_correlation(self) -> dict[str, Any]:
        return {
            "workflow_run_id": self.request.workflow_run_id,
            "trace_id": self.request.trace_id,
            "workflow_id": workflow.info().workflow_id,
            "project_id": self.request.project_id,
        }

    async def emit_event(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        task_id: str | None = None,
        attempt_id: str | None = None,
    ) -> dict[str, Any]:
        return await workflow.execute_activity(
            runtime_activities.emit_runtime_event,
            args=[
                event_type,
                {
                    **self.base_correlation,
                    "task_id": task_id,
                    "attempt_id": attempt_id,
                },
                payload or {},
            ],
            start_to_close_timeout=timedelta(seconds=5),
        )

    async def transition_workflow(
        self, current: str, target: str, reason: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return await workflow.execute_activity(
            runtime_activities.transition_workflow_status_activity,
            args=[
                current,
                target,
                reason,
                {"workflow_run_id": self.request.workflow_run_id, **(metadata or {})},
            ],
            start_to_close_timeout=timedelta(seconds=5),
        )

    async def transition_task(
        self, current: str, target: str, reason: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return await workflow.execute_activity(
            runtime_activities.transition_task_status_activity,
            args=[current, target, reason, metadata or {}],
            start_to_close_timeout=timedelta(seconds=5),
        )

    async def send_notification(
        self, title: str, body: str, metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return await workflow.execute_activity(
            runtime_activities.send_notification_activity,
            args=[
                {
                    "title": title,
                    "body": body,
                    "correlation": self.base_correlation,
                    "metadata": metadata or {},
                }
            ],
            start_to_close_timeout=timedelta(seconds=5),
        )

    async def wait_for_approval(self, approval_id: str | None = None) -> ApprovalResolution:
        def _approval_ready() -> bool:
            resolution = self.approval_getter()
            if resolution is None:
                return False
            if approval_id is None:
                return True
            return resolution.approval_id in {None, approval_id}

        try:
            await workflow.wait_condition(
                _approval_ready,
                timeout=timedelta(seconds=self.request.signal_timeout_seconds),
                timeout_summary=f"approval timeout for {self.workflow_name}",
            )
        except TimeoutError as exc:
            raise ApprovalTimeoutError(str(exc)) from exc
        resolution = self.approval_getter()
        assert resolution is not None
        self.approval_reset()
        return resolution

    async def _heartbeat_loop(
        self,
        claim_id: str,
        task_id: str,
        attempt_id: str,
        interval_seconds: int,
    ) -> None:
        while True:
            await workflow.sleep(timedelta(seconds=interval_seconds))
            try:
                await workflow.execute_activity(
                    runtime_activities.heartbeat_claim_activity,
                    args=[claim_id],
                    start_to_close_timeout=timedelta(seconds=5),
                )
                await self.emit_event(
                    EventType.TASK_HEARTBEAT,
                    {"claim_id": claim_id, "summary": f"Periodic heartbeat for {task_id}"},
                    task_id=task_id,
                    attempt_id=attempt_id,
                )
            except Exception:
                break

    async def _stop_heartbeat(self, handle: asyncio.Task[None]) -> None:
        handle.cancel()
        with suppress(BaseException):
            await handle

    def _build_attempt_id(self, task_id: str, attempt_no: int = 1) -> str:
        # Keep IDs short, deterministic, and run-scoped to avoid cross-run collisions.
        digest = hashlib.sha1(
            f"{self.request.workflow_run_id}:{task_id}:{attempt_no}".encode()
        ).hexdigest()[:20]
        return f"att-{digest}"

    def _retry_backoff_seconds(self, attempt_no: int) -> int:
        base = max(self._metadata_int("retry_backoff_base_seconds", 5), 1)
        cap = max(self._metadata_int("retry_backoff_cap_seconds", 60), base)
        return min(base * (2 ** max(attempt_no - 1, 0)), cap)

    def _metadata_int(self, key: str, default: int) -> int:
        raw = self.request.metadata.get(key, default)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_context_blocks(metadata: dict[str, Any]) -> list[dict[str, Any]]:
        return WorkflowExecutionPolicy.normalize_context_blocks(metadata)

    @staticmethod
    def _serialize_evidence_refs(metadata: dict[str, Any]) -> list[dict[str, Any]]:
        return WorkflowExecutionPolicy.serialize_evidence_refs(metadata)

    @staticmethod
    def _normalize_verify_commands(metadata: dict[str, Any]) -> list[dict[str, Any]]:
        return WorkflowExecutionPolicy.normalize_verify_commands(metadata)

    @staticmethod
    def _resolve_notification_metadata(
        request_metadata: dict[str, Any],
        workflow_name: str,
    ) -> dict[str, Any]:
        return WorkflowExecutionPolicy.resolve_notification_metadata(
            request_metadata,
            workflow_name,
        )

    @staticmethod
    def _resolve_runtime_full_access(metadata: dict[str, Any]) -> bool:
        return WorkflowExecutionPolicy.resolve_runtime_full_access(metadata)

    def _workspace_root_path(self) -> str:
        return self.execution_policy.workspace_root_path()

    def _workspace_writable_paths(
        self,
        approval_resolution: ApprovalResolution | None = None,
    ) -> list[str]:
        return self.execution_policy.workspace_writable_paths(approval_resolution)

    def _workspace_allowlist(self, workspace_root_path: str) -> list[str]:
        return self.execution_policy.workspace_allowlist(workspace_root_path)

    def _build_executor_dispatch_payload(
        self,
        *,
        task: WorkflowTaskSpec,
        attempt_id: str,
        executor_dispatch_timeout_seconds: int,
        normalized_verify_commands: list[dict[str, Any]],
        normalized_context_blocks: list[dict[str, Any]],
        approval_resolution: ApprovalResolution | None = None,
    ) -> dict[str, Any]:
        return self.execution_policy.build_executor_dispatch_payload(
            task=task,
            attempt_id=attempt_id,
            executor_dispatch_timeout_seconds=executor_dispatch_timeout_seconds,
            normalized_verify_commands=normalized_verify_commands,
            normalized_context_blocks=normalized_context_blocks,
            approval_resolution=approval_resolution,
        )

    @staticmethod
    def _todo_template(task: WorkflowTaskSpec) -> list[dict[str, str]]:
        if task.executor_name:
            return [
                {
                    "id": "context",
                    "title": "Assemble repo context and constraints",
                    "detail": (
                        "Load project facts, run objective, writable scope, "
                        "and verification commands."
                    ),
                },
                {
                    "id": "plan",
                    "title": "Choose the highest-impact implementation slice",
                    "detail": "Turn the task objective into a scoped code change before editing.",
                },
                {
                    "id": "implement",
                    "title": "Apply code changes inside the owned workspace",
                    "detail": (
                        "Edit only the declared project paths and keep the "
                        "increment shippable."
                    ),
                },
                {
                    "id": "verify",
                    "title": "Run required verification commands",
                    "detail": "Execute the run-level checks and capture failures as evidence.",
                },
                {
                    "id": "summarize",
                    "title": "Publish changed files, evidence, and blockers",
                    "detail": "Return a concise executor summary for review and follow-up tasks.",
                },
            ]

        return [
            {
                "id": "prepare",
                "title": f"Prepare {task.graph_kind} graph inputs",
                "detail": "Resolve objective, dependencies, and run context for this graph task.",
            },
            {
                "id": "execute",
                "title": f"Run {task.graph_kind} graph",
                "detail": "Produce structured output and runtime artifacts.",
            },
            {
                "id": "verify",
                "title": "Verify graph output shape",
                "detail": (
                    "Confirm the task produced usable structured output before "
                    "unblocking dependents."
                ),
            },
            {
                "id": "publish",
                "title": "Publish task result into the run graph",
                "detail": "Update timeline, graph state, and downstream dependency visibility.",
            },
        ]

    def _todo_items(
        self,
        task: WorkflowTaskSpec,
        *,
        active_id: str | None = None,
        completed_ids: set[str] | None = None,
        failed_id: str | None = None,
    ) -> list[dict[str, str]]:
        completed = completed_ids or set()
        items: list[dict[str, str]] = []
        for item in self._todo_template(task):
            status = "queued"
            if item["id"] in completed:
                status = "completed"
            if item["id"] == active_id:
                status = "running"
            if item["id"] == failed_id:
                status = "failed"
            items.append({**item, "status": status})
        return items

    def _task_graph_payload(self, summary: str) -> dict[str, Any]:
        return {
            "nodes": [
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "status": TaskStatus.QUEUED.value,
                    "blocked_reason": None if not task.depends_on else ", ".join(task.depends_on),
                    "executor_summary": task.executor_summary,
                    "todo_items": self._todo_items(task),
                }
                for task in self.request.tasks
            ],
            "edges": [
                {
                    "source_task_id": dependency,
                    "target_task_id": candidate.task_id,
                    "kind": "depends_on",
                }
                for candidate in self.request.tasks
                for dependency in candidate.depends_on
            ],
            "summary": summary,
        }

    async def emit_task_todo(
        self,
        task: WorkflowTaskSpec,
        *,
        summary: str,
        active_id: str | None = None,
        completed_ids: set[str] | None = None,
        failed_id: str | None = None,
        attempt_id: str | None = None,
    ) -> dict[str, Any]:
        return await self.emit_event(
            EventType.TASK_TODO_UPDATED,
            {
                "todo_items": self._todo_items(
                    task,
                    active_id=active_id,
                    completed_ids=completed_ids,
                    failed_id=failed_id,
                ),
                "active_todo_id": active_id,
                "summary": summary,
            },
            task_id=task.task_id,
            attempt_id=attempt_id,
        )

    def _build_context_assembly_payload(self, task: WorkflowTaskSpec) -> dict[str, Any]:
        return build_context_assembly_payload(
            request=self.request,
            task=task,
            metadata_int_resolver=self._metadata_int,
            evidence_serializer=self._serialize_evidence_refs,
        )

    @staticmethod
    def _summarize_notification_receipts(receipts: list[dict[str, Any]]) -> dict[str, Any]:
        return summarize_notification_receipts(receipts)

    async def _execute_task_once(
        self, task: WorkflowTaskSpec, workflow_status: str, attempt_no: int
    ) -> tuple[str, dict[str, Any]]:
        attempt_id = self._build_attempt_id(task.task_id, attempt_no)
        current_status = TaskStatus.QUEUED.value
        await self.emit_task_todo(
            task,
            summary=f"{task.title} todo checklist activated",
            active_id="context" if task.executor_name else "prepare",
            attempt_id=attempt_id,
        )

        if task.task_id in self.request.simulation.approval_task_ids or task.requires_approval:
            workflow_status = (
                await self.transition_workflow(
                    workflow_status,
                    WorkflowRunStatus.WAITING_APPROVAL.value,
                    reason=f"{task.task_id} awaiting approval",
                    metadata={"task_id": task.task_id},
                )
            )["to_status"]
            await self.emit_event(
                EventType.WORKFLOW_WAITING_APPROVAL,
                {"summary": f"{task.title} requires approval"},
                task_id=task.task_id,
                attempt_id=attempt_id,
            )
            try:
                resolution = await self.wait_for_approval()
            except ApprovalTimeoutError:
                return workflow_status, {
                    "status": TaskStatus.FAILED.value,
                    "attempt_id": attempt_id,
                    "error": "approval_timeout",
                }
            await self.emit_event(
                EventType.APPROVAL_RESOLVED,
                {
                    "approved": resolution.approved,
                    "actor": resolution.actor,
                    "comment": resolution.comment,
                    "summary": (
                        f"Approval {'approved' if resolution.approved else 'rejected'} "
                        f"by {resolution.actor}"
                    ),
                },
                task_id=task.task_id,
                attempt_id=attempt_id,
            )
            if not resolution.approved:
                return workflow_status, {
                    "status": TaskStatus.FAILED.value,
                    "attempt_id": attempt_id,
                    "error": "approval_rejected",
                }
            workflow_status = (
                await self.transition_workflow(
                    WorkflowRunStatus.WAITING_APPROVAL.value,
                    WorkflowRunStatus.RUNNING.value,
                    reason=f"{task.task_id} approval granted",
                )
            )["to_status"]

        claim = await workflow.execute_activity(
            runtime_activities.claim_task_activity,
            args=[
                task.task_id,
                self.request.workflow_run_id,
                attempt_id,
                self.worker_id,
                self.request.lease_timeout_seconds,
            ],
            start_to_close_timeout=timedelta(seconds=5),
        )
        current_status = (
            await self.transition_task(
                current_status,
                TaskStatus.CLAIMED.value,
                reason=f"{task.task_id} claimed",
                metadata={"attempt_id": attempt_id, "task_id": task.task_id},
            )
        )["to_status"]
        await self.emit_event(
            EventType.TASK_CLAIMED,
            {
                "claim_id": claim["claim_id"],
                "worker_id": claim["worker_id"],
                "lease_timeout_seconds": claim["lease_timeout_seconds"],
                "to_status": current_status,
                "summary": f"{task.title} claimed by {self.worker_id}",
            },
            task_id=task.task_id,
            attempt_id=attempt_id,
        )
        await workflow.execute_activity(
            runtime_activities.heartbeat_claim_activity,
            args=[claim["claim_id"]],
            start_to_close_timeout=timedelta(seconds=5),
        )
        await self.emit_event(
            EventType.TASK_HEARTBEAT,
            {"claim_id": claim["claim_id"], "summary": f"Heartbeat for {task.title}"},
            task_id=task.task_id,
            attempt_id=attempt_id,
        )
        heartbeat_interval = max(self.request.lease_timeout_seconds // 3, 5)
        heartbeat_handle = asyncio.create_task(
            self._heartbeat_loop(claim["claim_id"], task.task_id, attempt_id, heartbeat_interval)
        )

        if task.task_id in self.request.simulation.reclaim_task_ids:
            reclaimed = await workflow.execute_activity(
                runtime_activities.reclaim_stale_claims_activity,
                args=[self.request.workflow_run_id, [claim["claim_id"]]],
                start_to_close_timeout=timedelta(seconds=5),
            )
            if reclaimed:
                current_status = (
                    await self.transition_task(
                        current_status,
                        TaskStatus.RECLAIMED.value,
                        reason=f"{task.task_id} reclaimed after stale lease",
                    )
                )["to_status"]
                await self.emit_event(
                    EventType.TASK_RECLAIMED,
                    {
                        "claim_id": claim["claim_id"],
                        "to_status": current_status,
                        "summary": f"{task.title} reclaimed after lease expiry",
                    },
                    task_id=task.task_id,
                    attempt_id=attempt_id,
                )
                await self._stop_heartbeat(heartbeat_handle)
                return workflow_status, {
                    "status": current_status,
                    "attempt_id": attempt_id,
                }

        current_status = (
            await self.transition_task(
                current_status,
                TaskStatus.RUNNING.value,
                reason=f"{task.task_id} running in graph runtime",
                metadata={"attempt_id": attempt_id, "task_id": task.task_id},
            )
        )["to_status"]
        await self.emit_event(
            EventType.TASK_RUNNING,
            {
                "to_status": current_status,
                "executor_summary": task.executor_summary or f"{task.graph_kind} graph runtime",
                "summary": f"{task.title} running",
            },
            task_id=task.task_id,
            attempt_id=attempt_id,
        )

        if task.executor_name:
            normalized_context_blocks = self._normalize_context_blocks(self.request.metadata)
            if not normalized_context_blocks:
                context_bundle = await workflow.execute_activity(
                    runtime_activities.assemble_context_activity,
                    args=[self._build_context_assembly_payload(task)],
                    start_to_close_timeout=timedelta(seconds=15),
                    retry_policy=RetryPolicy(maximum_attempts=3),
                )
                assembled_blocks = context_bundle.get("blocks", [])
                if isinstance(assembled_blocks, list):
                    normalized_context_blocks = assembled_blocks
            await self.emit_task_todo(
                task,
                summary=f"{task.title} context assembled; executor implementation is running",
                active_id="implement",
                completed_ids={"context", "plan"},
                attempt_id=attempt_id,
            )
            normalized_verify_commands = self._normalize_verify_commands(self.request.metadata)
            executor_dispatch_timeout_seconds = max(
                self._metadata_int(
                    "executor_timeout_seconds",
                    self.request.signal_timeout_seconds,
                ),
                60,
            )
            # Keep the activity timeout slightly longer than provider timeout so
            # the adapter can return a structured failure instead of racing a
            # Temporal activity timeout.
            executor_activity_timeout_seconds = executor_dispatch_timeout_seconds + max(
                self._metadata_int("executor_activity_timeout_buffer_seconds", 30),
                5,
            )
            approval_resolution: ApprovalResolution | None = None
            while True:
                dispatch_result = await workflow.execute_activity(
                    runtime_activities.dispatch_executor_activity,
                    args=[
                        self._build_executor_dispatch_payload(
                            task=task,
                            attempt_id=attempt_id,
                            executor_dispatch_timeout_seconds=executor_dispatch_timeout_seconds,
                            normalized_verify_commands=normalized_verify_commands,
                            normalized_context_blocks=normalized_context_blocks,
                            approval_resolution=approval_resolution,
                        )
                    ],
                    start_to_close_timeout=timedelta(seconds=executor_activity_timeout_seconds),
                    # Retry is handled in workflow semantics; avoid activity-level
                    # replay loops that can leave long-running heartbeats.
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )
                dispatch_payload = dispatch_result.get("result")
                approval_payload = dispatch_result.get("approval")
                if approval_payload is None:
                    break
                if approval_resolution is not None:
                    current_status = (
                        await self.transition_task(
                            current_status,
                            TaskStatus.FAILED.value,
                            reason=f"{task.task_id} executor requested duplicate approval",
                            metadata={"attempt_id": attempt_id, "task_id": task.task_id},
                        )
                    )["to_status"]
                    await self.emit_event(
                        EventType.TASK_FAILED,
                        {
                            "to_status": current_status,
                            "summary": f"{task.title} failed due to repeated approval request",
                        },
                        task_id=task.task_id,
                        attempt_id=attempt_id,
                    )
                    await self._stop_heartbeat(heartbeat_handle)
                    await workflow.execute_activity(
                        runtime_activities.release_claim_activity,
                        args=[claim["claim_id"]],
                        start_to_close_timeout=timedelta(seconds=5),
                    )
                    return workflow_status, {
                        "status": current_status,
                        "attempt_id": attempt_id,
                        "error": "approval_reissued",
                    }

                approval_id = approval_payload.get("approval_id")
                current_status = (
                    await self.transition_task(
                        current_status,
                        TaskStatus.WAITING_APPROVAL.value,
                        reason=f"{task.task_id} waiting for executor approval",
                        metadata={
                            "attempt_id": attempt_id,
                            "task_id": task.task_id,
                            "approval_id": approval_id,
                            "blocked_reason": "executor approval pending",
                        },
                    )
                )["to_status"]
                workflow_status = (
                    await self.transition_workflow(
                        workflow_status,
                        WorkflowRunStatus.WAITING_APPROVAL.value,
                        reason=f"{task.task_id} awaiting executor approval",
                        metadata={"task_id": task.task_id, "approval_id": approval_id},
                    )
                )["to_status"]
                await self.emit_event(
                    EventType.WORKFLOW_WAITING_APPROVAL,
                    {
                        "approval_id": approval_id,
                        "summary": f"{task.title} waiting for executor approval",
                    },
                    task_id=task.task_id,
                    attempt_id=attempt_id,
                )
                await self.emit_event(
                    EventType.APPROVAL_REQUESTED,
                    {
                        "approval": approval_payload,
                        "summary": f"{task.title} requires manual approval in executor",
                    },
                    task_id=task.task_id,
                    attempt_id=attempt_id,
                )
                try:
                    approval_resolution = await self.wait_for_approval(
                        str(approval_id) if isinstance(approval_id, str) else None
                    )
                except ApprovalTimeoutError:
                    current_status = (
                        await self.transition_task(
                            current_status,
                            TaskStatus.FAILED.value,
                            reason=f"{task.task_id} approval timed out",
                            metadata={"attempt_id": attempt_id, "task_id": task.task_id},
                        )
                    )["to_status"]
                    workflow_status = (
                        await self.transition_workflow(
                            workflow_status,
                            WorkflowRunStatus.FAILED.value,
                            reason=f"{task.task_id} approval timed out",
                            metadata={"task_id": task.task_id, "approval_id": approval_id},
                        )
                    )["to_status"]
                    await self.emit_event(
                        EventType.TASK_FAILED,
                        {
                            "to_status": current_status,
                            "summary": f"{task.title} failed because approval timed out",
                        },
                        task_id=task.task_id,
                        attempt_id=attempt_id,
                    )
                    await self._stop_heartbeat(heartbeat_handle)
                    await workflow.execute_activity(
                        runtime_activities.release_claim_activity,
                        args=[claim["claim_id"]],
                        start_to_close_timeout=timedelta(seconds=5),
                    )
                    return workflow_status, {
                        "status": current_status,
                        "attempt_id": attempt_id,
                        "error": "approval_timeout",
                    }

                await self.emit_event(
                    EventType.APPROVAL_RESOLVED,
                    {
                        "approval_id": approval_id,
                        "approved": approval_resolution.approved,
                        "actor": approval_resolution.actor,
                        "comment": approval_resolution.comment,
                        "approved_write_paths": approval_resolution.approved_write_paths,
                        "summary": (
                            "Approval "
                            f"{'approved' if approval_resolution.approved else 'rejected'} "
                            f"by {approval_resolution.actor}"
                        ),
                    },
                    task_id=task.task_id,
                    attempt_id=attempt_id,
                )
                if not approval_resolution.approved:
                    current_status = (
                        await self.transition_task(
                            current_status,
                            TaskStatus.FAILED.value,
                            reason=f"{task.task_id} approval rejected",
                            metadata={"attempt_id": attempt_id, "task_id": task.task_id},
                        )
                    )["to_status"]
                    workflow_status = (
                        await self.transition_workflow(
                            workflow_status,
                            WorkflowRunStatus.FAILED.value,
                            reason=f"{task.task_id} approval rejected",
                            metadata={"task_id": task.task_id, "approval_id": approval_id},
                        )
                    )["to_status"]
                    await self.emit_event(
                        EventType.TASK_FAILED,
                        {
                            "to_status": current_status,
                            "summary": f"{task.title} failed because approval was rejected",
                        },
                        task_id=task.task_id,
                        attempt_id=attempt_id,
                    )
                    await self._stop_heartbeat(heartbeat_handle)
                    await workflow.execute_activity(
                        runtime_activities.release_claim_activity,
                        args=[claim["claim_id"]],
                        start_to_close_timeout=timedelta(seconds=5),
                    )
                    return workflow_status, {
                        "status": current_status,
                        "attempt_id": attempt_id,
                        "error": "approval_rejected",
                    }

                workflow_status = (
                    await self.transition_workflow(
                        workflow_status,
                        WorkflowRunStatus.RUNNING.value,
                        reason=f"{task.task_id} approval granted",
                        metadata={"task_id": task.task_id, "approval_id": approval_id},
                    )
                )["to_status"]
                current_status = (
                    await self.transition_task(
                        current_status,
                        TaskStatus.RUNNING.value,
                        reason=f"{task.task_id} resumed after approval",
                        metadata={"attempt_id": attempt_id, "task_id": task.task_id},
                    )
                )["to_status"]
                await self.emit_event(
                    EventType.TASK_RUNNING,
                    {
                        "to_status": current_status,
                        "executor_summary": (
                            task.executor_summary or f"{task.graph_kind} graph runtime"
                        ),
                        "summary": f"{task.title} resumed after approval",
                    },
                    task_id=task.task_id,
                    attempt_id=attempt_id,
                )

            if not isinstance(dispatch_payload, dict):
                await self.emit_task_todo(
                    task,
                    summary=f"{task.title} executor returned an invalid payload",
                    completed_ids={"context", "plan"},
                    failed_id="implement",
                    attempt_id=attempt_id,
                )
                current_status = (
                    await self.transition_task(
                        current_status,
                        TaskStatus.FAILED.value,
                        reason=f"{task.task_id} executor returned invalid payload",
                        metadata={"attempt_id": attempt_id, "task_id": task.task_id},
                    )
                )["to_status"]
                await self.emit_event(
                    EventType.TASK_FAILED,
                    {
                        "to_status": current_status,
                        "summary": f"{task.title} failed due to invalid executor payload",
                    },
                    task_id=task.task_id,
                    attempt_id=attempt_id,
                )
                await self._stop_heartbeat(heartbeat_handle)
                await workflow.execute_activity(
                    runtime_activities.release_claim_activity,
                    args=[claim["claim_id"]],
                    start_to_close_timeout=timedelta(seconds=5),
                )
                return workflow_status, {
                    "status": current_status,
                    "attempt_id": attempt_id,
                    "error": "invalid_executor_payload",
                }

            dispatch_status = str(dispatch_payload.get("status") or ExecutionStatus.FAILED.value)
            if dispatch_status != ExecutionStatus.SUCCEEDED.value:
                failure = dispatch_payload.get("failure")
                failure_reason = (
                    str(failure.get("reason"))
                    if isinstance(failure, dict) and failure.get("reason")
                    else f"executor returned {dispatch_status}"
                )
                await self.emit_task_todo(
                    task,
                    summary=f"{task.title} executor failed: {failure_reason}",
                    completed_ids={"context", "plan"},
                    failed_id="implement",
                    attempt_id=attempt_id,
                )
                current_status = (
                    await self.transition_task(
                        current_status,
                        TaskStatus.FAILED.value,
                        reason=f"{task.task_id} executor failed: {failure_reason}",
                        metadata={"attempt_id": attempt_id, "task_id": task.task_id},
                    )
                )["to_status"]
                await self.emit_event(
                    EventType.TASK_FAILED,
                    {
                        "to_status": current_status,
                        "summary": f"{task.title} failed: {failure_reason}",
                        "failure": failure if isinstance(failure, dict) else None,
                    },
                    task_id=task.task_id,
                    attempt_id=attempt_id,
                )
                await self._stop_heartbeat(heartbeat_handle)
                await workflow.execute_activity(
                    runtime_activities.release_claim_activity,
                    args=[claim["claim_id"]],
                    start_to_close_timeout=timedelta(seconds=5),
                )
                return workflow_status, {
                    "status": current_status,
                    "attempt_id": attempt_id,
                    "error": failure_reason,
                }

            dispatch_artifacts = dispatch_payload.get("artifacts", [])
            if not isinstance(dispatch_artifacts, list):
                dispatch_artifacts = []
            graph_result = {
                "status": GraphExecutionStatus.COMPLETED.value,
                "graph_kind": task.graph_kind,
                "artifacts": dispatch_artifacts,
                "structured_output": dispatch_payload,
            }
            await self.emit_task_todo(
                task,
                summary=f"{task.title} implementation finished; verification is being checked",
                active_id="verify",
                completed_ids={"context", "plan", "implement"},
                attempt_id=attempt_id,
            )
        else:
            await self.emit_task_todo(
                task,
                summary=f"{task.title} graph execution is running",
                active_id="execute",
                completed_ids={"prepare"},
                attempt_id=attempt_id,
            )
            graph_result = await workflow.execute_activity(
                runtime_activities.execute_graph_activity,
                args=[
                    {
                        "graph_kind": task.graph_kind,
                        "objective": task.title,
                        "correlation": {
                            **self.base_correlation,
                            "task_id": task.task_id,
                            "attempt_id": attempt_id,
                        },
                        "input_payload": {
                            "task_id": task.task_id,
                            "workflow_name": self.workflow_name,
                            "objective": self.request.objective,
                        },
                        "interrupt_before_finalize": task.task_id
                        in self.request.simulation.interrupt_task_ids,
                    }
                ],
                start_to_close_timeout=timedelta(seconds=15),
            )
        if graph_result["status"] == GraphExecutionStatus.INTERRUPTED.value:
            checkpoint = graph_result["checkpoint"]
            checkpoint_id = checkpoint.get("checkpoint_id")
            if not checkpoint_id:
                raise RuntimeError("runtime graph interruption missing checkpoint_id")
            await self.emit_event(
                EventType.RUNTIME_GRAPH_INTERRUPTED,
                {
                    "checkpoint_id": checkpoint_id,
                    "summary": f"{task.title} interrupted and checkpointed",
                },
                task_id=task.task_id,
                attempt_id=attempt_id,
            )
            graph_result = await workflow.execute_activity(
                runtime_activities.execute_graph_activity,
                args=[
                    {
                        "graph_kind": task.graph_kind,
                        "objective": task.title,
                        "correlation": {
                            **self.base_correlation,
                            "task_id": task.task_id,
                            "attempt_id": attempt_id,
                        },
                        "checkpoint_id": checkpoint_id,
                    }
                ],
                start_to_close_timeout=timedelta(seconds=15),
            )

        await self.emit_event(
            EventType.RUNTIME_GRAPH_COMPLETED,
            {
                "graph_kind": graph_result["graph_kind"],
                "artifacts": graph_result["artifacts"],
                "summary": f"{task.title} graph execution completed",
            },
            task_id=task.task_id,
            attempt_id=attempt_id,
        )
        if not task.executor_name:
            await self.emit_task_todo(
                task,
                summary=f"{task.title} graph output produced; verification is running",
                active_id="verify",
                completed_ids={"prepare", "execute"},
                attempt_id=attempt_id,
            )
        await self.emit_event(
            EventType.TASK_GRAPH_UPDATED,
            {
                "nodes": [
                    {
                        "task_id": candidate.task_id,
                        "title": candidate.title,
                        "status": current_status
                        if candidate.task_id == task.task_id
                        else TaskStatus.QUEUED.value,
                        "blocked_reason": None
                        if not candidate.depends_on
                        else ", ".join(candidate.depends_on),
                        "executor_summary": candidate.executor_summary,
                        "todo_items": self._todo_items(candidate),
                    }
                    for candidate in self.request.tasks
                ],
                "edges": [
                    {
                        "source_task_id": dependency,
                        "target_task_id": candidate.task_id,
                        "kind": "depends_on",
                    }
                    for candidate in self.request.tasks
                    for dependency in candidate.depends_on
                ],
                "summary": f"Updated task graph after {task.title}",
            },
            task_id=task.task_id,
            attempt_id=attempt_id,
        )

        current_status = (
            await self.transition_task(
                current_status,
                TaskStatus.VERIFYING.value,
                reason=f"{task.task_id} verifying graph result",
                metadata={"attempt_id": attempt_id, "task_id": task.task_id},
            )
        )["to_status"]
        await self.emit_event(
            EventType.TASK_VERIFYING,
            {"to_status": current_status, "summary": f"{task.title} verifying output"},
            task_id=task.task_id,
            attempt_id=attempt_id,
        )

        if task.task_id in self.request.simulation.retry_task_ids:
            current_status = (
                await self.transition_task(
                    current_status,
                    TaskStatus.RETRYING.value,
                    reason=f"{task.task_id} retry requested",
                    metadata={"attempt_id": attempt_id, "task_id": task.task_id},
                )
            )["to_status"]
            workflow_status = (
                await self.transition_workflow(
                    workflow_status,
                    WorkflowRunStatus.RETRYING.value,
                    reason=f"{task.task_id} retry requested",
                )
            )["to_status"]
            await self.emit_event(
                EventType.WORKFLOW_RETRYING,
                {"summary": f"{task.title} marked for retry"},
                task_id=task.task_id,
                attempt_id=attempt_id,
            )
            current_status = (
                await self.transition_task(
                    current_status,
                    TaskStatus.RUNNING.value,
                    reason=f"{task.task_id} retry execution started",
                    metadata={"attempt_id": attempt_id, "task_id": task.task_id},
                )
            )["to_status"]
            workflow_status = (
                await self.transition_workflow(
                    workflow_status,
                    WorkflowRunStatus.RUNNING.value,
                    reason=f"{task.task_id} retry resumed",
                )
            )["to_status"]

        if task.task_id in self.request.simulation.terminal_failure_task_ids:
            await self.emit_task_todo(
                task,
                summary=f"{task.title} failed during terminal verification",
                completed_ids={
                    "context",
                    "plan",
                    "implement",
                }
                if task.executor_name
                else {"prepare", "execute"},
                failed_id="verify",
                attempt_id=attempt_id,
            )
            current_status = (
                await self.transition_task(
                    current_status,
                    TaskStatus.FAILED.value,
                    reason=f"{task.task_id} terminal failure",
                    metadata={"attempt_id": attempt_id, "task_id": task.task_id},
                )
            )["to_status"]
            await self.emit_event(
                EventType.TASK_FAILED,
                {"to_status": current_status, "summary": f"{task.title} failed terminally"},
                task_id=task.task_id,
                attempt_id=attempt_id,
            )
            await self._stop_heartbeat(heartbeat_handle)
            await workflow.execute_activity(
                runtime_activities.release_claim_activity,
                args=[claim["claim_id"]],
                start_to_close_timeout=timedelta(seconds=5),
            )
            return workflow_status, {
                "status": current_status,
                "attempt_id": attempt_id,
            }

        current_status = (
            await self.transition_task(
                current_status,
                TaskStatus.COMPLETED.value,
                reason=f"{task.task_id} completed successfully",
                metadata={"attempt_id": attempt_id, "task_id": task.task_id},
            )
        )["to_status"]
        await self.emit_event(
            EventType.TASK_COMPLETED,
            {
                "to_status": current_status,
                "artifacts": graph_result["artifacts"],
                "structured_output": graph_result["structured_output"],
                "summary": f"{task.title} completed",
            },
            task_id=task.task_id,
            attempt_id=attempt_id,
        )
        await self.emit_task_todo(
            task,
            summary=f"{task.title} todo checklist completed",
            completed_ids={item["id"] for item in self._todo_template(task)},
            attempt_id=attempt_id,
        )
        await self._stop_heartbeat(heartbeat_handle)
        await workflow.execute_activity(
            runtime_activities.release_claim_activity,
            args=[claim["claim_id"]],
            start_to_close_timeout=timedelta(seconds=5),
        )
        self.outputs[task.task_id] = graph_result["structured_output"]
        return workflow_status, {"status": current_status, "attempt_id": attempt_id}

    async def execute_task(
        self, task: WorkflowTaskSpec, workflow_status: str
    ) -> tuple[str, dict[str, Any]]:
        max_attempts = max(self.request.max_attempts, 1)
        last_result: dict[str, Any] | None = None
        current_workflow_status = workflow_status

        for attempt_no in range(1, max_attempts + 1):
            current_workflow_status, result = await self._execute_task_once(
                task, current_workflow_status, attempt_no
            )
            last_result = result
            terminal_status = result.get("status")
            if terminal_status not in {TaskStatus.FAILED.value, TaskStatus.RECLAIMED.value}:
                return current_workflow_status, result
            if attempt_no >= max_attempts:
                return current_workflow_status, result

            attempt_id = str(
                result.get("attempt_id")
                or self._build_attempt_id(task.task_id, attempt_no)
            )
            current_workflow_status = (
                await self.transition_workflow(
                    current_workflow_status,
                    WorkflowRunStatus.RETRYING.value,
                    reason=f"{task.task_id} retrying after attempt {attempt_no}",
                )
            )["to_status"]
            await self.emit_event(
                EventType.WORKFLOW_RETRYING,
                {
                    "summary": (
                        f"{task.title} retrying ({attempt_no + 1}/{max_attempts})"
                    ),
                    "attempt_no": attempt_no,
                    "max_attempts": max_attempts,
                },
                task_id=task.task_id,
                attempt_id=attempt_id,
            )
            backoff_seconds = self._retry_backoff_seconds(attempt_no)
            await workflow.sleep(timedelta(seconds=backoff_seconds))
            current_workflow_status = (
                await self.transition_workflow(
                    current_workflow_status,
                    WorkflowRunStatus.RUNNING.value,
                    reason=f"{task.task_id} resumed for retry attempt {attempt_no + 1}",
                )
            )["to_status"]

        assert last_result is not None
        return current_workflow_status, last_result


async def execute_standard_workflow(context: WorkflowExecutionContext) -> WorkflowResult:
    current_workflow_status = WorkflowRunStatus.CREATED.value
    current_workflow_status = (
        await context.transition_workflow(
            current_workflow_status,
            WorkflowRunStatus.QUEUED.value,
            reason=f"{context.workflow_name} queued",
        )
    )["to_status"]
    current_workflow_status = (
        await context.transition_workflow(
            current_workflow_status,
            WorkflowRunStatus.RUNNING.value,
            reason=f"{context.workflow_name} started",
        )
    )["to_status"]

    await context.emit_event(
        EventType.WORKFLOW_STARTED,
        {
            "workflow_name": context.workflow_name,
            "objective": context.request.objective,
            "summary": f"{context.workflow_name} started",
        },
    )
    await context.emit_event(
        EventType.TASK_GRAPH_UPDATED,
        context._task_graph_payload(
            f"{context.workflow_name} task graph initialized with todo checklists"
        ),
    )

    await workflow.execute_activity(
        runtime_activities.report_worker_health_activity,
        args=[context.worker_id, "Workflow execution active", [context.workflow_name]],
        start_to_close_timeout=timedelta(seconds=5),
    )

    if context.request.require_manual_approval:
        await context.emit_event(
            EventType.APPROVAL_REQUESTED,
            {"summary": f"{context.workflow_name} requested workflow-level approval"},
        )

    failed = False
    try:
        task_by_id = {task.task_id: task for task in context.request.tasks}
        dag = {
            task.task_id: set(task.depends_on)
            for task in context.request.tasks
        }
        for task in context.request.tasks:
            unknown = [dep for dep in task.depends_on if dep not in task_by_id]
            if unknown:
                raise TaskDependencyError(
                    f"{task.task_id} depends on unknown task(s): {', '.join(unknown)}"
                )
        sorter = TopologicalSorter(dag)
        sorter.prepare()
    except CycleError as exc:
        failed = True
        cycle_nodes = [str(node) for node in exc.args[1]] if len(exc.args) > 1 else []
        reason = (
            f"task dependency cycle detected: {', '.join(cycle_nodes)}"
            if cycle_nodes
            else "task dependency cycle detected"
        )
        current_workflow_status = (
            await context.transition_workflow(
                current_workflow_status,
                WorkflowRunStatus.FAILED.value,
                reason=reason,
            )
        )["to_status"]
        await context.emit_event(
            EventType.WORKFLOW_FAILED,
            {"summary": reason},
        )
    except TaskDependencyError as exc:
        failed = True
        reason = str(exc)
        current_workflow_status = (
            await context.transition_workflow(
                current_workflow_status,
                WorkflowRunStatus.FAILED.value,
                reason=reason,
            )
        )["to_status"]
        await context.emit_event(
            EventType.WORKFLOW_FAILED,
            {"summary": reason},
        )

    if not failed:
        while sorter.is_active():
            ready_ids = sorted(str(item) for item in sorter.get_ready())
            if not ready_ids:
                break
            for task_id in ready_ids:
                task = task_by_id[task_id]
                current_workflow_status, task_result = await context.execute_task(
                    task, current_workflow_status
                )
                if task_result["status"] in {TaskStatus.FAILED.value, TaskStatus.RECLAIMED.value}:
                    failed = True
                    if current_workflow_status != WorkflowRunStatus.FAILED.value:
                        current_workflow_status = (
                            await context.transition_workflow(
                                current_workflow_status,
                                WorkflowRunStatus.FAILED.value,
                                reason=f"{task.task_id} did not complete",
                            )
                        )["to_status"]
                    await context.emit_event(
                        EventType.WORKFLOW_FAILED,
                        {"summary": f"{context.workflow_name} failed on {task.title}"},
                        task_id=task.task_id,
                        attempt_id=task_result["attempt_id"],
                    )
                    break
                sorter.done(task_id)
            if failed:
                break

    if not failed:
        current_workflow_status = (
            await context.transition_workflow(
                current_workflow_status,
                WorkflowRunStatus.COMPLETED.value,
                reason=f"{context.workflow_name} completed",
            )
        )["to_status"]
        await context.emit_event(
            EventType.WORKFLOW_COMPLETED,
            {"summary": f"{context.workflow_name} completed", "outputs": context.outputs},
        )
        receipts = await context.send_notification(
            title=f"{context.workflow_name} completed",
            body=f"Run {context.request.workflow_run_id} completed successfully",
            metadata=context._resolve_notification_metadata(
                context.request.metadata,
                context.workflow_name,
            ),
        )
        notification_summary = context._summarize_notification_receipts(receipts)
        await context.emit_event(
            EventType.NOTIFICATION_SENT,
            {
                "summary": f"Completion notification sent for {context.workflow_name}",
                "receipts": receipts,
                **notification_summary,
            },
        )

    return WorkflowResult(
        workflow_run_id=context.request.workflow_run_id,
        workflow_name=context.workflow_name,
        status=current_workflow_status,
        outputs=context.outputs,
        event_count=0,
        approval_state=None,
    )
