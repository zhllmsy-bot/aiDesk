from __future__ import annotations

import os

import pytest

from api.executors.contracts import (
    ArtifactType,
    ContextBlock,
    ContextLevel,
    DispatchControl,
    EvidenceKind,
    EvidenceRef,
    ExecutionStatus,
    ExecutorInputBundle,
    FailureKind,
    PermissionPolicy,
    TaskInfo,
    VerifyCommand,
    WorkspaceInfo,
    WorkspaceMode,
)
from api.executors.provider_contracts import FailureCategory
from api.executors.transports import CodexSessionConfig, ExecutorTransportError

CODEX_LIVE_ENABLED = os.environ.get("AI_DESK_LIVE_SMOKE_CODEX") == "1"
OPENHANDS_LIVE_ENABLED = os.environ.get("AI_DESK_LIVE_SMOKE_OPENHANDS") == "1"

skip_codex = pytest.mark.skipif(
    not CODEX_LIVE_ENABLED,
    reason="Set AI_DESK_LIVE_SMOKE_CODEX=1 to enable",
)
skip_openhands = pytest.mark.skipif(
    not OPENHANDS_LIVE_ENABLED,
    reason="Set AI_DESK_LIVE_SMOKE_OPENHANDS=1 to enable",
)

_LIVE_WS = os.environ.get("AI_DESK_LIVE_SMOKE_WORKSPACE", "/tmp/ai-desk-smoke")


def _live_bundle(*, executor: str = "codex") -> ExecutorInputBundle:
    return ExecutorInputBundle(
        task=TaskInfo(
            task_id="live-smoke-task-1",
            run_id="live-smoke-run-1",
            title="Live smoke test",
            description="Echo hello and verify the workspace is accessible",
            executor=executor,
            expected_artifact_types=[ArtifactType.LOG],
        ),
        workspace=WorkspaceInfo(
            project_id="live-smoke-project",
            workspace_ref="live-smoke-ws",
            root_path=_LIVE_WS,
            mode=WorkspaceMode.WORKTREE,
            writable_paths=[_LIVE_WS],
        ),
        context_blocks=[
            ContextBlock(
                level=ContextLevel.L0,
                title="Smoke test context",
                body="This is a live smoke test to verify executor connectivity.",
                source="live_smoke",
            )
        ],
        permission_policy=PermissionPolicy(
            workspace_allowlist=[_LIVE_WS],
            allowed_write_paths=[_LIVE_WS],
            command_allowlist=["echo", "ls", "cat", "python", "pytest"],
            command_denylist=["rm -rf"],
            require_manual_approval_for_write=False,
            workspace_mode=WorkspaceMode.WORKTREE,
        ),
        verify_commands=[VerifyCommand(id="verify-echo", command="echo hello")],
        proposed_commands=["echo hello"],
        secret_usages=[],
        evidence_refs=[
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                ref="smoke-seed",
                summary="smoke test seed",
            )
        ],
        dispatch=DispatchControl(
            idempotency_key="live-smoke-dispatch-1",
            attempt_id="live-smoke-attempt-1",
            timeout_seconds=300,
        ),
    )


@skip_codex
def test_codex_live_smoke() -> None:
    from api.executors.providers.codex import CodexExecutorAdapter

    config = CodexSessionConfig(
        transport=os.environ.get("AI_DESK_CODEX_TRANSPORT", "stdio"),
        url=os.environ.get("AI_DESK_CODEX_URL", "ws://127.0.0.1:8321"),
        command=os.environ.get(
            "AI_DESK_CODEX_COMMAND",
            "/Applications/Codex.app/Contents/Resources/codex",
        ),
        args=os.environ.get("AI_DESK_CODEX_ARGS", "app-server --listen stdio://").split(),
        model=os.environ.get("AI_DESK_CODEX_MODEL", "gpt-5.4"),
        reasoning_effort=os.environ.get("AI_DESK_CODEX_REASONING_EFFORT", "medium"),
        reasoning_summary=os.environ.get("AI_DESK_CODEX_REASONING_SUMMARY", "concise"),
        startup_timeout_seconds=float(os.environ.get("AI_DESK_CODEX_STARTUP_TIMEOUT", "20")),
        turn_timeout_seconds=float(os.environ.get("AI_DESK_CODEX_TURN_TIMEOUT", "300")),
    )
    adapter = CodexExecutorAdapter(config)
    bundle = _live_bundle(executor="codex")
    result = adapter.execute(bundle)

    assert result.status in (ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED)
    assert result.provenance.executor == "codex"
    assert result.provenance.provider_request_id.startswith("codex-")

    if result.status == ExecutionStatus.SUCCEEDED:
        assert len(result.artifacts) >= 1
        transcript_artifacts = [a for a in result.artifacts if a.artifact_type == ArtifactType.LOG]
        assert len(transcript_artifacts) >= 1
        if result.verification:
            assert isinstance(result.verification.passed, bool)
    else:
        assert result.failure is not None
        assert result.failure.kind in (FailureKind.RETRYABLE, FailureKind.TERMINAL)
        assert result.failure.category in (
            FailureCategory.TRANSPORT_FAILURE,
            FailureCategory.PROVIDER_TIMEOUT,
            FailureCategory.PROVIDER_ERROR,
            FailureCategory.SANDBOX_DENIAL,
            FailureCategory.PARTIAL_EXECUTION,
        )


@skip_openhands
def test_openhands_live_smoke() -> None:
    from api.executors.providers.openhands import OpenHandsExecutorAdapter

    base_url = os.environ.get("AI_DESK_OPENHANDS_URL", "http://127.0.0.1:3001")
    api_key = os.environ.get("AI_DESK_OPENHANDS_API_KEY")
    adapter = OpenHandsExecutorAdapter(
        base_url=base_url,
        api_key=api_key,
        allow_local_workspace=os.environ.get("AI_DESK_OPENHANDS_LOCAL_WORKSPACE_ENABLED") == "1",
    )
    bundle = _live_bundle(executor="openhands")
    result = adapter.execute(bundle)

    assert result.status in (ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED)
    assert result.provenance.executor == "openhands"
    assert result.provenance.provider_request_id.startswith("openhands-")

    if result.status == ExecutionStatus.SUCCEEDED:
        assert len(result.artifacts) >= 1
        session_log_artifacts = [a for a in result.artifacts if a.artifact_type == ArtifactType.LOG]
        assert len(session_log_artifacts) >= 1
        if result.verification:
            assert isinstance(result.verification.passed, bool)
    else:
        assert result.failure is not None
        assert result.failure.kind in (FailureKind.RETRYABLE, FailureKind.TERMINAL)
        assert result.failure.category in (
            FailureCategory.TRANSPORT_FAILURE,
            FailureCategory.PROVIDER_TIMEOUT,
            FailureCategory.PROVIDER_ERROR,
            FailureCategory.SANDBOX_DENIAL,
            FailureCategory.PARTIAL_EXECUTION,
        )


def test_codex_failure_mapping_transport_error() -> None:
    from api.executors.providers.codex import _classify_failure

    kind, category, _ = _classify_failure(ExecutorTransportError("connection refused"))
    assert kind == FailureKind.RETRYABLE
    assert category == FailureCategory.TRANSPORT_FAILURE


def test_codex_failure_mapping_timeout() -> None:
    from api.executors.providers.codex import _classify_failure

    kind, category, _ = _classify_failure(ExecutorTransportError("turn timed out"))
    assert kind == FailureKind.RETRYABLE
    assert category == FailureCategory.PROVIDER_TIMEOUT


def test_codex_failure_mapping_sandbox_denial() -> None:
    from api.executors.providers.codex import _classify_failure

    kind, category, _ = _classify_failure(ExecutorTransportError("sandbox permission denied"))
    assert kind == FailureKind.TERMINAL
    assert category == FailureCategory.SANDBOX_DENIAL


def test_codex_failure_mapping_cancelled() -> None:
    from api.executors.providers.codex import _classify_failure

    kind, category, _ = _classify_failure(ExecutorTransportError("execution cancelled by user"))
    assert kind == FailureKind.TERMINAL
    assert category == FailureCategory.CANCELLED


def test_codex_failure_mapping_generic_error() -> None:
    from api.executors.providers.codex import _classify_failure

    kind, category, _ = _classify_failure(RuntimeError("unexpected crash"))
    assert kind == FailureKind.TERMINAL
    assert category == FailureCategory.PROVIDER_ERROR


def test_openhands_failure_mapping_transport_error() -> None:
    from api.executors.providers.openhands import _classify_openhands_failure

    kind, category, _ = _classify_openhands_failure(
        ExecutorTransportError("OpenHands lost the session lease")
    )
    assert kind == FailureKind.RETRYABLE
    assert category == FailureCategory.TRANSPORT_FAILURE


def test_openhands_failure_mapping_timeout() -> None:
    import httpx

    from api.executors.providers.openhands import _classify_openhands_failure

    kind, category, _ = _classify_openhands_failure(httpx.TimeoutException("request timed out"))
    assert kind == FailureKind.RETRYABLE
    assert category == FailureCategory.PROVIDER_TIMEOUT


def test_openhands_failure_mapping_http_403() -> None:
    import httpx

    from api.executors.providers.openhands import _classify_openhands_failure

    request = httpx.Request("POST", "http://localhost/api/execute")
    response = httpx.Response(403, request=request)
    kind, category, _ = _classify_openhands_failure(
        httpx.HTTPStatusError("forbidden", request=request, response=response)
    )
    assert kind == FailureKind.TERMINAL
    assert category == FailureCategory.SANDBOX_DENIAL


def test_openhands_failure_mapping_http_503() -> None:
    import httpx

    from api.executors.providers.openhands import _classify_openhands_failure

    request = httpx.Request("POST", "http://localhost/api/execute")
    response = httpx.Response(503, request=request)
    kind, category, _ = _classify_openhands_failure(
        httpx.HTTPStatusError("unavailable", request=request, response=response)
    )
    assert kind == FailureKind.RETRYABLE
    assert category == FailureCategory.PROVIDER_TIMEOUT


def test_openhands_failure_mapping_http_400() -> None:
    import httpx

    from api.executors.providers.openhands import _classify_openhands_failure

    request = httpx.Request("POST", "http://localhost/api/execute")
    response = httpx.Response(400, request=request)
    kind, category, _ = _classify_openhands_failure(
        httpx.HTTPStatusError("bad request", request=request, response=response)
    )
    assert kind == FailureKind.TERMINAL
    assert category == FailureCategory.PROVIDER_ERROR


def test_codex_verification_from_command_execution_items() -> None:
    from api.executors.providers.codex import _extract_command_results

    items = [
        {
            "type": "commandExecution",
            "command": "pytest -q",
            "exitCode": 0,
            "status": "completed",
            "output": "3 passed",
        },
        {
            "type": "commandExecution",
            "command": "ruff check",
            "exitCode": 1,
            "status": "failed",
            "output": "1 error",
        },
        {"type": "fileChange", "changes": [{"path": "src/main.py"}]},
    ]
    results = _extract_command_results(items, ["pytest -q", "ruff check", "missing-cmd"])
    assert len(results) == 3
    assert results[0].command == "pytest -q"
    assert results[0].passed is True
    assert results[0].exit_code == 0
    assert results[1].command == "ruff check"
    assert results[1].passed is False
    assert results[1].exit_code == 1
    assert results[2].command == "missing-cmd"
    assert results[2].passed is False
    assert results[2].exit_code == 1


def test_codex_changed_paths_from_items() -> None:
    from api.executors.providers.codex import _extract_changed_paths_from_items

    items = [
        {
            "type": "fileChange",
            "changes": [{"path": "src/main.py"}, {"filePath": "src/utils.py"}],
        },
        {"type": "commandExecution", "command": "ls"},
        {"type": "fileChange", "changes": [{"path": "src/main.py"}]},
    ]
    paths = _extract_changed_paths_from_items(items)
    assert paths == ["src/main.py", "src/utils.py"]


def test_provider_contracts_are_serializable() -> None:
    from api.executors.provider_contracts import (
        CodexProviderError,
        FailureCategory,
        OpenHandsProviderError,
        ProviderCancellationPolicy,
        ProviderContract,
        ProviderName,
        ProviderTimeoutConfig,
    )

    timeout = ProviderTimeoutConfig()
    contract = ProviderContract(
        provider=ProviderName.CODEX,
        request_type="CodexProviderRequest",
        response_type="CodexProviderResponse",
        error_type="CodexProviderError",
        timeout=timeout,
        cancellation=ProviderCancellationPolicy(),
    )
    dumped = contract.model_dump(mode="json")
    assert dumped["provider"] == "codex"

    codex_error = CodexProviderError(
        failure_category=FailureCategory.PROVIDER_TIMEOUT,
        reason="turn timed out",
        retry_after_seconds=15,
    )
    assert codex_error.provider == "codex"
    assert codex_error.failure_category == FailureCategory.PROVIDER_TIMEOUT

    openhands_error = OpenHandsProviderError(
        failure_category=FailureCategory.TRANSPORT_FAILURE,
        reason="connection refused",
    )
    assert openhands_error.provider == "openhands"
    assert openhands_error.failure_category == FailureCategory.TRANSPORT_FAILURE
