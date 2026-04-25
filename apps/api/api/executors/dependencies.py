from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from api.config import Settings
from api.context.assembly import ContextAssemblyService
from api.context.query import (
    MemoryRecallQueryService,
    ProjectContextQueryService,
    RuntimeContextQueryService,
    SecurityContextQueryService,
)
from api.context.service import ContextBuilderService
from api.database import create_session_factory
from api.executors.providers import (
    AiderExecutorAdapter,
    ClaudeAgentExecutorAdapter,
    ClaudeCodeExecutorAdapter,
    CodexExecutorAdapter,
    OpenAIAgentsExecutorAdapter,
    OpenHandsExecutorAdapter,
)
from api.executors.registry import ExecutorRegistry
from api.executors.service import ExecutorDispatchService
from api.executors.transports import codex_config_from_settings
from api.integrations.memory import Mem0MemoryAdapter, OpenVikingMemoryAdapter
from api.memory.maintenance import MemoryMaintenanceService
from api.memory.service import MemoryGovernanceService
from api.review.service import ApprovalService, ArtifactService, AttemptStore, EvidenceService
from api.security.service import AuditLogService, SecurityPolicyService


@dataclass(slots=True)
class ExecutionContainer:
    settings: Settings
    context_builder: ContextBuilderService
    context_assembly: ContextAssemblyService
    memory: MemoryGovernanceService
    memory_maintenance: MemoryMaintenanceService
    security: SecurityPolicyService
    approvals: ApprovalService
    artifacts: ArtifactService
    evidence: EvidenceService
    attempts: AttemptStore
    registry: ExecutorRegistry
    dispatcher: ExecutorDispatchService


def configure_execution_container(settings: Settings) -> ExecutionContainer:
    session_factory = create_session_factory(settings.database_url)
    registry = ExecutorRegistry()
    registry.register(CodexExecutorAdapter(codex_config_from_settings(settings)))
    registry.register(
        ClaudeCodeExecutorAdapter(
            command=settings.claude_code_command,
            model=settings.claude_code_model,
        )
    )
    registry.register(ClaudeAgentExecutorAdapter(model=settings.claude_agent_model))
    registry.register(OpenAIAgentsExecutorAdapter(model=settings.openai_agents_model))
    registry.register(AiderExecutorAdapter(model=settings.aider_model))
    registry.register(
        OpenHandsExecutorAdapter(
            base_url=settings.openhands_api_url,
            api_key=settings.openhands_api_key,
            remote_working_dir=settings.openhands_remote_working_dir,
            allow_local_workspace=settings.openhands_local_workspace_enabled,
        )
    )

    context_builder = ContextBuilderService()
    mem0_adapter = (
        Mem0MemoryAdapter(settings)
        if settings.mem0_api_key
        else None
    )
    memory = MemoryGovernanceService(
        session_factory=session_factory,
        mem0_adapter=mem0_adapter,
        adapter=(None if mem0_adapter is not None else OpenVikingMemoryAdapter(settings)),
    )
    memory_maintenance = MemoryMaintenanceService(session_factory=session_factory)
    audit = AuditLogService(session_factory=session_factory)
    security = SecurityPolicyService(
        session_factory=session_factory,
        audit=audit,
        settings=settings,
    )
    approvals = ApprovalService(session_factory=session_factory)
    artifacts = ArtifactService(session_factory=session_factory)
    evidence = EvidenceService(session_factory=session_factory)
    attempts = AttemptStore(session_factory=session_factory)

    project_query = ProjectContextQueryService(session_factory=session_factory)
    runtime_query = RuntimeContextQueryService(
        session_factory=session_factory,
        attempts=attempts,
    )
    memory_query = MemoryRecallQueryService(memory=memory)
    security_query = SecurityContextQueryService(security=security)

    context_assembly = ContextAssemblyService(
        builder=context_builder,
        project_query=project_query,
        runtime_query=runtime_query,
        memory_query=memory_query,
        security_query=security_query,
    )

    dispatcher = ExecutorDispatchService(
        registry=registry,
        security_policy=security,
        approvals=approvals,
        artifacts=artifacts,
        evidence=evidence,
        attempts=attempts,
    )
    return ExecutionContainer(
        settings=settings,
        context_builder=context_builder,
        context_assembly=context_assembly,
        memory=memory,
        memory_maintenance=memory_maintenance,
        security=security,
        approvals=approvals,
        artifacts=artifacts,
        evidence=evidence,
        attempts=attempts,
        registry=registry,
        dispatcher=dispatcher,
    )


def get_execution_container(request: Request) -> ExecutionContainer:
    return request.app.state.execution_container


def get_dispatch_service(
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
) -> ExecutorDispatchService:
    return container.dispatcher
