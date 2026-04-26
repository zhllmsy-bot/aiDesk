from __future__ import annotations

from api.config import Settings
from api.integrations.llm.base import (
    AgentLoopProvider,
    ImplementationStatus,
    LLMProvider,
    LLMProviderUnavailableError,
    ProviderCapabilities,
)
from api.integrations.llm.claude_agent import ClaudeAgentProvider
from api.integrations.llm.litellm_provider import LiteLLMProvider
from api.integrations.llm.openai_agents import OpenAIAgentsProvider


def _reject_stub(capabilities: ProviderCapabilities) -> None:
    if capabilities.implementation_status == ImplementationStatus.STUB:
        raise LLMProviderUnavailableError(
            f"Provider {capabilities.provider} is declared as a stub and cannot be selected."
        )


def create_llm_provider(settings: Settings) -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "litellm":
        resolved = LiteLLMProvider(
            default_model=settings.llm_default_model,
            request_timeout_seconds=settings.llm_request_timeout_seconds,
        )
        _reject_stub(resolved.capabilities)
        return resolved
    raise LLMProviderUnavailableError(f"Unsupported LLM provider: {settings.llm_provider}")


def create_agent_loop_provider(settings: Settings) -> AgentLoopProvider:
    provider = settings.llm_agent_provider.lower()
    if provider == "claude_agent_sdk":
        resolved = ClaudeAgentProvider(model=settings.claude_agent_model)
        _reject_stub(resolved.capabilities)
        return resolved
    if provider in {"openai_agents", "openai-agents"}:
        resolved = OpenAIAgentsProvider(model=settings.openai_agents_model)
        _reject_stub(resolved.capabilities)
        return resolved
    raise LLMProviderUnavailableError(
        f"Unsupported agent-loop provider: {settings.llm_agent_provider}"
    )
