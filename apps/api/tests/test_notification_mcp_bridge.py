from __future__ import annotations

import json
import subprocess

from api.config import Settings
from api.events.models import CorrelationIds
from api.integrations.notifications import build_runtime_notification_adapters
from api.notifications.feishu_mcp_bridge import (
    _SEND_PAYLOAD_ENV,
    FeishuMcpBridgeNotificationAdapter,
)
from api.notifications.service import InMemoryNotificationAdapter


def _message():
    from api.notifications.base import NotificationMessage

    return NotificationMessage(
        title="Workflow completed",
        body="Run finished",
        correlation=CorrelationIds(workflow_run_id="run-1", trace_id="trace-1"),
        metadata={},
    )


def test_feishu_mcp_bridge_adapter_sends_message() -> None:
    class _FakeAdapter(FeishuMcpBridgeNotificationAdapter):
        def __init__(self) -> None:
            super().__init__(
                bridge_dir="/tmp/feishu_mcp",
                env_file="/tmp/feishu_mcp/.env",
                default_receive_id="oc_default",
            )
            self.payload: dict[str, str] | None = None

        def _run_command(
            self,
            command: list[str],
            *,
            env: dict[str, str],
            timeout_seconds: int,
        ) -> subprocess.CompletedProcess[str]:
            _ = command, timeout_seconds
            self.payload = json.loads(env[_SEND_PAYLOAD_ENV])
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=json.dumps(
                    {
                        "ok": True,
                        "message_id": "om_123",
                        "chat_id": "oc_default",
                        "receive_id_type": "chat_id",
                    },
                    ensure_ascii=False,
                ),
                stderr="",
            )

    adapter = _FakeAdapter()
    receipt = adapter.send(_message())

    assert adapter.payload is not None
    assert adapter.payload["receive_id"] == "oc_default"
    assert adapter.payload["receive_id_type"] == "chat_id"
    assert "workflow_run_id: run-1" in adapter.payload["text"]
    assert receipt.channel == "feishu"
    assert receipt.status == "sent"
    assert receipt.metadata["provider_message_id"] == "om_123"
    assert receipt.metadata["delivery_via"] == "feishu_mcp_bridge"


def test_feishu_mcp_bridge_adapter_raises_when_target_missing() -> None:
    adapter = FeishuMcpBridgeNotificationAdapter(
        bridge_dir="/tmp/feishu_mcp",
        env_file="/tmp/feishu_mcp/.env",
    )
    raised = False
    try:
        adapter.send(_message())
    except ValueError:
        raised = True
    assert raised


def test_build_runtime_notification_adapters_prefers_mcp_bridge() -> None:
    settings = Settings(
        AI_DESK_FEISHU_MCP_BRIDGE_ENABLED=True,
        AI_DESK_FEISHU_MCP_BRIDGE_DIR="/tmp/feishu_mcp",
        AI_DESK_FEISHU_MCP_ENV_FILE="/tmp/feishu_mcp/.env",
        AI_DESK_FEISHU_NOTIFICATION_ENABLED=True,
        AI_DESK_FEISHU_APP_ID="cli_123",
        AI_DESK_FEISHU_APP_SECRET="secret_123",
    )
    adapters = build_runtime_notification_adapters(
        settings,
        InMemoryNotificationAdapter(),
    )
    assert len(adapters) == 2
    assert isinstance(adapters[1], FeishuMcpBridgeNotificationAdapter)
