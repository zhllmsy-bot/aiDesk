from __future__ import annotations

from api.executors.providers.agent_harness import AgentHarnessExecutorAdapter


class ClaudeCodeExecutorAdapter(AgentHarnessExecutorAdapter):
    def __init__(self, *, command: str, model: str) -> None:
        super().__init__(
            executor="claude_code",
            model=model,
            supports_screenshots=True,
            unavailable_reason=(
                f"Claude Code command '{command}' is registered but subprocess execution is "
                "not enabled for this environment."
            ),
        )
