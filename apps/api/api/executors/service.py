from __future__ import annotations

from api.executors.contracts import (
    ApprovalType,
    DispatchExecutionResponse,
    ExecutionStatus,
    ExecutorInputBundle,
    FailureKind,
)
from api.executors.registry import ExecutorRegistry
from api.observability.logging import get_logger, set_correlation
from api.observability.metrics import get_metrics
from api.review.service import ApprovalService, ArtifactService, AttemptStore, EvidenceService
from api.security.service import SecurityPolicyService

logger = get_logger("executors.dispatch")


class ExecutorDispatchService:
    def __init__(
        self,
        registry: ExecutorRegistry,
        security_policy: SecurityPolicyService,
        approvals: ApprovalService,
        artifacts: ArtifactService,
        evidence: EvidenceService,
        attempts: AttemptStore,
    ) -> None:
        self._registry = registry
        self._security_policy = security_policy
        self._approvals = approvals
        self._artifacts = artifacts
        self._evidence = evidence
        self._attempts = attempts

    def dispatch_without_persistence(
        self,
        bundle: ExecutorInputBundle,
    ) -> DispatchExecutionResponse:
        metrics = get_metrics()
        set_correlation(
            workflow_run_id=bundle.task.run_id,
            task_id=bundle.task.task_id,
            attempt_id=bundle.dispatch.attempt_id or bundle.dispatch.idempotency_key,
        )
        executor_name = bundle.task.executor
        metrics.inc_counter("executor_dispatched", executor=executor_name)
        logger.info(
            "executor dispatch started",
            extra={"executor": executor_name, "project_id": bundle.workspace.project_id},
        )

        gate = self._security_policy.evaluate(bundle)
        if gate.needs_approval:
            approval = self._approvals.request_approval(
                project_id=bundle.workspace.project_id,
                run_id=bundle.task.run_id,
                task_id=bundle.task.task_id,
                approval_type=ApprovalType.WRITE_EXECUTION,
                requested_by="system",
                reason=gate.reason or "manual approval required before execution",
                required_scope=gate.required_scope,
            )
            self._attempts.record_waiting_approval(bundle, approval)
            metrics.inc_counter(
                "approval_requested",
                approval_type=str(ApprovalType.WRITE_EXECUTION),
            )
            metrics.gauge("approval_pending").inc()
            logger.info(
                "executor dispatch requires approval",
                extra={"executor": executor_name, "approval_id": approval.approval_id},
            )
            return DispatchExecutionResponse(result=None, approval=approval)

        adapter = self._registry.get(executor_name)
        result = adapter.execute(bundle)
        return DispatchExecutionResponse(result=result, approval=None)

    def persist_response(
        self,
        bundle: ExecutorInputBundle,
        response: DispatchExecutionResponse,
    ) -> None:
        result = response.result
        if result is None:
            return

        metrics = get_metrics()
        executor_name = bundle.task.executor
        adapter = self._registry.get(bundle.task.executor)
        attempt_id = bundle.dispatch.attempt_id or bundle.dispatch.idempotency_key

        if result.provenance and result.provenance.provider_request_id:
            set_correlation(provider_request_id=result.provenance.provider_request_id)

        if result.status == ExecutionStatus.SUCCEEDED:
            metrics.inc_counter("executor_succeeded", executor=executor_name)
            logger.info(
                "executor dispatch succeeded",
                extra={"executor": executor_name, "attempt_id": attempt_id},
            )
        elif result.failure is not None:
            if result.failure.kind == FailureKind.RETRYABLE:
                metrics.inc_counter("executor_retryable_failure", executor=executor_name)
                logger.warning(
                    "executor dispatch retryable failure",
                    extra={
                        "executor": executor_name,
                        "attempt_id": attempt_id,
                        "reason": result.failure.reason,
                    },
                )
            else:
                metrics.inc_counter("executor_terminal_failure", executor=executor_name)
                logger.error(
                    "executor dispatch terminal failure",
                    extra={
                        "executor": executor_name,
                        "attempt_id": attempt_id,
                        "reason": result.failure.reason,
                    },
                )

        artifact_ids = self._artifacts.register_artifacts(
            project_id=bundle.workspace.project_id,
            run_id=bundle.task.run_id,
            task_id=bundle.task.task_id,
            source_attempt_id=attempt_id,
            source_executor=adapter.capability.executor,
            artifacts=result.artifacts,
        )
        self._attempts.record_result(bundle, result, artifact_ids)
        self._evidence.record_execution(
            attempt_id=attempt_id,
            artifact_ids=artifact_ids,
            verification=result.verification,
            provenance=result.provenance,
        )

    def dispatch(self, bundle: ExecutorInputBundle) -> DispatchExecutionResponse:
        response = self.dispatch_without_persistence(bundle)
        self.persist_response(bundle, response)
        return response
