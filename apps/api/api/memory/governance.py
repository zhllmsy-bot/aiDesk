from __future__ import annotations

from dataclasses import dataclass

from api.executors.contracts import MemoryWriteCandidate


@dataclass(slots=True, frozen=True)
class NamespaceThreshold:
    min_quality: float = 0.65
    allow_supersede: bool = True
    allow_merge: bool = True


DEFAULT_NAMESPACE_THRESHOLDS: dict[str, NamespaceThreshold] = {
    "long_term_knowledge": NamespaceThreshold(
        min_quality=0.70, allow_supersede=True, allow_merge=True
    ),
    "project_fact": NamespaceThreshold(min_quality=0.60, allow_supersede=True, allow_merge=True),
    "lesson": NamespaceThreshold(min_quality=0.65, allow_supersede=True, allow_merge=False),
}

GLOBAL_DEFAULT_THRESHOLD = NamespaceThreshold()


class WriteGovernancePolicy:
    def __init__(
        self,
        namespace_thresholds: dict[str, NamespaceThreshold] | None = None,
    ) -> None:
        self._thresholds = namespace_thresholds or dict(DEFAULT_NAMESPACE_THRESHOLDS)

    def threshold_for(self, namespace: str) -> NamespaceThreshold:
        for key, threshold in self._thresholds.items():
            if key in namespace:
                return threshold
        return GLOBAL_DEFAULT_THRESHOLD

    def evaluate(
        self,
        candidate: MemoryWriteCandidate,
        *,
        has_existing: bool,
        existing_version: int = 0,
    ) -> WriteGovernanceDecision:
        threshold = self.threshold_for(candidate.namespace or "")

        if not candidate.force and candidate.quality_score < threshold.min_quality:
            threshold_info = (
                f"quality score {candidate.quality_score:.2f} below "
                f"namespace threshold {threshold.min_quality:.2f}"
            )
            return WriteGovernanceDecision(
                action=WriteAction.DECLINE,
                reason=threshold_info,
            )

        if not has_existing:
            return WriteGovernanceDecision(action=WriteAction.ACCEPT, reason="new record")

        if candidate.supersedes_record_id and threshold.allow_supersede:
            return WriteGovernanceDecision(
                action=WriteAction.SUPERSEDE,
                reason=f"supersede existing record {candidate.supersedes_record_id}",
            )

        if threshold.allow_merge:
            return WriteGovernanceDecision(
                action=WriteAction.MERGE,
                reason="duplicate content hash in namespace, merge candidate",
            )

        return WriteGovernanceDecision(
            action=WriteAction.DECLINE,
            reason="duplicate content hash for namespace, merge/supersede not allowed",
        )


class WriteAction:
    ACCEPT = "accept"
    DECLINE = "decline"
    SUPERSEDE = "supersede"
    MERGE = "merge"


@dataclass(slots=True)
class WriteGovernanceDecision:
    action: str
    reason: str

    @property
    def allowed(self) -> bool:
        return self.action != WriteAction.DECLINE
