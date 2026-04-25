from __future__ import annotations

# pyright: reportUnknownVariableType=false
from pydantic import Field

from api.context.dto import (
    ProjectFactRecord,
    RecentAttemptRecord,
    TaskCoreRecord,
)
from api.context.query import (
    MemoryRecallQueryService,
    ProjectContextQueryService,
    RuntimeContextQueryService,
    SecurityContextQueryService,
)
from api.context.service import ContextAssemblyInput, ContextBuilderService
from api.executors.contracts import ContextBundle, EvidenceRef, ExecutionModel


class AssemblyRequest(ExecutionModel):
    project_id: str
    task_id: str
    iteration_id: str | None = None
    workspace_mode: str = "read_only"
    require_approval: bool = True
    secret_broker_enabled: bool = False
    namespace_prefix: str | None = None
    memory_limit: int = Field(default=5, ge=1)
    attempt_limit: int = Field(default=3, ge=1)
    fact_limit: int = Field(default=5, ge=1)
    token_budget: int = Field(default=4000, ge=100)
    max_blocks_per_level: int = Field(default=5, ge=1)
    extra_evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ContextAssemblyService:
    def __init__(
        self,
        *,
        builder: ContextBuilderService,
        project_query: ProjectContextQueryService,
        runtime_query: RuntimeContextQueryService,
        memory_query: MemoryRecallQueryService,
        security_query: SecurityContextQueryService,
    ) -> None:
        self._builder = builder
        self._project_query = project_query
        self._runtime_query = runtime_query
        self._memory_query = memory_query
        self._security_query = security_query

    def assemble(self, request: AssemblyRequest) -> ContextBundle:
        task_core = self._project_query.query_task_core(request.task_id)

        project_facts = self._project_query.query_project_facts(
            request.project_id,
            limit=request.fact_limit,
        )

        recent_attempts = self._runtime_query.query_recent_attempts(
            project_id=request.project_id,
            task_id=request.task_id,
            limit=request.attempt_limit,
        )

        memory_recall = self._memory_query.query_memory(
            project_id=request.project_id,
            namespace_prefix=request.namespace_prefix,
            limit=request.memory_limit,
            evidence_refs=request.extra_evidence_refs or None,
        )

        security_constraints = self._security_query.query_constraints(
            workspace_mode=request.workspace_mode,
            require_approval=request.require_approval,
            secret_broker_enabled=request.secret_broker_enabled,
        )

        workflow_summary = self._derive_workflow_summary(
            task_core,
            project_facts,
            recent_attempts,
        )

        assembly_input = ContextAssemblyInput(
            task_id=request.task_id,
            task_core=task_core,
            project_facts=project_facts,
            workflow_summary=workflow_summary,
            recent_attempts=recent_attempts,
            memory_recall=memory_recall,
            security_constraints=security_constraints,
            evidence_refs=request.extra_evidence_refs,
            token_budget=request.token_budget,
            max_blocks_per_level=request.max_blocks_per_level,
        )

        return self._builder.build_from_records(assembly_input)

    @staticmethod
    def _derive_workflow_summary(
        task_core: TaskCoreRecord | None,
        facts: list[ProjectFactRecord],
        attempts: list[RecentAttemptRecord],
    ) -> str:
        parts: list[str] = []
        if task_core is not None:
            parts.append(f"Task: {task_core.title}")
        if facts:
            parts.append(f"Project has {len(facts)} recorded fact(s)")
        if attempts:
            parts.append(f"{len(attempts)} prior attempt(s)")
        return "; ".join(parts) if parts else ""
