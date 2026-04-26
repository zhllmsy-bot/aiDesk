from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI

    from api.config import Settings


@dataclass(frozen=True, slots=True)
class ObservabilityInstrumentationStatus:
    enabled: bool
    otel: str
    logfire: str


_httpx_instrumented = False


def resolve_traceparent(headers: dict[str, str], trace_id: str) -> str:
    incoming = headers.get("traceparent")
    if incoming and len(incoming.split("-")) == 4:
        return incoming
    normalized_trace_id = trace_id.replace("-", "")[:32].ljust(32, "0")
    span_id = secrets.token_hex(8)
    return f"00-{normalized_trace_id}-{span_id}-01"


def _configure_tracing(settings: Settings) -> tuple[Any | None, str]:
    if not settings.otel_enabled:
        return None, "disabled"

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    existing_provider = trace.get_tracer_provider()
    if existing_provider.__class__.__name__ == "ProxyTracerProvider":
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
        return provider, otel_status

    return existing_provider, "reused_provider"


def _configure_logfire(settings: Settings) -> str:
    if not settings.logfire_enabled:
        return "disabled"

    import logfire

    logfire.configure(service_name=settings.otel_service_name, send_to_logfire=False)
    return "enabled"


def _instrument_httpx() -> None:
    global _httpx_instrumented
    if _httpx_instrumented:
        return

    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    HTTPXClientInstrumentor().instrument()
    _httpx_instrumented = True


def configure_observability(app: FastAPI, settings: Settings) -> ObservabilityInstrumentationStatus:
    if not settings.otel_enabled and not settings.logfire_enabled:
        return ObservabilityInstrumentationStatus(
            enabled=False,
            otel="disabled",
            logfire="disabled",
        )

    provider, otel_status = _configure_tracing(settings)
    if provider is not None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        _instrument_httpx()
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

    logfire_status = _configure_logfire(settings)
    if logfire_status == "enabled":
        import logfire

        logfire.instrument_fastapi(app)

    return ObservabilityInstrumentationStatus(
        enabled=settings.otel_enabled or settings.logfire_enabled,
        otel=otel_status,
        logfire=logfire_status,
    )


def configure_worker_observability(settings: Settings) -> ObservabilityInstrumentationStatus:
    if not settings.otel_enabled and not settings.logfire_enabled:
        return ObservabilityInstrumentationStatus(
            enabled=False,
            otel="disabled",
            logfire="disabled",
        )

    provider, otel_status = _configure_tracing(settings)
    if provider is not None:
        _instrument_httpx()

    return ObservabilityInstrumentationStatus(
        enabled=settings.otel_enabled or settings.logfire_enabled,
        otel=otel_status,
        logfire=_configure_logfire(settings),
    )
