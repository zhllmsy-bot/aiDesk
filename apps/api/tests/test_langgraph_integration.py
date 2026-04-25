from __future__ import annotations

from api.integrations.langgraph import LangGraphCheckpointerFactory


def test_langgraph_database_url_normalization_accepts_psycopg() -> None:
    factory = LangGraphCheckpointerFactory("postgresql+psycopg://user:pass@db/app")
    assert factory._database_url == "postgresql://user:pass@db/app"


def test_langgraph_config_from_checkpoint_prefers_langgraph_checkpoint_id() -> None:
    config = LangGraphCheckpointerFactory.config_from_checkpoint(
        {
            "thread_id": "thread-1",
            "checkpoint_ns": "runtime",
            "langgraph_checkpoint_id": "lg-1",
            "checkpoint_id": "db-1",
        }
    )
    assert config == {
        "thread_id": "thread-1",
        "checkpoint_ns": "runtime",
        "checkpoint_id": "lg-1",
    }


def test_langgraph_checkpoint_payload_uses_stored_checkpoint_id_when_present() -> None:
    payload = LangGraphCheckpointerFactory.checkpoint_payload(
        configurable={"thread_id": "thread-1", "checkpoint_ns": "runtime", "checkpoint_id": "lg-1"},
        fallback_thread_id="fallback-thread",
        stored_checkpoint_id="db-1",
    )
    assert payload == {
        "thread_id": "thread-1",
        "checkpoint_ns": "runtime",
        "langgraph_checkpoint_id": "lg-1",
        "checkpoint_id": "db-1",
    }
