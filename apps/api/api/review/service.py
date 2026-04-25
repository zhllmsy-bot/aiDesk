from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from api.executors.contracts import (
    ApprovalRecord,
    ApprovalResolutionPayload,
    ApprovalStatus,
    ApprovalType,
    ArtifactDescriptor,
    ArtifactRecord,
    ArtifactType,
    AttemptStatus,
    AttemptSummary,
    EvidenceKind,
    EvidenceRef,
    EvidenceSummary,
    ExecutionProvenance,
    ExecutionStatus,
    ExecutorInputBundle,
    ExecutorResultBundle,
    FailureKind,
    MemoryRecord,
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    VerificationResult,
    utcnow,
)
from api.runtime_persistence.models import (
    ApprovalStatusDB,
    AttemptStatusDB,
    RuntimeApproval,
    RuntimeArtifact,
    RuntimeAttemptSummary,
    RuntimeEvidenceSummary,
)


class ApprovalService:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory
        self._approvals: dict[str, ApprovalRecord] = {}

    def request_approval(
        self,
        *,
        project_id: str,
        run_id: str,
        task_id: str,
        approval_type: ApprovalType,
        requested_by: str,
        reason: str,
        required_scope: list[str],
    ) -> ApprovalRecord:
        record = ApprovalRecord(
            approval_id=f"approval-{len(self._approvals) + 1}"
            if self._session_factory is None
            else "",
            project_id=project_id,
            run_id=run_id,
            task_id=task_id,
            approval_type=approval_type,
            status=ApprovalStatus.PENDING,
            requested_by=requested_by,
            reason=reason,
            required_scope=required_scope,
        )
        if self._session_factory is None:
            self._approvals[record.approval_id] = record
            return record
        with self._session_factory() as session:
            row = RuntimeApproval(
                project_id=project_id,
                workflow_run_id=run_id,
                task_id=task_id,
                approval_type=str(approval_type),
                status=ApprovalStatusDB.pending,
                requested_by=requested_by,
                reason=reason,
                required_scope=required_scope,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._to_approval(row)

    def resolve_approval(
        self,
        approval_id: str,
        *,
        resolved_by: str,
        payload: ApprovalResolutionPayload,
    ) -> ApprovalRecord:
        if self._session_factory is None:
            record = self.get_approval(approval_id)
            updated = record.model_copy(
                update={
                    "status": payload.decision,
                    "resolved_by": resolved_by,
                    "resolved_at": utcnow(),
                    "resolution_payload": payload,
                }
            )
            self._approvals[approval_id] = updated
            return updated
        with self._session_factory() as session:
            row = session.get(RuntimeApproval, approval_id)
            if row is None:
                raise KeyError(f"unknown approval id: {approval_id}")
            row.status = ApprovalStatusDB(payload.decision)
            row.resolved_by = resolved_by
            row.resolved_at = utcnow()
            row.resolution_json = payload.model_dump(mode="json")
            session.commit()
            return self._to_approval(row)

    def expire_approval(self, approval_id: str) -> ApprovalRecord:
        return self._set_terminal_status(approval_id, ApprovalStatus.EXPIRED)

    def cancel_approval(self, approval_id: str) -> ApprovalRecord:
        return self._set_terminal_status(approval_id, ApprovalStatus.CANCELLED)

    def _set_terminal_status(self, approval_id: str, status: ApprovalStatus) -> ApprovalRecord:
        if self._session_factory is None:
            record = self.get_approval(approval_id)
            updated = record.model_copy(update={"status": status, "resolved_at": utcnow()})
            self._approvals[approval_id] = updated
            return updated
        with self._session_factory() as session:
            row = session.get(RuntimeApproval, approval_id)
            if row is None:
                raise KeyError(f"unknown approval id: {approval_id}")
            row.status = ApprovalStatusDB(status)
            row.resolved_at = utcnow()
            session.commit()
            return self._to_approval(row)

    def list_approvals(self) -> list[ApprovalRecord]:
        if self._session_factory is None:
            return list(self._approvals.values())
        with self._session_factory() as session:
            rows = session.scalars(
                select(RuntimeApproval).order_by(RuntimeApproval.requested_at.desc())
            ).all()
            return [self._to_approval(row) for row in rows]

    def get_approval(self, approval_id: str) -> ApprovalRecord:
        if self._session_factory is None:
            try:
                return self._approvals[approval_id]
            except KeyError as exc:
                raise KeyError(f"unknown approval id: {approval_id}") from exc
        with self._session_factory() as session:
            row = session.get(RuntimeApproval, approval_id)
            if row is None:
                raise KeyError(f"unknown approval id: {approval_id}")
            return self._to_approval(row)

    @staticmethod
    def _to_approval(row: RuntimeApproval) -> ApprovalRecord:
        resolution_payload = (
            ApprovalResolutionPayload.model_validate(row.resolution_json)
            if row.resolution_json
            else None
        )
        return ApprovalRecord(
            approval_id=row.id,
            project_id=row.project_id,
            run_id=row.workflow_run_id,
            task_id=row.task_id,
            approval_type=ApprovalType(row.approval_type),
            status=ApprovalStatus(row.status),
            requested_by=row.requested_by,
            requested_at=row.requested_at,
            resolved_by=row.resolved_by,
            resolved_at=row.resolved_at,
            resolution_payload=resolution_payload,
            reason=row.reason,
            required_scope=list(row.required_scope),
        )


class ArtifactService:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory
        self._artifacts: dict[str, ArtifactRecord] = {}

    def register_artifacts(
        self,
        *,
        project_id: str,
        run_id: str,
        task_id: str,
        source_attempt_id: str,
        source_executor: str,
        artifacts: list[ArtifactDescriptor],
    ) -> list[str]:
        if self._session_factory is None:
            artifact_ids: list[str] = []
            for artifact in artifacts:
                artifact_id = f"artifact-{len(self._artifacts) + 1}"
                record = ArtifactRecord(
                    artifact_id=artifact_id,
                    project_id=project_id,
                    run_id=run_id,
                    task_id=task_id,
                    source_attempt_id=source_attempt_id,
                    source_executor=source_executor,
                    **artifact.model_dump(),
                )
                self._artifacts[artifact_id] = record
                artifact_ids.append(artifact_id)
            return artifact_ids

        ids: list[str] = []
        with self._session_factory() as session:
            for artifact in artifacts:
                row = RuntimeArtifact(
                    project_id=project_id,
                    workflow_run_id=run_id,
                    task_id=task_id,
                    source_attempt_id=source_attempt_id,
                    source_executor=source_executor,
                    artifact_type=str(artifact.artifact_type),
                    path=artifact.path,
                    content_hash=artifact.content_hash,
                    producer=artifact.producer,
                    workspace_ref=artifact.workspace_ref,
                    provenance_json=artifact.provenance.model_dump(mode="json"),
                    summary=artifact.summary,
                    metadata_json=artifact.metadata,
                    retention_policy=artifact.retention_policy,
                    evidence_refs_json=[
                        ref.model_dump(mode="json") for ref in artifact.evidence_refs
                    ],
                )
                session.add(row)
                session.flush()
                ids.append(row.id)
            session.commit()
        return ids

    def list_artifacts(
        self,
        *,
        project_id: str | None = None,
        run_id: str | None = None,
        task_id: str | None = None,
    ) -> list[ArtifactRecord]:
        if self._session_factory is None:
            values = list(self._artifacts.values())
            if project_id:
                values = [artifact for artifact in values if artifact.project_id == project_id]
            if run_id:
                values = [artifact for artifact in values if artifact.run_id == run_id]
            if task_id:
                values = [artifact for artifact in values if artifact.task_id == task_id]
            return values
        with self._session_factory() as session:
            statement = select(RuntimeArtifact).order_by(RuntimeArtifact.created_at.desc())
            if project_id:
                statement = statement.where(RuntimeArtifact.project_id == project_id)
            if run_id:
                statement = statement.where(RuntimeArtifact.workflow_run_id == run_id)
            if task_id:
                statement = statement.where(RuntimeArtifact.task_id == task_id)
            return [self._to_artifact(row) for row in session.scalars(statement).all()]

    def get_artifact(self, artifact_id: str) -> ArtifactRecord:
        if self._session_factory is None:
            try:
                return self._artifacts[artifact_id]
            except KeyError as exc:
                raise KeyError(f"unknown artifact id: {artifact_id}") from exc
        with self._session_factory() as session:
            row = session.get(RuntimeArtifact, artifact_id)
            if row is None:
                raise KeyError(f"unknown artifact id: {artifact_id}")
            return self._to_artifact(row)

    @staticmethod
    def _to_artifact(row: RuntimeArtifact) -> ArtifactRecord:
        return ArtifactRecord(
            artifact_id=row.id,
            project_id=row.project_id,
            run_id=row.workflow_run_id,
            task_id=row.task_id,
            source_attempt_id=row.source_attempt_id,
            source_executor=row.source_executor,
            artifact_type=ArtifactType(row.artifact_type),
            path=row.path,
            content_hash=row.content_hash,
            producer=row.producer,
            workspace_ref=row.workspace_ref,
            provenance=ExecutionProvenance.model_validate(row.provenance_json),
            summary=row.summary,
            metadata=dict(row.metadata_json),
            retention_policy=row.retention_policy,
            evidence_refs=[EvidenceRef.model_validate(item) for item in row.evidence_refs_json],
            created_at=row.created_at,
        )


class EvidenceService:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory
        self._evidence: dict[str, EvidenceSummary] = {}

    def record_execution(
        self,
        *,
        attempt_id: str,
        artifact_ids: list[str],
        verification: VerificationResult | None,
        provenance: ExecutionProvenance,
    ) -> None:
        verification_refs = []
        if verification:
            verification_refs = verification.evidence_refs or [
                EvidenceRef(
                    kind=EvidenceKind.VERIFICATION,
                    ref=f"verify:{attempt_id}",
                    summary=verification.summary,
                )
            ]
        nodes = [
            ProvenanceNode(
                node_id="attempt", kind=EvidenceKind.PROVENANCE, label="Attempt", ref=attempt_id
            ),
            ProvenanceNode(
                node_id="executor",
                kind=EvidenceKind.PROVENANCE,
                label=provenance.executor,
                ref=provenance.provider_request_id,
            ),
        ]
        edges = [ProvenanceEdge(source="attempt", target="executor", relation="executed_by")]
        for index, aid in enumerate(artifact_ids, start=1):
            node_id = f"artifact-{index}"
            nodes.append(
                ProvenanceNode(
                    node_id=node_id,
                    kind=EvidenceKind.ARTIFACT,
                    label="Artifact",
                    ref=aid,
                )
            )
            edges.append(ProvenanceEdge(source="attempt", target=node_id, relation="produced"))
        summary = EvidenceSummary(
            attempt_id=attempt_id,
            artifact_ids=artifact_ids,
            verification=verification,
            verification_refs=verification_refs,
            provenance_graph=ProvenanceGraph(nodes=nodes, edges=edges),
        )
        if self._session_factory is None:
            self._evidence[attempt_id] = summary
            return
        with self._session_factory() as session:
            row = session.get(RuntimeEvidenceSummary, attempt_id)
            data = self._summary_to_row_data(summary)
            if row is None:
                row = RuntimeEvidenceSummary(**data)
                session.add(row)
            else:
                for key, value in data.items():
                    setattr(row, key, value)
            session.commit()

    def attach_memory(self, attempt_id: str, memory_records: list[MemoryRecord]) -> EvidenceSummary:
        if self._session_factory is None:
            summary = self.get_summary(attempt_id)
            updated = summary.model_copy(update={"memory_refs": memory_records})
            self._evidence[attempt_id] = updated
            return updated
        with self._session_factory() as session:
            row = session.get(RuntimeEvidenceSummary, attempt_id)
            if row is None:
                raise KeyError(f"unknown attempt id: {attempt_id}")
            row.memory_refs_json = [rec.model_dump(mode="json") for rec in memory_records]
            session.commit()
            return self._to_summary(row)

    def get_summary(self, attempt_id: str) -> EvidenceSummary:
        if self._session_factory is None:
            try:
                return self._evidence[attempt_id]
            except KeyError as exc:
                raise KeyError(f"unknown attempt id: {attempt_id}") from exc
        with self._session_factory() as session:
            row = session.get(RuntimeEvidenceSummary, attempt_id)
            if row is None:
                raise KeyError(f"unknown attempt id: {attempt_id}")
            return self._to_summary(row)

    @staticmethod
    def _summary_to_row_data(summary: EvidenceSummary) -> dict[str, object]:
        return {
            "attempt_id": summary.attempt_id,
            "artifact_ids_json": summary.artifact_ids,
            "verification_json": (
                summary.verification.model_dump(mode="json") if summary.verification else None
            ),
            "verification_refs_json": [
                ref.model_dump(mode="json") for ref in summary.verification_refs
            ],
            "memory_refs_json": [rec.model_dump(mode="json") for rec in summary.memory_refs],
            "provenance_graph_json": summary.provenance_graph.model_dump(mode="json"),
        }

    @staticmethod
    def _to_summary(row: RuntimeEvidenceSummary) -> EvidenceSummary:
        verification = (
            VerificationResult.model_validate(row.verification_json)
            if row.verification_json
            else None
        )
        return EvidenceSummary(
            attempt_id=row.attempt_id,
            artifact_ids=list(row.artifact_ids_json),
            verification=verification,
            verification_refs=[
                EvidenceRef.model_validate(item) for item in row.verification_refs_json
            ],
            memory_refs=[MemoryRecord.model_validate(item) for item in row.memory_refs_json],
            provenance_graph=ProvenanceGraph.model_validate(row.provenance_graph_json),
        )


class AttemptStore:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory
        self._attempts: dict[str, AttemptSummary] = {}

    def record_waiting_approval(
        self, bundle: ExecutorInputBundle, approval: ApprovalRecord
    ) -> AttemptSummary:
        attempt_id = bundle.dispatch.attempt_id or bundle.dispatch.idempotency_key
        summary = AttemptSummary(
            attempt_id=attempt_id,
            project_id=bundle.workspace.project_id,
            task_id=bundle.task.task_id,
            run_id=bundle.task.run_id,
            executor_type=bundle.task.executor,
            status=AttemptStatus.WAITING_APPROVAL,
            linked_evidence_refs=bundle.evidence_refs,
            approval_id=approval.approval_id,
        )
        if self._session_factory is None:
            self._attempts[attempt_id] = summary
            return summary
        with self._session_factory() as session:
            row = session.get(RuntimeAttemptSummary, attempt_id)
            data = self._summary_to_row_data(summary)
            if row is None:
                row = RuntimeAttemptSummary(id=attempt_id, **data)
                session.add(row)
            else:
                for key, value in data.items():
                    setattr(row, key, value)
            session.commit()
            return summary

    def record_result(
        self,
        bundle: ExecutorInputBundle,
        result: ExecutorResultBundle,
        artifact_ids: list[str],
    ) -> AttemptSummary:
        attempt_id = bundle.dispatch.attempt_id or bundle.dispatch.idempotency_key
        status = self._to_attempt_status(
            result.status, result.failure.kind if result.failure else None
        )
        summary = AttemptSummary(
            attempt_id=attempt_id,
            project_id=bundle.workspace.project_id,
            task_id=bundle.task.task_id,
            run_id=bundle.task.run_id,
            executor_type=bundle.task.executor,
            status=status,
            failure_category=result.failure.category if result.failure else None,
            failure_reason=result.failure.reason if result.failure else None,
            started_at=result.started_at - timedelta(seconds=max(0, result.heartbeat_count)),
            ended_at=result.finished_at,
            linked_artifact_ids=artifact_ids,
            linked_evidence_refs=bundle.evidence_refs,
            verification_passed=result.verification.passed if result.verification else None,
            provenance=result.provenance,
        )
        if self._session_factory is None:
            self._attempts[attempt_id] = summary
            return summary
        with self._session_factory() as session:
            row = session.get(RuntimeAttemptSummary, attempt_id)
            data = self._summary_to_row_data(summary)
            if row is None:
                row = RuntimeAttemptSummary(id=attempt_id, **data)
                session.add(row)
            else:
                for key, value in data.items():
                    setattr(row, key, value)
            session.commit()
            return summary

    def list_attempts(
        self,
        *,
        run_id: str | None = None,
        task_id: str | None = None,
        project_id: str | None = None,
    ) -> list[AttemptSummary]:
        if self._session_factory is None:
            values = list(self._attempts.values())
            if run_id:
                values = [attempt for attempt in values if attempt.run_id == run_id]
            if task_id:
                values = [attempt for attempt in values if attempt.task_id == task_id]
            if project_id:
                values = [attempt for attempt in values if attempt.project_id == project_id]
            return values
        with self._session_factory() as session:
            statement = select(RuntimeAttemptSummary).order_by(
                RuntimeAttemptSummary.created_at.desc()
            )
            if run_id:
                statement = statement.where(RuntimeAttemptSummary.workflow_run_id == run_id)
            if task_id:
                statement = statement.where(RuntimeAttemptSummary.task_id == task_id)
            if project_id:
                statement = statement.where(RuntimeAttemptSummary.project_id == project_id)
            return [self._to_summary(row) for row in session.scalars(statement).all()]

    def get_attempt(self, attempt_id: str) -> AttemptSummary:
        if self._session_factory is None:
            try:
                return self._attempts[attempt_id]
            except KeyError as exc:
                raise KeyError(f"unknown attempt id: {attempt_id}") from exc
        with self._session_factory() as session:
            row = session.get(RuntimeAttemptSummary, attempt_id)
            if row is None:
                raise KeyError(f"unknown attempt id: {attempt_id}")
            return self._to_summary(row)

    @staticmethod
    def _summary_to_row_data(summary: AttemptSummary) -> dict[str, object]:
        return {
            "workflow_run_id": summary.run_id,
            "task_id": summary.task_id,
            "project_id": summary.project_id,
            "executor_type": summary.executor_type,
            "status": AttemptStatusDB(summary.status),
            "failure_category": summary.failure_category,
            "failure_reason": summary.failure_reason,
            "started_at": summary.started_at,
            "ended_at": summary.ended_at,
            "approval_id": summary.approval_id,
            "verification_passed": summary.verification_passed,
            "linked_artifact_ids_json": summary.linked_artifact_ids,
            "linked_evidence_refs_json": [
                ref.model_dump(mode="json") for ref in summary.linked_evidence_refs
            ],
            "provenance_json": (
                summary.provenance.model_dump(mode="json") if summary.provenance else None
            ),
        }

    @staticmethod
    def _to_summary(row: RuntimeAttemptSummary) -> AttemptSummary:
        provenance = (
            ExecutionProvenance.model_validate(row.provenance_json) if row.provenance_json else None
        )
        return AttemptSummary(
            attempt_id=row.id,
            project_id=row.project_id,
            task_id=row.task_id,
            run_id=row.workflow_run_id,
            executor_type=row.executor_type,
            status=AttemptStatus(row.status),
            failure_category=row.failure_category,
            failure_reason=row.failure_reason,
            started_at=row.started_at or utcnow(),
            ended_at=row.ended_at,
            linked_artifact_ids=list(row.linked_artifact_ids_json),
            linked_evidence_refs=[
                EvidenceRef.model_validate(item) for item in row.linked_evidence_refs_json
            ],
            verification_passed=row.verification_passed,
            approval_id=row.approval_id,
            provenance=provenance,
        )

    @staticmethod
    def _to_attempt_status(
        status: ExecutionStatus, failure_kind: FailureKind | None
    ) -> AttemptStatus:
        if status == ExecutionStatus.SUCCEEDED:
            return AttemptStatus.COMPLETED
        if status == ExecutionStatus.CANCELLED:
            return AttemptStatus.CANCELLED
        if status == ExecutionStatus.WAITING_APPROVAL:
            return AttemptStatus.WAITING_APPROVAL
        if failure_kind == FailureKind.RETRYABLE:
            return AttemptStatus.FAILED_RETRYABLE
        return AttemptStatus.FAILED_TERMINAL
