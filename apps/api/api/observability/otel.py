from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

    from api.config import Settings


@dataclass(frozen=True, slots=True)
class ObservabilityInstrumentationStatus:
    enabled: bool
    otel: str
    logfire: str


def resolve_traceparent(headers: dict[str, str], trace_id: str) -> str:
    incoming = headers.get("traceparent")
    if incoming and len(incoming.split("-")) == 4:
        return incoming
    normalized_trace_id = trace_id.replace("-", "")[:32].ljust(32, "0")
    span_id = secrets.token_hex(8)
    return f"00-{normalized_trace_id}-{span_id}-01"


def configure_observability(
    app: FastAPI,
    settings: Settings,
) -> ObservabilityInstrumentationStatus:
    if not settings.otel_enabled and not settings.logfire_enabled:
        return ObservabilityInstrumentationStatus(
            enabled=False,
            otel="disabled",
            logfire="disabled",
        )

    otel_status = "disabled"
    if settings.otel_enabled:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(
            resource=Resource.create({"service.name": settings.otel_service_name})
        )
        if settings.otel_exporter_otlp_endpoint:
            provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint),
                )
            )
            otel_status = "otlp_http"
        else:
            otel_status = "local_provider"
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

    logfire_status = "disabled"
    if settings.logfire_enabled:
        import logfire

        logfire.configure(service_name=settings.otel_service_name, send_to_logfire=False)
        logfire.instrument_fastapi(app)
        logfire_status = "enabled"

    return ObservabilityInstrumentationStatus(
        enabled=settings.otel_enabled or settings.logfire_enabled,
        otel=otel_status,
        logfire=logfire_status,
    )
