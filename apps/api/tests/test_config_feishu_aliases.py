from __future__ import annotations

from api.config import Settings


def test_settings_reads_feishu_aliases_without_ai_desk_prefix() -> None:
    settings = Settings(
        FEISHU_APP_ID="cli_123",
        FEISHU_APP_SECRET="secret_123",
        FEISHU_DOMAIN="https://open.larksuite.com",
    )
    assert settings.resolved_feishu_app_id == "cli_123"
    assert settings.resolved_feishu_app_secret == "secret_123"
    assert settings.resolved_feishu_domain == "https://open.larksuite.com"


def test_settings_reads_feishu_aliases_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_env_123")
    monkeypatch.setenv("FEISHU_APP_SECRET", "secret_env_123")
    monkeypatch.setenv("FEISHU_DOMAIN", "https://open.larksuite.com")
    settings = Settings()
    assert settings.resolved_feishu_app_id == "cli_env_123"
    assert settings.resolved_feishu_app_secret == "secret_env_123"
    assert settings.resolved_feishu_domain == "https://open.larksuite.com"


def test_settings_reads_feishu_mcp_aliases_without_ai_desk_prefix() -> None:
    settings = Settings(
        FEISHU_MCP_BRIDGE_ENABLED=True,
        FEISHU_MCP_BRIDGE_DIR="/tmp/feishu_mcp",
        FEISHU_MCP_ENV_FILE="/tmp/feishu_mcp/.env",
        FEISHU_MCP_TIMEOUT_SECONDS=45,
    )
    assert settings.feishu_mcp_bridge_enabled is True
    assert settings.resolved_feishu_mcp_bridge_dir == "/tmp/feishu_mcp"
    assert settings.resolved_feishu_mcp_env_file == "/tmp/feishu_mcp/.env"
    assert settings.feishu_mcp_timeout_seconds == 45


def test_settings_reads_feishu_mcp_aliases_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("FEISHU_MCP_BRIDGE_DIR", "/tmp/feishu_mcp_env")
    monkeypatch.setenv("FEISHU_MCP_ENV_FILE", "/tmp/feishu_mcp_env/.env")
    settings = Settings(
        FEISHU_MCP_BRIDGE_ENABLED=True,
    )
    assert settings.feishu_mcp_bridge_enabled is True
    assert settings.resolved_feishu_mcp_bridge_dir == "/tmp/feishu_mcp_env"
    assert settings.resolved_feishu_mcp_env_file == "/tmp/feishu_mcp_env/.env"
