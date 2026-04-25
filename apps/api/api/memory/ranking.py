from __future__ import annotations

import math
from dataclasses import dataclass

from api.executors.contracts import EvidenceRef, MemoryRecord


@dataclass(slots=True, frozen=True)
class RankingWeights:
    semantic_score: float = 0.30
    quality_score: float = 0.25
    recency: float = 0.20
    evidence_affinity: float = 0.15
    namespace_depth: float = 0.10


@dataclass(slots=True, frozen=True)
class RankingContext:
    project_id: str
    namespace_prefix: str | None = None
    evidence_refs: list[EvidenceRef] | None = None
    now_epoch_seconds: float = 0.0


class MemoryRankingService:
    RECENCY_HALF_LIFE_SECONDS = 7 * 24 * 3600.0

    def __init__(self, weights: RankingWeights | None = None) -> None:
        self._weights = weights or RankingWeights()

    def rank(
        self,
        records: list[MemoryRecord],
        context: RankingContext,
    ) -> list[MemoryRecord]:
        if not records:
            return []
        scored = [(self._compute_score(record, context), record) for record in records]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [record for _, record in scored]

    def _compute_score(self, record: MemoryRecord, context: RankingContext) -> float:
        w = self._weights
        semantic = self._normalize_semantic(record.score)
        quality = self._normalize_quality(record.quality_score)
        recency = self._compute_recency(record, context)
        evidence = self._compute_evidence_affinity(record, context)
        namespace = self._compute_namespace_depth(record, context)
        return (
            w.semantic_score * semantic
            + w.quality_score * quality
            + w.recency * recency
            + w.evidence_affinity * evidence
            + w.namespace_depth * namespace
        )

    @staticmethod
    def _normalize_semantic(score: float) -> float:
        return max(0.0, min(1.0, score))

    @staticmethod
    def _normalize_quality(score: float) -> float:
        return max(0.0, min(1.0, score))

    def _compute_recency(self, record: MemoryRecord, context: RankingContext) -> float:
        if context.now_epoch_seconds <= 0:
            return 0.5
        created_epoch = record.created_at.timestamp() if record.created_at else 0.0
        last_recalled_epoch = (
            record.last_recalled_at.timestamp() if record.last_recalled_at else 0.0
        )
        reference_epoch = max(created_epoch, last_recalled_epoch)
        if reference_epoch <= 0:
            return 0.5
        age_seconds = context.now_epoch_seconds - reference_epoch
        if age_seconds < 0:
            return 1.0
        decay = math.exp(-0.693 * age_seconds / self.RECENCY_HALF_LIFE_SECONDS)
        recall_boost = min(record.recall_count / 10.0, 0.3) if record.recall_count > 0 else 0.0
        return min(1.0, decay + recall_boost)

    @staticmethod
    def _compute_evidence_affinity(record: MemoryRecord, context: RankingContext) -> float:
        if not context.evidence_refs or not record.evidence_refs:
            return 0.0
        query_refs = {ref.ref for ref in context.evidence_refs}
        record_refs = {ref.ref for ref in record.evidence_refs}
        overlap = len(query_refs & record_refs)
        if overlap == 0:
            return 0.0
        return min(overlap / max(len(query_refs), 1), 1.0)

    @staticmethod
    def _compute_namespace_depth(record: MemoryRecord, context: RankingContext) -> float:
        if not context.namespace_prefix:
            return 0.5
        if not record.namespace.startswith(context.namespace_prefix):
            return 0.0
        remaining = record.namespace[len(context.namespace_prefix) :]
        depth = remaining.count(":") + remaining.count("/")
        return max(0.0, 1.0 - depth * 0.15)
