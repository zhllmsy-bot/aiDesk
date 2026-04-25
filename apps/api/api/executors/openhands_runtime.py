from __future__ import annotations

import os
from dataclasses import dataclass
from typing import cast

os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")

from openhands.sdk import RemoteWorkspace, Workspace
from openhands.sdk.workspace.base import BaseWorkspace


class OpenHandsRuntimeConfigurationError(RuntimeError):
    pass


@dataclass(slots=True)
class OpenHandsWorkspaceConfig:
    host: str | None
    api_key: str | None = None
    remote_working_dir: str | None = None
    allow_local_workspace: bool = False

    @property
    def normalized_host(self) -> str | None:
        if self.host is None:
            return None
        stripped = self.host.strip()
        return stripped or None

    @property
    def uses_remote_runtime(self) -> bool:
        return self.normalized_host is not None

    @property
    def uses_local_workspace(self) -> bool:
        return not self.uses_remote_runtime and self.allow_local_workspace

    @property
    def display_target(self) -> str:
        if self.uses_remote_runtime:
            return self.normalized_host or "remote-runtime"
        if self.uses_local_workspace:
            return "local-workspace"
        return "not-configured"


def build_openhands_workspace(
    config: OpenHandsWorkspaceConfig,
    *,
    root_path: str,
) -> BaseWorkspace:
    if config.uses_remote_runtime:
        working_dir = config.remote_working_dir or root_path
        host = config.normalized_host
        assert host is not None
        return cast(
            BaseWorkspace,
            Workspace(
                host=host,
                api_key=config.api_key,
                working_dir=working_dir,
            ),
        )
    if config.allow_local_workspace:
        return cast(BaseWorkspace, Workspace(working_dir=root_path))
    raise OpenHandsRuntimeConfigurationError(
        "OpenHands remote runtime is not configured and local workspace fallback is disabled"
    )


def describe_openhands_runtime(config: OpenHandsWorkspaceConfig) -> dict[str, str]:
    if config.uses_remote_runtime:
        workspace = build_openhands_workspace(
            config,
            root_path=config.remote_working_dir or "workspace/project",
        )
        if isinstance(workspace, RemoteWorkspace) and workspace.alive:
            return {"status": "ok", "target": config.display_target}
        return {
            "status": "error",
            "reason": f"openhands runtime unavailable at {config.display_target}",
        }

    if config.allow_local_workspace:
        return {
            "status": "ok",
            "note": "local workspace fallback enabled",
            "target": "local-workspace",
        }

    return {
        "status": "not_configured",
        "reason": "openhands remote runtime is not configured",
    }


def is_openhands_runtime_available(config: OpenHandsWorkspaceConfig) -> bool:
    return describe_openhands_runtime(config).get("status") == "ok"
