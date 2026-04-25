from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from api.context.assembly import AssemblyRequest, ContextAssemblyService
from api.context.dto import (
    MemoryRecallRecord,
    ProjectFactRecord,
    RecentAttemptRecord,
    SecurityConstraintRecord,
    TaskCoreRecord,
)
from api.context.query import (
    MemoryRecallQueryService,
    ProjectContextQueryService,
    RuntimeContextQueryService,
    SecurityContextQueryService,
)
from api.context.service import ContextAssemblyInput, ContextBuilderInput, ContextBuilderService
from api.executors.contracts import (
    ApprovalResolutionPayload,
    ApprovalStatus,
    ApprovalType,
    ArtifactDescriptor,
    ArtifactType,
    ContextLevel,
    DispatchControl,
    EvidenceKind,
    EvidenceRef,
    ExecutionProvenance,
    ExecutionStatus,
    ExecutorInputBundle,
    ExecutorResultBundle,
    FailureInfo,
    FailureKind,
    MemoryType,
    MemoryWriteCandidate,
    PermissionPolicy,
    SecretSource,
    SecretUsage,
    TaskInfo,
    VerifyCommand,
    WorkspaceInfo,
    WorkspaceMode,
)
from api.memory.service import MemoryGovernanceService
from api.review.service import ApprovalService, ArtifactService, AttemptStore, EvidenceService
from api.security.service import SecurityPolicyService


@dataclass(slots=True)
class _AssemblyFixture:
    service: ContextAssemblyService
    memory: MemoryGovernanceService


def sample_bundle(
    *,
    executor: str = "codex",
    workspace_mode: WorkspaceMode = WorkspaceMode.WORKTREE,
    metadata: dict[str, object] | None = None,
    secret_enabled: bool = False,
) -> ExecutorInputBundle:
    return ExecutorInputBundle(
        task=TaskInfo(
            task_id="task-1",
            run_id="run-1",
            title="Implement feature",
            description="Make a change",
            executor=executor,
            expected_artifact_types=[ArtifactType.PATCH],
            metadata=metadata or {},
        ),
        workspace=WorkspaceInfo(
            project_id="project-1",
            iteration_id="iter-1",
            workspace_ref="ws-1",
            root_path="/repo/project",
            mode=workspace_mode,
            writable_paths=(
                ["/repo/project/apps/api"] if workspace_mode != WorkspaceMode.READ_ONLY else []
            ),
        ),
        context_blocks=[],
        permission_policy=PermissionPolicy(
            workspace_allowlist=["/repo"],
            allowed_write_paths=["/repo/project/apps/api"],
            command_allowlist=["pytest", "python"],
            command_denylist=["rm -rf", "curl "],
            require_manual_approval_for_write=True,
            secret_broker_enabled=secret_enabled,
            workspace_mode=workspace_mode,
        ),
        verify_commands=[VerifyCommand(id="verify-1", command="pytest -q")],
        proposed_commands=["pytest -q"],
        secret_usages=[],
        evidence_refs=[
            EvidenceRef(kind=EvidenceKind.ARTIFACT, ref="artifact-seed", summary="seed")
        ],
        dispatch=DispatchControl(idempotency_key="dispatch-1", attempt_id="attempt-1"),
    )


def test_context_builder_orders_levels() -> None:
    service = ContextBuilderService()
    bundle = service.build(
        ContextBuilderInput(
            task_id="task-1",
            task_core="do the thing",
            project_facts=["fact a", "fact b"],
            workflow_summary="workflow ready",
            recent_attempts=["attempt 1", "attempt 2"],
            memory_recall=["memory 1"],
            security_summary="writes require approval",
            evidence_refs=[EvidenceRef(kind=EvidenceKind.MEMORY, ref="mem-1")],
        )
    )
    assert bundle.blocks[0].level == ContextLevel.L0
    assert bundle.blocks[-1].level == ContextLevel.L3
    assert all(block.evidence_refs for block in bundle.blocks)


def test_memory_governance_rejects_low_quality_and_dedups() -> None:
    service = MemoryGovernanceService()
    low_quality = service.write(
        MemoryWriteCandidate(
            project_id="project-1",
            iteration_id="iter-1",
            memory_type=MemoryType.LESSON,
            external_ref="ref-low",
            summary="bad memory",
            content_hash="hash-low",
            quality_score=0.2,
        )
    )
    accepted = service.write(
        MemoryWriteCandidate(
            project_id="project-1",
            iteration_id="iter-1",
            memory_type=MemoryType.LESSON,
            external_ref="ref-1",
            summary="good memory",
            content_hash="hash-1",
            quality_score=0.8,
        )
    )
    duplicate = service.write(
        MemoryWriteCandidate(
            project_id="project-1",
            iteration_id="iter-1",
            memory_type=MemoryType.LESSON,
            external_ref="ref-2",
            summary="duplicate memory",
            content_hash="hash-1",
            quality_score=0.95,
        )
    )
    assert low_quality is None
    assert accepted is not None
    assert duplicate is not None
    assert duplicate.record_id == accepted.record_id
    assert len(service.recall(project_id="project-1")) == 1


def test_security_policy_requires_write_approval() -> None:
    service = SecurityPolicyService()
    decision = service.evaluate(sample_bundle())
    assert decision.needs_approval is True
    assert "write execution" in (decision.reason or "")


def test_security_policy_blocks_secret_when_broker_disabled() -> None:
    service = SecurityPolicyService()
    bundle = sample_bundle(workspace_mode=WorkspaceMode.READ_ONLY).model_copy(
        update={
            "permission_policy": PermissionPolicy(
                workspace_allowlist=["/repo"],
                command_allowlist=["pytest", "python"],
                command_denylist=["rm -rf"],
                require_manual_approval_for_write=False,
                secret_broker_enabled=False,
                workspace_mode=WorkspaceMode.READ_ONLY,
            ),
            "secret_usages": [
                SecretUsage(name="API_KEY", source=SecretSource.BROKER, scope="executor")
            ],
        }
    )
    decision = service.evaluate(bundle)
    assert decision.needs_approval is True
    assert "secret broker is disabled" in (decision.reason or "")


def test_review_domain_tracks_evidence_and_attempts() -> None:
    approvals = ApprovalService()
    artifacts = ArtifactService()
    evidence = EvidenceService()
    attempts = AttemptStore()
    approval = approvals.request_approval(
        project_id="project-1",
        run_id="run-1",
        task_id="task-1",
        approval_type=ApprovalType.WRITE_EXECUTION,
        requested_by="system",
        reason="Need write permission",
        required_scope=["/repo/project/apps/api"],
    )
    resolved = approvals.resolve_approval(
        approval.approval_id,
        resolved_by="alice",
        payload=ApprovalResolutionPayload(
            decision=ApprovalStatus.APPROVED,
            reason="approved",
            approved_write_paths=["/repo/project/apps/api"],
        ),
    )
    assert resolved.status == ApprovalStatus.APPROVED

    provenance = ExecutionProvenance(
        executor="codex",
        provider_request_id="req-1",
        attempt_id="attempt-1",
        workspace_ref="ws-1",
        trigger="manual",
    )
    artifact_ids = artifacts.register_artifacts(
        project_id="project-1",
        run_id="run-1",
        task_id="task-1",
        source_attempt_id="attempt-1",
        source_executor="codex",
        artifacts=[
            ArtifactDescriptor(
                artifact_type=ArtifactType.PATCH,
                path="patch.diff",
                content_hash="sha256:123",
                producer="codex",
                workspace_ref="ws-1",
                provenance=provenance,
            )
        ],
    )
    verification = ExecutorResultBundle(
        status=ExecutionStatus.FAILED,
        failure=FailureInfo(kind=FailureKind.RETRYABLE, category="network", reason="retry later"),
        provenance=provenance,
    )
    evidence.record_execution(
        attempt_id="attempt-1",
        artifact_ids=artifact_ids,
        verification=verification.verification,
        provenance=provenance,
    )
    summary = evidence.get_summary("attempt-1")
    assert summary.artifact_ids == artifact_ids

    attempt = attempts.record_result(
        sample_bundle(workspace_mode=WorkspaceMode.READ_ONLY),
        result=verification,
        artifact_ids=[],
    )
    assert attempt.status == "failed_retryable"


def _register_user(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "super-secure-password",
            "display_name": email.split("@", maxsplit=1)[0].title(),
        },
    )
    token = response.json()["session"]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_be3_dispatch_and_review_apis(client: TestClient) -> None:
    headers = _register_user(client, "be3-owner@example.com")

    dispatch_response = client.post(
        "/executors/dispatch",
        json=sample_bundle().model_dump(mode="json"),
        headers=headers,
    )
    assert dispatch_response.status_code == 200
    payload = dispatch_response.json()
    assert payload["result"] is None
    assert payload["approval"] is not None

    approvals_response = client.get("/review/approvals", headers=headers)
    assert approvals_response.status_code == 200
    assert len(approvals_response.json()["items"]) >= 1

    success_bundle = sample_bundle(
        workspace_mode=WorkspaceMode.READ_ONLY,
        metadata={"simulate_success": True},
    ).model_copy(
        update={"dispatch": DispatchControl(idempotency_key="dispatch-2", attempt_id="attempt-2")}
    )
    success_response = client.post(
        "/executors/dispatch",
        json=success_bundle.model_dump(mode="json"),
        headers=headers,
    )
    assert success_response.status_code == 200
    success_payload = success_response.json()
    assert success_payload["result"] is not None

    artifacts_response = client.get("/review/artifacts?run_id=run-1", headers=headers)
    assert artifacts_response.status_code == 200
    assert len(artifacts_response.json()["items"]) >= 1

    evidence_response = client.get("/review/evidence/attempt-2", headers=headers)
    assert evidence_response.status_code == 200
    assert evidence_response.json()["attemptId"] == "attempt-2"

    attempt_response = client.get("/review/attempts/attempt-2", headers=headers)
    assert attempt_response.status_code == 200
    assert attempt_response.json()["id"] == "attempt-2"


def test_be3_retryable_failure_and_memory_apis(client: TestClient, project_root: Path) -> None:
    headers = _register_user(client, "be3-memory@example.com")

    bundle = sample_bundle(
        executor="openhands",
        workspace_mode=WorkspaceMode.READ_ONLY,
        metadata={"simulate_retryable_failure": True},
    ).model_copy(
        update={"dispatch": DispatchControl(idempotency_key="dispatch-3", attempt_id="attempt-3")}
    )
    dispatch_response = client.post(
        "/executors/dispatch",
        json=bundle.model_dump(mode="json"),
        headers=headers,
    )
    assert dispatch_response.status_code == 200
    assert dispatch_response.json()["result"]["failure"]["kind"] == "retryable"

    attempt_response = client.get("/review/attempts/attempt-3", headers=headers)
    assert attempt_response.status_code == 200
    assert "session lease" in attempt_response.json()["summary"].lower()

    contract_response = client.get("/contracts/execution")
    assert contract_response.status_code == 200
    assert contract_response.json()["schema_version"] == "2026-04-19.execution.v1"

    write_response = client.post(
        "/memory/writes",
        json=MemoryWriteCandidate(
            project_id="project-api",
            iteration_id="iter-api",
            memory_type=MemoryType.PROJECT_FACT,
            external_ref="doc://project-api",
            summary="project fact",
            content_hash="hash-api",
            quality_score=0.9,
        ).model_dump(mode="json"),
        headers=headers,
    )
    assert write_response.status_code == 201
    assert len(write_response.json()["items"]) == 1

    recall_response = client.get("/memory/hits?project_id=project-api", headers=headers)
    assert recall_response.status_code == 200
    assert len(recall_response.json()["items"]) == 1


def _build_assembly_service() -> _AssemblyFixture:
    memory = MemoryGovernanceService()
    security = SecurityPolicyService()
    attempts = AttemptStore()
    builder = ContextBuilderService()
    return _AssemblyFixture(
        service=ContextAssemblyService(
            builder=builder,
            project_query=ProjectContextQueryService(),
            runtime_query=RuntimeContextQueryService(attempts=attempts),
            memory_query=MemoryRecallQueryService(memory=memory),
            security_query=SecurityContextQueryService(security=security),
        ),
        memory=memory,
    )


def test_t3_build_from_records_orders_levels() -> None:
    service = ContextBuilderService()
    payload = ContextAssemblyInput(
        task_id="task-t3",
        task_core=TaskCoreRecord(
            task_id="task-t3",
            title="Implement feature X",
            description="Make X work end-to-end",
            evidence_refs=[EvidenceRef(kind=EvidenceKind.PROVENANCE, ref="task-t3")],
        ),
        project_facts=[
            ProjectFactRecord(
                project_id="proj-1",
                fact="Uses Python 3.12",
                relevance_score=0.9,
                evidence_refs=[EvidenceRef(kind=EvidenceKind.MEMORY, ref="mem-py")],
            ),
        ],
        recent_attempts=[
            RecentAttemptRecord(
                attempt_id="att-1",
                task_id="task-t3",
                executor="codex",
                status="failed_retryable",
                summary="Timeout during build",
                relevance_score=0.7,
            ),
        ],
        memory_recall=[
            MemoryRecallRecord(
                record_id="mem-1",
                project_id="proj-1",
                namespace="proj-1:global:lesson",
                summary="Always run lint before commit",
                score=0.85,
            ),
        ],
        security_constraints=[
            SecurityConstraintRecord(
                constraint_type="write_approval",
                description="Write execution requires manual approval",
            ),
        ],
    )
    bundle = service.build_from_records(payload)
    levels = [block.level for block in bundle.blocks]
    assert levels[0] == ContextLevel.L0
    assert levels[-1] == ContextLevel.L3
    assert any(block.source == "task_truth" for block in bundle.blocks)
    assert any(block.source == "memory_recall" for block in bundle.blocks)
    assert any(block.source.startswith("security:") for block in bundle.blocks)
    assert any(ref.kind == EvidenceKind.PROVENANCE for ref in bundle.evidence_refs)
    assert any(ref.kind == EvidenceKind.MEMORY for ref in bundle.evidence_refs)


def test_t3_ranking_stable_with_mixed_input() -> None:
    service = ContextBuilderService()
    payload = ContextAssemblyInput(
        task_id="task-rank",
        project_facts=[
            ProjectFactRecord(project_id="p1", fact="Low relevance", relevance_score=0.3),
            ProjectFactRecord(project_id="p1", fact="High relevance", relevance_score=0.9),
            ProjectFactRecord(project_id="p1", fact="Medium relevance", relevance_score=0.6),
        ],
        max_blocks_per_level=3,
    )
    bundle = service.build_from_records(payload)
    l1_blocks = [b for b in bundle.blocks if b.level == ContextLevel.L1]
    assert len(l1_blocks) == 3
    assert l1_blocks[0].body == "High relevance"
    assert l1_blocks[1].body == "Medium relevance"
    assert l1_blocks[2].body == "Low relevance"


def test_t3_truncation_preserves_evidence_refs() -> None:
    service = ContextBuilderService()
    long_body = "A" * 500
    payload = ContextAssemblyInput(
        task_id="task-trunc",
        memory_recall=[
            MemoryRecallRecord(
                record_id="mem-long",
                project_id="p1",
                namespace="ns",
                summary=long_body,
                score=0.8,
                evidence_refs=[
                    EvidenceRef(
                        kind=EvidenceKind.MEMORY,
                        ref="mem-long",
                        summary="long memory",
                    )
                ],
            ),
        ],
    )
    bundle = service.build_from_records(payload)
    mem_blocks = [b for b in bundle.blocks if b.level == ContextLevel.L3]
    assert len(mem_blocks) == 1
    assert mem_blocks[0].truncated is True
    assert len(mem_blocks[0].body) == ContextBuilderService.MAX_BODY_LENGTH
    assert any(ref.ref == "mem-long" for ref in mem_blocks[0].evidence_refs)


def test_t3_token_budget_truncates() -> None:
    service = ContextBuilderService()
    payload = ContextAssemblyInput(
        task_id="task-budget",
        task_core=TaskCoreRecord(task_id="task-budget", title="T", description="D"),
        memory_recall=[
            MemoryRecallRecord(
                record_id=f"mem-{i}",
                project_id="p1",
                namespace="ns",
                summary=f"Memory block {i} with some content",
                score=0.5,
            )
            for i in range(10)
        ],
        token_budget=100,
    )
    bundle = service.build_from_records(payload)
    total_chars = sum(len(b.body) for b in bundle.blocks)
    assert total_chars <= 100 * 4


def test_t3_dedup_removes_duplicate_entries() -> None:
    service = ContextBuilderService()
    payload = ContextAssemblyInput(
        task_id="task-dedup",
        project_facts=[
            ProjectFactRecord(project_id="p1", fact="Same fact", relevance_score=0.9),
            ProjectFactRecord(project_id="p1", fact="Same fact", relevance_score=0.8),
            ProjectFactRecord(project_id="p1", fact="Different fact", relevance_score=0.7),
        ],
    )
    bundle = service.build_from_records(payload)
    l1_bodies = [b.body for b in bundle.blocks if b.level == ContextLevel.L1]
    assert l1_bodies.count("Same fact") == 1
    assert "Different fact" in l1_bodies


def test_t3_minimal_context_without_recall() -> None:
    service = ContextBuilderService()
    payload = ContextAssemblyInput(
        task_id="task-minimal",
        workflow_summary="Running initial task",
    )
    bundle = service.build_from_records(payload)
    assert len(bundle.blocks) >= 1
    assert bundle.blocks[0].level == ContextLevel.L0
    assert bundle.task_id == "task-minimal"


def test_t3_assembly_service_full_path() -> None:
    fixture = _build_assembly_service()
    fixture.memory.write(
        MemoryWriteCandidate(
            project_id="proj-asm",
            memory_type=MemoryType.LESSON,
            external_ref="ref-asm",
            summary="Always test before deploy",
            content_hash="hash-asm",
            quality_score=0.9,
            evidence_refs=[EvidenceRef(kind=EvidenceKind.MEMORY, ref="ref-asm", summary="lesson")],
        )
    )
    request = AssemblyRequest(
        project_id="proj-asm",
        task_id="task-asm",
        workspace_mode="read_only",
        require_approval=True,
        secret_broker_enabled=False,
    )
    bundle = fixture.service.assemble(request)
    assert bundle.task_id == "task-asm"
    assert len(bundle.blocks) >= 1
    assert any(block.level == ContextLevel.L0 for block in bundle.blocks)
    assert any(block.level == ContextLevel.L1 for block in bundle.blocks)
    assert any(ref.kind == EvidenceKind.MEMORY for ref in bundle.evidence_refs)


def test_t3_assembly_service_minimal_without_data() -> None:
    fixture = _build_assembly_service()
    request = AssemblyRequest(
        project_id="proj-empty",
        task_id="task-empty",
    )
    bundle = fixture.service.assemble(request)
    assert bundle.task_id == "task-empty"
    assert len(bundle.blocks) >= 1
