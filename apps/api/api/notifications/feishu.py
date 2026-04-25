from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from api.notifications.base import NotificationMessage, NotificationReceipt

logger = logging.getLogger(__name__)


class FeishuNotificationAdapter:
    """Send workflow notifications to Feishu/Lark IM."""

    channel = "feishu"

    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        domain: str = "https://open.feishu.cn",
        default_receive_id: str | None = None,
        receive_id_type: str = "chat_id",
    ) -> None:
        self._app_id = app_id.strip()
        self._app_secret = app_secret.strip()
        self._domain = domain.strip() or "https://open.feishu.cn"
        self._default_receive_id = default_receive_id.strip() if default_receive_id else None
        self._receive_id_type = receive_id_type.strip() or "chat_id"
        self._client: Any | None = None
        self._CreateMessageRequest: Any | None = None
        self._CreateMessageRequestBody: Any | None = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            import lark_oapi as lark
            from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
        except ImportError as exc:  # pragma: no cover - depends on optional dependency
            raise RuntimeError(
                "lark-oapi is not installed; add it to API dependencies "
                "before enabling Feishu notifications"
            ) from exc

        self._client = (
            lark.Client.builder()
            .app_id(self._app_id)
            .app_secret(self._app_secret)
            .domain(self._domain)
            .build()
        )
        self._CreateMessageRequest = CreateMessageRequest
        self._CreateMessageRequestBody = CreateMessageRequestBody

    def _resolve_receive_id(self, message: NotificationMessage) -> str:
        candidate = str(message.metadata.get("receive_id") or "").strip()
        if candidate:
            return candidate
        if self._default_receive_id:
            return self._default_receive_id
        raise ValueError(
            "Feishu notification target is missing; set metadata.receive_id "
            "or AI_DESK_FEISHU_DEFAULT_RECEIVE_ID"
        )

    def _resolve_receive_id_type(self, message: NotificationMessage) -> str:
        candidate = str(message.metadata.get("receive_id_type") or "").strip()
        if candidate:
            return candidate
        return self._receive_id_type

    def _build_content(self, message: NotificationMessage) -> str:
        summary = message.body.strip()
        if not summary:
            summary = "(empty)"
        parts = [f"**{message.title.strip() or 'AI Desk Notification'}**", summary]
        workflow_run_id = message.correlation.workflow_run_id.strip()
        if workflow_run_id:
            parts.append(f"workflow_run_id: `{workflow_run_id}`")
        trace_id = message.correlation.trace_id.strip()
        if trace_id:
            parts.append(f"trace_id: `{trace_id}`")
        return json.dumps({"text": "\n\n".join(parts)}, ensure_ascii=False)

    def send(self, message: NotificationMessage) -> NotificationReceipt:
        self._ensure_client()
        receive_id = self._resolve_receive_id(message)
        receive_id_type = self._resolve_receive_id_type(message)
        content = self._build_content(message)
        assert self._client is not None
        assert self._CreateMessageRequest is not None
        assert self._CreateMessageRequestBody is not None

        request = (
            self._CreateMessageRequest.builder()
            .receive_id_type(receive_id_type)
            .request_body(
                self._CreateMessageRequestBody.builder()
                .receive_id(receive_id)
                .msg_type("text")
                .content(content)
                .build()
            )
            .build()
        )

        response = self._client.im.v1.message.create(request)
        if not response.success():
            code = getattr(response, "code", "")
            msg = getattr(response, "msg", "")
            log_id = getattr(getattr(response, "header", None), "log_id", "")
            raise RuntimeError(f"Feishu send failed: code={code} msg={msg} log_id={log_id}")

        message_id = ""
        data = getattr(response, "data", None)
        if data is not None:
            message_id = str(getattr(data, "message_id", "") or "")
        logger.info(
            "feishu notification delivered",
            extra={"receive_id": receive_id, "message_id": message_id},
        )
        return NotificationReceipt(
            receipt_id=str(uuid4()),
            channel=self.channel,
            status="sent",
            sent_at=datetime.now(UTC).isoformat(),
            metadata={
                "provider_message_id": message_id,
                "receive_id": receive_id,
                "receive_id_type": receive_id_type,
            },
        )
