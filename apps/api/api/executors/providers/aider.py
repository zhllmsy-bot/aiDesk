from __future__ import annotations

from api.executors.providers.agent_harness import AgentHarnessExecutorAdapter


class AiderExecutorAdapter(AgentHarnessExecutorAdapter):
    def __init__(self, *, model: str) -> None:
        super().__init__(
            executor="aider",
            model=model,
            supports_screenshots=False,
            unavailable_reason="Aider library executor requires aider runtime wiring.",
        )
