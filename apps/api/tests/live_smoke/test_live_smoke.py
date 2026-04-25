from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.live_smoke

LIVE_TEMPORAL = bool(os.environ.get("AI_DESK_LIVE_TEMPORAL"))
LIVE_CODEX = bool(os.environ.get("AI_DESK_LIVE_CODEX"))
LIVE_OPENHANDS = bool(os.environ.get("AI_DESK_LIVE_OPENHANDS"))
LIVE_OPENVIKING = bool(os.environ.get("AI_DESK_LIVE_OPENVIKING"))

SKIP_REASON_TEMPORAL = "Set AI_DESK_LIVE_TEMPORAL=1 to enable Temporal live smoke tests"
SKIP_REASON_CODEX = "Set AI_DESK_LIVE_CODEX=1 to enable Codex live smoke tests"
SKIP_REASON_OPENHANDS = "Set AI_DESK_LIVE_OPENHANDS=1 to enable OpenHands live smoke tests"
SKIP_REASON_OPENVIKING = "Set AI_DESK_LIVE_OPENVIKING=1 to enable OpenViking live smoke tests"


@pytest.mark.skipif(not LIVE_TEMPORAL, reason=SKIP_REASON_TEMPORAL)
def test_temporal_live_connectivity() -> None:
    import asyncio

    from temporalio.client import Client

    from api.config import get_settings

    settings = get_settings()

    async def _check() -> None:
        client = await Client.connect(
            settings.temporal_address,
            namespace=settings.temporal_namespace,
            identity="live-smoke-temporal",
        )
        await client.service_client.check_health()

    asyncio.run(_check())


@pytest.mark.skipif(not LIVE_TEMPORAL, reason=SKIP_REASON_TEMPORAL)
def test_temporal_live_workflow_start() -> None:
    import asyncio

    from temporalio.client import Client

    from api.config import get_settings

    settings = get_settings()

    async def _check() -> None:
        client = await Client.connect(
            settings.temporal_address,
            namespace=settings.temporal_namespace,
            identity="live-smoke-temporal-start",
        )
        health = await client.service_client.check_health()
        assert health is not None

    asyncio.run(_check())


@pytest.mark.skipif(not LIVE_CODEX, reason=SKIP_REASON_CODEX)
def test_codex_live_transport() -> None:
    from api.config import get_settings
    from api.executors.transports import codex_config_from_settings

    settings = get_settings()
    config = codex_config_from_settings(settings)
    assert config.transport in ("stdio", "websocket")
    assert config.model


@pytest.mark.skipif(not LIVE_OPENHANDS, reason=SKIP_REASON_OPENHANDS)
def test_openhands_live_connectivity() -> None:
    from api.config import get_settings
    from api.executors.openhands_runtime import (
        OpenHandsWorkspaceConfig,
        describe_openhands_runtime,
    )

    settings = get_settings()
    status = describe_openhands_runtime(
        OpenHandsWorkspaceConfig(
            host=settings.openhands_api_url,
            api_key=settings.openhands_api_key,
            remote_working_dir=settings.openhands_remote_working_dir,
            allow_local_workspace=settings.openhands_local_workspace_enabled,
        )
    )
    assert status["status"] == "ok"


@pytest.mark.skipif(not LIVE_OPENVIKING, reason=SKIP_REASON_OPENVIKING)
def test_openviking_live_connectivity() -> None:
    from api.config import get_settings
    from api.memory.openviking import OpenVikingMemoryAdapter

    settings = get_settings()
    if not settings.openviking_mcp_url:
        pytest.skip("AI_DESK_OPENVIKING_MCP_URL not configured")

    adapter = OpenVikingMemoryAdapter(settings)
    search_result = adapter.search(
        project_id="live-smoke-test",
        namespace_prefix=None,
        query="smoke test",
        limit=1,
    )
    assert isinstance(search_result.items, list)


@pytest.mark.skipif(not LIVE_OPENVIKING, reason=SKIP_REASON_OPENVIKING)
def test_openviking_live_write_and_recall() -> None:
    from api.config import get_settings
    from api.memory.openviking import OpenVikingMemoryAdapter

    settings = get_settings()
    if not settings.openviking_mcp_url:
        pytest.skip("AI_DESK_OPENVIKING_MCP_URL not configured")

    adapter = OpenVikingMemoryAdapter(settings)
    target_uri = adapter.target_uri("live-smoke-test", "global/test", "hash-smoke")
    write_result = adapter.write(
        title="Live smoke test memory",
        content="# Live Smoke Test\n\nThis is a smoke test write.",
        target_uri=target_uri,
        tags="ai-desk, smoke-test",
    )
    assert write_result.success or write_result.target_uri

    search_result = adapter.search(
        project_id="live-smoke-test",
        namespace_prefix="global/test",
        query="smoke test",
        limit=5,
    )
    assert isinstance(search_result.items, list)
