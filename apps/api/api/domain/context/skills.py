from __future__ import annotations

# pyright: reportUnknownVariableType=false
import hashlib
from datetime import datetime
from uuid import uuid4

from pydantic import Field

from api.executors.contracts import ContextBlock, ContextLevel, EvidenceRef, ExecutionModel, utcnow


class ContextSkill(ExecutionModel):
    skill_id: str
    title: str
    body: str
    source: str = "context.skill"
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ContextSkillLedgerEntry(ExecutionModel):
    ledger_id: str
    task_id: str
    skill_id: str
    injected_at: datetime
    content_hash: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ContextSkillLedger:
    def __init__(self) -> None:
        self._entries: list[ContextSkillLedgerEntry] = []

    def record(self, *, task_id: str, skill: ContextSkill) -> ContextSkillLedgerEntry:
        entry = ContextSkillLedgerEntry(
            ledger_id=f"skill-ledger-{uuid4().hex}",
            task_id=task_id,
            skill_id=skill.skill_id,
            injected_at=utcnow(),
            content_hash=hashlib.sha256(skill.body.encode()).hexdigest(),
            evidence_refs=list(skill.evidence_refs),
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> list[ContextSkillLedgerEntry]:
        return list(self._entries)


def skill_context_block(skill: ContextSkill, ledger_entry: ContextSkillLedgerEntry) -> ContextBlock:
    return ContextBlock(
        level=ContextLevel.L1,
        title=skill.title,
        body=skill.body,
        source=f"{skill.source}:{ledger_entry.ledger_id}",
        truncated=False,
        evidence_refs=list(skill.evidence_refs),
    )
