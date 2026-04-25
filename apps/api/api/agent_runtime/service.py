from __future__ import annotations

from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import StateGraph

from api.agent_runtime.models import GraphExecutionRequest
from api.events.models import GraphArtifact, GraphExecutionResult
from api.integrations import LangGraphCheckpointerFactory
from api.runtime_contracts import GraphExecutionStatus, GraphKind
from api.runtime_persistence.service import RuntimePersistenceService


class PreparedState(TypedDict):
    summary: str
    items: list[str]


class RuntimeGraphState(TypedDict, total=False):
    objective: str
    input_payload: dict[str, Any]
    trace_id: str
    step_log: list[str]
    prepared: PreparedState
    structured_output: dict[str, Any]
    artifacts: list[GraphArtifact]


class RuntimeGraphService:
    def __init__(
        self,
        checkpoint_store: RuntimePersistenceService | None = None,
        *,
        database_url: str | None = None,
    ) -> None:
        self._graphs = {kind: self._build_graph(kind) for kind in GraphKind}
        self._checkpoint_store = checkpoint_store
        self._langgraph = LangGraphCheckpointerFactory(database_url)

    def execute(self, request: GraphExecutionRequest) -> GraphExecutionResult:
        graph_kind = GraphKind(request.graph_kind)
        resolved_request = self._resolve_checkpoint_request(request)

        with self._langgraph.checkpointer() as checkpointer:
            compiled_graph = self._compile_graph(graph_kind, checkpointer)
            if resolved_request.checkpoint is not None:
                self._langgraph.validate_checkpoint(resolved_request.checkpoint)
                return self._resume_from_langgraph_checkpoint(
                    compiled_graph,
                    graph_kind,
                    resolved_request,
                )
            return self._start_graph_execution(compiled_graph, graph_kind, resolved_request)

    def _resolve_checkpoint_request(self, request: GraphExecutionRequest) -> GraphExecutionRequest:
        if request.checkpoint is not None:
            return request
        if request.checkpoint_id is None or self._checkpoint_store is None:
            return request
        checkpoint = self._checkpoint_store.load_graph_checkpoint(request.checkpoint_id)
        self._checkpoint_store.mark_graph_checkpoint_resumed(request.checkpoint_id)
        return request.model_copy(update={"checkpoint": checkpoint})

    def _compile_graph(self, graph_kind: GraphKind, checkpointer: Any):
        return self._graphs[graph_kind].compile(checkpointer=checkpointer)

    def _start_graph_execution(
        self,
        compiled_graph: Any,
        graph_kind: GraphKind,
        request: GraphExecutionRequest,
    ) -> GraphExecutionResult:
        initial_state: RuntimeGraphState = {
            "objective": request.objective,
            "input_payload": dict(request.input_payload),
            "trace_id": request.correlation.trace_id,
            "step_log": [],
        }
        config = {"configurable": {"thread_id": self._thread_id(graph_kind, request)}}

        if request.interrupt_before_finalize:
            compiled_graph.invoke(
                initial_state,
                config=config,
                interrupt_before=["finalize"],
                durability="sync",
            )
            snapshot = compiled_graph.get_state(config)
            checkpoint = self._create_checkpoint_record(
                graph_kind=graph_kind,
                request=request,
                snapshot=snapshot,
            )
            values = dict(snapshot.values)
            prepared_payload = values.get("prepared")
            step_log = list(values.get("step_log", []))
            if not isinstance(prepared_payload, dict):
                raise ValueError("runtime graph prepare step returned an incomplete state")
            return GraphExecutionResult(
                graph_kind=graph_kind,
                status=GraphExecutionStatus.INTERRUPTED,
                trace_id=request.correlation.trace_id,
                structured_output={"prepared": prepared_payload},
                checkpoint=checkpoint,
                step_log=step_log,
            )

        final_state = compiled_graph.invoke(initial_state, config=config, durability="sync")
        return self._completed_result(
            graph_kind=graph_kind,
            trace_id=request.correlation.trace_id,
            state=final_state,
        )

    def _resume_from_langgraph_checkpoint(
        self,
        compiled_graph: Any,
        graph_kind: GraphKind,
        request: GraphExecutionRequest,
    ) -> GraphExecutionResult:
        checkpoint = dict(request.checkpoint or {})
        configurable = self._langgraph.config_from_checkpoint(checkpoint)
        final_state = compiled_graph.invoke(
            None,
            config={"configurable": configurable},
            durability="sync",
        )
        return self._completed_result(
            graph_kind=graph_kind,
            trace_id=request.correlation.trace_id,
            state=final_state,
        )

    def _create_checkpoint_record(
        self,
        *,
        graph_kind: GraphKind,
        request: GraphExecutionRequest,
        snapshot: Any,
    ) -> dict[str, Any]:
        configurable = dict(snapshot.config.get("configurable", {}))
        stored_checkpoint_id = None
        if self._checkpoint_store is not None:
            stored_checkpoint_id = self._checkpoint_store.save_graph_checkpoint(
                workflow_run_id=request.correlation.workflow_run_id,
                task_id=request.correlation.task_id,
                attempt_id=request.correlation.attempt_id,
                trace_id=request.correlation.trace_id,
                graph_kind=graph_kind.value,
                state=self._langgraph.checkpoint_payload(
                    configurable=configurable,
                    fallback_thread_id=self._thread_id(graph_kind, request),
                    stored_checkpoint_id=None,
                ),
            )
        return self._langgraph.checkpoint_payload(
            configurable=configurable,
            fallback_thread_id=self._thread_id(graph_kind, request),
            stored_checkpoint_id=stored_checkpoint_id,
        )

    def _completed_result(
        self,
        *,
        graph_kind: GraphKind,
        trace_id: str,
        state: dict[str, Any],
    ) -> GraphExecutionResult:
        structured_output = state.get("structured_output")
        artifacts = state.get("artifacts")
        step_log = state.get("step_log")
        if structured_output is None or artifacts is None or step_log is None:
            raise ValueError("runtime graph finalize step returned an incomplete state")
        return GraphExecutionResult(
            graph_kind=graph_kind,
            status=GraphExecutionStatus.COMPLETED,
            trace_id=trace_id,
            structured_output=structured_output,
            artifacts=artifacts,
            step_log=step_log,
        )

    def _thread_id(self, graph_kind: GraphKind, request: GraphExecutionRequest) -> str:
        parts = [
            request.correlation.workflow_run_id,
            request.correlation.task_id or graph_kind.value,
            request.correlation.attempt_id or "attempt",
            graph_kind.value,
        ]
        return "::".join(parts)

    def _build_graph(self, graph_kind: GraphKind) -> StateGraph:
        def prepare_node(state: RuntimeGraphState) -> RuntimeGraphState:
            return self._prepare_state(graph_kind, state)

        def finalize_node(state: RuntimeGraphState) -> RuntimeGraphState:
            return self._finalize_state(graph_kind, state)

        graph = StateGraph(RuntimeGraphState)
        graph.add_node("prepare", prepare_node)
        graph.add_node("finalize", finalize_node)
        graph.set_entry_point("prepare")
        graph.add_edge("prepare", "finalize")
        graph.set_finish_point("finalize")
        return graph

    def _prepare_state(self, graph_kind: GraphKind, state: RuntimeGraphState) -> RuntimeGraphState:
        objective = state.get("objective")
        if objective is None:
            raise ValueError("runtime graph state is missing objective")
        input_payload = dict(state.get("input_payload", {}))
        step_log = list(state.get("step_log", []))
        step_log.append(f"{graph_kind.value}:prepare")

        if graph_kind == GraphKind.AUDITOR:
            targets = input_payload.get("targets") or [objective]
            prepared: PreparedState = {
                "summary": f"Audited {len(targets)} target(s)",
                "items": [f"Inspect {target}" for target in targets],
            }
        elif graph_kind == GraphKind.PLANNER:
            milestones = input_payload.get("milestones") or [
                "Clarify outcomes",
                "Sequence execution lanes",
                "Define verification",
            ]
            prepared = {"summary": "Prepared execution plan", "items": milestones}
        elif graph_kind == GraphKind.DECOMPOSITION:
            work_items = input_payload.get("work_items") or [objective, f"Verify {objective}"]
            prepared = {
                "summary": f"Decomposed into {len(work_items)} work item(s)",
                "items": work_items,
            }
        else:
            checks = input_payload.get("checks") or ["output quality", "verification coverage"]
            prepared = {
                "summary": f"Prepared review over {len(checks)} check(s)",
                "items": checks,
            }

        return {**state, "prepared": prepared, "step_log": step_log}

    def _finalize_state(self, graph_kind: GraphKind, state: RuntimeGraphState) -> RuntimeGraphState:
        prepared = state.get("prepared")
        if prepared is None:
            raise ValueError("runtime graph state is missing prepared payload")
        step_log = list(state.get("step_log", []))
        step_log.append(f"{graph_kind.value}:finalize")
        objective = str(state.get("objective", prepared["summary"]))

        if graph_kind == GraphKind.AUDITOR:
            structured_output = {
                "summary": prepared["summary"],
                "findings": [
                    {"id": f"finding-{index + 1}", "detail": item}
                    for index, item in enumerate(prepared["items"])
                ],
            }
            artifact_type = "audit.report"
        elif graph_kind == GraphKind.PLANNER:
            structured_output = {
                "summary": prepared["summary"],
                "plan_steps": [
                    {"id": f"step-{index + 1}", "title": item}
                    for index, item in enumerate(prepared["items"])
                ],
            }
            artifact_type = "plan.bundle"
        elif graph_kind == GraphKind.DECOMPOSITION:
            structured_output = {
                "summary": prepared["summary"],
                "tasks": [
                    {"task_id": f"task-{index + 1}", "title": item}
                    for index, item in enumerate(prepared["items"])
                ],
            }
            artifact_type = "task.bundle"
        else:
            checks = list(prepared["items"])
            structured_output = {
                "summary": prepared["summary"],
                "verdict": "approved" if len(checks) >= 2 else "needs_changes",
                "checks": checks,
            }
            artifact_type = "review.report"

        return {
            **state,
            "structured_output": structured_output,
            "artifacts": [
                GraphArtifact(
                    artifact_id=str(uuid4()),
                    artifact_type=artifact_type,
                    title=f"{graph_kind.value} output",
                    metadata={"objective": objective},
                )
            ],
            "step_log": step_log,
        }
