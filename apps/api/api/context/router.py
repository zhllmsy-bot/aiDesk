from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from api.auth.models import User
from api.context.assembly import AssemblyRequest, ContextAssemblyService
from api.context.service import ContextBuilderInput, ContextBuilderService
from api.control_plane.dependencies import get_current_user
from api.executors.contracts import ContextBundle
from api.executors.dependencies import ExecutionContainer, get_execution_container

router = APIRouter(prefix="/context", tags=["context"])


def get_context_builder(
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
) -> ContextBuilderService:
    return container.context_builder


def get_context_assembly(
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
) -> ContextAssemblyService:
    return container.context_assembly


@router.post("/build", response_model=ContextBundle)
def build_context(
    payload: ContextBuilderInput,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[ContextBuilderService, Depends(get_context_builder)],
) -> ContextBundle:
    return service.build(payload)


@router.post("/assemble", response_model=ContextBundle)
def assemble_context(
    payload: AssemblyRequest,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[ContextAssemblyService, Depends(get_context_assembly)],
) -> ContextBundle:
    return service.assemble(payload)
