from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.context.service import ContextBuilderInput
from api.executors.contracts import (
    ContextLevel,
    MemoryType,
    MemoryWriteCandidate,
)
from tests.e2e.conftest import register_user

pytestmark = pytest.mark.e2e


def _create_project(client: TestClient, headers: dict[str, str], root_path: str) -> str:
    response = client.post(
        "/projects",
        json={
            "name": f"E2E Memory Project {root_path[-8:]}",
            "root_path": root_path,
            "description": "E2E test project for memory",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_memory_write_and_recall(
    e2e_client: TestClient,
    project_root: Path,
) -> None:
    headers = register_user(e2e_client, "e2e-memory@example.com")
    project_id = _create_project(e2e_client, headers, str(project_root))

    write_response = e2e_client.post(
        "/memory/writes",
        json=MemoryWriteCandidate(
            project_id=project_id,
            iteration_id="iter-memory-e2e",
            memory_type=MemoryType.PROJECT_FACT,
            external_ref="doc://project-memory-e2e/facts/api-structure",
            summary="API follows modular architecture with FastAPI routers",
            content_hash="hash-e2e-fact-1",
            quality_score=0.92,
        ).model_dump(mode="json"),
        headers=headers,
    )
    assert write_response.status_code == 201
    write_data = write_response.json()
    assert len(write_data["items"]) == 1
    assert (
        write_data["items"][0]["summary"] == "API follows modular architecture with FastAPI routers"
    )

    write_response_2 = e2e_client.post(
        "/memory/writes",
        json=MemoryWriteCandidate(
            project_id=project_id,
            iteration_id="iter-memory-e2e",
            memory_type=MemoryType.LESSON,
            external_ref="doc://project-memory-e2e/lessons/retry-pattern",
            summary="Retryable failures should use exponential backoff",
            content_hash="hash-e2e-lesson-1",
            quality_score=0.85,
        ).model_dump(mode="json"),
        headers=headers,
    )
    assert write_response_2.status_code == 201
    assert len(write_response_2.json()["items"]) == 1

    recall_response = e2e_client.get(
        f"/memory/hits?project_id={project_id}&limit=10",
        headers=headers,
    )
    assert recall_response.status_code == 200
    recalled = recall_response.json()["items"]
    assert len(recalled) == 2
    summaries = {item["summary"] for item in recalled}
    assert "API follows modular architecture with FastAPI routers" in summaries
    assert "Retryable failures should use exponential backoff" in summaries


def test_memory_recall_to_context_build(
    e2e_client: TestClient,
    project_root: Path,
) -> None:
    headers = register_user(e2e_client, "e2e-ctx@example.com")
    project_id = _create_project(e2e_client, headers, str(project_root))

    e2e_client.post(
        "/memory/writes",
        json=MemoryWriteCandidate(
            project_id=project_id,
            iteration_id="iter-ctx-e2e",
            memory_type=MemoryType.PROJECT_FACT,
            external_ref="doc://project-ctx-e2e/facts/arch",
            summary="Context builder produces L0..L3 blocks",
            content_hash="hash-ctx-fact",
            quality_score=0.9,
        ).model_dump(mode="json"),
        headers=headers,
    )

    context_response = e2e_client.post(
        "/context/build",
        json=ContextBuilderInput(
            task_id="task-ctx-e2e",
            task_core="Test context assembly",
            project_facts=["Project uses FastAPI"],
            workflow_summary="Context test workflow",
            recent_attempts=[],
            memory_recall=["Context builder produces L0..L3 blocks"],
            security_summary="No special constraints",
            evidence_refs=[],
        ).model_dump(mode="json"),
        headers=headers,
    )
    assert context_response.status_code == 200
    context_data = context_response.json()
    assert context_data["task_id"] == "task-ctx-e2e"
    levels = [block["level"] for block in context_data["blocks"]]
    assert ContextLevel.L0 in levels
    assert ContextLevel.L3 in levels
    l3_blocks = [b for b in context_data["blocks"] if b["level"] == ContextLevel.L3]
    assert len(l3_blocks) >= 1
    assert any("Context builder produces L0..L3 blocks" in b["body"] for b in l3_blocks)


def test_memory_dedup_same_content_hash(
    e2e_client: TestClient,
    project_root: Path,
) -> None:
    headers = register_user(e2e_client, "e2e-dedup@example.com")
    project_id = _create_project(e2e_client, headers, str(project_root))

    candidate = MemoryWriteCandidate(
        project_id=project_id,
        iteration_id="iter-dedup-e2e",
        memory_type=MemoryType.LESSON,
        external_ref="doc://dedup/test",
        summary="Dedup test memory",
        content_hash="hash-dedup-e2e",
        quality_score=0.9,
    )

    first = e2e_client.post(
        "/memory/writes",
        json=candidate.model_dump(mode="json"),
        headers=headers,
    )
    assert first.status_code == 201
    assert len(first.json()["items"]) >= 1

    second = e2e_client.post(
        "/memory/writes",
        json=candidate.model_dump(mode="json"),
        headers=headers,
    )
    assert second.status_code == 201

    recall = e2e_client.get(
        f"/memory/hits?project_id={project_id}",
        headers=headers,
    )
    assert recall.status_code == 200
    items = recall.json()["items"]
    summaries = [item["summary"] for item in items]
    dedup_count = summaries.count("Dedup test memory")
    assert dedup_count == 1, f"Expected exactly 1 'Dedup test memory' in recall, got {dedup_count}"
