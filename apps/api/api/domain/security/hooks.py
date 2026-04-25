from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from pydantic import Field

from api.executors.contracts import ExecutionModel


class ToolHookPhase(StrEnum):
    SESSION_START = "session_start"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    SESSION_END = "session_end"


class ToolHook(ExecutionModel):
    hook_id: str
    phase: ToolHookPhase
    idempotent: bool
    tool_allowlist: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ToolHookContext(ExecutionModel):
    phase: ToolHookPhase
    tool_name: str
    run_id: str
    task_id: str
    attempt_id: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class ToolHookDecision(ExecutionModel):
    allowed: bool
    hook_id: str
    reason: str | None = None


HookHandler = Callable[[ToolHookContext], ToolHookDecision]


@dataclass(slots=True)
class _HookRegistration:
    hook: ToolHook
    handler: HookHandler


class ToolHookPipeline:
    def __init__(self) -> None:
        self._registrations: list[_HookRegistration] = []

    def register(self, hook: ToolHook, handler: HookHandler) -> None:
        self._registrations.append(_HookRegistration(hook=hook, handler=handler))

    def run(self, context: ToolHookContext) -> ToolHookDecision:
        for registration in self._registrations:
            hook = registration.hook
            if hook.phase != context.phase:
                continue
            if hook.tool_allowlist and context.tool_name not in hook.tool_allowlist:
                continue
            if not hook.idempotent:
                return ToolHookDecision(
                    allowed=False,
                    hook_id=hook.hook_id,
                    reason="tool hook must declare idempotent=true",
                )
            try:
                decision = registration.handler(context)
            except Exception as exc:
                return ToolHookDecision(
                    allowed=False,
                    hook_id=hook.hook_id,
                    reason=f"tool hook failed: {exc}",
                )
            if not decision.allowed:
                return decision
        return ToolHookDecision(allowed=True, hook_id="pipeline")
