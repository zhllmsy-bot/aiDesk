from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic.config import Config

from alembic import command
from api.config import Settings


def run_migrations(database_url: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    config.attributes["database_url"] = database_url
    command.upgrade(config, "head")


def run_downgrade(database_url: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    config.attributes["database_url"] = database_url
    command.downgrade(config, "base")


def build_test_settings(**overrides: Any) -> Settings:
    defaults: dict[str, Any] = {
        "app_name": "AI Desk Control Plane",
        "database_url": "sqlite+pysqlite:///:memory:",
        "web_origin": "http://localhost:3000",
        "session_ttl_hours": 4,
        "temporal_address": "localhost:7233",
        "temporal_namespace": "test",
        "runtime_task_queue": "ai-desk.runtime",
        "runtime_worker_id": "test-worker",
        "runtime_lease_timeout_seconds": 30,
        "runtime_signal_timeout_seconds": 300,
    }
    defaults.update(overrides)
    return Settings(**defaults)
