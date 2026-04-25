from __future__ import annotations

from typing import Any

from pydantic import Field

from api.events.models import CorrelationIds, RuntimeModel
from api.runtime_contracts import GraphKind


class GraphExecutionRequest(RuntimeModel):
    graph_kind: GraphKind
    objective: str
    correlation: CorrelationIds
    input_payload: dict[str, Any] = Field(default_factory=dict)
    checkpoint_id: str | None = None
    checkpoint: dict[str, Any] | None = None
    interrupt_before_finalize: bool = False
