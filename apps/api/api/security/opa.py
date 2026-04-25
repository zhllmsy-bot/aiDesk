from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class OpaDecision:
    allowed: bool
    reason: str | None = None
    required_scope: list[str] = field(default_factory=list)


class OpaPolicyEngine:
    def __init__(self, *, policy_dir: str | Path, enabled: bool = True) -> None:
        self._policy_dir = Path(policy_dir)
        self._enabled = enabled

    def evaluate(self, policy: str, input_data: dict[str, Any]) -> OpaDecision:
        if not self._enabled:
            return OpaDecision(allowed=True)
        policy_path = self._policy_dir / f"{policy}.rego"
        if not policy_path.exists():
            return OpaDecision(
                allowed=False,
                reason=f"OPA policy file not found: {policy_path}",
                required_scope=[policy],
            )
        if policy == "execution":
            return self._evaluate_execution(input_data)
        return OpaDecision(allowed=True)

    def _evaluate_execution(self, input_data: dict[str, Any]) -> OpaDecision:
        workspace = _mapping(input_data.get("workspace"))
        permission = _mapping(input_data.get("permission"))
        root_path = str(workspace.get("root_path") or "")
        allowlist = _string_list(permission.get("workspace_allowlist"))
        if allowlist and not any(root_path.startswith(root) for root in allowlist):
            return OpaDecision(
                allowed=False,
                reason="workspace root outside allowlist",
                required_scope=[root_path],
            )

        commands = _string_list(input_data.get("commands"))
        denylist = _string_list(permission.get("command_denylist"))
        for command in commands:
            if any(command.startswith(prefix) for prefix in denylist):
                return OpaDecision(
                    allowed=False,
                    reason=f"blocked command: {command}",
                    required_scope=[command],
                )

        writable_paths = _string_list(workspace.get("writable_paths"))
        break_glass_reason = permission.get("break_glass_reason")
        if (
            permission.get("require_manual_approval_for_write") is True
            and writable_paths
            and not break_glass_reason
        ):
            return OpaDecision(
                allowed=False,
                reason="manual approval required for write execution",
                required_scope=writable_paths,
            )
        return OpaDecision(allowed=True)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]
