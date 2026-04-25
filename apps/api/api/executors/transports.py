from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportMissingParameterType=false
import asyncio
import contextlib
import json
from dataclasses import dataclass
from types import TracebackType
from typing import Any

from websockets.asyncio.client import connect as ws_connect

from api.config import Settings


class ExecutorTransportError(RuntimeError):
    pass


class _BaseTransport:
    async def send(self, payload: dict[str, Any]) -> None: ...

    async def recv(self) -> dict[str, Any]: ...

    async def aclose(self) -> None: ...


class _WebSocketTransport(_BaseTransport):
    def __init__(self, *, url: str, timeout_seconds: float):
        self._url = url
        self._timeout_seconds = timeout_seconds
        self._socket = None

    async def open(self) -> None:
        self._socket = await ws_connect(self._url, open_timeout=self._timeout_seconds, proxy=None)

    async def send(self, payload: dict[str, Any]) -> None:
        if self._socket is None:
            raise ExecutorTransportError("websocket transport is not open")
        await self._socket.send(json.dumps(payload, ensure_ascii=True))

    async def recv(self) -> dict[str, Any]:
        if self._socket is None:
            raise ExecutorTransportError("websocket transport is not open")
        raw = await self._socket.recv()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    async def aclose(self) -> None:
        if self._socket is not None:
            await self._socket.close()
            self._socket = None


class _StdioTransport(_BaseTransport):
    def __init__(self, *, command: str, args: list[str], timeout_seconds: float):
        self._command = command
        self._args = args
        self._timeout_seconds = timeout_seconds
        # Codex app-server can emit large single-line JSON-RPC payloads
        # (for example, long completed items). Raise the reader buffer limit
        # to avoid asyncio "chunk exceed the limit" failures on readline().
        self._stream_limit_bytes = 4 * 1024 * 1024
        self._proc: asyncio.subprocess.Process | None = None
        self._stderr_task: asyncio.Task[None] | None = None

    async def open(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            self._command,
            *self._args,
            limit=self._stream_limit_bytes,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._stderr_task = asyncio.create_task(self._pump_stderr())

    async def _pump_stderr(self) -> None:
        if self._proc is None or self._proc.stderr is None:
            return
        while True:
            line = await self._proc.stderr.readline()
            if not line:
                return

    async def send(self, payload: dict[str, Any]) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise ExecutorTransportError("stdio transport is not open")
        self._proc.stdin.write((json.dumps(payload, ensure_ascii=True) + "\n").encode("utf-8"))
        await self._proc.stdin.drain()

    async def recv(self) -> dict[str, Any]:
        if self._proc is None or self._proc.stdout is None:
            raise ExecutorTransportError("stdio transport is not open")
        raw = await asyncio.wait_for(self._proc.stdout.readline(), timeout=self._timeout_seconds)
        if not raw:
            raise ExecutorTransportError("executor closed stdout before sending a response")
        return json.loads(raw.decode("utf-8"))

    async def aclose(self) -> None:
        if self._proc is not None:
            if self._proc.stdin is not None:
                self._proc.stdin.close()
            if self._proc.returncode is None:
                self._proc.terminate()
                try:
                    await asyncio.wait_for(self._proc.wait(), timeout=5)
                except TimeoutError:
                    self._proc.kill()
                    await self._proc.wait()
            self._proc = None
        if self._stderr_task is not None:
            self._stderr_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stderr_task
            self._stderr_task = None


@dataclass(slots=True)
class CodexSessionConfig:
    transport: str
    url: str
    command: str
    args: list[str]
    model: str
    reasoning_effort: str
    reasoning_summary: str
    startup_timeout_seconds: float
    turn_timeout_seconds: float


def codex_config_from_settings(settings: Settings) -> CodexSessionConfig:
    return CodexSessionConfig(
        transport=settings.codex_app_server_transport,
        url=settings.codex_app_server_url,
        command=settings.codex_app_server_command,
        args=list(settings.codex_app_server_args),
        model=settings.codex_app_server_model,
        reasoning_effort=settings.codex_app_server_reasoning_effort,
        reasoning_summary=settings.codex_app_server_reasoning_summary,
        startup_timeout_seconds=settings.codex_app_server_startup_timeout_seconds,
        turn_timeout_seconds=settings.codex_app_server_turn_timeout_seconds,
    )


class CodexAppServerSession:
    def __init__(self, config: CodexSessionConfig):
        self._config = config
        self._transport: _BaseTransport | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._notifications: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._next_id = 0

    async def __aenter__(self) -> CodexAppServerSession:
        if self._config.transport == "websocket":
            transport = _WebSocketTransport(
                url=self._config.url,
                timeout_seconds=self._config.startup_timeout_seconds,
            )
        else:
            transport = _StdioTransport(
                command=self._config.command,
                args=self._config.args,
                timeout_seconds=self._config.startup_timeout_seconds,
            )
        self._transport = transport
        await transport.open()
        self._reader_task = asyncio.create_task(self._reader_loop())
        await self.request(
            "initialize",
            {
                "clientInfo": {"name": "ai-desk-control-plane", "version": "0.1.0"},
                "capabilities": None,
            },
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._reader_task is not None:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader_task
            self._reader_task = None
        if self._transport is not None:
            await self._transport.aclose()
            self._transport = None

    async def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if self._transport is None:
            raise ExecutorTransportError("codex session is not open")
        self._next_id += 1
        request_id = self._next_id
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        await self._transport.send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )
        return await future

    async def next_notification(self) -> dict[str, Any]:
        return await asyncio.wait_for(
            self._notifications.get(), timeout=self._config.turn_timeout_seconds
        )

    async def _reader_loop(self) -> None:
        assert self._transport is not None
        while True:
            message = await self._transport.recv()
            if "id" in message:
                future = self._pending.pop(int(message["id"]), None)
                if future is None:
                    continue
                if "error" in message:
                    future.set_exception(
                        ExecutorTransportError(json.dumps(message["error"], ensure_ascii=False))
                    )
                else:
                    future.set_result(message.get("result"))
                continue
            await self._notifications.put(message)
