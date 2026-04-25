from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from api.notifications.base import NotificationDeliveryRecord
from api.notifications.service import NotificationHistoryService


class NotificationQueryService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._history = NotificationHistoryService(session_factory)

    def list_deliveries(
        self,
        *,
        workflow_run_id: str | None = None,
        project_id: str | None = None,
        source_channel: str | None = None,
        delivery_channel: str | None = None,
        delivery_status: str | None = None,
        limit: int = 50,
    ) -> list[NotificationDeliveryRecord]:
        return self._history.list_deliveries(
            workflow_run_id=workflow_run_id,
            project_id=project_id,
            source_channel=source_channel,
            delivery_channel=delivery_channel,
            delivery_status=delivery_status,
            limit=limit,
        )
