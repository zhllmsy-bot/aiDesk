from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.auth.models import User
from api.control_plane.dependencies import get_current_user
from api.notifications.base import (
    NotificationDeliveryListResponse,
    NotificationDeliveryRecord,
    NotificationDeliveryStatusUpdateRequest,
)
from api.notifications.query import NotificationQueryService
from api.notifications.service import NotificationHistoryService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/deliveries", response_model=NotificationDeliveryListResponse)
def list_notification_deliveries(
    _: Annotated[User, Depends(get_current_user)],
    request: Request,
    workflow_run_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    source_channel: str | None = Query(default=None),
    delivery_channel: str | None = Query(default=None),
    delivery_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> NotificationDeliveryListResponse:
    query = NotificationQueryService(request.app.state.session_factory)
    items = query.list_deliveries(
        workflow_run_id=workflow_run_id,
        project_id=project_id,
        source_channel=source_channel,
        delivery_channel=delivery_channel,
        delivery_status=delivery_status,
        limit=limit,
    )
    return NotificationDeliveryListResponse(items=items)


@router.post("/deliveries/{receipt_id}/status", response_model=NotificationDeliveryRecord)
def update_notification_delivery_status(
    _: Annotated[User, Depends(get_current_user)],
    receipt_id: str,
    payload: NotificationDeliveryStatusUpdateRequest,
    request: Request,
) -> NotificationDeliveryRecord:
    history = NotificationHistoryService(request.app.state.session_factory)
    updated = history.update_delivery_status(
        receipt_id=receipt_id,
        delivery_status=payload.delivery_status,
        provider_message_id=payload.provider_message_id,
        metadata_patch=payload.metadata_patch,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="notification delivery not found")
    return updated
