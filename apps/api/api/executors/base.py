from __future__ import annotations

from typing import Protocol

from api.executors.contracts import ExecutorCapability, ExecutorInputBundle, ExecutorResultBundle
from api.executors.provider_contracts import ProviderTimeoutConfig


class ExecutorAdapter(Protocol):
    @property
    def capability(self) -> ExecutorCapability: ...

    @property
    def timeout_config(self) -> ProviderTimeoutConfig: ...

    def execute(self, bundle: ExecutorInputBundle) -> ExecutorResultBundle: ...
