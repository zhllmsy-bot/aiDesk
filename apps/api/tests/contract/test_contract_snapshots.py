from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.app import create_app
from api.config import CONTRACTS_DIR, RUNTIME_CONTRACTS_DIR
from api.executors.contracts import EXECUTION_SCHEMA_VERSION, contract_snapshot
from api.generated_contracts.openapi_models import WorkflowRequest
from api.runtime_contracts import (
    RUNTIME_SCHEMA_VERSION,
    ApprovalStatus,
    ClaimStatus,
    EventType,
    GraphExecutionStatus,
    GraphKind,
    TaskStatus,
    WorkerHealthStatus,
    WorkflowName,
    WorkflowRunStatus,
)
from tests.helpers import build_test_settings

pytestmark = pytest.mark.contract

CONTRACTS_SNAPSHOT_DIR = Path(__file__).resolve().parents[1] / "contracts_snapshots"

_SNAPSHOT_MISSING_MSG = (
    "{} snapshot did not exist; created initial snapshot. Re-run to verify stability."
)


def _assert_json_snapshot(snapshot_path: Path, current: object, label: str) -> None:
    current_json = json.dumps(current, indent=2, sort_keys=True) + "\n"
    if not snapshot_path.exists():
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(current_json, encoding="utf-8")
        pytest.fail(_SNAPSHOT_MISSING_MSG.format(label))

    expected = snapshot_path.read_text(encoding="utf-8")
    assert json.loads(expected) == current, f"{label} snapshot mismatch. Inspect {snapshot_path}"


def test_execution_contract_snapshot_matches() -> None:
    snapshot_path = CONTRACTS_SNAPSHOT_DIR / "execution-contract.json"
    current = contract_snapshot()
    _assert_json_snapshot(snapshot_path, current, "Execution contract")


def test_execution_contract_schema_version_stable() -> None:
    assert EXECUTION_SCHEMA_VERSION == "2026-04-19.execution.v1"


def test_runtime_contract_snapshot_matches() -> None:
    snapshot_path = CONTRACTS_SNAPSHOT_DIR / "runtime-contract.json"
    current = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "task_queue": "ai-desk.runtime",
        "workflow_names": [name.value for name in WorkflowName],
        "workflow_run_statuses": [s.value for s in WorkflowRunStatus],
        "task_statuses": [s.value for s in TaskStatus],
        "approval_statuses": [s.value for s in ApprovalStatus],
        "claim_statuses": [s.value for s in ClaimStatus],
        "graph_kinds": [k.value for k in GraphKind],
        "graph_execution_statuses": [s.value for s in GraphExecutionStatus],
        "worker_health_statuses": [s.value for s in WorkerHealthStatus],
        "event_types": [e.value for e in EventType],
    }
    _assert_json_snapshot(snapshot_path, current, "Runtime contract")


def test_runtime_contract_schema_version_stable() -> None:
    assert RUNTIME_SCHEMA_VERSION == "2026-04-19.runtime.v1"


def test_runtime_contract_matches_committed_artifact() -> None:
    committed_path = RUNTIME_CONTRACTS_DIR / "runtime-contract.json"
    if not committed_path.exists():
        pytest.skip("No committed runtime-contract.json in packages/contracts/runtime/")

    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    current = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "task_queue": "ai-desk.runtime",
        "workflow_names": [name.value for name in WorkflowName],
        "workflow_run_statuses": [s.value for s in WorkflowRunStatus],
        "task_statuses": [s.value for s in TaskStatus],
        "approval_statuses": [s.value for s in ApprovalStatus],
        "claim_statuses": [s.value for s in ClaimStatus],
        "graph_kinds": [k.value for k in GraphKind],
        "graph_execution_statuses": [s.value for s in GraphExecutionStatus],
        "worker_health_statuses": [s.value for s in WorkerHealthStatus],
        "event_types": [e.value for e in EventType],
    }

    assert committed["schema_version"] == current["schema_version"]
    assert set(committed["workflow_names"]) == set(current["workflow_names"])
    assert set(committed["event_types"]) == set(current["event_types"])
    assert set(committed["task_statuses"]) == set(current["task_statuses"])


def test_openapi_snapshot_matches_full_surface() -> None:
    snapshot_path = CONTRACTS_SNAPSHOT_DIR / "openapi-full.json"
    app = create_app(
        build_test_settings(),
        include_runtime_surface=True,
        include_execution_surface=True,
    )
    _assert_json_snapshot(snapshot_path, app.openapi(), "Full OpenAPI")


def test_openapi_control_plane_snapshot_matches() -> None:
    snapshot_path = CONTRACTS_DIR / "openapi" / "control-plane.openapi.json"
    generated = create_app(
        build_test_settings(),
        include_runtime_surface=False,
        include_execution_surface=False,
    ).openapi()
    assert json.loads(snapshot_path.read_text(encoding="utf-8")) == generated


def test_openapi_python_models_are_generated_from_contract() -> None:
    assert WorkflowRequest.model_fields["workflow_run_id"].is_required()


def test_review_api_contract_models_stable() -> None:
    from api.executors.contracts import (
        ApprovalDetailView,
        ApprovalListResponse,
        ApprovalSummaryView,
        ArtifactListResponse,
        ArtifactView,
        AttemptListResponse,
        EvidenceSummaryView,
        ExecutorAttemptView,
    )

    snapshot_path = CONTRACTS_SNAPSHOT_DIR / "review-api-contract.json"
    models = {
        "ApprovalSummaryView": ApprovalSummaryView.model_json_schema(),
        "ApprovalDetailView": ApprovalDetailView.model_json_schema(),
        "ApprovalListResponse": ApprovalListResponse.model_json_schema(),
        "ArtifactView": ArtifactView.model_json_schema(),
        "ArtifactListResponse": ArtifactListResponse.model_json_schema(),
        "ExecutorAttemptView": ExecutorAttemptView.model_json_schema(),
        "AttemptListResponse": AttemptListResponse.model_json_schema(),
        "EvidenceSummaryView": EvidenceSummaryView.model_json_schema(),
    }
    current = {
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "models": models,
    }
    _assert_json_snapshot(snapshot_path, current, "Review API contract")
