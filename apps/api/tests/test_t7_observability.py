from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from api.app import create_app
from tests.helpers import build_test_settings


def _make_client() -> TestClient:
    import os
    import tempfile

    db_path = os.path.join(tempfile.mkdtemp(), "test.db")
    settings = build_test_settings(
        database_url=f"sqlite+pysqlite:///{db_path}",
    )
    app = create_app(settings, include_runtime_surface=False, include_execution_surface=False)
    return TestClient(app)


def test_health_live():
    client = _make_client()
    resp = client.get("/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "api"
    assert data["status"] == "ok"


def test_health_ready_returns_required_and_optional():
    with patch("api.health.router.Client") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.service_client.check_health = AsyncMock()
        mock_client_cls.connect = AsyncMock(return_value=mock_instance)
        client = _make_client()
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert "required" in data
        assert "optional" in data
        assert "database" in data["required"]
        assert "temporal" in data["required"]
        assert "codex" in data["optional"]
        assert "openhands" in data["optional"]
        assert "mem0" in data["optional"]
        assert "feishu" in data["optional"]
        assert "openviking" in data["optional"]
        assert "degraded_reasons" in data


def test_health_ready_degraded_when_temporal_down():
    with patch("api.health.router.Client") as mock_client_cls:
        mock_client_cls.connect = AsyncMock(side_effect=Exception("temporal down"))
        client = _make_client()
        resp = client.get("/health/ready")
        data = resp.json()
        assert data["status"] == "degraded"
        assert any("temporal" in reason for reason in data["degraded_reasons"])


def test_health_ready_optional_degraded():
    with patch("api.health.router.Client") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.service_client.check_health = AsyncMock()
        mock_client_cls.connect = AsyncMock(return_value=mock_instance)
        client = _make_client()
        resp = client.get("/health/ready")
        data = resp.json()
        assert data["optional"]["openhands"]["status"] in {"ok", "error", "not_configured"}
        assert data["optional"]["mem0"]["status"] in {"ok", "error", "not_configured"}
        assert data["optional"]["codex"]["status"] in {"ok", "error", "not_configured"}
        assert data["optional"]["feishu"]["status"] in {"ok", "error", "not_configured"}
        assert data["optional"]["openviking"]["status"] in {"ok", "error", "not_configured"}


def test_health_ready_degraded_when_optional_error():
    with patch("api.health.router.Client") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.service_client.check_health = AsyncMock()
        mock_client_cls.connect = AsyncMock(return_value=mock_instance)
        with patch(
            "api.health.router._check_codex",
            return_value={"status": "error", "reason": "codex down"},
        ):
            client = _make_client()
            resp = client.get("/health/ready")
            data = resp.json()
            assert data["status"] == "degraded"
            assert any("codex" in reason for reason in data["degraded_reasons"])


def test_metrics_endpoint():
    client = _make_client()
    resp = client.get("/observability/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "counters" in data
    assert "gauges" in data
    counter_names = [c["name"] for c in data["counters"]]
    assert "workflow_started" in counter_names
    assert "executor_dispatched" in counter_names
    assert "memory_write_attempted" in counter_names
    assert "eval_suite_run" in counter_names
    gauge_names = [g["name"] for g in data["gauges"]]
    assert "approval_pending" in gauge_names
    assert "runtime_sla" in data
    assert "notification_deliveries" in data


def test_runtime_regression_endpoint():
    client = _make_client()
    resp = client.get("/observability/evals/runtime-regression")
    assert resp.status_code == 200
    data = resp.json()
    assert data["suite_id"] == "runtime_regression"
    assert data["passed"] is True
    assert data["failed_count"] == 0


def test_correlation_middleware():
    client = _make_client()
    resp = client.get("/", headers={"X-Trace-ID": "trace-abc", "X-Request-ID": "req-123"})
    assert resp.headers.get("X-Trace-ID") == "trace-abc"
    assert resp.headers.get("X-Request-ID") == "req-123"


def test_correlation_middleware_generates_ids():
    client = _make_client()
    resp = client.get("/")
    assert resp.headers.get("X-Trace-ID") is not None
    assert resp.headers.get("X-Request-ID") is not None
    assert len(resp.headers["X-Trace-ID"]) > 0
    assert len(resp.headers["X-Request-ID"]) > 0
