from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
import asyncio
import contextlib
import json
from pathlib import Path
from typing import Any

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
from api.executors.provider_contracts import (
    CodexCompletedItem,
    CodexTurnResult,
    FailureCategory,
    ProviderTimeoutConfig,
)
from api.executors.transports import (
    CodexAppServerSession,
    CodexSessionConfig,
    ExecutorTransportError,
)


def _summarize_completed_item(item: dict[str, Any]) -> str | None:
    item_type = item.get("type")
    if item_type == "agentMessage":
        text = item.get("text")
        return str(text) if isinstance(text, str) else None
    if item_type == "commandExecution":
        command = item.get("command") or "<unknown>"
        status = item.get("status") or "unknown"
        exit_code = item.get("exitCode")
        return f"commandExecution: {command} [{status}, exit={exit_code}]"
    if item_type == "mcpToolCall":
        return f"mcpToolCall: {item.get('server')}::{item.get('tool')} [{item.get('status')}]"
    if item_type == "fileChange":
        changes = item.get("changes") or []
        if isinstance(changes, list):
            return f"fileChange: {len(changes)} change(s)"
    return None


def _extract_changed_paths_from_items(
    items: list[dict[str, Any]],
) -> list[str]:
    paths: list[str] = []
    for item in items:
        if item.get("type") != "fileChange":
            continue
        changes = item.get("changes") or []
        if not isinstance(changes, list):
            continue
        for change in changes:
            path = change.get("path") or change.get("filePath")
            if isinstance(path, str) and path:
                paths.append(path)
    return list(dict.fromkeys(paths))


def _extract_changed_paths(evidence: str) -> list[str]:
    paths: list[str] = []
    for raw_line in evidence.splitlines():
        line = raw_line.strip().strip("`")
        if line.startswith("/") or line.startswith("./"):
            paths.append(line)
    return list(dict.fromkeys(paths))


def _extract_command_results(
    items: list[dict[str, Any]],
    verify_commands: list[str],
) -> list[VerificationCommandResult]:
    command_map: dict[str, dict[str, Any]] = {}
    for item in items:
        if item.get("type") != "commandExecution":
            continue
        command = str(item.get("command") or "")
        if command:
            command_map[command] = item

    results: list[VerificationCommandResult] = []
    for verify_cmd in verify_commands:
        matched_item = command_map.get(verify_cmd)
        if matched_item is not None:
            exit_code = matched_item.get("exitCode")
            status = str(matched_item.get("status") or "")
            passed = exit_code == 0 and status not in ("failed", "error")
            output = str(matched_item.get("output") or matched_item.get("text") or "")
            results.append(
                VerificationCommandResult(
                    command=verify_cmd,
                    exit_code=(int(exit_code) if exit_code is not None else 1),
                    output=output or "observed in executor command execution",
                    passed=passed,
                )
            )
        else:
            results.append(
                VerificationCommandResult(
                    command=verify_cmd,
                    exit_code=1,
                    output="not observed in executor output",
                    passed=False,
                )
            )
    return results


def _classify_failure(
    exc: Exception,
) -> tuple[FailureKind, FailureCategory, str]:
    reason = str(exc).strip() or type(exc).__name__
    if isinstance(exc, ExecutorTransportError):
        message = reason.lower()
        if "timeout" in message or "timed out" in message:
            return (
                FailureKind.RETRYABLE,
                FailureCategory.PROVIDER_TIMEOUT,
                reason or "provider transport timed out",
            )
        if "sandbox" in message or "permission" in message or "denied" in message:
            return (
                FailureKind.TERMINAL,
                FailureCategory.SANDBOX_DENIAL,
                reason,
            )
        if "cancel" in message:
            return (
                FailureKind.TERMINAL,
                FailureCategory.CANCELLED,
                reason,
            )
        return (
            FailureKind.RETRYABLE,
            FailureCategory.TRANSPORT_FAILURE,
            reason,
        )
    message = reason.lower()
    exc_name = type(exc).__name__.lower()
    if "timeout" in message or "timedout" in message or "timeouterror" in exc_name:
        return (
            FailureKind.RETRYABLE,
            FailureCategory.PROVIDER_TIMEOUT,
            reason or "provider execution timed out",
        )
    return FailureKind.TERMINAL, FailureCategory.PROVIDER_ERROR, reason


class CodexExecutorAdapter(ExecutorAdapter):
    def __init__(self, config: CodexSessionConfig) -> None:
        self._config = config

    @property
    def capability(self) -> ExecutorCapability:
        return ExecutorCapability(
            executor="codex",
            supports_write=True,
            supports_verify=True,
            supports_tools=True,
            supports_screenshots=True,
        )

    @property
    def timeout_config(self) -> ProviderTimeoutConfig:
        return ProviderTimeoutConfig(
            startup_timeout_seconds=self._config.startup_timeout_seconds,
            turn_timeout_seconds=self._config.turn_timeout_seconds,
        )

    def execute(self, bundle: ExecutorInputBundle) -> ExecutorResultBundle:
        provider_request_id = f"codex-{bundle.dispatch.idempotency_key}"
        workspace_root_path = str(Path(bundle.workspace.root_path).expanduser())
        provenance = ExecutionProvenance(
            executor="codex",
            provider_request_id=provider_request_id,
            model=self._config.model,
            attempt_id=(bundle.dispatch.attempt_id or bundle.dispatch.idempotency_key),
            workspace_ref=bundle.workspace.workspace_ref,
            trigger="runtime_dispatch",
            metadata={
                "context_block_count": len(bundle.context_blocks),
                "supports_verify": self.capability.supports_verify,
                "project_id": bundle.workspace.project_id,
                "run_id": bundle.task.run_id,
                "task_id": bundle.task.task_id,
                "secret_names": [usage.name for usage in bundle.secret_usages],
                "transport": self._config.transport,
                "dispatch_timeout_seconds": bundle.dispatch.timeout_seconds,
                "workspace_root_path": workspace_root_path,
                "workspace_writable_paths": list(bundle.workspace.writable_paths),
            },
        )
        if bundle.task.metadata.get("simulate_success"):
            simulated_completed_items: list[CodexCompletedItem] = []
            for verify_command in bundle.verify_commands:
                simulated_completed_items.append(
                    CodexCompletedItem(
                        type="commandExecution",
                        command=verify_command.command,
                        status="completed",
                        exitCode=0,
                        text="simulated command verification result",
                    )
                )
            turn_result = CodexTurnResult(
                thread_id="simulated-thread",
                turn_id="simulated-turn",
                agent_message=(
                    "Simulated Codex execution completed successfully.\n"
                    + "\n".join(command.command for command in bundle.verify_commands)
                ),
                completed_items=simulated_completed_items,
                changed_paths=[],
            )
            verification = self._map_verification(bundle, turn_result)
            return ExecutorResultBundle(
                status=ExecutionStatus.SUCCEEDED,
                logs=self._build_logs(turn_result),
                artifacts=self._build_artifacts(bundle, turn_result, provenance, verification),
                verification=verification,
                provenance=provenance,
                heartbeat_count=max(1, len(bundle.proposed_commands)),
            )
        workspace_precheck_error = self._validate_workspace(bundle)
        if workspace_precheck_error is not None:
            return ExecutorResultBundle(
                status=ExecutionStatus.FAILED,
                logs=[LogEntry(stream="stderr", message=workspace_precheck_error)],
                artifacts=[],
                failure=FailureInfo(
                    kind=FailureKind.TERMINAL,
                    category=FailureCategory.PROVIDER_ERROR,
                    reason=workspace_precheck_error,
                ),
                provenance=provenance,
            )
        try:
            # Enforce an upper bound for provider execution to avoid workflow
            # activities hanging until Temporal-level cancellation.
            timeout_seconds = max(1, int(bundle.dispatch.timeout_seconds))
            turn_result = asyncio.run(
                asyncio.wait_for(self._run_codex(bundle), timeout=timeout_seconds)
            )
        except Exception as exc:
            failure_kind, failure_category, reason = _classify_failure(exc)
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

        verification = self._map_verification(bundle, turn_result)
        artifacts = self._build_artifacts(bundle, turn_result, provenance, verification)
        is_partial = turn_result.error is not None and turn_result.agent_message.strip() != ""
        if is_partial:
            return ExecutorResultBundle(
                status=ExecutionStatus.FAILED,
                logs=self._build_logs(turn_result),
                artifacts=artifacts,
                verification=verification,
                failure=FailureInfo(
                    kind=FailureKind.RETRYABLE,
                    category=FailureCategory.PARTIAL_EXECUTION,
                    reason=turn_result.error or "partial execution",
                    retry_after_seconds=15,
                ),
                provenance=provenance,
                heartbeat_count=max(1, len(bundle.proposed_commands)),
            )

        return ExecutorResultBundle(
            status=ExecutionStatus.SUCCEEDED,
            logs=self._build_logs(turn_result),
            artifacts=artifacts,
            verification=verification,
            provenance=provenance,
            heartbeat_count=max(1, len(bundle.proposed_commands)),
        )

    @staticmethod
    def _validate_workspace(bundle: ExecutorInputBundle) -> str | None:
        root = Path(bundle.workspace.root_path).expanduser()
        if not root.is_absolute():
            return (
                "workspace root path must be absolute: "
                f"{bundle.workspace.root_path}"
            )
        if not root.exists() or not root.is_dir():
            return (
                "workspace root path does not exist or is not a directory: "
                f"{root}"
            )
        resolved_root = root.resolve()
        for path in bundle.workspace.writable_paths:
            writable = Path(path).expanduser()
            if not writable.is_absolute():
                return f"workspace writable path must be absolute: {path}"
            try:
                writable.resolve().relative_to(resolved_root)
            except ValueError:
                return (
                    "workspace writable path is outside workspace root: "
                    f"{writable} (root={resolved_root})"
                )
        return None

    def _build_logs(self, turn_result: CodexTurnResult) -> list[LogEntry]:
        entries: list[LogEntry] = [
            LogEntry(
                stream="system",
                message="codex executor completed request",
            ),
        ]
        if turn_result.agent_message.strip():
            entries.append(
                LogEntry(
                    stream="stdout",
                    message=turn_result.agent_message,
                )
            )
        for item_summary in turn_result.completed_items:
            summary = _summarize_completed_item(item_summary.model_dump(by_alias=True))
            if summary:
                entries.append(LogEntry(stream="stdout", message=summary))
        return entries

    def _build_artifacts(
        self,
        bundle: ExecutorInputBundle,
        turn_result: CodexTurnResult,
        provenance: ExecutionProvenance,
        verification: VerificationResult | None,
    ) -> list[ArtifactDescriptor]:
        artifacts: list[ArtifactDescriptor] = []
        artifacts.append(
            ArtifactDescriptor(
                artifact_type=ArtifactType.LOG,
                path="artifacts/codex/transcript.md",
                content_hash=(f"sha256:codex:transcript:{bundle.dispatch.idempotency_key}"),
                producer="codex",
                workspace_ref=bundle.workspace.workspace_ref,
                provenance=provenance,
                summary="Codex execution transcript",
                metadata={
                    "content": turn_result.agent_message,
                    "thread_id": turn_result.thread_id,
                    "turn_id": turn_result.turn_id,
                    "completed_items": [
                        item.model_dump(by_alias=True) for item in turn_result.completed_items
                    ],
                },
                evidence_refs=bundle.evidence_refs,
            )
        )
        changed_paths = turn_result.changed_paths or _extract_changed_paths(
            turn_result.agent_message
        )
        if changed_paths:
            artifacts.append(
                ArtifactDescriptor(
                    artifact_type=ArtifactType.PATCH,
                    path="artifacts/codex/changed-files.json",
                    content_hash=(f"sha256:codex:changes:{bundle.dispatch.idempotency_key}"),
                    producer="codex",
                    workspace_ref=bundle.workspace.workspace_ref,
                    provenance=provenance,
                    summary=f"Codex changed {len(changed_paths)} file(s)",
                    metadata={
                        "changed_paths": changed_paths,
                        "write_paths": bundle.workspace.writable_paths,
                    },
                    evidence_refs=bundle.evidence_refs,
                )
            )
        if bundle.verify_commands:
            artifacts.append(
                ArtifactDescriptor(
                    artifact_type=ArtifactType.EVIDENCE,
                    path="artifacts/codex/verification.json",
                    content_hash=(f"sha256:codex:verification:{bundle.dispatch.idempotency_key}"),
                    producer="codex",
                    workspace_ref=bundle.workspace.workspace_ref,
                    provenance=provenance,
                    summary="Codex verification evidence",
                    metadata={
                        "verify_commands": [cmd.command for cmd in bundle.verify_commands],
                        "verification": (
                            verification.model_dump(mode="json")
                            if verification is not None
                            else None
                        ),
                        "verification_source": (
                            "transcript_inference"
                            if verification is not None
                            and "transcript" in verification.summary.lower()
                            else "command_execution"
                        ),
                    },
                    evidence_refs=bundle.evidence_refs,
                )
            )
        return artifacts

    async def _run_codex(self, bundle: ExecutorInputBundle) -> CodexTurnResult:
        final_agent_message = ""
        completed_items_raw: list[dict[str, Any]] = []
        turn_error: str | None = None
        async with CodexAppServerSession(self._config) as session:
            thread_result = await session.request(
                "thread/start",
                {
                    "approvalPolicy": "never",
                    "cwd": bundle.workspace.root_path,
                    "model": self._config.model,
                    "sandbox": "danger-full-access",
                    "personality": "pragmatic",
                },
            )
            thread_id = thread_result["thread"]["id"]
            turn_result = await session.request(
                "turn/start",
                {
                    "threadId": thread_id,
                    "cwd": bundle.workspace.root_path,
                    "model": self._config.model,
                    "effort": self._config.reasoning_effort,
                    "summary": self._config.reasoning_summary,
                    "approvalPolicy": "never",
                    "sandboxPolicy": {"type": "dangerFullAccess"},
                    "input": [
                        {
                            "type": "text",
                            "text": self._prompt(bundle),
                            "text_elements": [],
                        }
                    ],
                },
            )
            turn_id = turn_result["turn"]["id"]
            while True:
                notification = await session.next_notification()
                method = notification.get("method")
                params = notification.get("params") or {}
                if params.get("threadId") != thread_id:
                    continue
                if params.get("turnId") not in {None, turn_id}:
                    continue
                if method == "item/agentMessage/delta":
                    final_agent_message += str(params.get("delta", ""))
                    continue
                if method == "item/completed":
                    item = params.get("item") or {}
                    completed_items_raw.append(item)
                    continue
                if method == "error" and not params.get("willRetry"):
                    error_payload = params.get("error") or {}
                    msg = error_payload.get("message") or json.dumps(
                        error_payload, ensure_ascii=False
                    )
                    turn_error = str(msg)
                    continue
                if method == "turn/completed":
                    turn = params.get("turn") or {}
                    if turn.get("status") == "failed":
                        error_payload = turn.get("error") or {}
                        msg = (
                            error_payload.get("message")
                            or turn_error
                            or "Codex app-server turn failed."
                        )
                        turn_error = str(msg)
                    break

        changed_paths = _extract_changed_paths_from_items(completed_items_raw)
        completed_items = []
        for raw_item in completed_items_raw:
            with contextlib.suppress(Exception):
                completed_items.append(CodexCompletedItem.model_validate(raw_item))

        if turn_error and not final_agent_message.strip() and not completed_items_raw:
            raise ExecutorTransportError(turn_error)

        return CodexTurnResult(
            thread_id=thread_id,
            turn_id=turn_id,
            agent_message=final_agent_message.strip(),
            completed_items=completed_items,
            error=turn_error,
            changed_paths=changed_paths,
        )

    def _prompt(self, bundle: ExecutorInputBundle) -> str:
        lines = [
            "You are the Codex execution agent for an AI Desk task.",
            f"Project root: {bundle.workspace.root_path}",
            f"Task title: {bundle.task.title}",
            f"Task description: {bundle.task.description}",
        ]
        if bundle.workspace.writable_paths:
            writable = ", ".join(bundle.workspace.writable_paths)
            lines.append(f"Write ownership is restricted to: {writable}")
        if bundle.verify_commands:
            lines.append("Verification commands:")
            lines.extend(f"- {command.command}" for command in bundle.verify_commands)
        if bundle.context_blocks:
            lines.append("Context:")
            lines.extend(
                f"- [{block.level}] {block.title}: {block.body}" for block in bundle.context_blocks
            )
        lines.extend(
            [
                "Instructions:",
                "- Work directly in the provided project root.",
                "- Keep changes within the declared ownership scope.",
                "- Run listed verification commands when possible.",
                (
                    "- End with a concise execution summary including"
                    " changed files, verification status, and blockers."
                ),
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _map_verification(
        bundle: ExecutorInputBundle,
        turn_result: CodexTurnResult,
    ) -> VerificationResult | None:
        if not bundle.verify_commands:
            return None
        verify_commands = [command.command for command in bundle.verify_commands]
        item_results = _extract_command_results(
            [item.model_dump(by_alias=True) for item in turn_result.completed_items],
            verify_commands,
        )
        if item_results:
            return VerificationResult(
                passed=all(r.passed for r in item_results),
                summary="Verification from Codex command execution results.",
                results=item_results,
            )
        results: list[VerificationCommandResult] = []
        lower = turn_result.agent_message.lower()
        for command in bundle.verify_commands:
            mentioned = command.command.lower() in lower
            fail_tokens = ("failed", "exit=1", "traceback")
            passed = mentioned and not any(token in lower for token in fail_tokens)
            results.append(
                VerificationCommandResult(
                    command=command.command,
                    exit_code=0 if passed else 1,
                    output=("observed in executor transcript" if mentioned else "not observed"),
                    passed=passed,
                )
            )
        return VerificationResult(
            passed=all(r.passed for r in results),
            summary=(
                "Verification inferred from Codex transcript (no command execution items found)."
            ),
            results=results,
        )
