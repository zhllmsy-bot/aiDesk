from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.e2e


def test_runtime_bootstrap_to_read_models_cross_module(e2e_client: TestClient) -> None:
    bootstrap = e2e_client.post(
        "/runtime/dev/bootstrap?workflow_name=project.planning&include_retry=true&include_interrupt=true"
    )
    assert bootstrap.status_code == 202
    workflow_run_id = bootstrap.json()["workflow_run_id"]

    timeline = e2e_client.get(f"/runtime/runs/{workflow_run_id}/timeline")
    assert timeline.status_code == 200
    timeline_data = timeline.json()
    assert len(timeline_data["entries"]) >= 3
    event_types = {entry["event_type"] for entry in timeline_data["entries"]}
    assert "workflow.started" in event_types
    assert "task.completed" in event_types
    assert "workflow.retrying" in event_types

    graph = e2e_client.get(f"/runtime/runs/{workflow_run_id}/graph")
    assert graph.status_code == 200
    graph_data = graph.json()
    assert any(node["task_id"] == "task-1" for node in graph_data["nodes"])

    attempts = e2e_client.get("/runtime/tasks/task-1/attempts")
    assert attempts.status_code == 200
    attempts_data = attempts.json()
    assert any(a["task_id"] == "task-1" for a in attempts_data["attempts"])

    workers = e2e_client.get("/runtime/workers/health")
    assert workers.status_code == 200
    assert any(w["worker_id"] == "e2e-worker" for w in workers.json())


def test_runtime_task_execution_full_lifecycle(e2e_client: TestClient) -> None:
    bootstrap = e2e_client.post("/runtime/dev/bootstrap?workflow_name=task.execution")
    assert bootstrap.status_code == 202
    workflow_run_id = bootstrap.json()["workflow_run_id"]

    timeline = e2e_client.get(f"/runtime/runs/{workflow_run_id}/timeline")
    assert timeline.status_code == 200
    entries = timeline.json()["entries"]
    assert len(entries) >= 2
    event_types = [entry["event_type"] for entry in entries]
    assert "workflow.started" in event_types
    assert "task.completed" in event_types

    graph = e2e_client.get(f"/runtime/runs/{workflow_run_id}/graph")
    assert graph.status_code == 200
    nodes = graph.json()["nodes"]
    assert len(nodes) >= 1
    task_node = nodes[0]
    assert task_node["status"] == "completed"

    attempts = e2e_client.get(f"/runtime/tasks/{task_node['task_id']}/attempts")
    assert attempts.status_code == 200
    assert len(attempts.json()["attempts"]) >= 1
