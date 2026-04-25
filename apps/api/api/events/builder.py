from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from api.events.models import CorrelationIds, RunEventEnvelope, TimelineEntry
from api.runtime_contracts import EVENT_LABELS, RUNTIME_SCHEMA_VERSION, EventType


class RuntimeEventBuilder:
    def __init__(self, producer: str, schema_version: str = RUNTIME_SCHEMA_VERSION) -> None:
        self._producer = producer
        self._schema_version = schema_version

    def build(
        self,
        *,
        event_type: EventType | str,
        sequence: int,
        correlation: CorrelationIds | Mapping[str, Any],
        payload: Mapping[str, Any] | None = None,
        occurred_at: datetime | None = None,
        idempotency_key: str | None = None,
    ) -> RunEventEnvelope:
        resolved_event_type = EventType(event_type)
        resolved_correlation = (
            correlation
            if isinstance(correlation, CorrelationIds)
            else CorrelationIds.model_validate(correlation)
        )
        event_timestamp = (occurred_at or datetime.now(UTC)).isoformat()
        return RunEventEnvelope(
            event_id=str(uuid4()),
            event_type=resolved_event_type,
            schema_version=self._schema_version,
            payload_version=self._schema_version,
            sequence=sequence,
            producer=self._producer,
            occurred_at=event_timestamp,
            idempotency_key=idempotency_key
            or f"{resolved_correlation.workflow_run_id}:{sequence}:{resolved_event_type.value}",
            correlation=resolved_correlation,
            payload=dict(payload or {}),
        )


def build_timeline_entry(event: RunEventEnvelope) -> TimelineEntry:
    summary = event.payload.get("summary")
    return TimelineEntry(
        sequence=event.sequence,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        label=EVENT_LABELS[event.event_type],
        trace_id=event.correlation.trace_id,
        task_id=event.correlation.task_id,
        attempt_id=event.correlation.attempt_id,
        summary=None if summary is None else str(summary),
    )
