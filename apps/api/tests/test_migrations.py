from __future__ import annotations

import sqlite3
from pathlib import Path

from tests.helpers import run_downgrade, run_migrations


def test_migrations_upgrade_and_downgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite+pysqlite:///{database_path}"

    run_migrations(database_url)

    connection = sqlite3.connect(database_path)
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "projects" in tables
        assert "users" in tables
        assert "api_sessions" in tables
        assert "workflow_runs" in tables
        assert "run_events" in tables
        assert "memory_records" in tables
    finally:
        connection.close()

    run_downgrade(database_url)

    connection = sqlite3.connect(database_path)
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "projects" not in tables
        assert "users" not in tables
    finally:
        connection.close()
