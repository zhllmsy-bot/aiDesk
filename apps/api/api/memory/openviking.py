from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportMissingImports=false
import asyncio
import enum
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx

from api.config import Settings

logger = logging.getLogger(__name__)


class OpenVikingErrorCategory(str, enum.Enum):
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTH = "auth"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    SERVER = "server"
    PAYLOAD = "payload"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class OpenVikingWriteResult:
    success: bool
    target_uri: str
    error_category: OpenVikingErrorCategory | None = None
    error_message: str | None = None
    retryable: bool = False


@dataclass(slots=True)
class OpenVikingSearchResult:
    items: list[dict[str, Any]]
    error_category: OpenVikingErrorCategory | None = None
    partial: bool = False


@dataclass(slots=True)
class RetryPolicy:
    max_retries: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 10.0
    backoff_factor: float = 2.0

    def delay_for_attempt(self, attempt: int) -> float:
        delay = self.base_delay_seconds * (self.backoff_factor**attempt)
        return min(delay, self.max_delay_seconds)


DEFAULT_RETRY_POLICY = RetryPolicy()


def classify_error(exc: Exception) -> tuple[OpenVikingErrorCategory, bool]:
    if isinstance(exc, httpx.TimeoutException):
        return OpenVikingErrorCategory.TIMEOUT, True
    if isinstance(exc, httpx.ConnectError):
        return OpenVikingErrorCategory.NETWORK, True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 401 or status == 403:
            return OpenVikingErrorCategory.AUTH, False
        if status == 404:
            return OpenVikingErrorCategory.NOT_FOUND, False
        if status == 429:
            return OpenVikingErrorCategory.RATE_LIMIT, True
        if 500 <= status < 600:
            return OpenVikingErrorCategory.SERVER, True
        return OpenVikingErrorCategory.UNKNOWN, False
    if isinstance(exc, (json.JSONDecodeError, ValueError)):
        return OpenVikingErrorCategory.PAYLOAD, False
    return OpenVikingErrorCategory.UNKNOWN, False


def _extract_tool_payload(tool_result: Any) -> dict[str, Any]:
    if isinstance(tool_result, list):
        for item in tool_result:
            if isinstance(item, Mapping):
                text = item.get("text")
                if isinstance(text, str):
                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(payload, dict):
                        return payload
    elif isinstance(tool_result, Mapping):
        return dict(tool_result)
    elif isinstance(tool_result, str):
        try:
            payload = json.loads(tool_result)
        except json.JSONDecodeError:
            return {}
        if isinstance(payload, dict):
            return payload
    return {}


@dataclass(slots=True)
class OpenVikingMemoryAdapter:
    settings: Settings
    retry_policy: RetryPolicy = field(default_factory=lambda: RetryPolicy())

    def target_uri(self, project_id: str, namespace: str, content_hash: str) -> str:
        root = self.settings.openviking_target_root.rstrip("/")
        safe_hash = content_hash.replace("/", "_").replace(":", "_")
        return f"{root}/{project_id}/{namespace}/{safe_hash}.md"

    def write(
        self,
        *,
        title: str,
        content: str,
        target_uri: str,
        tags: str,
    ) -> OpenVikingWriteResult:
        if not self.settings.openviking_mcp_url:
            return OpenVikingWriteResult(success=True, target_uri=target_uri)
        try:
            return asyncio.run(
                self._write_with_retry(
                    title=title,
                    content=content,
                    target_uri=target_uri,
                    tags=tags,
                )
            )
        except Exception as exc:
            category, retryable = classify_error(exc)
            logger.warning(
                "OpenViking write failed: %s [%s] retryable=%s", exc, category, retryable
            )
            return OpenVikingWriteResult(
                success=False,
                target_uri=target_uri,
                error_category=category,
                error_message=str(exc),
                retryable=retryable,
            )

    async def _write_with_retry(
        self,
        *,
        title: str,
        content: str,
        target_uri: str,
        tags: str,
    ) -> OpenVikingWriteResult:
        last_exc: Exception | None = None
        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                result_uri = await self._write_async(
                    title=title,
                    content=content,
                    target_uri=target_uri,
                    tags=tags,
                )
                return OpenVikingWriteResult(success=True, target_uri=result_uri)
            except Exception as exc:
                category, retryable = classify_error(exc)
                if not retryable or attempt == self.retry_policy.max_retries:
                    return OpenVikingWriteResult(
                        success=False,
                        target_uri=target_uri,
                        error_category=category,
                        error_message=str(exc),
                        retryable=retryable,
                    )
                last_exc = exc
                delay = self.retry_policy.delay_for_attempt(attempt)
                logger.info(
                    "OpenViking write retry %d/%d after %.1fs: %s",
                    attempt + 1,
                    self.retry_policy.max_retries,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
        return OpenVikingWriteResult(
            success=False,
            target_uri=target_uri,
            error_category=OpenVikingErrorCategory.UNKNOWN,
            error_message=str(last_exc),
            retryable=False,
        )

    async def _write_async(
        self,
        *,
        title: str,
        content: str,
        target_uri: str,
        tags: str,
    ) -> str:
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except ImportError:
            return target_uri

        client = MultiServerMCPClient(
            {"openviking": {"transport": "http", "url": self.settings.openviking_mcp_url}},
            tool_name_prefix=True,
        )
        tools = {tool.name: tool for tool in await client.get_tools()}
        add_text_resource = tools.get("openviking_add_text_resource")
        if add_text_resource is None:
            return target_uri
        result = await add_text_resource.ainvoke(
            {
                "title": title,
                "content": content,
                "target_uri": target_uri,
                "tags": tags,
            }
        )
        payload = _extract_tool_payload(result)
        return str(payload.get("resource_uri") or target_uri)

    def search(
        self,
        *,
        project_id: str,
        namespace_prefix: str | None,
        query: str,
        limit: int,
    ) -> OpenVikingSearchResult:
        if not self.settings.openviking_mcp_url:
            return OpenVikingSearchResult(items=[])
        try:
            items = asyncio.run(
                self._search_async(
                    project_id=project_id,
                    namespace_prefix=namespace_prefix,
                    query=query,
                    limit=limit,
                )
            )
            return OpenVikingSearchResult(items=items)
        except Exception as exc:
            category, _ = classify_error(exc)
            logger.warning("OpenViking search failed: %s [%s]", exc, category)
            return OpenVikingSearchResult(items=[], error_category=category, partial=True)

    async def _search_async(
        self,
        *,
        project_id: str,
        namespace_prefix: str | None,
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except ImportError:
            return []

        client = MultiServerMCPClient(
            {"openviking": {"transport": "http", "url": self.settings.openviking_mcp_url}},
            tool_name_prefix=True,
        )
        tools = {tool.name: tool for tool in await client.get_tools()}
        search_tool = tools.get("openviking_search")
        if search_tool is None:
            return []
        target_root = f"{self.settings.openviking_target_root.rstrip('/')}/{project_id}"
        if namespace_prefix:
            target_root = f"{target_root}/{namespace_prefix.strip('/')}"
        result = await search_tool.ainvoke(
            {
                "query": query,
                "top_k": limit,
                "target_uri": target_root,
            }
        )
        payload = _extract_tool_payload(result)
        matches = payload.get("results")
        if isinstance(matches, list):
            return [item for item in matches if isinstance(item, dict)]
        return []
