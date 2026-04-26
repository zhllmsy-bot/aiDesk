from __future__ import annotations

from importlib.util import find_spec

from api.integrations.llm.base import (
    AgentEvent,
    AgentEventType,
    AgentLoopProvider,
    AgentLoopRequest,
    CapabilityFlag,
    ImplementationStatus,
    LLMProviderUnavailableError,
    ProviderCapabilities,
    ProviderKind,
)


class ClaudeAgentProvider(AgentLoopProvider):
    def __init__(self, *, model: str) -> None:
        self._model = model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider="claude_agent_sdk",
            kind=ProviderKind.AGENT_LOOP,
            implementation_status=ImplementationStatus.STUB,
            models=[self._model],
            flags=[
                CapabilityFlag.TOOL_CALLING,
                CapabilityFlag.COMPUTER_USE,
                CapabilityFlag.SUBAGENTS,
                CapabilityFlag.SKILLS,
                CapabilityFlag.HOOKS,
            ],
        )

    def run_agent_loop(self, request: AgentLoopRequest) -> list[AgentEvent]:
        if find_spec("claude_agent_sdk") is None:
            raise LLMProviderUnavailableError("claude_agent_sdk is not installed")
        return [
            AgentEvent(
                id=f"{request.session_id}-started",
                session_id=request.session_id,
                type=AgentEventType.SESSION_STARTED,
                sequence=1,
                summary="Claude Agent SDK session started",
            )
        ]
