from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from temporalio.client import Client

from api.database import get_db_session
from api.integrations.mem0 import check_mem0
from api.integrations.openhands import check_openhands
from api.integrations.openviking import check_openviking

router = APIRouter(prefix="/health", tags=["health"])


def _check_codex(settings: Any) -> dict[str, str]:
    if settings.codex_app_server_transport == "websocket" and settings.codex_app_server_url:
        try:
            url = settings.codex_app_server_url.replace("ws://", "http://").replace(
                "wss://", "https://"
            )
            base = url.split("/")[0] + "//" + url.split("/")[2]
            response = httpx.get(f"{base}/health", timeout=2.0)
            if response.status_code < 500:
                return {"status": "ok"}
            return {"status": "error", "reason": f"codex returned {response.status_code}"}
        except httpx.HTTPError as exc:
            return {"status": "error", "reason": f"codex unreachable: {exc}"}
        except Exception as exc:
            return {"status": "error", "reason": f"codex check failed: {exc}"}
    if settings.codex_app_server_transport == "stdio":
        from pathlib import Path

        command = Path(settings.codex_app_server_command)
        if command.exists():
            return {"status": "ok", "note": "stdio transport; binary exists"}
        return {
            "status": "error",
            "reason": (f"codex binary not found: {settings.codex_app_server_command}"),
        }
    return {"status": "not_configured", "reason": "no codex transport configured"}


def _check_openhands(settings: Any) -> dict[str, str]:
    return check_openhands(settings)


def _check_feishu(settings: Any) -> dict[str, str]:
    if settings.feishu_mcp_bridge_enabled:
        bridge_dir = settings.resolved_feishu_mcp_bridge_dir
        if not bridge_dir:
            return {"status": "error", "reason": "feishu mcp bridge enabled but dir is missing"}
        bridge_path = Path(bridge_dir).expanduser()
        if not bridge_path.exists():
            return {
                "status": "error",
                "reason": f"feishu mcp bridge dir not found: {bridge_path}",
            }
        env_file = settings.resolved_feishu_mcp_env_file
        if env_file:
            env_path = Path(env_file).expanduser()
            if not env_path.exists():
                return {
                    "status": "error",
                    "reason": f"feishu mcp env file not found: {env_path}",
                }
        return {"status": "ok", "mode": "mcp_bridge"}

    if not settings.feishu_notification_enabled:
        return {"status": "not_configured", "reason": "feishu notifications disabled"}
    if not settings.resolved_feishu_app_id or not settings.resolved_feishu_app_secret:
        return {"status": "error", "reason": "feishu enabled but app_id/app_secret missing"}
    try:
        __import__("lark_oapi")
    except ImportError:
        return {
            "status": "error",
            "reason": "lark-oapi is not installed; run dependency sync for apps/api",
        }
    return {"status": "ok"}

@router.get("/live")
def live() -> dict[str, str]:
    return {
        "service": "api",
        "status": "ok",
        "checked_at": datetime.now(UTC).isoformat(),
    }


_db_session_dep = Depends(get_db_session)


@router.get("/ready")
async def ready(
    request: Request,
    session: Session = _db_session_dep,
) -> dict[str, Any]:
    session.execute(text("SELECT 1"))
    settings = request.app.state.settings

    temporal_status = "ok"
    temporal_reason = ""
    try:
        client = await Client.connect(
            settings.temporal_address,
            namespace=settings.temporal_namespace,
            identity=f"{settings.runtime_worker_id}-healthcheck",
        )
        await client.service_client.check_health()
    except Exception as exc:
        temporal_status = "error"
        temporal_reason = str(exc)

    required: dict[str, Any] = {
        "database": {"status": "ok"},
        "temporal": {"status": temporal_status},
    }
    if temporal_reason:
        required["temporal"]["reason"] = temporal_reason
    if temporal_status == "ok":
        required["temporal"]["address"] = settings.temporal_address
        required["temporal"]["namespace"] = settings.temporal_namespace

    codex_result = await asyncio.to_thread(_check_codex, settings)
    openhands_result = await asyncio.to_thread(_check_openhands, settings)
    mem0_result = await asyncio.to_thread(check_mem0, settings)
    feishu_result = await asyncio.to_thread(_check_feishu, settings)
    openviking_result = await check_openviking(settings)

    optional: dict[str, Any] = {
        "codex": codex_result,
        "openhands": openhands_result,
        "mem0": mem0_result,
        "feishu": feishu_result,
        "openviking": openviking_result,
    }

    degraded_reasons: list[str] = []
    if temporal_status != "ok":
        degraded_reasons.append(f"temporal: {temporal_reason}")
    for name, result in optional.items():
        if result.get("status") == "error":
            degraded_reasons.append(f"{name}: {result.get('reason', 'unreachable')}")

    overall = "ready"
    if temporal_status != "ok" or any(r.get("status") == "error" for r in optional.values()):
        overall = "degraded"

    return {
        "service": "api",
        "status": overall,
        "required": required,
        "optional": optional,
        "degraded_reasons": degraded_reasons,
        "checked_at": datetime.now(UTC).isoformat(),
    }
