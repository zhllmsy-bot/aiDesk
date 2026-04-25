from __future__ import annotations

# pyright: reportMissingImports=false
from api.config import Settings

try:
    from mem0 import MemoryClient
except ImportError:  # pragma: no cover - dependency is installed in runtime
    MemoryClient = None


def check_mem0(settings: Settings) -> dict[str, str]:
    if not settings.mem0_api_key:
        return {"status": "not_configured", "reason": "mem0_api_key not set"}
    if MemoryClient is None:
        return {"status": "error", "reason": "mem0 client dependency is not installed"}
    try:
        client = MemoryClient(
            api_key=settings.mem0_api_key,
            host=settings.mem0_api_url,
        )
        try:
            http_client = getattr(client, "client", None)
            if http_client is not None:
                http_client.close()
        except Exception:
            pass
        return {"status": "ok", "target": settings.mem0_api_url}
    except Exception as exc:
        return {"status": "error", "reason": f"mem0 unreachable: {exc}"}
