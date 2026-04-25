from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
import asyncio
from typing import Any

import httpx

from api.executors.base import ExecutorAdapter
from api.executors.contracts import (
    ArtifactDescriptor,
    ArtifactType,
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
from api.executors.openhands_runtime import (
    OpenHandsRuntimeConfigurationError,
    OpenHandsWorkspaceConfig,
    build_openhands_workspace,
)
from api.executors.provider_contracts import (
    FailureCategory,
    OpenHandsProviderResponse,
    OpenHandsVerificationItem,
    ProviderTimeoutConfig,
)
from api.executors.transports import ExecutorTransportError


def _classify_openhands_failure(
    exc: Exception,
) -> tuple[FailureKind, FailureCategory, str]:
    if isinstance(exc, ExecutorTransportError):
        message = str(exc).lower()
        if "timeout" in message or "timed out" in message:
            return (
                FailureKind.RETRYABLE,
                FailureCategory.PROVIDER_TIMEOUT,
                str(exc),
            )
        if "sandbox" in message or "permission" in message or "denied" in message:
            return (
                FailureKind.TERMINAL,
                FailureCategory.SANDBOX_DENIAL,
                str(exc),
            )
        if "cancel" in message:
            return (
                FailureKind.TERMINAL,
                FailureCategory.CANCELLED,
                str(exc),
            )
        if "session lease" in message or "lease" in message:
            return (
                FailureKind.RETRYABLE,
                FailureCategory.TRANSPORT_FAILURE,
                str(exc),
            )
        return (
            FailureKind.RETRYABLE,
            FailureCategory.TRANSPORT_FAILURE,
            str(exc),
        )
    if isinstance(exc, httpx.TimeoutException):
        return (
            FailureKind.RETRYABLE,
            FailureCategory.PROVIDER_TIMEOUT,
            str(exc),
        )
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code == 403:
            return (
                FailureKind.TERMINAL,
                FailureCategory.SANDBOX_DENIAL,
                str(exc),
            )
        if status_code in (408, 429, 502, 503, 504):
            return (
                FailureKind.RETRYABLE,
                FailureCategory.PROVIDER_TIMEOUT,
                str(exc),
            )
        if 400 <= status_code < 500:
            return (
                FailureKind.TERMINAL,
                FailureCategory.PROVIDER_ERROR,
                str(exc),
            )
        return (
            FailureKind.RETRYABLE,
            FailureCategory.TRANSPORT_FAILURE,
            str(exc),
        )
    message = str(exc).lower()
    exc_name = type(exc).__name__.lower()
    if "timeout" in message or "timeouterror" in exc_name:
        return (
            FailureKind.RETRYABLE,
            FailureCategory.PROVIDER_TIMEOUT,
            str(exc),
        )
    return FailureKind.TERMINAL, FailureCategory.PROVIDER_ERROR, str(exc)


class OpenHandsExecutorAdapter(ExecutorAdapter):
    def __init__(
        self,
        *,
        base_url: str | None,
        api_key: str | None = None,
        remote_working_dir: str | None = None,
        allow_local_workspace: bool = False,
    ) -> None:
        self._workspace_config = OpenHandsWorkspaceConfig(
            host=base_url,
            api_key=api_key,
            remote_working_dir=remote_working_dir,
            allow_local_workspace=allow_local_workspace,
        )

    @property
    def capability(self) -> ExecutorCapability:
        return ExecutorCapability(
            executor="openhands",
            supports_write=True,
            supports_verify=True,
            supports_tools=True,
            supports_screenshots=False,
        )

    @property
    def timeout_config(self) -> ProviderTimeoutConfig:
        return ProviderTimeoutConfig(request_timeout_seconds=60.0)

    def execute(self, bundle: ExecutorInputBundle) -> ExecutorResultBundle:
        provider_request_id = f"openhands-{bundle.dispatch.idempotency_key}"
        provenance = ExecutionProvenance(
            executor="openhands",
            provider_request_id=provider_request_id,
            model="openhands-runtime",
            attempt_id=(bundle.dispatch.attempt_id or bundle.dispatch.idempotency_key),
            workspace_ref=bundle.workspace.workspace_ref,
            trigger="runtime_dispatch",
            metadata={
                "context_block_count": len(bundle.context_blocks),
                "project_id": bundle.workspace.project_id,
                "run_id": bundle.task.run_id,
                "task_id": bundle.task.task_id,
                "secret_names": [usage.name for usage in bundle.secret_usages],
                "runtime_target": self._workspace_config.display_target,
                "runtime_mode": (
                    "remote"
                    if self._workspace_config.uses_remote_runtime
                    else "local"
                ),
            },
        )
        try:
            result_payload = asyncio.run(self._run(bundle))
        except Exception as exc:
            failure_kind, failure_category, reason = _classify_openhands_failure(exc)
            return ExecutorResultBundle(
                status=ExecutionStatus.FAILED,
                logs=[LogEntry(stream="stderr", message=str(exc))],
                artifacts=[],
                failure=FailureInfo(
                    kind=failure_kind,
                    category=failure_category,
                    reason=reason,
                    retry_after_seconds=(15 if failure_kind == FailureKind.RETRYABLE else None),
                ),
                provenance=provenance,
            )

        provider_response = self._parse_response(result_payload)
        evidence = provider_response.summary
        verification = self._map_verification(provider_response)
        artifacts = self._build_artifacts(bundle, provider_response, provenance)

        if provider_response.workspace_output:
            partial = provider_response.workspace_output.get("partial")
            if partial:
                error_msg = str(
                    provider_response.workspace_output.get("error") or "partial execution"
                )
                return ExecutorResultBundle(
                    status=ExecutionStatus.FAILED,
                    logs=[LogEntry(stream="stdout", message=evidence)],
                    artifacts=artifacts,
                    verification=verification,
                    failure=FailureInfo(
                        kind=FailureKind.RETRYABLE,
                        category=FailureCategory.PARTIAL_EXECUTION,
                        reason=error_msg,
                        retry_after_seconds=15,
                    ),
                    provenance=provenance,
                    heartbeat_count=1,
                )

        return ExecutorResultBundle(
            status=ExecutionStatus.SUCCEEDED,
            logs=[LogEntry(stream="stdout", message=evidence)],
            artifacts=artifacts,
            verification=verification,
            provenance=provenance,
            heartbeat_count=1,
        )

    def _parse_response(self, result_payload: dict[str, object]) -> OpenHandsProviderResponse:
        verification_payload = result_payload.get("verification")
        verify_payload: dict[str, object] = (
            verification_payload if isinstance(verification_payload, dict) else {}
        )
        workspace_output_payload = result_payload.get("workspace_output")
        workspace_output: dict[str, Any] | None = (
            workspace_output_payload if isinstance(workspace_output_payload, dict) else None
        )
        return OpenHandsProviderResponse(
            summary=str(result_payload.get("summary") or "OpenHands execution completed"),
            artifact_path=str(
                result_payload.get("artifact_path") or "artifacts/openhands/session.log"
            ),
            verification=verify_payload if verify_payload else None,
            workspace_output=workspace_output,
            raw=result_payload,
        )

    def _map_verification(self, response: OpenHandsProviderResponse) -> VerificationResult | None:
        if response.verification is None:
            return None
        verification_results: list[VerificationCommandResult] = []
        raw_results = response.verification.get("results")
        if not isinstance(raw_results, list):
            return None
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            parsed = OpenHandsVerificationItem.model_validate(item)
            verification_results.append(
                VerificationCommandResult(
                    command=parsed.command,
                    exit_code=parsed.exit_code,
                    output=parsed.output,
                    passed=parsed.passed,
                )
            )
        if not verification_results:
            return None
        return VerificationResult(
            passed=all(item.passed for item in verification_results),
            summary=str(response.verification.get("summary") or "OpenHands verification results"),
            results=verification_results,
        )

    def _build_artifacts(
        self,
        bundle: ExecutorInputBundle,
        response: OpenHandsProviderResponse,
        provenance: ExecutionProvenance,
    ) -> list[ArtifactDescriptor]:
        artifacts: list[ArtifactDescriptor] = []
        artifacts.append(
            ArtifactDescriptor(
                artifact_type=ArtifactType.LOG,
                path=response.artifact_path,
                content_hash=(f"sha256:openhands:session:{bundle.dispatch.idempotency_key}"),
                producer="openhands",
                workspace_ref=bundle.workspace.workspace_ref,
                provenance=provenance,
                summary="OpenHands session log",
                metadata={
                    "content": response.summary,
                    "supports_tools": self.capability.supports_tools,
                },
                evidence_refs=bundle.evidence_refs,
            )
        )
        if response.verification:
            artifacts.append(
                ArtifactDescriptor(
                    artifact_type=ArtifactType.EVIDENCE,
                    path="artifacts/openhands/verification.json",
                    content_hash=(
                        f"sha256:openhands:verification:{bundle.dispatch.idempotency_key}"
                    ),
                    producer="openhands",
                    workspace_ref=bundle.workspace.workspace_ref,
                    provenance=provenance,
                    summary="OpenHands verification evidence",
                    metadata={"verification": response.verification},
                    evidence_refs=bundle.evidence_refs,
                )
            )
        if response.workspace_output:
            artifacts.append(
                ArtifactDescriptor(
                    artifact_type=ArtifactType.FILE,
                    path="artifacts/openhands/workspace-output.json",
                    content_hash=(f"sha256:openhands:workspace:{bundle.dispatch.idempotency_key}"),
                    producer="openhands",
                    workspace_ref=bundle.workspace.workspace_ref,
                    provenance=provenance,
                    summary="OpenHands workspace output",
                    metadata={"workspace_output": response.workspace_output},
                    evidence_refs=bundle.evidence_refs,
                )
            )
        return artifacts

    async def _run(self, bundle: ExecutorInputBundle) -> dict[str, object]:
        if bundle.task.metadata.get("simulate_retryable_failure"):
            raise ExecutorTransportError("OpenHands lost the session lease")
        return await asyncio.to_thread(self._run_with_workspace, bundle)

    def _run_with_workspace(self, bundle: ExecutorInputBundle) -> dict[str, object]:
        try:
            workspace = build_openhands_workspace(
                self._workspace_config,
                root_path=bundle.workspace.root_path,
            )
        except OpenHandsRuntimeConfigurationError as exc:
            raise ExecutorTransportError(str(exc)) from exc
        timeout_seconds = float(bundle.dispatch.timeout_seconds)
        command_summaries: list[str] = []
        command_results: list[dict[str, object]] = []
        verification_results: list[dict[str, object]] = []
        workspace_output: dict[str, object] = {
            "workspace_ref": bundle.workspace.workspace_ref,
            "working_dir": workspace.working_dir,
            "runtime_mode": (
                "remote" if self._workspace_config.uses_remote_runtime else "local"
            ),
            "commands": command_results,
        }

        try:
            with workspace:
                for command in bundle.proposed_commands:
                    result = workspace.execute_command(
                        command,
                        cwd=workspace.working_dir,
                        timeout=timeout_seconds,
                    )
                    command_results.append(
                        {
                            "command": result.command,
                            "exit_code": result.exit_code,
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                            "timeout_occurred": result.timeout_occurred,
                        }
                    )
                    command_summaries.append(
                        self._summarize_command_result(result.command, result.exit_code)
                    )
                    if result.timeout_occurred:
                        raise ExecutorTransportError(
                            f"OpenHands command timed out: {result.command}"
                        )
                    if result.exit_code != 0:
                        raise ExecutorTransportError(
                            f"OpenHands command failed: {result.command} exited {result.exit_code}"
                        )

                for command in bundle.verify_commands:
                    result = workspace.execute_command(
                        command.command,
                        cwd=workspace.working_dir,
                        timeout=timeout_seconds,
                    )
                    verification_results.append(
                        {
                            "command": result.command,
                            "exit_code": result.exit_code,
                            "output": self._merge_output(result.stdout, result.stderr),
                            "passed": result.exit_code == 0 and not result.timeout_occurred,
                        }
                    )

                try:
                    changes = workspace.git_changes(".")
                    workspace_output["git_changes"] = [
                        change.model_dump(mode="json") for change in changes
                    ]
                except Exception:
                    workspace_output["git_changes"] = []
        except httpx.HTTPError as exc:
            raise ExecutorTransportError(str(exc)) from exc

        summary = "OpenHands workspace execution completed"
        if command_summaries:
            summary = "; ".join(command_summaries)
        if bundle.task.description:
            summary = f"{summary}. {bundle.task.description}"

        verification_payload: dict[str, object] | None = None
        if verification_results:
            verification_payload = {
                "summary": "OpenHands verification results",
                "results": verification_results,
            }

        return {
            "summary": summary,
            "artifact_path": "artifacts/openhands/session.log",
            "verification": verification_payload,
            "workspace_output": workspace_output,
            "status": "completed",
        }

    def _summarize_command_result(self, command: str, exit_code: int) -> str:
        return f"`{command}` exited {exit_code}"

    def _merge_output(self, stdout: str, stderr: str) -> str:
        if stdout and stderr:
            return f"{stdout}\n{stderr}"
        return stdout or stderr
