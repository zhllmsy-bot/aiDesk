from __future__ import annotations

from api.executors.base import ExecutorAdapter
from api.executors.contracts import ExecutorCapability


class ExecutorRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ExecutorAdapter] = {}

    def register(self, adapter: ExecutorAdapter) -> None:
        self._adapters[adapter.capability.executor] = adapter

    def get(self, executor_name: str) -> ExecutorAdapter:
        adapter = self._adapters.get(executor_name)
        if adapter is None:
            available = ", ".join(sorted(self._adapters)) or "none"
            raise KeyError(f"Unknown executor '{executor_name}'. Available executors: {available}.")
        return adapter

    def capabilities(self) -> list[ExecutorCapability]:
        return [adapter.capability for adapter in self._adapters.values()]
