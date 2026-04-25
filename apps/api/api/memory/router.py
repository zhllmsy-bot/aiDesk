from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from api.auth.models import User
from api.control_plane.dependencies import get_current_user
from api.executors.contracts import MemoryHitsResponse, MemoryWriteCandidate, map_memory_hit
from api.executors.dependencies import ExecutionContainer, get_execution_container

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/writes", response_model=MemoryHitsResponse, status_code=status.HTTP_201_CREATED)
def write_memory(
    payload: MemoryWriteCandidate,
    _: Annotated[User, Depends(get_current_user)],
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
) -> MemoryHitsResponse:
    record = container.memory.write(payload)
    if record is None:
        return MemoryHitsResponse(items=[])
    return MemoryHitsResponse(items=[map_memory_hit(record)])


@router.get("/hits", response_model=MemoryHitsResponse)
def list_memory_hits(
    _: Annotated[User, Depends(get_current_user)],
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
    project_id: str = Query(..., min_length=1),
    namespace_prefix: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
) -> MemoryHitsResponse:
    records = container.memory.recall(
        project_id=project_id,
        namespace_prefix=namespace_prefix,
        limit=limit,
    )
    return MemoryHitsResponse(items=[map_memory_hit(record) for record in records])


@router.post("/maintenance", response_model=dict)
def run_maintenance(
    _: Annotated[User, Depends(get_current_user)],
    container: Annotated[ExecutionContainer, Depends(get_execution_container)],
) -> dict[str, object]:
    results = container.memory_maintenance.run_full_maintenance()
    return {"status": "completed", "details": results}
