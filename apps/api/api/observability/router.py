from __future__ import annotations

from fastapi import APIRouter, Query, Request

from api.notifications.query import NotificationQueryService
from api.observability.evals import run_runtime_regression_suite
from api.observability.metrics import get_metrics

router = APIRouter(prefix="/observability", tags=["observability"])


def _empty_runtime_sla(window_hours: int) -> dict[str, object]:
    return {
        "window_hours": window_hours,
        "scope": {"project_id": None, "iteration_id": None},
        "run_count": 0,
        "event_count": 0,
        "retry_recovery": {
            "count": 0,
            "avg_seconds": None,
            "p50_seconds": None,
            "p95_seconds": None,
        },
        "approval_resolution": {
            "count": 0,
            "avg_seconds": None,
            "p50_seconds": None,
            "p95_seconds": None,
        },
        "failure_recovery": {
            "count": 0,
            "avg_seconds": None,
            "p50_seconds": None,
            "p95_seconds": None,
        },
        "notifications": {"total": 0, "delivered": 0, "failed": 0, "channels": []},
        "trend": {"bucket_minutes": 60, "points": []},
    }


@router.get("/metrics")
def metrics(request: Request) -> dict[str, object]:
    payload = get_metrics().snapshot()
    runtime_container = getattr(request.app.state, "runtime_container", None)
    if runtime_container is None:
        return payload
    try:
        payload["runtime_sla"] = runtime_container.persistence.runtime_sla_snapshot(
            window_hours=24 * 7
        )
    except Exception:
        payload["runtime_sla"] = _empty_runtime_sla(24 * 7)
    try:
        notifications = NotificationQueryService(request.app.state.session_factory)
        payload["notification_deliveries"] = [
            item.model_dump(mode="json") for item in notifications.list_deliveries(limit=20)
        ]
    except Exception:
        payload["notification_deliveries"] = []
    return payload


@router.get("/runtime-sla")
def runtime_sla(
    request: Request,
    window_hours: int = Query(default=24 * 7, ge=1, le=24 * 90),
    project_id: str | None = Query(default=None),
    iteration_id: str | None = Query(default=None),
    bucket_minutes: int = Query(default=60, ge=5, le=24 * 60),
) -> dict[str, object]:
    runtime_container = getattr(request.app.state, "runtime_container", None)
    if runtime_container is None:
        payload = _empty_runtime_sla(window_hours)
        payload["scope"] = {"project_id": project_id, "iteration_id": iteration_id}
        payload["trend"] = {"bucket_minutes": bucket_minutes, "points": []}
        return payload
    try:
        return runtime_container.persistence.runtime_sla_snapshot(
            window_hours=window_hours,
            project_id=project_id,
            iteration_id=iteration_id,
            bucket_minutes=bucket_minutes,
        )
    except Exception:
        payload = _empty_runtime_sla(window_hours)
        payload["scope"] = {"project_id": project_id, "iteration_id": iteration_id}
        payload["trend"] = {"bucket_minutes": bucket_minutes, "points": []}
        return payload


@router.get("/evals/runtime-regression")
def runtime_regression() -> dict[str, object]:
    return run_runtime_regression_suite().model_dump(mode="json")
