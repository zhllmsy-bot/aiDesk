from __future__ import annotations

from importlib import import_module


def register_models() -> None:
    import_module("api.auth.models")
    import_module("api.control_plane.models")
    import_module("api.runtime_persistence.models")
    import_module("api.security.models")
