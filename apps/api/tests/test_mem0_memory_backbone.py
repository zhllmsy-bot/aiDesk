from __future__ import annotations

from api.database import Base, create_session_factory
from api.executors.contracts import MemoryType, MemoryWriteCandidate
from api.executors.dependencies import configure_execution_container
from api.memory.mem0 import Mem0MemoryAdapter
from api.memory.service import MemoryGovernanceService
from api.models import register_models
from tests.helpers import build_test_settings


class _FakeMem0Client:
    def __init__(self) -> None:
        self.add_calls: list[dict[str, object]] = []
        self.update_calls: list[dict[str, object]] = []
        self.get_all_payload = {
            "results": [
                {
                    "id": "mem0-remote-1",
                    "memory": "Remote memory from mem0",
                    "score": 0.88,
                    "metadata": {
                        "project_id": "project-1",
                        "namespace": "project-1:global:lesson",
                        "memory_type": MemoryType.LESSON.value,
                        "external_ref": "doc://mem0/remote",
                        "content_hash": "hash-remote-1",
                        "quality_score": 0.88,
                    },
                }
            ]
        }

    def add(self, messages, **kwargs):  # noqa: ANN001, ANN201
        self.add_calls.append(
            {
                "messages": messages,
                "kwargs": kwargs,
            }
        )
        return {"results": [{"id": "mem0-write-1"}]}

    def update(self, memory_id, **kwargs):  # noqa: ANN001, ANN201
        self.update_calls.append(
            {
                "memory_id": memory_id,
                "kwargs": kwargs,
            }
        )
        return {"id": memory_id}

    def get_all(self, **kwargs):  # noqa: ANN001, ANN201
        return self.get_all_payload


def _init_memory_service() -> tuple[MemoryGovernanceService, _FakeMem0Client]:
    session_factory = create_session_factory("sqlite+pysqlite:///:memory:")
    register_models()
    engine = session_factory.kw["bind"]
    assert engine is not None
    Base.metadata.create_all(engine)
    client = _FakeMem0Client()
    settings = build_test_settings(
        mem0_api_key="mem0-test-key",
        mem0_api_url="https://api.mem0.test",
    )
    return (
        MemoryGovernanceService(
            session_factory=session_factory,
            mem0_adapter=Mem0MemoryAdapter(settings, client=client),
        ),
        client,
    )


def test_mem0_write_is_persisted_locally_with_mem0_provider() -> None:
    service, client = _init_memory_service()

    record = service.write(
        MemoryWriteCandidate(
            project_id="project-1",
            iteration_id="iter-1",
            memory_type=MemoryType.LESSON,
            namespace="project-1:global:lesson",
            external_ref="doc://memory/source",
            summary="Use Mem0 as the primary memory backbone",
            content_hash="hash-mem0-write-1",
            quality_score=0.93,
        )
    )

    assert record is not None
    assert record.external_ref == "mem0://memories/mem0-write-1"
    assert record.metadata == {}
    assert service.provider_name == "mem0"
    assert client.add_calls[0]["kwargs"]["filters"] == {
        "user_id": "project-1",
        "agent_id": "project-1:global:lesson",
    }


def test_mem0_remote_recall_maps_to_memory_records() -> None:
    service, _ = _init_memory_service()

    records = service.recall(
        project_id="project-1",
        namespace_prefix="project-1:global",
        limit=5,
    )

    assert len(records) == 1
    assert records[0].record_id == "mem0-remote-1"
    assert records[0].summary == "Remote memory from mem0"
    assert records[0].metadata["provider"] == "mem0"
    assert records[0].metadata["remote"] is True


def test_execution_container_prefers_mem0_when_configured(tmp_path) -> None:
    settings = build_test_settings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'mem0-container.db'}",
        mem0_api_key="mem0-test-key",
        mem0_api_url="https://api.mem0.test",
    )

    container = configure_execution_container(settings)

    assert container.memory.provider_name == "mem0"
