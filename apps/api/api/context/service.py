from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
from pydantic import ConfigDict, Field

from api.context.dto import (
    MemoryRecallRecord,
    ProjectFactRecord,
    RecentAttemptRecord,
    SecurityConstraintRecord,
    TaskCoreRecord,
)
from api.executors.contracts import (
    ContextBlock,
    ContextBundle,
    ContextLevel,
    EvidenceRef,
    ExecutionModel,
)


class ContextBuilderInput(ExecutionModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_core: str
    project_facts: list[str]
    workflow_summary: str
    recent_attempts: list[str]
    memory_recall: list[str]
    security_summary: str
    evidence_refs: list[EvidenceRef]


class ContextAssemblyInput(ExecutionModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_core: TaskCoreRecord | None = None
    project_facts: list[ProjectFactRecord] = Field(default_factory=list)
    workflow_summary: str = ""
    recent_attempts: list[RecentAttemptRecord] = Field(default_factory=list)
    memory_recall: list[MemoryRecallRecord] = Field(default_factory=list)
    security_constraints: list[SecurityConstraintRecord] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    token_budget: int = Field(default=4000, ge=100)
    max_blocks_per_level: int = Field(default=5, ge=1)


class _RankedEntry:
    __slots__ = ("body", "source", "evidence_refs", "score")

    def __init__(
        self,
        body: str,
        source: str,
        evidence_refs: list[EvidenceRef],
        score: float,
    ) -> None:
        self.body = body
        self.source = source
        self.evidence_refs = evidence_refs
        self.score = score


class ContextBuilderService:
    MAX_BLOCKS_PER_LEVEL = 3
    MAX_BODY_LENGTH = 280

    def build(self, payload: ContextBuilderInput) -> ContextBundle:
        blocks: list[ContextBlock] = []
        blocks.extend(
            self._make_blocks(
                ContextLevel.L0,
                "Task Core",
                [payload.task_core],
                "task_truth",
                payload.evidence_refs,
            )
        )
        l1_entries = [
            *payload.project_facts[: self.MAX_BLOCKS_PER_LEVEL - 1],
            payload.workflow_summary,
            payload.security_summary,
        ]
        blocks.extend(
            self._make_blocks(
                ContextLevel.L1,
                "Project Facts",
                l1_entries,
                "project_domain",
                payload.evidence_refs,
            )
        )
        blocks.extend(
            self._make_blocks(
                ContextLevel.L2,
                "Recent Attempts",
                payload.recent_attempts,
                "recent_attempts",
                payload.evidence_refs,
            )
        )
        blocks.extend(
            self._make_blocks(
                ContextLevel.L3,
                "Long-Term Memory",
                payload.memory_recall,
                "memory_recall",
                payload.evidence_refs,
            )
        )
        return ContextBundle(
            task_id=payload.task_id,
            blocks=blocks,
            evidence_refs=payload.evidence_refs,
        )

    def build_from_records(self, payload: ContextAssemblyInput) -> ContextBundle:
        all_evidence = list(payload.evidence_refs)
        blocks: list[ContextBlock] = []

        l0_entries = self._rank_entries(
            self._task_core_entries(payload, all_evidence),
            payload.max_blocks_per_level,
        )
        blocks.extend(self._entries_to_blocks(ContextLevel.L0, "Task Core", l0_entries))

        l1_entries = self._rank_entries(
            self._project_fact_entries(payload, all_evidence)
            + self._workflow_summary_entries(payload, all_evidence)
            + self._security_entries(payload, all_evidence),
            payload.max_blocks_per_level,
        )
        blocks.extend(self._entries_to_blocks(ContextLevel.L1, "Project Facts", l1_entries))

        l2_entries = self._rank_entries(
            self._attempt_entries(payload, all_evidence),
            payload.max_blocks_per_level,
        )
        blocks.extend(self._entries_to_blocks(ContextLevel.L2, "Recent Attempts", l2_entries))

        l3_entries = self._rank_entries(
            self._memory_entries(payload, all_evidence),
            payload.max_blocks_per_level,
        )
        blocks.extend(self._entries_to_blocks(ContextLevel.L3, "Long-Term Memory", l3_entries))

        blocks = self._apply_token_budget(blocks, payload.token_budget)

        return ContextBundle(
            task_id=payload.task_id,
            blocks=blocks,
            evidence_refs=all_evidence,
        )

    def _task_core_entries(
        self, payload: ContextAssemblyInput, evidence: list[EvidenceRef]
    ) -> list[_RankedEntry]:
        if payload.task_core is not None:
            evidence.extend(payload.task_core.evidence_refs)
            return [
                _RankedEntry(
                    body=payload.task_core.title,
                    source="task_truth",
                    evidence_refs=payload.task_core.evidence_refs,
                    score=1.0,
                ),
                _RankedEntry(
                    body=payload.task_core.description,
                    source="task_truth",
                    evidence_refs=[],
                    score=0.95,
                ),
            ]
        return [
            _RankedEntry(
                body=payload.workflow_summary or "No task core available",
                source="task_truth",
                evidence_refs=[],
                score=1.0,
            ),
        ]

    def _project_fact_entries(
        self, payload: ContextAssemblyInput, evidence: list[EvidenceRef]
    ) -> list[_RankedEntry]:
        entries: list[_RankedEntry] = []
        for fact in payload.project_facts:
            evidence.extend(fact.evidence_refs)
            entries.append(
                _RankedEntry(
                    body=fact.fact,
                    source=fact.source,
                    evidence_refs=fact.evidence_refs,
                    score=fact.relevance_score,
                )
            )
        return entries

    def _workflow_summary_entries(
        self, payload: ContextAssemblyInput, evidence: list[EvidenceRef]
    ) -> list[_RankedEntry]:
        if not payload.workflow_summary:
            return []
        return [
            _RankedEntry(
                body=payload.workflow_summary,
                source="workflow_summary",
                evidence_refs=[],
                score=0.8,
            ),
        ]

    def _security_entries(
        self, payload: ContextAssemblyInput, evidence: list[EvidenceRef]
    ) -> list[_RankedEntry]:
        entries: list[_RankedEntry] = []
        for constraint in payload.security_constraints:
            evidence.extend(constraint.evidence_refs)
            entries.append(
                _RankedEntry(
                    body=constraint.description,
                    source=f"security:{constraint.constraint_type}",
                    evidence_refs=constraint.evidence_refs,
                    score=0.75,
                )
            )
        return entries

    def _attempt_entries(
        self, payload: ContextAssemblyInput, evidence: list[EvidenceRef]
    ) -> list[_RankedEntry]:
        entries: list[_RankedEntry] = []
        for attempt in payload.recent_attempts:
            evidence.extend(attempt.evidence_refs)
            entries.append(
                _RankedEntry(
                    body=attempt.summary,
                    source="recent_attempts",
                    evidence_refs=attempt.evidence_refs,
                    score=attempt.relevance_score,
                )
            )
        return entries

    def _memory_entries(
        self, payload: ContextAssemblyInput, evidence: list[EvidenceRef]
    ) -> list[_RankedEntry]:
        entries: list[_RankedEntry] = []
        for memory in payload.memory_recall:
            evidence.extend(memory.evidence_refs)
            entries.append(
                _RankedEntry(
                    body=memory.summary,
                    source="memory_recall",
                    evidence_refs=memory.evidence_refs,
                    score=memory.score,
                )
            )
        return entries

    def _make_blocks(
        self,
        level: ContextLevel,
        title: str,
        entries: list[str],
        source: str,
        evidence_refs: list[EvidenceRef],
    ) -> list[ContextBlock]:
        blocks: list[ContextBlock] = []
        for entry in entries[: self.MAX_BLOCKS_PER_LEVEL]:
            body = entry[: self.MAX_BODY_LENGTH]
            blocks.append(
                ContextBlock(
                    level=level,
                    title=title,
                    body=body,
                    source=source,
                    truncated=len(entry) > self.MAX_BODY_LENGTH,
                    evidence_refs=evidence_refs,
                )
            )
        return blocks

    @staticmethod
    def _rank_entries(entries: list[_RankedEntry], limit: int) -> list[_RankedEntry]:
        seen_bodies: set[str] = set()
        deduped: list[_RankedEntry] = []
        for entry in entries:
            key = entry.body.strip().lower()
            if key and key not in seen_bodies:
                seen_bodies.add(key)
                deduped.append(entry)
        ranked = sorted(deduped, key=lambda e: e.score, reverse=True)
        return ranked[:limit]

    @staticmethod
    def _entries_to_blocks(
        level: ContextLevel, title: str, entries: list[_RankedEntry]
    ) -> list[ContextBlock]:
        blocks: list[ContextBlock] = []
        for entry in entries:
            truncated = len(entry.body) > ContextBuilderService.MAX_BODY_LENGTH
            body = entry.body[: ContextBuilderService.MAX_BODY_LENGTH]
            blocks.append(
                ContextBlock(
                    level=level,
                    title=title,
                    body=body,
                    source=entry.source,
                    truncated=truncated,
                    evidence_refs=entry.evidence_refs,
                )
            )
        return blocks

    @staticmethod
    def _apply_token_budget(blocks: list[ContextBlock], token_budget: int) -> list[ContextBlock]:
        char_budget = token_budget * 4
        total_chars = sum(len(block.body) for block in blocks)
        if total_chars <= char_budget:
            return blocks
        result: list[ContextBlock] = []
        remaining = char_budget
        for block in blocks:
            if remaining <= 0:
                break
            if len(block.body) <= remaining:
                result.append(block)
                remaining -= len(block.body)
            else:
                truncated_body = block.body[:remaining]
                result.append(
                    ContextBlock(
                        level=block.level,
                        title=block.title,
                        body=truncated_body,
                        source=block.source,
                        truncated=True,
                        evidence_refs=block.evidence_refs,
                    )
                )
                remaining = 0
        return result
