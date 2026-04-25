from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from api.notifications.base import (
    NotificationAdapter,
    NotificationDeliveryRecord,
    NotificationMessage,
    NotificationReceipt,
)
from api.runtime_persistence.models import RuntimeNotificationDelivery, RuntimeWorkflowRun


def _parse_sent_at(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _normalize_delivery_status(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_")
    if not normalized:
        return "unknown"
    return normalized[:64]


class NotificationRecorder(Protocol):
    def record(self, message: NotificationMessage, receipt: NotificationReceipt) -> None: ...


class InMemoryNotificationAdapter:
    channel = "runtime"

    def __init__(self) -> None:
        self.messages: list[NotificationMessage] = []
        self.receipts: list[NotificationReceipt] = []

    def send(self, message: NotificationMessage) -> NotificationReceipt:
        receipt = NotificationReceipt(
            receipt_id=str(uuid4()),
            channel=self.channel,
            status="sent",
            sent_at=datetime.now(UTC).isoformat(),
            metadata={"title": message.title},
        )
        self.messages.append(message)
        self.receipts.append(receipt)
        return receipt


class NotificationHistoryService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_delivery(
        self,
        *,
        message: NotificationMessage,
        receipt: NotificationReceipt,
    ) -> NotificationDeliveryRecord:
        provider_message_id = receipt.metadata.get("provider_message_id")
        row = RuntimeNotificationDelivery(
            workflow_run_id=message.correlation.workflow_run_id,
            trace_id=message.correlation.trace_id,
            source_channel=message.channel,
            delivery_channel=receipt.channel or message.channel,
            delivery_status=_normalize_delivery_status(receipt.status),
            title=message.title,
            body=message.body,
            receipt_id=receipt.receipt_id,
            provider_message_id=(
                str(provider_message_id)
                if isinstance(provider_message_id, str) and provider_message_id.strip()
                else None
            ),
            metadata_json={
                **dict(message.metadata),
                "message": dict(message.metadata),
                "receipt": dict(receipt.metadata),
            },
            sent_at=_parse_sent_at(receipt.sent_at),
        )

        with self._session_factory() as session:
            existing = session.scalar(
                select(RuntimeNotificationDelivery).where(
                    RuntimeNotificationDelivery.receipt_id == receipt.receipt_id
                )
            )
            if existing is not None:
                return self._to_record(existing)

            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.scalar(
                    select(RuntimeNotificationDelivery).where(
                        RuntimeNotificationDelivery.receipt_id == receipt.receipt_id
                    )
                )
                if existing is not None:
                    return self._to_record(existing)
                raise
            session.refresh(row)
            return self._to_record(row)

    def update_delivery_status(
        self,
        *,
        receipt_id: str,
        delivery_status: str,
        provider_message_id: str | None = None,
        metadata_patch: dict[str, object] | None = None,
    ) -> NotificationDeliveryRecord | None:
        normalized_status = _normalize_delivery_status(delivery_status)
        safe_patch = dict(metadata_patch or {})
        with self._session_factory() as session:
            row = session.scalar(
                select(RuntimeNotificationDelivery).where(
                    RuntimeNotificationDelivery.receipt_id == receipt_id
                )
            )
            if row is None:
                return None
            row.delivery_status = normalized_status
            if isinstance(provider_message_id, str) and provider_message_id.strip():
                row.provider_message_id = provider_message_id.strip()
            metadata_json = dict(row.metadata_json)
            existing_provider_update = metadata_json.get("provider_update")
            if not isinstance(existing_provider_update, dict):
                existing_provider_update = {}
            metadata_json["provider_update"] = {**existing_provider_update, **safe_patch}
            metadata_json["delivery_updated_at"] = datetime.now(UTC).isoformat()
            row.metadata_json = metadata_json
            session.commit()
            session.refresh(row)
            return self._to_record(row)

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
        safe_limit = max(1, min(limit, 200))
        with self._session_factory() as session:
            statement = select(RuntimeNotificationDelivery).order_by(
                RuntimeNotificationDelivery.sent_at.desc()
            )
            if project_id:
                statement = statement.join(
                    RuntimeWorkflowRun,
                    RuntimeNotificationDelivery.workflow_run_id == RuntimeWorkflowRun.id,
                ).where(RuntimeWorkflowRun.project_id == project_id)
            if workflow_run_id:
                statement = statement.where(
                    RuntimeNotificationDelivery.workflow_run_id == workflow_run_id
                )
            if source_channel:
                statement = statement.where(
                    RuntimeNotificationDelivery.source_channel == source_channel
                )
            if delivery_channel:
                statement = statement.where(
                    RuntimeNotificationDelivery.delivery_channel == delivery_channel
                )
            if delivery_status:
                statement = statement.where(
                    RuntimeNotificationDelivery.delivery_status == delivery_status
                )
            rows = session.scalars(statement.limit(safe_limit)).all()
            return [self._to_record(row) for row in rows]

    @staticmethod
    def _to_record(row: RuntimeNotificationDelivery) -> NotificationDeliveryRecord:
        return NotificationDeliveryRecord(
            delivery_id=row.id,
            workflow_run_id=row.workflow_run_id,
            trace_id=row.trace_id,
            source_channel=row.source_channel,
            delivery_channel=row.delivery_channel,
            delivery_status=row.delivery_status,
            title=row.title,
            body=row.body,
            receipt_id=row.receipt_id,
            provider_message_id=row.provider_message_id,
            sent_at=row.sent_at,
            metadata=dict(row.metadata_json),
            created_at=row.created_at,
        )


class PersistentNotificationRecorder:
    def __init__(self, history: NotificationHistoryService) -> None:
        self._history = history

    def record(self, message: NotificationMessage, receipt: NotificationReceipt) -> None:
        self._history.record_delivery(message=message, receipt=receipt)


class NotificationService:
    def __init__(
        self,
        adapters: list[NotificationAdapter] | None = None,
        recorders: list[NotificationRecorder] | None = None,
        max_attempts: int = 2,
        backoff_base_seconds: float = 0.0,
        backoff_cap_seconds: float = 0.0,
    ) -> None:
        self._adapters = adapters or []
        self._recorders = recorders or []
        self._max_attempts = max(1, int(max_attempts))
        self._backoff_base_seconds = max(0.0, float(backoff_base_seconds))
        self._backoff_cap_seconds = max(
            self._backoff_base_seconds,
            float(backoff_cap_seconds),
        )

    @staticmethod
    def _adapter_channel_name(adapter: NotificationAdapter, fallback: str) -> str:
        channel = getattr(adapter, "channel", None)
        if isinstance(channel, str) and channel.strip():
            return channel.strip()
        return fallback

    def _record(self, message: NotificationMessage, receipt: NotificationReceipt) -> None:
        for recorder in self._recorders:
            try:
                recorder.record(message, receipt)
            except Exception:
                # Notification delivery should not fail user workflows due to
                # recorder storage issues.
                continue

    @staticmethod
    def _failure_category(exc: Exception) -> str:
        reason = str(exc).lower()
        if "timeout" in reason:
            return "timeout"
        if any(token in reason for token in ("401", "403", "unauthorized", "forbidden")):
            return "auth"
        if any(token in reason for token in ("404", "not found", "receive_id", "target")):
            return "target_missing"
        if any(token in reason for token in ("429", "rate limit", "throttle")):
            return "rate_limit"
        return "unknown"

    def _backoff_delay(self, attempt_no: int) -> float:
        if self._backoff_base_seconds <= 0:
            return 0.0
        exponential = self._backoff_base_seconds * (2 ** max(attempt_no - 1, 0))
        return min(exponential, self._backoff_cap_seconds)

    def _send_with_retry(
        self,
        *,
        adapter: NotificationAdapter,
        message: NotificationMessage,
    ) -> NotificationReceipt:
        last_error: Exception | None = None
        for attempt_no in range(1, self._max_attempts + 1):
            try:
                receipt = adapter.send(message)
                if attempt_no <= 1:
                    return receipt
                merged_metadata = {
                    **dict(receipt.metadata),
                    "attempt_no": attempt_no,
                    "attempts_total": self._max_attempts,
                }
                return receipt.model_copy(update={"metadata": merged_metadata})
            except Exception as exc:  # pragma: no cover - adapter specific
                last_error = exc
                if attempt_no >= self._max_attempts:
                    break
                delay_seconds = self._backoff_delay(attempt_no)
                if delay_seconds > 0:
                    time.sleep(delay_seconds)

        assert last_error is not None
        return NotificationReceipt(
            receipt_id=str(uuid4()),
            channel=self._adapter_channel_name(adapter, message.channel),
            status="failed",
            sent_at=datetime.now(UTC).isoformat(),
            metadata={
                "title": message.title,
                "adapter": adapter.__class__.__name__,
                "reason": str(last_error),
                "failure_category": self._failure_category(last_error),
                "attempts_total": self._max_attempts,
            },
        )

    def send(self, message: NotificationMessage) -> list[NotificationReceipt]:
        receipts: list[NotificationReceipt] = []
        for adapter in self._adapters:
            receipt = self._send_with_retry(adapter=adapter, message=message)
            receipts.append(receipt)
            self._record(message, receipt)
        return receipts
