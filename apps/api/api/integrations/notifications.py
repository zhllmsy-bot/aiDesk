from __future__ import annotations

from api.config import Settings
from api.notifications.base import NotificationAdapter
from api.notifications.feishu import FeishuNotificationAdapter
from api.notifications.feishu_mcp_bridge import FeishuMcpBridgeNotificationAdapter
from api.notifications.service import InMemoryNotificationAdapter


def build_runtime_notification_adapters(
    settings: Settings,
    in_memory_adapter: InMemoryNotificationAdapter,
) -> list[NotificationAdapter]:
    adapters: list[NotificationAdapter] = [in_memory_adapter]
    if settings.feishu_mcp_bridge_enabled and settings.resolved_feishu_mcp_bridge_dir:
        adapters.append(
            FeishuMcpBridgeNotificationAdapter(
                bridge_dir=settings.resolved_feishu_mcp_bridge_dir,
                env_file=settings.resolved_feishu_mcp_env_file,
                default_receive_id=settings.feishu_default_receive_id,
                receive_id_type=settings.feishu_receive_id_type,
                timeout_seconds=settings.feishu_mcp_timeout_seconds,
            )
        )
        return adapters

    if (
        settings.feishu_notification_enabled
        and settings.resolved_feishu_app_id
        and settings.resolved_feishu_app_secret
    ):
        adapters.append(
            FeishuNotificationAdapter(
                app_id=settings.resolved_feishu_app_id,
                app_secret=settings.resolved_feishu_app_secret,
                domain=settings.resolved_feishu_domain,
                default_receive_id=settings.feishu_default_receive_id,
                receive_id_type=settings.feishu_receive_id_type,
            )
        )
    return adapters
