from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from tests.helpers import build_test_settings, run_migrations


@pytest.fixture()
def e2e_client(tmp_path: Path) -> Iterator[TestClient]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'e2e.db'}"
    run_migrations(database_url)
    settings = build_test_settings(
        database_url=database_url,
        runtime_worker_id="e2e-worker",
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        test_client.app_state["settings"] = settings
        test_client.app_state["database_url"] = database_url
        yield test_client


def register_user(client: TestClient, email: str = "e2e-user@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "super-secure-password",
            "display_name": email.split("@", maxsplit=1)[0].title(),
        },
    )
    token = response.json()["session"]["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project-root"
    root.mkdir()
    return root
