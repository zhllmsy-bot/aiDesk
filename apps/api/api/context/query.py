from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from api.context.dto import (
    MemoryRecallRecord,
    ProjectFactRecord,
    RecentAttemptRecord,
    SecurityConstraintRecord,
    TaskCoreRecord,
)
from api.executors.contracts import EvidenceKind, EvidenceRef
from api.memory.service import MemoryGovernanceService
from api.review.service import AttemptStore
from api.runtime_persistence.models import RuntimeTask, RuntimeTaskAttempt, RuntimeWorkflowRun
from api.security.service import SecurityPolicyService


class ProjectContextQueryService:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory

    def query_task_core(self, task_id: str) -> TaskCoreRecord | None:
        if self._session_factory is None:
            return None
        with self._session_factory() as session:
            row = session.get(RuntimeTask, task_id)
            if row is None:
                return None
            return TaskCoreRecord(
                task_id=row.id,
                title=row.title,
                description=str(row.metadata_json.get("description", "")),
                objective=str(row.metadata_json.get("objective"))
                if row.metadata_json.get("objective") is not None
                else None,
                priority=str(row.metadata_json.get("priority", "normal")),
                evidence_refs=[
                    EvidenceRef(kind=EvidenceKind.PROVENANCE, ref=row.id, summary=row.title),
                ],
            )

    def query_project_facts(self, project_id: str, limit: int = 5) -> list[ProjectFactRecord]:
        if self._session_factory is None:
            return []
        with self._session_factory() as session:
            statement = (
                select(RuntimeWorkflowRun)
                .where(RuntimeWorkflowRun.project_id == project_id)
                .order_by(RuntimeWorkflowRun.created_at.desc())
                .limit(limit)
            )
            rows = session.scalars(statement).all()
            records: list[ProjectFactRecord] = []
            for row in rows:
                records.append(
                    ProjectFactRecord(
                        project_id=project_id,
                        fact=row.objective[:500],
                        source="workflow_objective",
                        relevance_score=0.7,
                        evidence_refs=[
                            EvidenceRef(
                                kind=EvidenceKind.PROVENANCE,
                                ref=row.id,
                                summary=f"Workflow: {row.workflow_name}",
                            ),
                        ],
                    )
                )
            return records


class RuntimeContextQueryService:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        attempts: AttemptStore | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._attempts = attempts

    def query_recent_attempts(
        self,
        *,
        project_id: str,
        task_id: str | None = None,
        limit: int = 3,
    ) -> list[RecentAttemptRecord]:
        if self._attempts is not None:
            attempt_summaries = self._attempts.list_attempts(
                project_id=project_id,
                task_id=task_id,
            )
            attempt_summaries.sort(key=lambda a: a.started_at, reverse=True)
            records: list[RecentAttemptRecord] = []
            for summary in attempt_summaries[:limit]:
                records.append(
                    RecentAttemptRecord(
                        attempt_id=summary.attempt_id,
                        task_id=summary.task_id,
                        executor=summary.executor_type,
                        status=str(summary.status),
                        summary=summary.failure_reason or f"Attempt {summary.status}",
                        failure_reason=summary.failure_reason,
                        relevance_score=0.6,
                        evidence_refs=summary.linked_evidence_refs,
                    )
                )
            return records

        if self._session_factory is None:
            return []
        with self._session_factory() as session:
            statement = (
                select(RuntimeTaskAttempt)
                .join(RuntimeTask, RuntimeTaskAttempt.task_id == RuntimeTask.id)
                .join(
                    RuntimeWorkflowRun,
                    RuntimeTaskAttempt.workflow_run_id == RuntimeWorkflowRun.id,
                )
                .where(RuntimeWorkflowRun.project_id == project_id)
                .order_by(RuntimeTaskAttempt.created_at.desc())
                .limit(limit)
            )
            if task_id:
                statement = statement.where(RuntimeTaskAttempt.task_id == task_id)
            rows = session.scalars(statement).all()
            return [
                RecentAttemptRecord(
                    attempt_id=row.id,
                    task_id=row.task_id,
                    executor=row.executor or "unknown",
                    status=str(row.status),
                    summary=str(row.metadata_json.get("summary", "")),
                    failure_reason=str(row.metadata_json.get("failure_reason"))
                    if row.metadata_json.get("failure_reason") is not None
                    else None,
                    relevance_score=0.6,
                    evidence_refs=[],
                )
                for row in rows
            ]


class MemoryRecallQueryService:
    def __init__(self, memory: MemoryGovernanceService | None = None) -> None:
        self._memory = memory

    def query_memory(
        self,
        *,
        project_id: str,
        namespace_prefix: str | None = None,
        limit: int = 5,
        evidence_refs: list[EvidenceRef] | None = None,
    ) -> list[MemoryRecallRecord]:
        if self._memory is None:
            return []
        records = self._memory.recall(
            project_id=project_id,
            namespace_prefix=namespace_prefix,
            limit=limit,
            evidence_refs=evidence_refs,
        )
        return [
            MemoryRecallRecord(
                record_id=rec.record_id,
                project_id=rec.project_id,
                namespace=rec.namespace,
                summary=rec.summary,
                score=rec.score,
                evidence_refs=rec.evidence_refs,
            )
            for rec in records
        ]


class SecurityContextQueryService:
    def __init__(self, security: SecurityPolicyService | None = None) -> None:
        self._security = security

    def query_constraints(
        self,
        *,
        workspace_mode: str = "read_only",
        require_approval: bool = True,
        secret_broker_enabled: bool = False,
    ) -> list[SecurityConstraintRecord]:
        constraints: list[SecurityConstraintRecord] = []
        if require_approval:
            constraints.append(
                SecurityConstraintRecord(
                    constraint_type="write_approval",
                    description="Write execution requires manual approval",
                    scope="workspace",
                    evidence_refs=[],
                )
            )
        if not secret_broker_enabled:
            constraints.append(
                SecurityConstraintRecord(
                    constraint_type="secret_broker_disabled",
                    description="Secret broker is disabled; secret access requires approval",
                    scope="secrets",
                    evidence_refs=[],
                )
            )
        if workspace_mode == "read_only":
            constraints.append(
                SecurityConstraintRecord(
                    constraint_type="read_only_workspace",
                    description="Workspace is in read-only mode",
                    scope="workspace",
                    evidence_refs=[],
                )
            )
        return constraints
