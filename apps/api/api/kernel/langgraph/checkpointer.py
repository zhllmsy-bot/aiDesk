from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ImportError:  # pragma: no cover - dependency is installed in runtime
    PostgresSaver = None


class LangGraphCheckpointerFactory:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = self._normalize_database_url(database_url)
        self._in_memory_checkpointer = InMemorySaver()
        self._postgres_setup_complete = False

    @contextmanager
    def checkpointer(self) -> Iterator[Any]:
        if self._database_url and PostgresSaver is not None:
            with PostgresSaver.from_conn_string(self._database_url) as saver:
                if not self._postgres_setup_complete:
                    saver.setup()
                    self._postgres_setup_complete = True
                yield saver
            return
        yield self._in_memory_checkpointer

    @staticmethod
    def validate_checkpoint(checkpoint: dict[str, Any]) -> None:
        if "thread_id" not in checkpoint:
            raise ValueError("langgraph checkpoint is missing thread_id")
        if "langgraph_checkpoint_id" not in checkpoint and "checkpoint_id" not in checkpoint:
            raise ValueError("langgraph checkpoint is missing checkpoint_id")

    @staticmethod
    def config_from_checkpoint(checkpoint: dict[str, Any]) -> dict[str, str]:
        LangGraphCheckpointerFactory.validate_checkpoint(checkpoint)
        configurable: dict[str, str] = {"thread_id": str(checkpoint["thread_id"])}
        checkpoint_ns = checkpoint.get("checkpoint_ns")
        if checkpoint_ns is not None:
            configurable["checkpoint_ns"] = str(checkpoint_ns)
        checkpoint_id = checkpoint.get("langgraph_checkpoint_id") or checkpoint.get("checkpoint_id")
        if checkpoint_id is not None:
            configurable["checkpoint_id"] = str(checkpoint_id)
        return configurable

    @staticmethod
    def checkpoint_payload(
        *,
        configurable: dict[str, object],
        fallback_thread_id: str,
        stored_checkpoint_id: str | None,
    ) -> dict[str, Any]:
        checkpoint: dict[str, Any] = {
            "thread_id": str(configurable.get("thread_id", fallback_thread_id)),
            "checkpoint_ns": str(configurable.get("checkpoint_ns", "")),
        }
        langgraph_checkpoint_id = configurable.get("checkpoint_id")
        if langgraph_checkpoint_id is not None:
            checkpoint["langgraph_checkpoint_id"] = str(langgraph_checkpoint_id)
        checkpoint["checkpoint_id"] = stored_checkpoint_id or str(langgraph_checkpoint_id)
        return checkpoint

    @staticmethod
    def _normalize_database_url(database_url: str | None) -> str | None:
        if not database_url:
            return None
        if database_url.startswith("postgresql+psycopg://"):
            return database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        if database_url.startswith("postgresql://"):
            return database_url
        return None
