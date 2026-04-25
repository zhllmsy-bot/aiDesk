from __future__ import annotations

from pathlib import Path

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


def test_traceparent_is_preserved_or_created() -> None:
    existing = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
    assert resolve_traceparent({"traceparent": existing}, "trace-1") == existing

    generated = resolve_traceparent({}, "trace-1")
    assert generated.startswith("00-")
    assert len(generated.split("-")) == 4
