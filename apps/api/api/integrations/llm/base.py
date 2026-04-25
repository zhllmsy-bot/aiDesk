from __future__ import annotations

# pyright: reportUnknownVariableType=false
from collections.abc import Iterable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

LLM_CONTRACT_VERSION = "2026-04-25.llm.v1"

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


def utcnow() -> datetime:
    return datetime.now(UTC)


class LLMContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class StreamChunkType(StrEnum):
    MESSAGE_START = "message_start"
    DELTA = "delta"
    TOOL_CALL = "tool_call"
    DONE = "done"
    ERROR = "error"


class ProviderKind(StrEnum):
    CHAT = "chat"
    AGENT_LOOP = "agent_loop"
    EXECUTOR_HARNESS = "executor_harness"


class CapabilityFlag(StrEnum):
    STREAMING = "streaming"
    TOOL_CALLING = "tool_calling"
    STRUCTURED_OUTPUT = "structured_output"
    VISION = "vision"
    COMPUTER_USE = "computer_use"
    SUBAGENTS = "subagents"
    SKILLS = "skills"
    HOOKS = "hooks"


class ToolCallStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AgentEventType(StrEnum):
    SESSION_STARTED = "session.started"
    MESSAGE_DELTA = "message.delta"
    MESSAGE_COMPLETED = "message.completed"
    TOOL_REQUESTED = "tool.requested"
    TOOL_COMPLETED = "tool.completed"
    SKILL_INJECTED = "skill.injected"
    HOOK_COMPLETED = "hook.completed"
    SESSION_COMPLETED = "session.completed"
    SESSION_FAILED = "session.failed"


class ToolDefinition(LLMContractModel):
    name: str
    description: str | None = None
    parameters: JsonObject = Field(default_factory=dict)
    strict: bool = False
    provider_payload: JsonObject = Field(default_factory=dict)


class ToolCall(LLMContractModel):
    id: str
    name: str
    arguments: JsonObject = Field(default_factory=dict)
    status: ToolCallStatus = ToolCallStatus.PENDING
    provider_payload: JsonObject = Field(default_factory=dict)


class ToolResult(LLMContractModel):
    tool_call_id: str
    name: str
    status: ToolCallStatus
    content: str | JsonValue
    error: str | None = None
    provider_payload: JsonObject = Field(default_factory=dict)


class ChatMessage(LLMContractModel):
    role: ChatRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    provider_payload: JsonObject = Field(default_factory=dict)


class ChatRequest(LLMContractModel):
    schema_version: str = LLM_CONTRACT_VERSION
    provider: str | None = None
    model: str
    messages: list[ChatMessage]
    tools: list[ToolDefinition] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    stream: bool = False
    metadata: JsonObject = Field(default_factory=dict)


class StreamChunk(LLMContractModel):
    schema_version: str = LLM_CONTRACT_VERSION
    id: str
    type: StreamChunkType
    delta: str | None = None
    tool_call: ToolCall | None = None
    error: str | None = None
    provider_payload: JsonObject = Field(default_factory=dict)


class Usage(LLMContractModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class ChatResponse(LLMContractModel):
    schema_version: str = LLM_CONTRACT_VERSION
    id: str
    provider: str
    model: str
    message: ChatMessage
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: str | None = None
    usage: Usage | None = None
    provider_payload: JsonObject = Field(default_factory=dict)


class AgentBudget(LLMContractModel):
    max_tokens: int | None = Field(default=None, ge=1)
    max_tool_calls: int | None = Field(default=None, ge=1)
    max_wall_clock_seconds: int | None = Field(default=None, ge=1)
    max_cost_usd: float | None = Field(default=None, ge=0)


class AgentProfile(LLMContractModel):
    id: str
    prompt: str
    tool_allowlist: list[str]
    model: str
    budget: AgentBudget = Field(default_factory=AgentBudget)
    skills: list[str] = Field(default_factory=list)
    hooks: list[str] = Field(default_factory=list)
    metadata: JsonObject = Field(default_factory=dict)


class ProviderCapabilities(LLMContractModel):
    provider: str
    kind: ProviderKind
    models: list[str]
    flags: list[CapabilityFlag] = Field(default_factory=list)
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    metadata: JsonObject = Field(default_factory=dict)


class AgentLoopRequest(LLMContractModel):
    session_id: str
    profile: AgentProfile
    messages: list[ChatMessage]
    context_ledger_id: str | None = None
    capabilities: ProviderCapabilities | None = None
    metadata: JsonObject = Field(default_factory=dict)


class AgentEvent(LLMContractModel):
    id: str
    session_id: str
    type: AgentEventType
    sequence: int = Field(ge=1)
    occurred_at: datetime = Field(default_factory=utcnow)
    message: ChatMessage | None = None
    tool_call: ToolCall | None = None
    tool_result: ToolResult | None = None
    summary: str | None = None
    metadata: JsonObject = Field(default_factory=dict)


class LLMProviderError(RuntimeError):
    pass


class LLMProviderUnavailableError(LLMProviderError):
    pass


class LLMProvider(Protocol):
    @property
    def capabilities(self) -> ProviderCapabilities: ...

    def complete_chat(self, request: ChatRequest) -> ChatResponse: ...


class AgentLoopProvider(Protocol):
    @property
    def capabilities(self) -> ProviderCapabilities: ...

    def run_agent_loop(self, request: AgentLoopRequest) -> Iterable[AgentEvent]: ...
