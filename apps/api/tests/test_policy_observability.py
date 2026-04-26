from __future__ import annotations

from pathlib import Path

from api.app import create_app
from api.config import Settings
from api.observability.otel import resolve_traceparent
from api.security.opa import OpaPolicyEngine


def test_opa_execution_policy_denies_workspace_outside_allowlist(tmp_path: Path) -> None:
    (tmp_path / "execution.rego").write_text("package ai_desk.execution\n", encoding="utf-8")
    engine = OpaPolicyEngine(policy_dir=tmp_path)

    decision = engine.evaluate(
        "execution",
        {
            "workspace": {"root_path": "/outside/project", "writable_paths": []},
            "permission": {"workspace_allowlist": ["/repo"]},
            "commands": [],
        },
    )

    assert decision.allowed is False
    assert decision.reason == "workspace root outside allowlist"


def test_opa_policy_facade_covers_tool_and_write_gates(tmp_path: Path) -> None:
    for policy in ("tool_allowlist", "write_gate"):
        (tmp_path / f"{policy}.rego").write_text(f"package ai_desk.{policy}\n", encoding="utf-8")
    engine = OpaPolicyEngine(policy_dir=tmp_path)

    tool_decision = engine.evaluate(
        "tool_allowlist",
        {
            "permission": {
                "command_allowlist": ["pytest"],
                "command_denylist": ["rm"],
            },
            "commands": ["python manage.py"],
        },
    )
    assert tool_decision.allowed is False
    assert tool_decision.reason == "command outside allowlist: python manage.py"

    write_decision = engine.evaluate(
        "write_gate",
        {
            "workspace": {"writable_paths": ["/repo"]},
            "permission": {
                "require_manual_approval_for_write": True,
                "break_glass_reason": None,
            },
        },
    )
    assert write_decision.allowed is False
    assert write_decision.reason == "manual approval required for write execution"


def test_traceparent_is_preserved_or_created() -> None:
    existing = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
    assert resolve_traceparent({"traceparent": existing}, "trace-1") == existing

    generated = resolve_traceparent({}, "trace-1")
    assert generated.startswith("00-")
    assert len(generated.split("-")) == 4


def test_observability_instrumentation_is_disabled_by_default() -> None:
    app = create_app(Settings(database_url="sqlite+pysqlite:///:memory:"))
    status = app.state.observability
    assert status.enabled is False
    assert status.otel == "disabled"
    assert status.logfire == "disabled"


def test_observability_instrumentation_can_enable_local_provider() -> None:
    app = create_app(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            otel_enabled=True,
            otel_service_name="ai-desk-test",
        )
    )
    status = app.state.observability
    assert status.enabled is True
    assert status.otel == "local_provider"
