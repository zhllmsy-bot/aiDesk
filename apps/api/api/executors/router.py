from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from api.auth.models import User
from api.control_plane.dependencies import get_current_user
from api.executors.contracts import (
    DispatchExecutionResponse,
    ExecutorCapabilitiesResponse,
    ExecutorInputBundle,
)
from api.executors.dependencies import (
    ExecutionContainer,
    get_dispatch_service,
    get_execution_container,
)
from api.executors.service import ExecutorDispatchService

router = APIRouter(prefix="/executors", tags=["executors"])


@router.get("/capabilities", response_model=ExecutorCapabilitiesResponse)
def list_capabilities(
    _: Annotated[User, Depends(get_current_user)],
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
) -> ExecutorCapabilitiesResponse:
    return ExecutorCapabilitiesResponse(items=container.registry.capabilities())


@router.post("/dispatch", response_model=DispatchExecutionResponse)
def dispatch_execution(
    payload: ExecutorInputBundle,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutorDispatchService, Depends(get_dispatch_service)],
) -> DispatchExecutionResponse:
    return service.dispatch(payload)
