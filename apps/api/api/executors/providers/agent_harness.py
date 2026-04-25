from __future__ import annotations

from api.executors.base import ExecutorAdapter
from api.executors.contracts import (
    ExecutionProvenance,
    ExecutionStatus,
    ExecutorCapability,
    ExecutorInputBundle,
    ExecutorResultBundle,
    FailureInfo,
    FailureKind,
    LogEntry,
    VerificationCommandResult,
    VerificationResult,
)
from api.executors.provider_contracts import FailureCategory, ProviderTimeoutConfig


class AgentHarnessExecutorAdapter(ExecutorAdapter):
    def __init__(
        self,
        *,
        executor: str,
        model: str,
        supports_screenshots: bool = False,
        unavailable_reason: str | None = None,
    ) -> None:
        self._executor = executor
        self._model = model
        self._supports_screenshots = supports_screenshots
        self._unavailable_reason = unavailable_reason

    @property
    def capability(self) -> ExecutorCapability:
        return ExecutorCapability(
            executor=self._executor,
            supports_write=True,
            supports_verify=True,
            supports_tools=True,
            supports_screenshots=self._supports_screenshots,
        )

    @property
    def timeout_config(self) -> ProviderTimeoutConfig:
        return ProviderTimeoutConfig(turn_timeout_seconds=1800.0, request_timeout_seconds=60.0)

    def execute(self, bundle: ExecutorInputBundle) -> ExecutorResultBundle:
        provider_request_id = f"{self._executor}-{bundle.dispatch.idempotency_key}"
        provenance = ExecutionProvenance(
            executor=self._executor,
            provider_request_id=provider_request_id,
            model=self._model,
            attempt_id=(bundle.dispatch.attempt_id or bundle.dispatch.idempotency_key),
            workspace_ref=bundle.workspace.workspace_ref,
            trigger="runtime_dispatch",
            metadata={
                "context_block_count": len(bundle.context_blocks),
                "project_id": bundle.workspace.project_id,
                "run_id": bundle.task.run_id,
                "task_id": bundle.task.task_id,
                "harness": "agent",
            },
        )
        if bundle.task.metadata.get("simulate_success"):
            verification = self._verification(bundle)
            return ExecutorResultBundle(
                status=ExecutionStatus.SUCCEEDED,
                logs=[
                    LogEntry(
                        stream="stdout",
                        message=f"Simulated {self._executor} agent harness execution completed.",
                    )
                ],
                verification=verification,
                provenance=provenance,
                heartbeat_count=max(1, len(bundle.verify_commands)),
            )

        reason = self._unavailable_reason or f"{self._executor} agent harness is not configured"
        return ExecutorResultBundle(
            status=ExecutionStatus.FAILED,
            logs=[LogEntry(stream="stderr", message=reason)],
            failure=FailureInfo(
                kind=FailureKind.TERMINAL,
                category=FailureCategory.PROVIDER_ERROR,
                reason=reason,
            ),
            provenance=provenance,
        )

    def _verification(self, bundle: ExecutorInputBundle) -> VerificationResult:
        results = [
            VerificationCommandResult(
                command=command.command,
                exit_code=0,
                output="simulated agent harness verification result",
                passed=True,
            )
            for command in bundle.verify_commands
        ]
        return VerificationResult(
            passed=all(result.passed for result in results),
            summary="All simulated verification commands passed.",
            results=results,
        )
