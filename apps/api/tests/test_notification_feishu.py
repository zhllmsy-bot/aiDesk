from __future__ import annotations

from types import SimpleNamespace

from api.events.models import CorrelationIds
from api.notifications.base import NotificationMessage
from api.notifications.feishu import FeishuNotificationAdapter
from api.notifications.service import NotificationService


class _FakeCreateMessageRequestBodyBuilder:
    def __init__(self) -> None:
        self._payload: dict[str, str] = {}

    def receive_id(self, value: str) -> _FakeCreateMessageRequestBodyBuilder:
        self._payload["receive_id"] = value
        return self

    def msg_type(self, value: str) -> _FakeCreateMessageRequestBodyBuilder:
        self._payload["msg_type"] = value
        return self

    def content(self, value: str) -> _FakeCreateMessageRequestBodyBuilder:
        self._payload["content"] = value
        return self

    def build(self) -> dict[str, str]:
        return dict(self._payload)


class _FakeCreateMessageRequestBody:
    @staticmethod
    def builder() -> _FakeCreateMessageRequestBodyBuilder:
        return _FakeCreateMessageRequestBodyBuilder()


class _FakeCreateMessageRequestBuilder:
    def __init__(self) -> None:
        self._payload: dict[str, object] = {}

    def receive_id_type(self, value: str) -> _FakeCreateMessageRequestBuilder:
        self._payload["receive_id_type"] = value
        return self

    def request_body(self, value: object) -> _FakeCreateMessageRequestBuilder:
        self._payload["request_body"] = value
        return self

    def build(self) -> dict[str, object]:
        return dict(self._payload)


class _FakeCreateMessageRequest:
    @staticmethod
    def builder() -> _FakeCreateMessageRequestBuilder:
        return _FakeCreateMessageRequestBuilder()


class _FakeResponse:
    def __init__(self, success: bool = True, message_id: str = "msg_123") -> None:
        self._success = success
        self.code = 999 if not success else 0
        self.msg = "failed" if not success else "ok"
        self.header = SimpleNamespace(log_id="log_x")
        self.data = SimpleNamespace(message_id=message_id)

    def success(self) -> bool:
        return self._success


class _FakeMessageAPI:
    def __init__(self, response: _FakeResponse | None = None) -> None:
        self.response = response or _FakeResponse()
        self.last_request: dict[str, object] | None = None

    def create(self, request: dict[str, object]) -> _FakeResponse:
        self.last_request = request
        return self.response


def _bind_fake_client(
    adapter: FeishuNotificationAdapter,
    *,
    fake_message_api: _FakeMessageAPI,
) -> None:
    adapter._client = SimpleNamespace(
        im=SimpleNamespace(v1=SimpleNamespace(message=fake_message_api))
    )
    adapter._CreateMessageRequest = _FakeCreateMessageRequest
    adapter._CreateMessageRequestBody = _FakeCreateMessageRequestBody


def _message() -> NotificationMessage:
    return NotificationMessage(
        title="Workflow completed",
        body="Run finished",
        correlation=CorrelationIds(workflow_run_id="run-1", trace_id="trace-1"),
        metadata={},
    )


def test_feishu_adapter_sends_message_with_default_receive_id() -> None:
    adapter = FeishuNotificationAdapter(
        app_id="app_id",
        app_secret="app_secret",
        default_receive_id="oc_x",
    )
    fake_message_api = _FakeMessageAPI()
    _bind_fake_client(adapter, fake_message_api=fake_message_api)

    receipt = adapter.send(_message())

    assert receipt.channel == "feishu"
    assert receipt.status == "sent"
    assert receipt.metadata["provider_message_id"] == "msg_123"
    assert fake_message_api.last_request is not None
    assert fake_message_api.last_request["receive_id_type"] == "chat_id"


def test_feishu_adapter_uses_message_metadata_receive_id() -> None:
    adapter = FeishuNotificationAdapter(
        app_id="app_id",
        app_secret="app_secret",
        default_receive_id="oc_default",
    )
    fake_message_api = _FakeMessageAPI()
    _bind_fake_client(adapter, fake_message_api=fake_message_api)

    message = _message().model_copy(update={"metadata": {"receive_id": "oc_override"}})
    adapter.send(message)

    assert fake_message_api.last_request is not None
    body = fake_message_api.last_request["request_body"]
    assert isinstance(body, dict)
    assert body["receive_id"] == "oc_override"


def test_feishu_adapter_uses_message_metadata_receive_id_type() -> None:
    adapter = FeishuNotificationAdapter(
        app_id="app_id",
        app_secret="app_secret",
        default_receive_id="ou_default",
        receive_id_type="chat_id",
    )
    fake_message_api = _FakeMessageAPI()
    _bind_fake_client(adapter, fake_message_api=fake_message_api)

    message = _message().model_copy(
        update={
            "metadata": {
                "receive_id": "ou_123",
                "receive_id_type": "open_id",
            }
        }
    )
    receipt = adapter.send(message)

    assert fake_message_api.last_request is not None
    assert fake_message_api.last_request["receive_id_type"] == "open_id"
    assert receipt.metadata["receive_id_type"] == "open_id"


def test_feishu_adapter_raises_when_target_missing() -> None:
    adapter = FeishuNotificationAdapter(app_id="app_id", app_secret="app_secret")
    fake_message_api = _FakeMessageAPI()
    _bind_fake_client(adapter, fake_message_api=fake_message_api)

    raised = False
    try:
        adapter.send(_message())
    except ValueError:
        raised = True

    assert raised


def test_notification_service_marks_failed_receipt_when_adapter_throws() -> None:
    class BrokenAdapter:
        channel = "feishu"

        def send(self, message: NotificationMessage):
            raise RuntimeError("network down")

    service = NotificationService(adapters=[BrokenAdapter()])
    receipts = service.send(_message())
    assert len(receipts) == 1
    assert receipts[0].channel == "feishu"
    assert receipts[0].status == "failed"
    assert "network down" in str(receipts[0].metadata.get("reason"))


def test_notification_service_retries_adapter_before_marking_failure() -> None:
    attempts: dict[str, int] = {"count": 0}

    class FlakyAdapter:
        channel = "feishu"

        def send(self, message: NotificationMessage):  # pragma: no cover - deterministic
            _ = message
            attempts["count"] += 1
            raise RuntimeError("timeout")

    service = NotificationService(
        adapters=[FlakyAdapter()],
        max_attempts=3,
        backoff_base_seconds=0,
        backoff_cap_seconds=0,
    )
    receipts = service.send(_message())
    assert attempts["count"] == 3
    assert receipts[0].status == "failed"
    assert receipts[0].metadata["failure_category"] == "timeout"
    assert receipts[0].metadata["attempts_total"] == 3
