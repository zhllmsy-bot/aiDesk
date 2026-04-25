from __future__ import annotations

import asyncio
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy.orm import sessionmaker

from api.control_plane.models import Project
from api.database import Base
from api.models import register_models


def initialize_database(session_factory: sessionmaker) -> None:
    register_models()
    engine = session_factory.kw["bind"]
    assert engine is not None
    Base.metadata.create_all(engine)


def seed_project(
    session_factory: sessionmaker,
    *,
    project_id: str,
    root_path: Path,
    name: str = "Temporal Harness Project",
    slug: str = "temporal-harness-project",
) -> None:
    with session_factory() as session:
        session.add(
            Project(
                id=project_id,
                name=name,
                slug=slug,
                root_path=str(root_path),
                default_branch="main",
            )
        )
        session.commit()


async def wait_for_timeline_event(
    client: AsyncClient,
    workflow_run_id: str,
    event_type: str,
    *,
    timeout_seconds: float = 5.0,
    poll_interval_seconds: float = 0.05,
) -> list[dict[str, object]]:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get(f"/runtime/runs/{workflow_run_id}/timeline")
        response.raise_for_status()
        entries = response.json()["entries"]
        if any(entry["event_type"] == event_type for entry in entries):
            return entries
        await asyncio.sleep(poll_interval_seconds)
    raise AssertionError(
        f"Timed out waiting for {event_type} on workflow run {workflow_run_id}"
    )
