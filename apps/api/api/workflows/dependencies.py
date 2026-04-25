from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from api.agent_runtime.service import RuntimeGraphService
from api.config import Settings
from api.database import create_session_factory
from api.events.store import RuntimeEventStore
from api.integrations.notifications import build_runtime_notification_adapters
from api.notifications.service import (
    InMemoryNotificationAdapter,
    NotificationHistoryService,
    NotificationService,
    PersistentNotificationRecorder,
)
from api.runtime_persistence.projectors import RuntimeProjectorService
from api.runtime_persistence.service import RuntimePersistenceService


@dataclass(slots=True)
class RuntimeContainer:
    settings: Settings
    worker_id: str
    task_queue: str
    event_store: RuntimeEventStore
    notification_adapter: InMemoryNotificationAdapter
    notification_service: NotificationService
    agent_runtime: RuntimeGraphService
    persistence: RuntimePersistenceService
    projector: RuntimeProjectorService

    @property
    def runtime_task_queue(self) -> str:
        return self.task_queue

    def reset(self) -> None:
        self.notification_adapter.messages.clear()
        self.notification_adapter.receipts.clear()


def _build_runtime_container(settings: Settings) -> RuntimeContainer:
    session_factory = create_session_factory(settings.database_url)
    persistence = RuntimePersistenceService(session_factory=session_factory)
    notification_adapter = InMemoryNotificationAdapter()
    notification_history = NotificationHistoryService(session_factory=session_factory)
    notification_service = NotificationService(
        adapters=build_runtime_notification_adapters(settings, notification_adapter),
        recorders=[PersistentNotificationRecorder(notification_history)],
    )
    agent_runtime = RuntimeGraphService(
        checkpoint_store=persistence,
        database_url=settings.database_url,
    )
    return RuntimeContainer(
        settings=settings,
        worker_id=settings.runtime_worker_id,
        task_queue=settings.runtime_task_queue,
        event_store=persistence,
        notification_adapter=notification_adapter,
        notification_service=notification_service,
        agent_runtime=agent_runtime,
        persistence=persistence,
        projector=persistence.projector,
    )


def configure_runtime_container(settings: Settings) -> RuntimeContainer:
    container = _build_runtime_container(settings)
    global _standalone_runtime_container
    _standalone_runtime_container = container
    return container


_standalone_runtime_container: RuntimeContainer | None = None


@lru_cache(maxsize=1)
def _default_runtime_container() -> RuntimeContainer:
    from api.config import get_settings

    return _build_runtime_container(get_settings())


def get_standalone_runtime_container() -> RuntimeContainer:
    return _standalone_runtime_container or _default_runtime_container()
