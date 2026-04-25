from __future__ import annotations

from api.executors.providers.agent_harness import AgentHarnessExecutorAdapter


class OpenAIAgentsExecutorAdapter(AgentHarnessExecutorAdapter):
    def __init__(self, *, model: str) -> None:
        super().__init__(
            executor="openai_agents",
            model=model,
            supports_screenshots=False,
            unavailable_reason="OpenAI Agents executor requires openai-agents runtime wiring.",
        )
