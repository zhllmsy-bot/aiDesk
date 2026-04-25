from __future__ import annotations

import json

from api.app import create_app
from api.config import API_CONTRACTS_DIR, CONTRACTS_DIR
from tests.helpers import build_test_settings


def test_openapi_snapshot_matches_generated() -> None:
    snapshot_path = CONTRACTS_DIR / "openapi" / "control-plane.openapi.json"
    generated = create_app(
        build_test_settings(),
        include_runtime_surface=False,
        include_execution_surface=False,
    ).openapi()
    assert json.loads(snapshot_path.read_text(encoding="utf-8")) == generated


def test_full_openapi_snapshot_matches_generated() -> None:
    snapshot_path = API_CONTRACTS_DIR / "openapi" / "full.openapi.json"
    generated = create_app(
        build_test_settings(),
        include_runtime_surface=True,
        include_execution_surface=True,
    ).openapi()
    assert json.loads(snapshot_path.read_text(encoding="utf-8")) == generated
