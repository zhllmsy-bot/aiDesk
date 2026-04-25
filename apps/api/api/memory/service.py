from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

from api.executors.contracts import (
    EvidenceRef,
    MemoryRecord,
    MemoryType,
    MemoryWriteCandidate,
    RetentionPolicy,
)
from api.memory.governance import WriteAction, WriteGovernancePolicy
from api.memory.mem0 import Mem0MemoryAdapter, map_mem0_item
from api.memory.openviking import OpenVikingMemoryAdapter, OpenVikingWriteResult
from api.memory.ranking import MemoryRankingService, RankingContext
from api.observability.logging import get_logger
from api.observability.metrics import get_metrics
from api.runtime_persistence.models import RuntimeMemoryRecord

logger = get_logger("memory.governance")


@dataclass(slots=True)
class MemoryDecision:
    allowed: bool
    reason: str
    namespace: str
    dedup_key: str
    action: str = WriteAction.ACCEPT


class MemoryGovernanceService:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] | None = None,
        mem0_adapter: Mem0MemoryAdapter | None = None,
        adapter: OpenVikingMemoryAdapter | None = None,
        governance: WriteGovernancePolicy | None = None,
        ranking: MemoryRankingService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._mem0_adapter = mem0_adapter
        self._adapter = adapter
        self._governance = governance or WriteGovernancePolicy()
        self._ranking = ranking or MemoryRankingService()
        self._records: dict[str, MemoryRecord] = {}
        self._dedup_index: dict[str, str] = {}

    @property
    def provider_name(self) -> str:
        if self._mem0_adapter is not None:
            return "mem0"
        if self._adapter is not None:
            return "openviking"
        return "local"

    def namespace_for(
        self, project_id: str, memory_type: MemoryType, iteration_id: str | None
    ) -> str:
        scope = iteration_id or "global"
        return f"{project_id}:{scope}:{memory_type}"

    def evaluate_write(self, candidate: MemoryWriteCandidate) -> MemoryDecision:
        namespace = candidate.namespace or self.namespace_for(
            project_id=candidate.project_id,
            memory_type=candidate.memory_type,
            iteration_id=candidate.iteration_id,
        )
        dedup_key = f"{namespace}:{candidate.content_hash}"
        has_existing = False
        existing_version = 0

        if self._session_factory is not None:
            with self._session_factory() as session:
                existing = session.scalar(
                    select(RuntimeMemoryRecord)
                    .where(RuntimeMemoryRecord.project_id == candidate.project_id)
                    .where(RuntimeMemoryRecord.namespace == namespace)
                    .where(RuntimeMemoryRecord.content_hash == candidate.content_hash)
                )
                if existing is not None:
                    has_existing = True
                    existing_version = existing.version
        else:
            if dedup_key in self._dedup_index:
                has_existing = True

        decision = self._governance.evaluate(
            candidate,
            has_existing=has_existing,
            existing_version=existing_version,
        )

        if not decision.allowed:
            return MemoryDecision(
                allowed=False,
                reason=decision.reason,
                namespace=namespace,
                dedup_key=dedup_key,
                action=decision.action,
            )

        return MemoryDecision(
            allowed=True,
            reason=decision.reason,
            namespace=namespace,
            dedup_key=dedup_key,
            action=decision.action,
        )

    def write(self, candidate: MemoryWriteCandidate) -> MemoryRecord | None:
        metrics = get_metrics()
        provider = self.provider_name
        metrics.inc_counter("memory_write_attempted", provider=provider)

        decision = self.evaluate_write(candidate)
        if not decision.allowed:
            metrics.inc_counter("memory_write_rejected", provider=provider, reason=decision.reason)
            logger.info(
                "memory write rejected",
                extra={
                    "project_id": candidate.project_id,
                    "namespace": decision.namespace,
                    "reason": decision.reason,
                },
            )
            return None

        metrics.inc_counter("memory_write_accepted", provider=provider)
        logger.info(
            "memory write accepted",
            extra={
                "project_id": candidate.project_id,
                "namespace": decision.namespace,
                "action": decision.action,
            },
        )

        if decision.action == WriteAction.MERGE:
            return self._handle_merge(candidate, decision)

        if decision.action == WriteAction.SUPERSEDE:
            return self._handle_supersede(candidate, decision)

        return self._handle_accept(candidate, decision)

    def _handle_accept(
        self, candidate: MemoryWriteCandidate, decision: MemoryDecision
    ) -> MemoryRecord | None:
        if self._session_factory is None:
            return self._write_inmemory(candidate, decision)

        assert self._session_factory is not None
        remote_uri = candidate.external_ref
        remote_result: OpenVikingWriteResult | None = None
        remote_provider = "local"

        if self._mem0_adapter is not None:
            mem0_result = self._mem0_adapter.write(
                candidate=candidate,
                namespace=decision.namespace,
            )
            remote_provider = "mem0"
            if mem0_result.success:
                remote_uri = mem0_result.external_ref
            else:
                logger.warning(
                    "Mem0 write failed — falling back to local-only",
                    extra={
                        "error_message": mem0_result.error_message,
                        "retryable": mem0_result.retryable,
                    },
                )

        elif self._adapter is not None:
            remote_result = self._adapter.write(
                title=candidate.summary,
                content=self._render_memory_document(candidate, decision.namespace),
                target_uri=self._adapter.target_uri(
                    candidate.project_id,
                    decision.namespace.replace(":", "/"),
                    candidate.content_hash,
                ),
                tags=self._render_tags(candidate, decision.namespace),
            )
            if remote_result.success:
                remote_uri = remote_result.target_uri
            else:
                logger.warning(
                    "OpenViking write failed — falling back to local-only",
                    extra={
                        "error_category": remote_result.error_category,
                        "error_message": remote_result.error_message,
                    },
                )
            remote_provider = "openviking"

        with self._session_factory() as session:
            row = RuntimeMemoryRecord(
                project_id=candidate.project_id,
                iteration_id=candidate.iteration_id,
                workflow_run_id=self._metadata_str(candidate.metadata, "workflow_run_id"),
                task_id=self._metadata_str(candidate.metadata, "task_id"),
                source_attempt_id=self._metadata_str(candidate.metadata, "attempt_id"),
                namespace=decision.namespace,
                memory_type=str(candidate.memory_type),
                external_ref=remote_uri,
                summary=candidate.summary,
                content_hash=candidate.content_hash,
                score=candidate.quality_score,
                quality_score=candidate.quality_score,
                version=1,
                supersedes_record_id=candidate.supersedes_record_id,
                retention_policy=candidate.retention_policy,
                provider=remote_provider,
                metadata_json=dict(candidate.metadata),
                evidence_refs_json=[ref.model_dump(mode="json") for ref in candidate.evidence_refs],
            )
            if remote_result and not remote_result.success:
                row.metadata_json = {
                    **row.metadata_json,
                    "remote_write_error": {
                        "category": str(remote_result.error_category),
                        "message": remote_result.error_message,
                        "retryable": remote_result.retryable,
                    },
                }
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._to_record(row)

    def _handle_supersede(
        self, candidate: MemoryWriteCandidate, decision: MemoryDecision
    ) -> MemoryRecord | None:
        if self._session_factory is None:
            return self._write_inmemory(candidate, decision)

        assert self._session_factory is not None
        remote_uri = candidate.external_ref
        remote_result: OpenVikingWriteResult | None = None
        remote_provider = "local"
        if self._mem0_adapter is not None:
            existing_external_ref = None
            with self._session_factory() as session:
                existing = session.scalar(
                    select(RuntimeMemoryRecord)
                    .where(RuntimeMemoryRecord.project_id == candidate.project_id)
                    .where(RuntimeMemoryRecord.namespace == decision.namespace)
                    .where(RuntimeMemoryRecord.content_hash == candidate.content_hash)
                )
                if existing is not None:
                    existing_external_ref = existing.external_ref
            mem0_result = self._mem0_adapter.write(
                candidate=candidate,
                namespace=decision.namespace,
                existing_external_ref=existing_external_ref,
            )
            remote_provider = "mem0"
            if mem0_result.success:
                remote_uri = mem0_result.external_ref
            else:
                logger.warning(
                    "Mem0 write failed during supersede — falling back to local-only",
                    extra={
                        "error_message": mem0_result.error_message,
                        "retryable": mem0_result.retryable,
                    },
                )
        elif self._adapter is not None:
            remote_result = self._adapter.write(
                title=candidate.summary,
                content=self._render_memory_document(candidate, decision.namespace),
                target_uri=self._adapter.target_uri(
                    candidate.project_id,
                    decision.namespace.replace(":", "/"),
                    candidate.content_hash,
                ),
                tags=self._render_tags(candidate, decision.namespace),
            )
            if remote_result.success:
                remote_uri = remote_result.target_uri
            else:
                logger.warning(
                    "OpenViking write failed during supersede — falling back to local-only",
                    extra={
                        "error_category": remote_result.error_category,
                        "error_message": remote_result.error_message,
                    },
                )
            remote_provider = "openviking"

        with self._session_factory() as session:
            metadata_json: dict[str, object] = {str(k): v for k, v in candidate.metadata.items()}
            if remote_result and not remote_result.success:
                metadata_json = {
                    **metadata_json,
                    "remote_write_error": {
                        "category": str(remote_result.error_category),
                        "message": remote_result.error_message,
                        "retryable": remote_result.retryable,
                    },
                }

            project_id = candidate.project_id
            iteration_id = candidate.iteration_id
            workflow_run_id = self._metadata_str(candidate.metadata, "workflow_run_id")
            task_id = self._metadata_str(candidate.metadata, "task_id")
            source_attempt_id = self._metadata_str(candidate.metadata, "attempt_id")
            namespace = decision.namespace
            memory_type = str(candidate.memory_type)
            external_ref = remote_uri
            summary = candidate.summary
            content_hash = candidate.content_hash
            score = candidate.quality_score
            quality_score = candidate.quality_score
            version = 1
            supersedes_record_id = candidate.supersedes_record_id
            retention_policy = str(candidate.retention_policy)
            provider = remote_provider
            evidence_refs_json = [
                cast(dict[str, object], ref.model_dump(mode="json"))
                for ref in candidate.evidence_refs
            ]
            stale_at = None

            table = RuntimeMemoryRecord.__table__
            dialect_name = ""
            if session.bind is not None:
                dialect_name = session.bind.dialect.name

            upsert_stmt = None
            if dialect_name == "postgresql":
                insert_stmt = postgresql_insert(RuntimeMemoryRecord).values(
                    project_id=project_id,
                    iteration_id=iteration_id,
                    workflow_run_id=workflow_run_id,
                    task_id=task_id,
                    source_attempt_id=source_attempt_id,
                    namespace=namespace,
                    memory_type=memory_type,
                    external_ref=external_ref,
                    summary=summary,
                    content_hash=content_hash,
                    score=score,
                    quality_score=quality_score,
                    version=version,
                    supersedes_record_id=supersedes_record_id,
                    retention_policy=retention_policy,
                    provider=provider,
                    metadata_json=metadata_json,
                    evidence_refs_json=evidence_refs_json,
                    stale_at=stale_at,
                )
                upsert_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=["project_id", "namespace", "content_hash"],
                    set_={
                        "iteration_id": iteration_id,
                        "workflow_run_id": workflow_run_id,
                        "task_id": task_id,
                        "source_attempt_id": source_attempt_id,
                        "memory_type": memory_type,
                        "external_ref": external_ref,
                        "summary": summary,
                        "score": score,
                        "quality_score": quality_score,
                        "version": table.c.version + 1,
                        "supersedes_record_id": func.coalesce(
                            insert_stmt.excluded.supersedes_record_id,
                            table.c.supersedes_record_id,
                        ),
                        "retention_policy": retention_policy,
                        "provider": provider,
                        "metadata_json": metadata_json,
                        "evidence_refs_json": evidence_refs_json,
                        "stale_at": None,
                    },
                )
            elif dialect_name == "sqlite":
                insert_stmt = sqlite_insert(RuntimeMemoryRecord).values(
                    project_id=project_id,
                    iteration_id=iteration_id,
                    workflow_run_id=workflow_run_id,
                    task_id=task_id,
                    source_attempt_id=source_attempt_id,
                    namespace=namespace,
                    memory_type=memory_type,
                    external_ref=external_ref,
                    summary=summary,
                    content_hash=content_hash,
                    score=score,
                    quality_score=quality_score,
                    version=version,
                    supersedes_record_id=supersedes_record_id,
                    retention_policy=retention_policy,
                    provider=provider,
                    metadata_json=metadata_json,
                    evidence_refs_json=evidence_refs_json,
                    stale_at=stale_at,
                )
                upsert_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=["project_id", "namespace", "content_hash"],
                    set_={
                        "iteration_id": iteration_id,
                        "workflow_run_id": workflow_run_id,
                        "task_id": task_id,
                        "source_attempt_id": source_attempt_id,
                        "memory_type": memory_type,
                        "external_ref": external_ref,
                        "summary": summary,
                        "score": score,
                        "quality_score": quality_score,
                        "version": table.c.version + 1,
                        "supersedes_record_id": func.coalesce(
                            insert_stmt.excluded.supersedes_record_id,
                            table.c.supersedes_record_id,
                        ),
                        "retention_policy": retention_policy,
                        "provider": provider,
                        "metadata_json": metadata_json,
                        "evidence_refs_json": evidence_refs_json,
                        "stale_at": None,
                    },
                )

            if upsert_stmt is not None:
                session.execute(upsert_stmt)
                session.commit()
                row = session.scalar(
                    select(RuntimeMemoryRecord)
                    .where(RuntimeMemoryRecord.project_id == candidate.project_id)
                    .where(RuntimeMemoryRecord.namespace == decision.namespace)
                    .where(RuntimeMemoryRecord.content_hash == candidate.content_hash)
                )
                if row is None:
                    return None
                return self._to_record(row)

            # Fallback for unsupported SQL dialects.
            existing = session.scalar(
                select(RuntimeMemoryRecord)
                .where(RuntimeMemoryRecord.project_id == candidate.project_id)
                .where(RuntimeMemoryRecord.namespace == decision.namespace)
                .where(RuntimeMemoryRecord.content_hash == candidate.content_hash)
            )
            if existing is None:
                return self._handle_accept(candidate, decision)

            existing.iteration_id = iteration_id
            existing.workflow_run_id = workflow_run_id
            existing.task_id = task_id
            existing.source_attempt_id = source_attempt_id
            existing.memory_type = memory_type
            existing.external_ref = external_ref
            existing.summary = summary
            existing.score = score
            existing.quality_score = quality_score
            existing.version = max(existing.version, 1) + 1
            existing.supersedes_record_id = (
                candidate.supersedes_record_id or existing.supersedes_record_id
            )
            existing.retention_policy = retention_policy
            existing.provider = provider
            existing.stale_at = None
            existing.metadata_json = metadata_json
            existing.evidence_refs_json = evidence_refs_json
            session.commit()
            session.refresh(existing)
            return self._to_record(existing)

    def _handle_merge(
        self, candidate: MemoryWriteCandidate, decision: MemoryDecision
    ) -> MemoryRecord | None:
        if self._session_factory is None:
            if decision.dedup_key in self._dedup_index:
                return self._records.get(self._dedup_index[decision.dedup_key])
            return self._write_inmemory(candidate, decision)

        assert self._session_factory is not None
        with self._session_factory() as session:
            existing = session.scalar(
                select(RuntimeMemoryRecord)
                .where(RuntimeMemoryRecord.project_id == candidate.project_id)
                .where(RuntimeMemoryRecord.namespace == decision.namespace)
                .where(RuntimeMemoryRecord.content_hash == candidate.content_hash)
            )
            if existing is not None:
                if candidate.quality_score > existing.quality_score:
                    existing.quality_score = candidate.quality_score
                    existing.score = candidate.quality_score
                    existing.summary = candidate.summary
                    existing.recall_count += 1
                    session.commit()
                    session.refresh(existing)
                return self._to_record(existing)

        return self._handle_accept(candidate, decision)

    def recall(
        self,
        *,
        project_id: str,
        namespace_prefix: str | None = None,
        limit: int = 5,
        evidence_refs: list[EvidenceRef] | None = None,
    ) -> list[MemoryRecord]:
        metrics = get_metrics()
        provider = self.provider_name
        metrics.inc_counter("memory_recall_requested", provider=provider)

        if self._session_factory is None:
            result = self._recall_inmemory(
                project_id=project_id,
                namespace_prefix=namespace_prefix,
                limit=limit,
                evidence_refs=evidence_refs,
            )
            if result:
                metrics.inc_counter("memory_recall_hit", provider=provider)
            logger.info(
                "memory recall completed",
                extra={
                    "project_id": project_id,
                    "namespace_prefix": namespace_prefix,
                    "results": len(result),
                },
            )
            return result

        assert self._session_factory is not None
        with self._session_factory() as session:
            statement = (
                select(RuntimeMemoryRecord)
                .where(RuntimeMemoryRecord.project_id == project_id)
                .where(RuntimeMemoryRecord.stale_at.is_(None))
            )
            if namespace_prefix:
                statement = statement.where(
                    RuntimeMemoryRecord.namespace.like(f"{namespace_prefix}%")
                )
            rows = session.scalars(statement.limit(limit * 3)).all()
            records = [self._to_record(row) for row in rows]

            if self._mem0_adapter is not None and len(records) < limit:
                mem0_items = self._mem0_adapter.recall(
                    project_id=project_id,
                    namespace_prefix=namespace_prefix,
                    limit=limit - len(records),
                )
                for item in mem0_items:
                    records.append(
                        MemoryRecord(
                            **map_mem0_item(
                                item=item,
                                project_id=project_id,
                                namespace_prefix=namespace_prefix,
                            )
                        )
                    )

            elif self._adapter is not None and len(records) < limit:
                search_result = self._adapter.search(
                    project_id=project_id,
                    namespace_prefix=namespace_prefix,
                    query=namespace_prefix or project_id,
                    limit=limit - len(records),
                )
                for item in search_result.items:
                    records.append(
                        MemoryRecord(
                            record_id=str(
                                item.get("resource_uri")
                                or item.get("uri")
                                or item.get("id")
                                or "remote"
                            ),
                            project_id=project_id,
                            namespace=namespace_prefix or f"{project_id}:remote",
                            memory_type=MemoryType.LONG_TERM_KNOWLEDGE,
                            external_ref=str(item.get("resource_uri") or item.get("uri") or ""),
                            summary=str(
                                item.get("summary") or item.get("title") or "OpenViking hit"
                            ),
                            content_hash=str(item.get("resource_uri") or item.get("uri") or ""),
                            score=float(item.get("score") or 0.5),
                            quality_score=float(item.get("score") or 0.5),
                            evidence_refs=[],
                            metadata={"provider": "openviking", "remote": True},
                        )
                    )

            context = RankingContext(
                project_id=project_id,
                namespace_prefix=namespace_prefix,
                evidence_refs=evidence_refs,
                now_epoch_seconds=self._now_epoch(),
            )
            ranked = self._ranking.rank(records, context)

            for record in ranked[:limit]:
                self._touch_recall_stats(record.record_id)

            if ranked:
                metrics.inc_counter("memory_recall_hit", provider=provider)
            logger.info(
                "memory recall completed",
                extra={
                    "project_id": project_id,
                    "namespace_prefix": namespace_prefix,
                    "results": len(ranked[:limit]),
                },
            )
            return ranked[:limit]

    def get(self, record_id: str) -> MemoryRecord:
        if self._session_factory is None:
            return self._records[record_id]
        with self._session_factory() as session:
            row = session.get(RuntimeMemoryRecord, record_id)
            if row is None:
                raise KeyError(record_id)
            return self._to_record(row)

    def _touch_recall_stats(self, record_id: str) -> None:
        if self._session_factory is None:
            record = self._records.get(record_id)
            if record is not None:
                record.recall_count += 1
                record.last_recalled_at = self._utcnow()
            return
        try:
            with self._session_factory() as session:
                row = session.get(RuntimeMemoryRecord, record_id)
                if row is not None:
                    row.recall_count += 1
                    row.last_recalled_at = self._utcnow()
                    session.commit()
        except Exception:
            logger.debug("Failed to update recall stats for %s", record_id, exc_info=True)

    def _write_inmemory(
        self, candidate: MemoryWriteCandidate, decision: MemoryDecision
    ) -> MemoryRecord:
        record_id = f"mem-{len(self._records) + 1}"
        record = MemoryRecord(
            record_id=record_id,
            project_id=candidate.project_id,
            iteration_id=candidate.iteration_id,
            namespace=decision.namespace,
            memory_type=candidate.memory_type,
            external_ref=candidate.external_ref,
            summary=candidate.summary,
            content_hash=candidate.content_hash,
            score=candidate.quality_score,
            quality_score=candidate.quality_score,
            evidence_refs=candidate.evidence_refs,
            metadata=candidate.metadata,
            retention_policy=candidate.retention_policy,
            supersedes_record_id=candidate.supersedes_record_id,
        )
        self._records[record_id] = record
        self._dedup_index[decision.dedup_key] = record_id
        return record

    def _recall_inmemory(
        self,
        *,
        project_id: str,
        namespace_prefix: str | None,
        limit: int,
        evidence_refs: list[EvidenceRef] | None,
    ) -> list[MemoryRecord]:
        matches = [record for record in self._records.values() if record.project_id == project_id]
        if namespace_prefix:
            matches = [
                record for record in matches if record.namespace.startswith(namespace_prefix)
            ]
        context = RankingContext(
            project_id=project_id,
            namespace_prefix=namespace_prefix,
            evidence_refs=evidence_refs,
            now_epoch_seconds=self._now_epoch(),
        )
        ranked = self._ranking.rank(matches, context)
        if evidence_refs:
            evidence_set = {ref.ref for ref in evidence_refs}
            filtered = [
                record
                for record in ranked
                if any(ref.ref in evidence_set for ref in record.evidence_refs)
            ]
            if filtered:
                ranked = filtered
        return ranked[:limit]

    @staticmethod
    def _metadata_str(metadata: dict[str, object], key: str) -> str | None:
        value = metadata.get(key)
        return str(value) if value is not None else None

    def _render_memory_document(self, candidate: MemoryWriteCandidate, namespace: str) -> str:
        lines = [
            f"# {candidate.summary}",
            "",
            f"- project_id: {candidate.project_id}",
            f"- iteration_id: {candidate.iteration_id or 'global'}",
            f"- namespace: {namespace}",
            f"- memory_type: {candidate.memory_type}",
            f"- quality_score: {candidate.quality_score}",
            f"- external_ref: {candidate.external_ref}",
            f"- retention_policy: {candidate.retention_policy}",
            "",
            "## Summary",
            "",
            candidate.summary,
        ]
        if candidate.evidence_refs:
            lines.extend(["", "## Evidence"])
            lines.extend([f"- {ref.kind}: {ref.ref}" for ref in candidate.evidence_refs])
        return "\n".join(lines) + "\n"

    def _render_tags(self, candidate: MemoryWriteCandidate, namespace: str) -> str:
        tags = [
            "ai-desk",
            "memory",
            candidate.project_id,
            str(candidate.memory_type),
            namespace,
            candidate.retention_policy,
        ]
        return ", ".join(tags)

    @staticmethod
    def _to_record(row: RuntimeMemoryRecord) -> MemoryRecord:
        return MemoryRecord(
            record_id=row.id,
            project_id=row.project_id,
            iteration_id=row.iteration_id,
            namespace=row.namespace,
            memory_type=MemoryType(row.memory_type),
            external_ref=row.external_ref,
            summary=row.summary,
            content_hash=row.content_hash,
            score=row.score,
            quality_score=row.quality_score,
            version=row.version,
            supersedes_record_id=row.supersedes_record_id,
            stale_at=row.stale_at,
            retention_policy=RetentionPolicy(row.retention_policy),
            last_recalled_at=row.last_recalled_at,
            recall_count=row.recall_count,
            created_at=row.created_at,
            evidence_refs=[EvidenceRef.model_validate(item) for item in row.evidence_refs_json],
            metadata=dict(row.metadata_json),
        )

    @staticmethod
    def _utcnow():
        from datetime import UTC, datetime

        return datetime.now(UTC)

    @staticmethod
    def _now_epoch() -> float:
        from datetime import UTC, datetime

        return datetime.now(UTC).timestamp()
