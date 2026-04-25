from __future__ import annotations

from api.executors.providers.agent_harness import AgentHarnessExecutorAdapter


class ClaudeAgentExecutorAdapter(AgentHarnessExecutorAdapter):
    def __init__(self, *, model: str) -> None:
        super().__init__(
            executor="claude_agent",
            model=model,
            supports_screenshots=True,
            unavailable_reason=(
                "Claude Agent SDK executor requires claude_agent_sdk runtime wiring."
            ),
        )
