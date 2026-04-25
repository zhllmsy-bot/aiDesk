from __future__ import annotations

from api.workflows.definitions.base import TaskDependencyError, resolve_task_execution_order
from api.workflows.types import WorkflowTaskSpec


def test_resolve_task_execution_order_respects_depends_on() -> None:
    tasks = [
        WorkflowTaskSpec(task_id="task-c", title="C", graph_kind="planner", depends_on=["task-b"]),
        WorkflowTaskSpec(task_id="task-a", title="A", graph_kind="planner"),
        WorkflowTaskSpec(task_id="task-b", title="B", graph_kind="planner", depends_on=["task-a"]),
    ]
    order = resolve_task_execution_order(tasks)
    assert order.index("task-a") < order.index("task-b")
    assert order.index("task-b") < order.index("task-c")


def test_resolve_task_execution_order_rejects_unknown_dependency() -> None:
    tasks = [
        WorkflowTaskSpec(task_id="task-a", title="A", graph_kind="planner", depends_on=["missing"]),
    ]
    try:
        resolve_task_execution_order(tasks)
    except TaskDependencyError as exc:
        assert "unknown task" in str(exc)
    else:
        raise AssertionError("Expected TaskDependencyError for unknown dependency")


def test_resolve_task_execution_order_rejects_cycle() -> None:
    tasks = [
        WorkflowTaskSpec(task_id="task-a", title="A", graph_kind="planner", depends_on=["task-b"]),
        WorkflowTaskSpec(task_id="task-b", title="B", graph_kind="planner", depends_on=["task-a"]),
    ]
    try:
        resolve_task_execution_order(tasks)
    except TaskDependencyError as exc:
        assert "cycle" in str(exc)
    else:
        raise AssertionError("Expected TaskDependencyError for cycle")
