from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.executors.contracts import ExecutionModel

PROVIDER_CONTRACT_VERSION = "2026-04-19.provider.v1"


class ProviderName(StrEnum):
    CODEX = "codex"
    OPENHANDS = "openhands"


class FailureCategory(StrEnum):
    TRANSPORT_FAILURE = "transport_failure"
    PROVIDER_TIMEOUT = "provider_timeout"
    SANDBOX_DENIAL = "sandbox_denial"
    VERIFICATION_FAILURE = "verification_failure"
    PARTIAL_EXECUTION = "partial_execution"
    PROVIDER_ERROR = "provider_error"
    CANCELLED = "cancelled"


class CodexTransportMode(StrEnum):
    STDIO = "stdio"
    WEBSOCKET = "websocket"


class CodexThreadRequest(ExecutionModel):
    approval_policy: str = "never"
    cwd: str
    model: str
    sandbox: str = "danger-full-access"
    personality: str = "pragmatic"


class CodexTurnRequest(ExecutionModel):
    thread_id: str
    cwd: str
    model: str
    effort: str = "medium"
    summary: str = "concise"
    approval_policy: str = "never"
    sandbox_policy: dict[str, Any] = Field(default_factory=lambda: {"type": "dangerFullAccess"})
    input: list[dict[str, Any]] = Field(default_factory=list)


class CodexCompletedItem(ExecutionModel):
    item_type: str = Field(alias="type")
    text: str | None = None
    command: str | None = None
    status: str | None = None
    exit_code: int | None = Field(default=None, alias="exitCode")
    server: str | None = None
    tool: str | None = None
    changes: list[dict[str, Any]] | None = None


class CodexTurnResult(ExecutionModel):
    thread_id: str
    turn_id: str
    agent_message: str = ""
    completed_items: list[CodexCompletedItem] = Field(default_factory=list)
    error: str | None = None
    changed_paths: list[str] = Field(default_factory=list)


class CodexProviderRequest(ExecutionModel):
    contract_version: str = PROVIDER_CONTRACT_VERSION
    provider: str = ProviderName.CODEX
    transport: CodexTransportMode
    thread_config: CodexThreadRequest
    turn_config: CodexTurnRequest
    prompt: str
    verify_commands: list[str] = Field(default_factory=list)
    timeout_seconds: float = 1800.0


class CodexProviderResponse(ExecutionModel):
    contract_version: str = PROVIDER_CONTRACT_VERSION
    provider: str = ProviderName.CODEX
    turn_result: CodexTurnResult
    status: str = "completed"


class CodexProviderError(ExecutionModel):
    contract_version: str = PROVIDER_CONTRACT_VERSION
    provider: str = ProviderName.CODEX
    failure_category: FailureCategory
    reason: str
    detail: dict[str, Any] = Field(default_factory=dict)
    retry_after_seconds: int | None = None
class OpenHandsVerificationItem(ExecutionModel):
    command: str
    exit_code: int = 1
    output: str = ""
    passed: bool = False


class OpenHandsProviderResponse(ExecutionModel):
    contract_version: str = PROVIDER_CONTRACT_VERSION
    provider: str = ProviderName.OPENHANDS
    summary: str = "OpenHands execution completed"
    artifact_path: str = "artifacts/openhands/session.log"
    verification: dict[str, Any] | None = None
    workspace_output: dict[str, Any] | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"


class OpenHandsProviderError(ExecutionModel):
    contract_version: str = PROVIDER_CONTRACT_VERSION
    provider: str = ProviderName.OPENHANDS
    failure_category: FailureCategory
    reason: str
    detail: dict[str, Any] = Field(default_factory=dict)
    retry_after_seconds: int | None = None


class ProviderTimeoutConfig(ExecutionModel):
    startup_timeout_seconds: float = 20.0
    turn_timeout_seconds: float = 1800.0
    request_timeout_seconds: float = 60.0
    retry_after_seconds: int = 15


class ProviderCancellationPolicy(ExecutionModel):
    graceful_timeout_seconds: float = 5.0
    force_kill: bool = True


class ProviderContract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: str = PROVIDER_CONTRACT_VERSION
    provider: ProviderName
    request_type: str
    response_type: str
    error_type: str
    timeout: ProviderTimeoutConfig
    cancellation: ProviderCancellationPolicy
