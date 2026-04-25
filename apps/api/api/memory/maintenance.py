from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from api.executors.contracts import RetentionPolicy
from api.runtime_persistence.models import RuntimeMemoryRecord


class MemoryMaintenanceService:
    DECAY_30D_DAYS = 30
    DECAY_90D_DAYS = 90
    BATCH_SIZE = 200

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def mark_stale_records(self) -> int:
        now = datetime.now(UTC)
        cutoff_map: dict[str, datetime] = {
            RetentionPolicy.DECAY_30D: now - timedelta(days=self.DECAY_30D_DAYS),
            RetentionPolicy.DECAY_90D: now - timedelta(days=self.DECAY_90D_DAYS),
            RetentionPolicy.RETAIN_FOR_RUN: now - timedelta(days=7),
        }
        total = 0
        with self._session_factory() as session:
            for policy_value, cutoff in cutoff_map.items():
                rows = session.scalars(
                    select(RuntimeMemoryRecord)
                    .where(RuntimeMemoryRecord.retention_policy == policy_value)
                    .where(RuntimeMemoryRecord.stale_at.is_(None))
                    .where(RuntimeMemoryRecord.created_at < cutoff)
                    .limit(self.BATCH_SIZE)
                ).all()
                for row in rows:
                    row.stale_at = now
                    total += 1
                session.commit()
        return total

    def merge_superseded_records(self) -> int:
        total = 0
        with self._session_factory() as session:
            superseded_ids: list[str] = []
            rows = session.scalars(
                select(RuntimeMemoryRecord)
                .where(RuntimeMemoryRecord.supersedes_record_id.isnot(None))
                .limit(self.BATCH_SIZE)
            ).all()
            for row in rows:
                if row.supersedes_record_id:
                    superseded_ids.append(row.supersedes_record_id)
            if superseded_ids:
                session.execute(
                    update(RuntimeMemoryRecord)
                    .where(RuntimeMemoryRecord.id.in_(superseded_ids))
                    .values(stale_at=datetime.now(UTC))
                )
                session.commit()
                total = len(superseded_ids)
        return total

    def purge_stale_records(self, max_age_days: int = 90) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
        total = 0
        with self._session_factory() as session:
            rows = session.scalars(
                select(RuntimeMemoryRecord)
                .where(RuntimeMemoryRecord.stale_at.isnot(None))
                .where(RuntimeMemoryRecord.stale_at < cutoff)
                .limit(self.BATCH_SIZE)
            ).all()
            ids_to_delete = [row.id for row in rows]
            for record_id in ids_to_delete:
                record = session.get(RuntimeMemoryRecord, record_id)
                if record is not None:
                    session.delete(record)
                    total += 1
            session.commit()
        return total

    def cleanup_invalid_external_refs(self) -> int:
        total = 0
        with self._session_factory() as session:
            rows = session.scalars(
                select(RuntimeMemoryRecord)
                .where(RuntimeMemoryRecord.external_ref == "")
                .limit(self.BATCH_SIZE)
            ).all()
            for row in rows:
                row.stale_at = datetime.now(UTC)
                total += 1
            session.commit()
        return total

    def run_full_maintenance(self) -> dict[str, int]:
        results: dict[str, int] = {}
        results["marked_stale"] = self.mark_stale_records()
        results["merged_superseded"] = self.merge_superseded_records()
        results["cleaned_refs"] = self.cleanup_invalid_external_refs()
        results["purged"] = self.purge_stale_records()
        return results
