from __future__ import annotations

from importlib.util import find_spec

from api.integrations.llm.base import (
    AgentEvent,
    AgentEventType,
    AgentLoopProvider,
    AgentLoopRequest,
    CapabilityFlag,
    LLMProviderUnavailableError,
    ProviderCapabilities,
    ProviderKind,
)


class OpenAIAgentsProvider(AgentLoopProvider):
    def __init__(self, *, model: str) -> None:
        self._model = model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider="openai_agents",
            kind=ProviderKind.AGENT_LOOP,
            models=[self._model],
            flags=[
                CapabilityFlag.STREAMING,
                CapabilityFlag.TOOL_CALLING,
                CapabilityFlag.STRUCTURED_OUTPUT,
                CapabilityFlag.SUBAGENTS,
                CapabilityFlag.HOOKS,
            ],
        )

    def run_agent_loop(self, request: AgentLoopRequest) -> list[AgentEvent]:
        if find_spec("agents") is None and find_spec("openai_agents") is None:
            raise LLMProviderUnavailableError("openai-agents SDK is not installed")
        return [
            AgentEvent(
                id=f"{request.session_id}-started",
                session_id=request.session_id,
                type=AgentEventType.SESSION_STARTED,
                sequence=1,
                summary="OpenAI Agents SDK session started",
            )
        ]
