from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from pydantic import Field

from api.events.models import CorrelationIds, RuntimeModel


class NotificationMessage(RuntimeModel):
    channel: str = "runtime"
    title: str
    body: str
    correlation: CorrelationIds
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationReceipt(RuntimeModel):
    receipt_id: str
    channel: str
    status: str
    sent_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationDeliveryRecord(RuntimeModel):
    delivery_id: str
    workflow_run_id: str
    trace_id: str
    source_channel: str
    delivery_channel: str
    delivery_status: str
    title: str
    body: str
    receipt_id: str
    provider_message_id: str | None = None
    sent_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @property
    def channel(self) -> str:
        return self.delivery_channel or self.source_channel

    @property
    def status(self) -> str:
        return self.delivery_status


class NotificationDeliveryListResponse(RuntimeModel):
    items: list[NotificationDeliveryRecord] = Field(default_factory=list)


class NotificationDeliveryStatusUpdateRequest(RuntimeModel):
    delivery_status: str = Field(min_length=1, max_length=64)
    provider_message_id: str | None = None
    metadata_patch: dict[str, Any] = Field(default_factory=dict)


class NotificationAdapter(Protocol):
    def send(self, message: NotificationMessage) -> NotificationReceipt: ...
