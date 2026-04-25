from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from api.notifications.base import NotificationMessage, NotificationReceipt

_SEND_PAYLOAD_ENV = "AI_DESK_FEISHU_MCP_SEND_PAYLOAD"
_SEND_SCRIPT = """
import asyncio
import json
import os
from pathlib import Path

from feishu_mcp_bridge.bridge import FeishuBridge
from feishu_mcp_bridge.config import Settings
from feishu_mcp_bridge.store import MessageStore

payload = json.loads(os.environ["AI_DESK_FEISHU_MCP_SEND_PAYLOAD"])
env_file_value = payload.get("env_file")
env_file = Path(env_file_value) if isinstance(env_file_value, str) and env_file_value else None
settings = Settings.from_env(env_file)
store = MessageStore(settings.database_path)
bridge = FeishuBridge(settings=settings, store=store)

async def _run() -> None:
    result = await bridge.send_message(
        receive_id=str(payload["receive_id"]),
        text=str(payload["text"]),
        receive_id_type=str(payload.get("receive_id_type") or "chat_id"),
    )
    print(json.dumps(result, ensure_ascii=False))

asyncio.run(_run())
""".strip()


class FeishuMcpBridgeNotificationAdapter:
    """Send notifications through an external Feishu MCP bridge project."""

    channel = "feishu"

    def __init__(
        self,
        *,
        bridge_dir: str,
        env_file: str | None = None,
        default_receive_id: str | None = None,
        receive_id_type: str = "chat_id",
        timeout_seconds: int = 30,
    ) -> None:
        self._bridge_dir = Path(bridge_dir).expanduser()
        self._env_file = Path(env_file).expanduser() if env_file else self._bridge_dir / ".env"
        self._default_receive_id = default_receive_id.strip() if default_receive_id else None
        self._receive_id_type = receive_id_type.strip() or "chat_id"
        self._timeout_seconds = max(5, int(timeout_seconds))

    def _resolve_receive_id(self, message: NotificationMessage) -> str:
        candidate = str(message.metadata.get("receive_id") or "").strip()
        if candidate:
            return candidate
        if self._default_receive_id:
            return self._default_receive_id
        raise ValueError(
            "Feishu MCP bridge target is missing; set metadata.receive_id "
            "or AI_DESK_FEISHU_DEFAULT_RECEIVE_ID"
        )

    def _resolve_receive_id_type(self, message: NotificationMessage) -> str:
        candidate = str(message.metadata.get("receive_id_type") or "").strip()
        if candidate:
            return candidate
        return self._receive_id_type

    @staticmethod
    def _build_text(message: NotificationMessage) -> str:
        summary = message.body.strip() or "(empty)"
        parts = [f"{message.title.strip() or 'AI Desk Notification'}", summary]
        workflow_run_id = message.correlation.workflow_run_id.strip()
        if workflow_run_id:
            parts.append(f"workflow_run_id: {workflow_run_id}")
        trace_id = message.correlation.trace_id.strip()
        if trace_id:
            parts.append(f"trace_id: {trace_id}")
        return "\n\n".join(parts)

    @staticmethod
    def _parse_result(stdout: str) -> dict[str, Any]:
        for line in reversed(stdout.splitlines()):
            content = line.strip()
            if not content:
                continue
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return cast(dict[str, Any], parsed)
        raise RuntimeError("Feishu MCP bridge did not return a JSON result")

    def _run_command(
        self,
        command: list[str],
        *,
        env: dict[str, str],
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=timeout_seconds,
        )

    def send(self, message: NotificationMessage) -> NotificationReceipt:
        receive_id = self._resolve_receive_id(message)
        receive_id_type = self._resolve_receive_id_type(message)
        payload = {
            "receive_id": receive_id,
            "receive_id_type": receive_id_type,
            "text": self._build_text(message),
            "env_file": str(self._env_file),
        }
        env = dict(os.environ)
        env[_SEND_PAYLOAD_ENV] = json.dumps(payload, ensure_ascii=False)
        command = [
            "uv",
            "--directory",
            str(self._bridge_dir),
            "run",
            "python",
            "-c",
            _SEND_SCRIPT,
        ]
        completed = self._run_command(
            command,
            env=env,
            timeout_seconds=self._timeout_seconds,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or "").strip() or (completed.stdout or "").strip()
            raise RuntimeError(f"Feishu MCP bridge send failed: {detail or completed.returncode}")

        result = self._parse_result(completed.stdout or "")
        if not bool(result.get("ok", False)):
            raise RuntimeError(f"Feishu MCP bridge send failed: {result}")

        provider_message_id = str(result.get("message_id") or "")
        return NotificationReceipt(
            receipt_id=str(uuid4()),
            channel=self.channel,
            status="sent",
            sent_at=datetime.now(UTC).isoformat(),
            metadata={
                "provider_message_id": provider_message_id,
                "receive_id": receive_id,
                "receive_id_type": receive_id_type,
                "delivery_via": "feishu_mcp_bridge",
                "bridge_chat_id": str(result.get("chat_id") or receive_id),
            },
        )
