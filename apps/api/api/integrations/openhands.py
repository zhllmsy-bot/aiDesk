from __future__ import annotations

from api.config import Settings
from api.executors.openhands_runtime import (
    OpenHandsWorkspaceConfig,
    describe_openhands_runtime,
    is_openhands_runtime_available,
)


def openhands_workspace_config_from_settings(settings: Settings) -> OpenHandsWorkspaceConfig:
    return OpenHandsWorkspaceConfig(
        host=settings.openhands_api_url,
        api_key=settings.openhands_api_key,
        remote_working_dir=settings.openhands_remote_working_dir,
        allow_local_workspace=settings.openhands_local_workspace_enabled,
    )


def check_openhands(settings: Settings) -> dict[str, str]:
    return describe_openhands_runtime(openhands_workspace_config_from_settings(settings))


def is_openhands_available(settings: Settings) -> bool:
    return is_openhands_runtime_available(openhands_workspace_config_from_settings(settings))
