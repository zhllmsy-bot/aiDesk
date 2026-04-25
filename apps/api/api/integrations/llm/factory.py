from __future__ import annotations

from api.config import Settings
from api.integrations.llm.base import AgentLoopProvider, LLMProvider, LLMProviderUnavailableError
from api.integrations.llm.claude_agent import ClaudeAgentProvider
from api.integrations.llm.litellm_provider import LiteLLMProvider
from api.integrations.llm.openai_agents import OpenAIAgentsProvider


def create_llm_provider(settings: Settings) -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "litellm":
        return LiteLLMProvider(
            default_model=settings.llm_default_model,
            request_timeout_seconds=settings.llm_request_timeout_seconds,
        )
    raise LLMProviderUnavailableError(f"Unsupported LLM provider: {settings.llm_provider}")


def create_agent_loop_provider(settings: Settings) -> AgentLoopProvider:
    provider = settings.llm_agent_provider.lower()
    if provider == "claude_agent_sdk":
        return ClaudeAgentProvider(model=settings.claude_agent_model)
    if provider in {"openai_agents", "openai-agents"}:
        return OpenAIAgentsProvider(model=settings.openai_agents_model)
    raise LLMProviderUnavailableError(
        f"Unsupported agent-loop provider: {settings.llm_agent_provider}"
    )
