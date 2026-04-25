from __future__ import annotations

import json

from api.app import create_app
from api.config import API_CONTRACTS_DIR, CONTRACTS_DIR


def _write_snapshot(snapshot_path, payload: object) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    control_plane_app = create_app(include_runtime_surface=False, include_execution_surface=False)
    control_plane_snapshot_path = CONTRACTS_DIR / "openapi" / "control-plane.openapi.json"
    _write_snapshot(control_plane_snapshot_path, control_plane_app.openapi())

    full_surface_app = create_app(include_runtime_surface=True, include_execution_surface=True)
    full_surface_snapshot_path = API_CONTRACTS_DIR / "openapi" / "full.openapi.json"
    _write_snapshot(full_surface_snapshot_path, full_surface_app.openapi())

    print(control_plane_snapshot_path)
    print(full_surface_snapshot_path)


if __name__ == "__main__":
    main()
