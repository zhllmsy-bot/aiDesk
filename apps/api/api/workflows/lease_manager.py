from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from api.runtime_contracts import ClaimStatus


@dataclass(frozen=True, slots=True)
class TaskClaim:
    claim_id: str
    task_id: str
    workflow_run_id: str
    attempt_id: str
    worker_id: str
    lease_timeout_seconds: int
    status: ClaimStatus
    claimed_at: str
    heartbeat_at: str
    expired_at: str | None = None
    reclaimed_at: str | None = None
    released_at: str | None = None


def _utcnow(now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)).astimezone(UTC)


class ClaimLeaseManager:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._claims: dict[str, TaskClaim] = {}
        self._active_by_task: dict[str, str] = {}

    def claim_task(
        self,
        *,
        task_id: str,
        workflow_run_id: str,
        attempt_id: str,
        worker_id: str,
        lease_timeout_seconds: int,
        now: datetime | None = None,
    ) -> TaskClaim:
        active_id = self._active_by_task.get(task_id)
        if active_id is not None and self._claims[active_id].status == ClaimStatus.ACTIVE:
            raise ValueError(f"Task {task_id} already has an active claim")
        timestamp = _utcnow(now).isoformat()
        claim = TaskClaim(
            claim_id=str(uuid4()),
            task_id=task_id,
            workflow_run_id=workflow_run_id,
            attempt_id=attempt_id,
            worker_id=worker_id,
            lease_timeout_seconds=lease_timeout_seconds,
            status=ClaimStatus.ACTIVE,
            claimed_at=timestamp,
            heartbeat_at=timestamp,
        )
        self._claims[claim.claim_id] = claim
        self._active_by_task[task_id] = claim.claim_id
        return claim

    def heartbeat(self, claim_id: str, now: datetime | None = None) -> TaskClaim:
        claim = self._claims[claim_id]
        if claim.status != ClaimStatus.ACTIVE:
            raise ValueError(f"Cannot heartbeat claim {claim_id} in status {claim.status.value}")
        updated = replace(claim, heartbeat_at=_utcnow(now).isoformat())
        self._claims[claim_id] = updated
        return updated

    def release(self, claim_id: str, now: datetime | None = None) -> TaskClaim:
        claim = self._claims[claim_id]
        updated = replace(
            claim,
            status=ClaimStatus.RELEASED,
            released_at=_utcnow(now).isoformat(),
        )
        self._claims[claim_id] = updated
        self._active_by_task.pop(updated.task_id, None)
        return updated

    def reclaim_stale_claims(
        self,
        *,
        workflow_run_id: str | None = None,
        force_claim_ids: list[str] | None = None,
        now: datetime | None = None,
    ) -> list[TaskClaim]:
        force_set = set(force_claim_ids or [])
        current_time = _utcnow(now)
        reclaimed: list[TaskClaim] = []
        for claim in list(self._claims.values()):
            if workflow_run_id is not None and claim.workflow_run_id != workflow_run_id:
                continue
            if claim.status != ClaimStatus.ACTIVE:
                continue
            stale = claim.claim_id in force_set
            if not stale:
                heartbeat_at = datetime.fromisoformat(claim.heartbeat_at)
                stale = current_time >= heartbeat_at + timedelta(
                    seconds=claim.lease_timeout_seconds
                )
            if not stale:
                continue
            reclaimed_claim = replace(
                claim,
                status=ClaimStatus.RECLAIMED,
                expired_at=current_time.isoformat(),
                reclaimed_at=current_time.isoformat(),
            )
            self._claims[claim.claim_id] = reclaimed_claim
            self._active_by_task.pop(claim.task_id, None)
            reclaimed.append(reclaimed_claim)
        return reclaimed

    def list_claims(self) -> list[TaskClaim]:
        return list(self._claims.values())
