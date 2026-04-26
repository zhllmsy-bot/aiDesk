from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth.router import router as auth_router
from api.config import Settings, get_settings
from api.context.router import router as context_router
from api.control_plane.router import router as control_plane_router
from api.database import create_session_factory
from api.executors.contracts import contract_snapshot
from api.executors.dependencies import configure_execution_container
from api.executors.router import router as executors_router
from api.health.router import router as health_router
from api.memory.router import router as memory_router
from api.models import register_models
from api.notifications.router import router as notifications_router
from api.observability.logging import configure_root_logging
from api.observability.middleware import CorrelationMiddleware
from api.observability.otel import configure_observability
from api.observability.router import router as observability_router
from api.review.router import router as review_router
from api.workflows.dependencies import configure_runtime_container
from api.workflows.router import router as runtime_router


def root_endpoint() -> dict[str, str]:
    return {"service": "api", "status": "ok"}


def execution_contract_endpoint() -> dict[str, object]:
    return contract_snapshot()


def create_app(
    settings: Settings | None = None,
    *,
    include_runtime_surface: bool = True,
    include_execution_surface: bool = True,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_root_logging()
    register_models()
    session_factory = create_session_factory(resolved_settings.database_url)
    runtime_container = configure_runtime_container(resolved_settings)
    execution_container = (
        configure_execution_container(resolved_settings)
        if include_runtime_surface or include_execution_surface
        else None
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.session_factory = session_factory
        app.state.settings = resolved_settings
        app.state.runtime_container = runtime_container
        if execution_container is not None:
            app.state.execution_container = execution_container
        try:
            yield
        finally:
            bind = session_factory.kw.get("bind")
            if bind is not None:
                bind.dispose()

    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.session_factory = session_factory
    app.state.settings = resolved_settings
    app.state.runtime_container = runtime_container
    if execution_container is not None:
        app.state.execution_container = execution_container

    app.state.observability = configure_observability(app, resolved_settings)
    app.add_middleware(CorrelationMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[resolved_settings.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_api_route("/", root_endpoint, methods=["GET"], tags=["root"])

    app.include_router(health_router)
    app.include_router(observability_router)
    app.include_router(auth_router)
    app.include_router(control_plane_router)
    if include_execution_surface:
        app.add_api_route(
            "/contracts/execution",
            execution_contract_endpoint,
            methods=["GET"],
            tags=["contracts"],
        )
        app.include_router(executors_router)
        app.include_router(context_router)
        app.include_router(memory_router)
        app.include_router(notifications_router)
        app.include_router(review_router)
    if include_runtime_surface:
        app.include_router(runtime_router)
    return app


app = create_app()
