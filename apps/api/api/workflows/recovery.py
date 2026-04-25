from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from api.workflows.dependencies import get_standalone_runtime_container


class RecoveryDecision(StrEnum):
    RETRY = "retry"
    FAIL = "fail"
    REQUEUE = "requeue"


@dataclass(slots=True)
class RecoveryResult:
    claim_id: str
    task_id: str
    workflow_run_id: str
    decision: RecoveryDecision
    detail: str


def scan_stale_claims() -> list[dict[str, Any]]:
    container = get_standalone_runtime_container()
    stale = container.persistence.scan_all_stale_claims()
    return [
        {
            "claim_id": claim.claim_id,
            "task_id": claim.task_id,
            "workflow_run_id": claim.workflow_run_id,
            "attempt_id": claim.attempt_id,
            "worker_id": claim.worker_id,
            "heartbeat_at": claim.heartbeat_at,
            "lease_timeout_seconds": claim.lease_timeout_seconds,
        }
        for claim in stale
    ]


def recover_stale_claims() -> list[RecoveryResult]:
    container = get_standalone_runtime_container()
    stale = container.persistence.scan_all_stale_claims()
    results: list[RecoveryResult] = []
    for claim in stale:
        reclaimed = container.persistence.reclaim_stale_claims(
            workflow_run_id=claim.workflow_run_id,
            force_claim_ids=[claim.claim_id],
        )
        if not reclaimed:
            continue
        results.append(
            RecoveryResult(
                claim_id=claim.claim_id,
                task_id=claim.task_id,
                workflow_run_id=claim.workflow_run_id,
                decision=RecoveryDecision.REQUEUE,
                detail=f"Claim {claim.claim_id} reclaimed, task requeued",
            )
        )
    return results
