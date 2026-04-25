from datetime import UTC, datetime, timedelta

from api.executors.contracts import (
    MemoryRecord,
    MemoryType,
    MemoryWriteCandidate,
    RetentionPolicy,
    map_memory_hit,
)
from api.memory.governance import WriteAction, WriteGovernancePolicy
from api.memory.ranking import MemoryRankingService, RankingContext


def test_ranking():
    ranking = MemoryRankingService()
    now = datetime.now(UTC)
    records = [
        MemoryRecord(
            record_id="r1",
            project_id="p1",
            namespace="p1:global:long_term_knowledge",
            memory_type=MemoryType.LONG_TERM_KNOWLEDGE,
            external_ref="ref1",
            summary="High quality old",
            content_hash="h1",
            score=0.9,
            quality_score=0.9,
            version=1,
            created_at=now - timedelta(days=30),
            recall_count=0,
        ),
        MemoryRecord(
            record_id="r2",
            project_id="p1",
            namespace="p1:global:project_fact",
            memory_type=MemoryType.PROJECT_FACT,
            external_ref="ref2",
            summary="Medium quality recent",
            content_hash="h2",
            score=0.7,
            quality_score=0.7,
            version=1,
            created_at=now - timedelta(hours=1),
            recall_count=5,
        ),
        MemoryRecord(
            record_id="r3",
            project_id="p1",
            namespace="p1:global:lesson",
            memory_type=MemoryType.LESSON,
            external_ref="ref3",
            summary="Low quality",
            content_hash="h3",
            score=0.3,
            quality_score=0.3,
            version=1,
            created_at=now,
            recall_count=0,
        ),
    ]
    context = RankingContext(
        project_id="p1",
        namespace_prefix="p1:global",
        evidence_refs=None,
        now_epoch_seconds=now.timestamp(),
    )
    ranked = ranking.rank(records, context)
    print(f"Ranking order: {[r.record_id for r in ranked]}")
    assert ranked[0].record_id in ("r1", "r2"), (
        f"Expected r1 or r2 at top, got {ranked[0].record_id}"
    )
    assert ranked[-1].record_id == "r3", f"Expected r3 at bottom, got {ranked[-1].record_id}"
    print("PASS: ranking test")


def test_governance():
    gov = WriteGovernancePolicy()

    candidate_low = MemoryWriteCandidate(
        project_id="p1",
        memory_type=MemoryType.LONG_TERM_KNOWLEDGE,
        external_ref="ref",
        summary="bad",
        content_hash="h",
        quality_score=0.3,
    )
    decision = gov.evaluate(candidate_low, has_existing=False)
    assert decision.action == WriteAction.DECLINE, f"Expected DECLINE, got {decision.action}"
    print("PASS: decline low quality")

    candidate_good = MemoryWriteCandidate(
        project_id="p1",
        memory_type=MemoryType.LONG_TERM_KNOWLEDGE,
        external_ref="ref",
        summary="good",
        content_hash="h",
        quality_score=0.8,
    )
    decision = gov.evaluate(candidate_good, has_existing=False)
    assert decision.action == WriteAction.ACCEPT, f"Expected ACCEPT, got {decision.action}"
    print("PASS: accept new good quality")

    decision = gov.evaluate(candidate_good, has_existing=True)
    assert decision.action == WriteAction.MERGE, f"Expected MERGE, got {decision.action}"
    print("PASS: merge duplicate")

    candidate_supersede = MemoryWriteCandidate(
        project_id="p1",
        memory_type=MemoryType.LONG_TERM_KNOWLEDGE,
        external_ref="ref",
        summary="updated",
        content_hash="h",
        quality_score=0.8,
        supersedes_record_id="old-id",
    )
    decision = gov.evaluate(candidate_supersede, has_existing=True)
    assert decision.action == WriteAction.SUPERSEDE, f"Expected SUPERSEDE, got {decision.action}"
    print("PASS: supersede existing")


def test_hit_mapping():
    now = datetime.now(UTC)
    record = MemoryRecord(
        record_id="r1",
        project_id="p1",
        namespace="p1:global:fact",
        memory_type=MemoryType.PROJECT_FACT,
        external_ref="ref1",
        summary="test",
        content_hash="h1",
        score=0.9,
        quality_score=0.9,
        version=2,
        supersedes_record_id="old-r1",
        stale_at=None,
        retention_policy=RetentionPolicy.RETAIN_PERMANENT,
        recall_count=5,
        created_at=now,
    )
    hit = map_memory_hit(record)
    assert hit.version == 2
    assert hit.supersedes_record_id == "old-r1"
    assert hit.retention_policy == RetentionPolicy.RETAIN_PERMANENT
    assert hit.recall_count == 5
    print("PASS: hit mapping test")


def test_inmemory_service():
    from api.memory.service import MemoryGovernanceService

    svc = MemoryGovernanceService()
    candidate = MemoryWriteCandidate(
        project_id="p1",
        memory_type=MemoryType.PROJECT_FACT,
        external_ref="ref",
        summary="test fact",
        content_hash="hash1",
        quality_score=0.8,
        retention_policy=RetentionPolicy.RETAIN_FOR_PROJECT,
    )
    record = svc.write(candidate)
    assert record is not None
    assert record.version == 1
    assert record.retention_policy == RetentionPolicy.RETAIN_FOR_PROJECT
    print("PASS: inmemory write")

    results = svc.recall(project_id="p1", limit=10)
    assert len(results) == 1
    assert results[0].record_id == record.record_id
    print("PASS: inmemory recall")

    duplicate = MemoryWriteCandidate(
        project_id="p1",
        memory_type=MemoryType.PROJECT_FACT,
        external_ref="ref",
        summary="test fact v2",
        content_hash="hash1",
        quality_score=0.9,
        retention_policy=RetentionPolicy.RETAIN_FOR_PROJECT,
    )
    merged = svc.write(duplicate)
    assert merged is not None
    print("PASS: inmemory merge duplicate")

    low_quality = MemoryWriteCandidate(
        project_id="p1",
        memory_type=MemoryType.LONG_TERM_KNOWLEDGE,
        external_ref="ref",
        summary="bad",
        content_hash="hash2",
        quality_score=0.3,
    )
    declined = svc.write(low_quality)
    assert declined is None
    print("PASS: inmemory decline low quality")


if __name__ == "__main__":
    test_ranking()
    test_governance()
    test_hit_mapping()
    test_inmemory_service()
    print("\nAll tests passed!")
