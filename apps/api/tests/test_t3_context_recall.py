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
from api.context.service import ContextAssemblyInput, ContextBuilderService
from api.executors.contracts import (
    ContextLevel,
    EvidenceKind,
    EvidenceRef,
    MemoryType,
    MemoryWriteCandidate,
)
from api.memory.service import MemoryGovernanceService
from api.review.service import AttemptStore
from api.security.service import SecurityPolicyService


def test_build_from_records_orders_levels():
    service = ContextBuilderService()
    payload = ContextAssemblyInput(
        task_id="task-t3",
        task_core=TaskCoreRecord(
            task_id="task-t3",
            title="Implement feature X",
            description="Make X work",
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
    print("PASS: build_from_records orders levels")


def test_ranking_stable():
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
    print("PASS: ranking stable")


def test_truncation_preserves_evidence_refs():
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
                    EvidenceRef(kind=EvidenceKind.MEMORY, ref="mem-long", summary="long memory")
                ],
            ),
        ],
    )
    bundle = service.build_from_records(payload)
    mem_blocks = [b for b in bundle.blocks if b.level == ContextLevel.L3]
    assert len(mem_blocks) == 1
    assert mem_blocks[0].truncated is True
    assert any(ref.ref == "mem-long" for ref in mem_blocks[0].evidence_refs)
    print("PASS: truncation preserves evidence refs")


def test_dedup():
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
    print("PASS: dedup")


def test_minimal_context():
    service = ContextBuilderService()
    payload = ContextAssemblyInput(
        task_id="task-minimal",
        workflow_summary="Running initial task",
    )
    bundle = service.build_from_records(payload)
    assert len(bundle.blocks) >= 1
    assert bundle.blocks[0].level == ContextLevel.L0
    print("PASS: minimal context without recall")


def test_assembly_service_full_path():
    memory = MemoryGovernanceService()
    security = SecurityPolicyService()
    attempts = AttemptStore()
    builder = ContextBuilderService()
    assembly = ContextAssemblyService(
        builder=builder,
        project_query=ProjectContextQueryService(),
        runtime_query=RuntimeContextQueryService(attempts=attempts),
        memory_query=MemoryRecallQueryService(memory=memory),
        security_query=SecurityContextQueryService(security=security),
    )
    memory.write(
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
    )
    bundle = assembly.assemble(request)
    assert bundle.task_id == "task-asm"
    assert len(bundle.blocks) >= 1
    assert any(block.level == ContextLevel.L0 for block in bundle.blocks)
    assert any(block.level == ContextLevel.L1 for block in bundle.blocks)
    assert any(ref.kind == EvidenceKind.MEMORY for ref in bundle.evidence_refs)
    print("PASS: assembly service full path")


def test_assembly_service_minimal():
    memory = MemoryGovernanceService()
    security = SecurityPolicyService()
    attempts = AttemptStore()
    builder = ContextBuilderService()
    assembly = ContextAssemblyService(
        builder=builder,
        project_query=ProjectContextQueryService(),
        runtime_query=RuntimeContextQueryService(attempts=attempts),
        memory_query=MemoryRecallQueryService(memory=memory),
        security_query=SecurityContextQueryService(security=security),
    )
    request = AssemblyRequest(project_id="proj-empty", task_id="task-empty")
    bundle = assembly.assemble(request)
    assert bundle.task_id == "task-empty"
    assert len(bundle.blocks) >= 1
    print("PASS: assembly service minimal")


def test_token_budget():
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
    print("PASS: token budget truncation")


if __name__ == "__main__":
    test_build_from_records_orders_levels()
    test_ranking_stable()
    test_truncation_preserves_evidence_refs()
    test_dedup()
    test_minimal_context()
    test_assembly_service_full_path()
    test_assembly_service_minimal()
    test_token_budget()
    print("\nALL T3 TESTS PASSED!")
