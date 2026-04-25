from __future__ import annotations

import httpx

from api.config import Settings


async def check_openviking(settings: Settings) -> dict[str, str]:
    if not settings.openviking_mcp_url:
        return {"status": "not_configured", "reason": "openviking_mcp_url not set"}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(settings.openviking_mcp_url)
            if response.status_code < 500:
                return {"status": "ok"}
            return {"status": "error", "reason": f"openviking returned {response.status_code}"}
    except httpx.HTTPError as exc:
        return {"status": "error", "reason": f"openviking unreachable: {exc}"}
    except Exception as exc:
        return {"status": "error", "reason": f"openviking check failed: {exc}"}
