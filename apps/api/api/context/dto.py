from __future__ import annotations

# pyright: reportUnknownVariableType=false
from pydantic import ConfigDict, Field

from api.executors.contracts import EvidenceRef, ExecutionModel


class TaskCoreRecord(ExecutionModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    description: str
    objective: str | None = None
    priority: str = "normal"
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ProjectFactRecord(ExecutionModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    fact: str
    source: str = "project_domain"
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class RecentAttemptRecord(ExecutionModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: str
    task_id: str
    executor: str
    status: str
    summary: str
    failure_reason: str | None = None
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class MemoryRecallRecord(ExecutionModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    project_id: str
    namespace: str
    summary: str
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class SecurityConstraintRecord(ExecutionModel):
    model_config = ConfigDict(extra="forbid")

    constraint_type: str
    description: str
    scope: str = "workspace"
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
