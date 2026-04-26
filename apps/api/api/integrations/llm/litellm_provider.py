from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
import json
from collections.abc import Callable, Mapping, Sequence
from importlib import import_module
from typing import Any, cast
from uuid import uuid4

from api.integrations.llm.base import (
    CapabilityFlag,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatRole,
    ImplementationStatus,
    JsonObject,
    JsonValue,
    LLMProvider,
    LLMProviderUnavailableError,
    ProviderCapabilities,
    ProviderKind,
    ToolCall,
    ToolDefinition,
    Usage,
)


def _as_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, Mapping):
            return cast(Mapping[str, object], dumped)
    return {}


def _first_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Sequence) and not isinstance(value, str) and value:
        return _as_mapping(value[0])
    return {}


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _json_object(value: object) -> JsonObject:
    return cast(JsonObject, value) if isinstance(value, dict) else {}


def _message_payload(message: ChatMessage) -> dict[str, object]:
    payload: dict[str, object] = {
        "role": message.role.value,
        "content": message.content,
    }
    if message.name:
        payload["name"] = message.name
    if message.tool_call_id:
        payload["tool_call_id"] = message.tool_call_id
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": json.dumps(call.arguments),
                },
            }
            for call in message.tool_calls
        ]
    return payload


def _tool_payload(tool: ToolDefinition) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.parameters,
            "strict": tool.strict,
        },
    }


def _parse_tool_calls(message_payload: Mapping[str, object]) -> list[ToolCall]:
    raw_tool_calls = message_payload.get("tool_calls")
    if not isinstance(raw_tool_calls, Sequence) or isinstance(raw_tool_calls, str):
        return []

    parsed: list[ToolCall] = []
    for raw_call in raw_tool_calls:
        call_payload = _as_mapping(raw_call)
        function_payload = _as_mapping(call_payload.get("function"))
        arguments = function_payload.get("arguments")
        parsed_arguments: JsonObject = {}
        if isinstance(arguments, str) and arguments:
            try:
                loaded = json.loads(arguments)
                parsed_arguments = _json_object(loaded)
            except json.JSONDecodeError:
                parsed_arguments = {"raw": arguments}
        parsed.append(
            ToolCall(
                id=_string_or_none(call_payload.get("id")) or f"tool-{uuid4()}",
                name=_string_or_none(function_payload.get("name")) or "unknown",
                arguments=parsed_arguments,
                provider_payload=_json_object(dict(call_payload)),
            )
        )
    return parsed


def _parse_usage(raw: Mapping[str, object]) -> Usage | None:
    usage_payload = _as_mapping(raw.get("usage"))
    if not usage_payload:
        return None

    prompt_tokens = usage_payload.get("prompt_tokens")
    completion_tokens = usage_payload.get("completion_tokens")
    total_tokens = usage_payload.get("total_tokens")
    return Usage(
        input_tokens=(int(prompt_tokens) if isinstance(prompt_tokens, int | float) else None),
        output_tokens=(
            int(completion_tokens) if isinstance(completion_tokens, int | float) else None
        ),
        total_tokens=(int(total_tokens) if isinstance(total_tokens, int | float) else None),
    )


class LiteLLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        default_model: str,
        provider_name: str = "litellm",
        request_timeout_seconds: float = 60.0,
    ) -> None:
        self._default_model = default_model
        self._provider_name = provider_name
        self._request_timeout_seconds = request_timeout_seconds

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self._provider_name,
            kind=ProviderKind.CHAT,
            implementation_status=ImplementationStatus.GA,
            models=[self._default_model],
            flags=[
                CapabilityFlag.STREAMING,
                CapabilityFlag.TOOL_CALLING,
                CapabilityFlag.STRUCTURED_OUTPUT,
                CapabilityFlag.VISION,
            ],
            metadata={"router": "litellm"},
        )

    def complete_chat(self, request: ChatRequest) -> ChatResponse:
        module = import_module("litellm")
        completion = cast(Callable[..., Any], getattr(module, "completion", None))
        if completion is None:
            raise LLMProviderUnavailableError("litellm.completion is not available")

        response = completion(
            model=request.model or self._default_model,
            messages=[_message_payload(message) for message in request.messages],
            tools=[_tool_payload(tool) for tool in request.tools] or None,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            timeout=self._request_timeout_seconds,
            metadata=request.metadata or None,
        )
        raw = _as_mapping(response)
        choice = _first_mapping(raw.get("choices"))
        message_payload = _as_mapping(choice.get("message"))
        content_value = message_payload.get("content")
        tool_calls = _parse_tool_calls(message_payload)
        content = content_value if isinstance(content_value, str) else ""
        return ChatResponse(
            id=_string_or_none(raw.get("id")) or f"chatcmpl-{uuid4()}",
            provider=self._provider_name,
            model=_string_or_none(raw.get("model")) or request.model or self._default_model,
            message=ChatMessage(
                role=ChatRole.ASSISTANT,
                content=content,
                tool_calls=tool_calls,
                provider_payload=_json_object(dict(message_payload)),
            ),
            tool_calls=tool_calls,
            finish_reason=_string_or_none(choice.get("finish_reason")),
            usage=_parse_usage(raw),
            provider_payload=cast(dict[str, JsonValue], dict(raw)),
        )
