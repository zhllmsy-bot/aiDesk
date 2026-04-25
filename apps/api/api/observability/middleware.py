from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from api.observability.logging import clear_correlation, get_logger, set_correlation

logger = get_logger("middleware.correlation")


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_correlation(trace_id=trace_id, request_id=request_id)
        request.state.trace_id = trace_id
        request.state.request_id = request_id
        try:
            response = await call_next(request)
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            clear_correlation()
