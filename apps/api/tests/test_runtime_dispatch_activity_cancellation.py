from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest

from api.executors.contracts import (
    DispatchControl,
    DispatchExecutionResponse,
    ExecutionProvenance,
    ExecutionStatus,
    ExecutorInputBundle,
    ExecutorResultBundle,
    PermissionPolicy,
    TaskInfo,
    WorkspaceInfo,
    WorkspaceMode,
)
from api.workflows.activities import runtime_activities


def _bundle() -> ExecutorInputBundle:
    return ExecutorInputBundle(
        task=TaskInfo(
            task_id="task-activity-1",
            run_id="run-activity-1",
            title="Dispatch activity test",
            description="Verify cancellation-safe persistence",
            executor="codex",
        ),
        workspace=WorkspaceInfo(
            project_id="project-activity-1",
            workspace_ref="ws-activity-1",
            root_path="/tmp",
            mode=WorkspaceMode.READ_ONLY,
            writable_paths=[],
        ),
        context_blocks=[],
        permission_policy=PermissionPolicy(
            workspace_allowlist=["/tmp"],
            allowed_write_paths=[],
            command_allowlist=[],
            command_denylist=[],
            require_manual_approval_for_write=False,
            workspace_mode=WorkspaceMode.READ_ONLY,
        ),
        verify_commands=[],
        proposed_commands=[],
        secret_usages=[],
        evidence_refs=[],
        dispatch=DispatchControl(
            idempotency_key="dispatch-activity-1",
            attempt_id="attempt-activity-1",
            timeout_seconds=60,
        ),
    )


def _response() -> DispatchExecutionResponse:
    return DispatchExecutionResponse(
        result=ExecutorResultBundle(
            status=ExecutionStatus.SUCCEEDED,
            provenance=ExecutionProvenance(
                executor="codex",
                provider_request_id="provider-activity-1",
                attempt_id="attempt-activity-1",
                workspace_ref="ws-activity-1",
                trigger="test",
            ),
        ),
        approval=None,
    )


class _FakeDispatcher:
    def __init__(self, response: DispatchExecutionResponse, *, delay_seconds: float = 0.0) -> None:
        self._response = response
        self._delay_seconds = delay_seconds
        self.dispatch_calls = 0
        self.persist_calls = 0

    def dispatch_without_persistence(
        self,
        bundle: ExecutorInputBundle,
    ) -> DispatchExecutionResponse:
        self.dispatch_calls += 1
        if self._delay_seconds > 0:
            time.sleep(self._delay_seconds)
        return self._response

    def persist_response(
        self,
        bundle: ExecutorInputBundle,
        response: DispatchExecutionResponse,
    ) -> None:
        self.persist_calls += 1


def _patch_runtime_activity(monkeypatch: pytest.MonkeyPatch, dispatcher: _FakeDispatcher) -> None:
    monkeypatch.setattr(runtime_activities, "_ensure_models_registered", lambda: None)
    monkeypatch.setattr(
        runtime_activities,
        "_container",
        lambda: SimpleNamespace(settings=object()),
    )
    monkeypatch.setattr(
        "api.executors.dependencies.configure_execution_container",
        lambda _settings: SimpleNamespace(dispatcher=dispatcher),
    )


@pytest.mark.asyncio
async def test_dispatch_executor_activity_persists_when_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispatcher = _FakeDispatcher(_response())
    _patch_runtime_activity(monkeypatch, dispatcher)
    monkeypatch.setattr(runtime_activities.activity, "is_cancelled", lambda: False)

    payload = await runtime_activities.dispatch_executor_activity(_bundle().model_dump(mode="json"))

    assert payload["result"]["status"] == ExecutionStatus.SUCCEEDED.value
    assert dispatcher.dispatch_calls == 1
    assert dispatcher.persist_calls == 1


@pytest.mark.asyncio
async def test_dispatch_executor_activity_skips_persistence_if_task_cancelled_while_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispatcher = _FakeDispatcher(_response(), delay_seconds=0.05)
    _patch_runtime_activity(monkeypatch, dispatcher)
    monkeypatch.setattr(runtime_activities.activity, "is_cancelled", lambda: False)

    task = asyncio.create_task(
        runtime_activities.dispatch_executor_activity(_bundle().model_dump(mode="json"))
    )
    await asyncio.sleep(0.01)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    await asyncio.sleep(0.08)
    assert dispatcher.dispatch_calls == 1
    assert dispatcher.persist_calls == 0


@pytest.mark.asyncio
async def test_dispatch_executor_activity_skips_persistence_if_temporal_already_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispatcher = _FakeDispatcher(_response())
    _patch_runtime_activity(monkeypatch, dispatcher)
    monkeypatch.setattr(runtime_activities.activity, "is_cancelled", lambda: True)

    with pytest.raises(asyncio.CancelledError):
        await runtime_activities.dispatch_executor_activity(_bundle().model_dump(mode="json"))

    assert dispatcher.dispatch_calls == 1
    assert dispatcher.persist_calls == 0
