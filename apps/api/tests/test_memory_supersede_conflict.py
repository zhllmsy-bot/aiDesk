from __future__ import annotations

from sqlalchemy import select

from api.database import Base, create_session_factory
from api.executors.contracts import MemoryType, MemoryWriteCandidate
from api.memory.service import MemoryGovernanceService
from api.models import register_models
from api.runtime_persistence.models import RuntimeMemoryRecord


def _init_memory_service() -> MemoryGovernanceService:
    session_factory = create_session_factory("sqlite+pysqlite:///:memory:")
    register_models()
    engine = session_factory.kw["bind"]
    assert engine is not None
    Base.metadata.create_all(engine)
    return MemoryGovernanceService(session_factory=session_factory)


def test_supersede_updates_existing_row_without_unique_conflict() -> None:
    service = _init_memory_service()
    namespace = "project-1:global:lesson"
    original = service.write(
        MemoryWriteCandidate(
            project_id="project-1",
            memory_type=MemoryType.LESSON,
            namespace=namespace,
            external_ref="doc://original",
            summary="original",
            content_hash="hash-1",
            quality_score=0.8,
        )
    )
    assert original is not None

    superseded = service.write(
        MemoryWriteCandidate(
            project_id="project-1",
            memory_type=MemoryType.LESSON,
            namespace=namespace,
            external_ref="doc://superseded",
            summary="superseded",
            content_hash="hash-1",
            quality_score=0.95,
            supersedes_record_id=original.record_id,
        )
    )
    assert superseded is not None
    assert superseded.record_id == original.record_id
    assert superseded.version == original.version + 1
    assert superseded.summary == "superseded"
    assert superseded.external_ref == "doc://superseded"


def test_supersede_upsert_keeps_single_row_and_monotonic_version() -> None:
    service = _init_memory_service()
    namespace = "project-1:global:lesson"

    first = service.write(
        MemoryWriteCandidate(
            project_id="project-1",
            memory_type=MemoryType.LESSON,
            namespace=namespace,
            external_ref="doc://v1",
            summary="v1",
            content_hash="hash-upsert",
            quality_score=0.7,
        )
    )
    assert first is not None

    second = service.write(
        MemoryWriteCandidate(
            project_id="project-1",
            memory_type=MemoryType.LESSON,
            namespace=namespace,
            external_ref="doc://v2",
            summary="v2",
            content_hash="hash-upsert",
            quality_score=0.8,
            supersedes_record_id=first.record_id,
        )
    )
    assert second is not None

    third = service.write(
        MemoryWriteCandidate(
            project_id="project-1",
            memory_type=MemoryType.LESSON,
            namespace=namespace,
            external_ref="doc://v3",
            summary="v3",
            content_hash="hash-upsert",
            quality_score=0.9,
            supersedes_record_id=first.record_id,
        )
    )
    assert third is not None
    assert third.record_id == first.record_id
    assert third.version == first.version + 2
    assert third.summary == "v3"
    assert third.external_ref == "doc://v3"

    session_factory = service._session_factory  # type: ignore[attr-defined]
    assert session_factory is not None
    with session_factory() as session:
        rows = session.scalars(
            select(RuntimeMemoryRecord)
            .where(RuntimeMemoryRecord.project_id == "project-1")
            .where(RuntimeMemoryRecord.namespace == namespace)
            .where(RuntimeMemoryRecord.content_hash == "hash-upsert")
        ).all()
        assert len(rows) == 1
