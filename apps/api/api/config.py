from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]
CONTRACTS_DIR = ROOT_DIR / "packages" / "contracts" / "projects"
API_CONTRACTS_DIR = ROOT_DIR / "packages" / "contracts" / "api"
RUNTIME_CONTRACTS_DIR = ROOT_DIR / "packages" / "contracts" / "runtime"


def _non_empty(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


class Settings(BaseSettings):
    app_name: str = Field(default="AI Desk Control Plane")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    database_url: str = Field(default="postgresql+psycopg://ai_desk:ai_desk@localhost:5432/ai_desk")
    web_origin: str = Field(default="http://localhost:3000")
    session_ttl_hours: int = Field(default=12, ge=1, le=168)
    temporal_address: str = Field(default="localhost:7233")
    temporal_namespace: str = Field(default="default")
    runtime_task_queue: str = Field(default="ai-desk.runtime")
    runtime_worker_id: str = Field(default="runtime-worker")
    runtime_lease_timeout_seconds: int = Field(default=30, ge=5, le=3600)
    runtime_signal_timeout_seconds: int = Field(default=300, ge=5, le=3600)
    codex_app_server_transport: str = Field(default="stdio")
    codex_app_server_url: str = Field(default="ws://127.0.0.1:8321")
    codex_app_server_command: str = Field(
        default="/Applications/Codex.app/Contents/Resources/codex"
    )
    codex_app_server_args: list[str] = Field(
        default_factory=lambda: ["app-server", "--listen", "stdio://"]
    )
    codex_app_server_model: str = Field(default="gpt-5.4")
    codex_app_server_reasoning_effort: str = Field(default="medium")
    codex_app_server_reasoning_summary: str = Field(default="concise")
    codex_app_server_startup_timeout_seconds: float = Field(default=20.0, gt=0)
    codex_app_server_turn_timeout_seconds: float = Field(default=1800.0, gt=0)
    openhands_api_url: str = Field(default="http://127.0.0.1:3001")
    openhands_api_key: str | None = Field(default=None)
    openhands_local_workspace_enabled: bool = Field(default=False)
    openhands_remote_working_dir: str | None = Field(default=None)
    llm_provider: str = Field(default="litellm")
    llm_default_model: str = Field(default="openai/gpt-5.4")
    llm_request_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_agent_provider: str = Field(default="claude_agent_sdk")
    claude_code_command: str = Field(default="claude")
    claude_code_model: str = Field(default="claude-sonnet-4-5")
    claude_agent_model: str = Field(default="claude-sonnet-4-5")
    openai_agents_model: str = Field(default="gpt-5.4")
    aider_model: str = Field(default="openai/gpt-5.4")
    opa_enabled: bool = Field(default=True)
    opa_policy_dir: str = Field(default=str(ROOT_DIR / "infra" / "policies"))
    mem0_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("mem0_api_key", "AI_DESK_MEM0_API_KEY", "MEM0_API_KEY"),
    )
    mem0_api_url: str = Field(
        default="https://api.mem0.ai",
        validation_alias=AliasChoices("mem0_api_url", "AI_DESK_MEM0_API_URL", "MEM0_API_URL"),
    )
    openviking_mcp_url: str | None = Field(default=None)
    openviking_target_root: str = Field(default="viking://resources/ai-desk/projects")
    feishu_notification_enabled: bool = Field(default=False)
    feishu_app_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AI_DESK_FEISHU_APP_ID", "FEISHU_APP_ID"),
    )
    feishu_app_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AI_DESK_FEISHU_APP_SECRET", "FEISHU_APP_SECRET"),
    )
    feishu_domain: str = Field(
        default="https://open.feishu.cn",
        validation_alias=AliasChoices("AI_DESK_FEISHU_DOMAIN", "FEISHU_DOMAIN"),
    )
    feishu_default_receive_id: str | None = Field(default=None)
    feishu_receive_id_type: str = Field(default="chat_id")
    feishu_mcp_bridge_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "AI_DESK_FEISHU_MCP_BRIDGE_ENABLED",
            "FEISHU_MCP_BRIDGE_ENABLED",
        ),
    )
    feishu_mcp_bridge_dir: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AI_DESK_FEISHU_MCP_BRIDGE_DIR",
            "FEISHU_MCP_BRIDGE_DIR",
        ),
    )
    feishu_mcp_env_file: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AI_DESK_FEISHU_MCP_ENV_FILE",
            "FEISHU_MCP_ENV_FILE",
        ),
    )
    feishu_mcp_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        validation_alias=AliasChoices(
            "AI_DESK_FEISHU_MCP_TIMEOUT_SECONDS",
            "FEISHU_MCP_TIMEOUT_SECONDS",
        ),
    )

    model_config = SettingsConfigDict(
        env_prefix="AI_DESK_",
        # Programmatic Settings(...) construction should stay deterministic and
        # never silently pick up developer-local overrides from .env.local.
        # Runtime bootstrapping uses get_settings(), which explicitly opts into
        # loading base .env first and then overlaying .env.local.
        env_file=(ROOT_DIR / ".env",),
        extra="ignore",
    )

    @property
    def resolved_feishu_app_id(self) -> str | None:
        return _non_empty(self.feishu_app_id) or _non_empty(os.getenv("FEISHU_APP_ID"))

    @property
    def resolved_feishu_app_secret(self) -> str | None:
        return _non_empty(self.feishu_app_secret) or _non_empty(os.getenv("FEISHU_APP_SECRET"))

    @property
    def resolved_feishu_domain(self) -> str:
        env_domain = _non_empty(os.getenv("FEISHU_DOMAIN"))
        if env_domain and _non_empty(self.feishu_domain) == "https://open.feishu.cn":
            return env_domain
        return (
            _non_empty(self.feishu_domain)
            or env_domain
            or "https://open.feishu.cn"
        )

    @property
    def resolved_feishu_mcp_bridge_dir(self) -> str | None:
        return _non_empty(self.feishu_mcp_bridge_dir) or _non_empty(
            os.getenv("FEISHU_MCP_BRIDGE_DIR")
        )

    @property
    def resolved_feishu_mcp_env_file(self) -> str | None:
        configured = _non_empty(self.feishu_mcp_env_file) or _non_empty(
            os.getenv("FEISHU_MCP_ENV_FILE")
        )
        if configured:
            return configured
        bridge_dir = self.resolved_feishu_mcp_bridge_dir
        if bridge_dir:
            return str(Path(bridge_dir).expanduser() / ".env")
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings_cls = cast(Any, Settings)
    return settings_cls(_env_file=(ROOT_DIR / ".env", ROOT_DIR / ".env.local"))
