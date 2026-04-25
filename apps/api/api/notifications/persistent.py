from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from api.notifications.base import NotificationMessage, NotificationReceipt
from api.notifications.service import NotificationHistoryService


class PersistentNotificationAdapter:
    """Compatibility adapter that writes notifications directly to storage."""

    channel = "notification_store"

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._history = NotificationHistoryService(session_factory)

    def send(self, message: NotificationMessage) -> NotificationReceipt:
        receipt = NotificationReceipt(
            receipt_id=str(uuid4()),
            channel=self.channel,
            status="sent",
            sent_at=datetime.now(UTC).isoformat(),
            metadata={"adapter": self.__class__.__name__},
        )
        self._history.record_delivery(message=message, receipt=receipt)
        return receipt
