from __future__ import annotations

import secrets


def resolve_traceparent(headers: dict[str, str], trace_id: str) -> str:
    incoming = headers.get("traceparent")
    if incoming and len(incoming.split("-")) == 4:
        return incoming
    normalized_trace_id = trace_id.replace("-", "")[:32].ljust(32, "0")
    span_id = secrets.token_hex(8)
    return f"00-{normalized_trace_id}-{span_id}-01"
