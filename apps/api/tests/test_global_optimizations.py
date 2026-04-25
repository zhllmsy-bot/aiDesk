from __future__ import annotations

import api.config as config_module
from api.executors.openhands_runtime import (
    OpenHandsWorkspaceConfig,
    describe_openhands_runtime,
)
from api.observability.evals import run_runtime_regression_suite


def test_get_settings_reads_env_local_before_env(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AI_DESK_APP_NAME", raising=False)
    (tmp_path / ".env").write_text(
        'AI_DESK_APP_NAME="base-env"\n',
        encoding="utf-8",
    )
    (tmp_path / ".env.local").write_text(
        'AI_DESK_APP_NAME="local-env"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "ROOT_DIR", tmp_path)
    config_module.get_settings.cache_clear()
    try:
        settings = config_module.get_settings()
        assert settings.app_name == "local-env"
    finally:
        config_module.get_settings.cache_clear()


def test_openhands_runtime_requires_explicit_local_opt_in() -> None:
    status = describe_openhands_runtime(
        OpenHandsWorkspaceConfig(host=None, allow_local_workspace=False)
    )
    assert status["status"] == "not_configured"


def test_openhands_runtime_reports_local_fallback_when_enabled() -> None:
    status = describe_openhands_runtime(
        OpenHandsWorkspaceConfig(host=None, allow_local_workspace=True)
    )
    assert status["status"] == "ok"
    assert status["target"] == "local-workspace"


def test_runtime_regression_suite_passes() -> None:
    result = run_runtime_regression_suite()
    assert result.passed is True
    assert result.failed_count == 0
    assert result.passed_count == len(result.results)
