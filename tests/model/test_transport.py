"""F9 transport limits with an injected clock and fake connection. No network."""

import http.client
import json
import socket
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow.model.providers import ErrorKind, ProviderError, error_from_transport
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.transport import (
    ConnectTimeout,
    IdleTimeout,
    InsecureUrl,
    OverallTimeout,
    Request,
    TransportError,
    https_transport,
)


LIMITS_KEY = Path(__file__).parents[2] / "cases" / "pilot-fixes" / "limits.json"
OVERALL_S = float(json.loads(LIMITS_KEY.read_text(encoding="utf-8"))["overall_s"])


@pytest.fixture(autouse=True)
def _default_transport_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("the default network path was used in a test")

    monkeypatch.setattr(http.client, "HTTPSConnection", boom)
    monkeypatch.setattr(socket, "create_connection", boom)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class FakeSock:
    def __init__(self) -> None:
        self.timeouts: list[float] = []
        self.shut = False

    def settimeout(self, value: float) -> None:
        self.timeouts.append(value)

    def shutdown(self, _how: int) -> None:
        self.shut = True


class FakeReply:
    def __init__(self, status: int, reads: Iterator[bytes | Exception]) -> None:
        self.status = status
        self._reads = reads

    def read1(self, _size: int = -1, /) -> bytes:
        item = next(self._reads, b"")
        if isinstance(item, Exception):
            raise item
        return item

    def getheaders(self) -> list[tuple[str, str]]:
        return [("Retry-After", "7"), ("Location", "https://elsewhere.example/")]


class FakeConnection:
    def __init__(
        self,
        reply: FakeReply,
        *,
        connect_error: Exception | None = None,
    ) -> None:
        self.reply = reply
        self.raw_sock = FakeSock()
        self.sock: Any = self.raw_sock
        self.connect_error = connect_error
        self.sent: list[tuple[str, str]] = []
        self.closed = False

    def connect(self) -> None:
        if self.connect_error:
            raise self.connect_error

    def request(self, method: str, url: str, body: bytes, headers: object) -> None:
        self.sent.append((method, url))

    def getresponse(self) -> FakeReply:
        return self.reply

    def close(self) -> None:
        self.closed = True


def _req(url: str = "https://api.example/v1/x", stream: bool = False) -> Request:
    return Request(url=url, headers={}, body=b"{}", stream=stream)


def test_http_refused_before_any_connection() -> None:
    def factory(*_a: object) -> FakeConnection:
        raise AssertionError("connected")

    with pytest.raises(InsecureUrl):
        https_transport(_req(url="http://api.example/x"), connection_factory=factory)


def test_connect_uses_connect_limit_and_times_out() -> None:
    seen: list[float] = []
    conn = FakeConnection(FakeReply(200, iter([])), connect_error=TimeoutError())

    def factory(host: str, port: int, timeout: float) -> FakeConnection:
        seen.append(timeout)
        assert (host, port) == ("api.example", 443)
        return conn

    with pytest.raises(ConnectTimeout):
        https_transport(_req(), clock=Clock(), connection_factory=factory)
    assert seen == [30.0]
    assert conn.closed


def test_connection_refused_is_a_transport_error_without_detail() -> None:
    conn = FakeConnection(FakeReply(200, iter([])), connect_error=ConnectionRefusedError("x"))
    with pytest.raises(TransportError, match="ConnectionRefusedError") as info:
        https_transport(_req(), clock=Clock(), connection_factory=lambda *_: conn)
    assert not isinstance(info.value, ConnectTimeout)


def test_stream_idle_timeout_after_data_keeps_partial() -> None:
    reads: Iterator[bytes | Exception] = iter([b"data: 1\n\n", TimeoutError()])
    conn = FakeConnection(FakeReply(200, reads))
    with pytest.raises(IdleTimeout) as info:
        https_transport(_req(stream=True), clock=Clock(), connection_factory=lambda *_: conn)
    assert conn.raw_sock.timeouts == [120.0]
    assert info.value.partial == b"data: 1\n\n"


def test_slow_trickle_past_overall_limit() -> None:
    clock = Clock()

    class Trickle(FakeReply):
        def read1(self, _size: int = -1, /) -> bytes:
            clock.now += 100.0  # a byte every 100 s: never idle for 120 s
            return b"x"

    conn = FakeConnection(Trickle(200, iter([])))
    with pytest.raises(OverallTimeout) as info:
        https_transport(_req(stream=True), clock=clock, connection_factory=lambda *_: conn)
    assert clock.now == 1000.0
    assert len(info.value.partial) == 10


def test_non_streaming_read_uses_overall_as_per_read_timeout() -> None:
    conn = FakeConnection(FakeReply(200, iter([b'{"ok":1}'])))
    out = https_transport(_req(), clock=Clock(), connection_factory=lambda *_: conn)
    assert conn.raw_sock.timeouts == [OVERALL_S]
    assert out.status == 200 and out.body == b'{"ok":1}'
    assert conn.sent == [("POST", "/v1/x")]


def test_non_streaming_silent_socket_is_an_overall_timeout() -> None:
    conn = FakeConnection(FakeReply(200, iter([TimeoutError()])))
    with pytest.raises(OverallTimeout):
        https_transport(_req(), clock=Clock(), connection_factory=lambda *_: conn)


def test_redirect_is_returned_not_followed() -> None:
    conn = FakeConnection(FakeReply(302, iter([b""])))
    out = https_transport(_req(), clock=Clock(), connection_factory=lambda *_: conn)
    assert out.status == 302
    assert out.headers["location"] == "https://elsewhere.example/"
    assert out.headers["retry-after"] == "7"
    assert len(conn.sent) == 1


class FakeTimer:
    def __init__(self, interval: float, fn: Callable[[], None]) -> None:
        self.interval, self.fn, self.cancelled, self.started = interval, fn, False, False

    def start(self) -> None:
        self.started = True

    def cancel(self) -> None:
        self.cancelled = True

    def join(self) -> None:
        self.joined = True


def test_watchdog_shuts_the_socket_at_the_deadline_and_is_an_overall_timeout() -> None:
    timers: list[FakeTimer] = []

    def factory(interval: float, fn: Callable[[], None]) -> FakeTimer:
        timers.append(FakeTimer(interval, fn))
        return timers[-1]

    class Hung(FakeReply):
        def read1(self, _size: int = -1, /) -> bytes:
            timers[0].fn()  # the deadline passes while the read is blocked
            raise OSError("socket shut down")

    conn = FakeConnection(Hung(200, iter([])))
    with pytest.raises(OverallTimeout):
        https_transport(
            _req(stream=True),
            clock=Clock(),
            connection_factory=lambda *_: conn,
            timer_factory=factory,
        )
    assert timers[0].interval == OVERALL_S and timers[0].started and timers[0].cancelled
    assert conn.raw_sock.shut


def test_watchdog_is_cancelled_on_success() -> None:
    timers: list[FakeTimer] = []

    def factory(interval: float, fn: Callable[[], None]) -> FakeTimer:
        timers.append(FakeTimer(interval, fn))
        return timers[-1]

    conn = FakeConnection(FakeReply(200, iter([b"ok"])))
    https_transport(
        _req(), clock=Clock(), connection_factory=lambda *_: conn, timer_factory=factory
    )
    assert timers[0].cancelled


def test_per_read_timeout_is_recomputed_before_each_socket_read() -> None:
    import io

    clock = Clock()
    seen: list[float] = []

    class Raw(io.RawIOBase):
        def readable(self) -> bool:
            return True

        def readinto(self, b: Any) -> int:
            clock.now += 400.0
            b[0:1] = b"x"
            return 1

    class Sock(FakeSock):
        def settimeout(self, value: float) -> None:
            seen.append(value)

        def makefile(self, _mode: str, buffering: int | None = None) -> Any:
            return Raw() if buffering == 0 else io.BufferedReader(Raw())

    class Conn(FakeConnection):
        def getresponse(self) -> Any:
            fp = self.sock.makefile("rb")
            for _ in range(4):
                fp.read(1)

    conn = Conn(FakeReply(200, iter([])))
    conn.sock = Sock()
    with pytest.raises(OverallTimeout):
        https_transport(_req(stream=True), clock=clock, connection_factory=lambda *_: conn)
    assert seen == [120.0, 120.0, 120.0, 100.0]  # the last read gets only what is left


class PairConn(http.client.HTTPConnection):
    """A real http.client connection over a local socketpair: no network."""

    def __init__(self, reply: bytes) -> None:
        super().__init__("api.example", 443, timeout=30)
        self._reply = reply
        self.peer: socket.socket | None = None

    def connect(self) -> None:
        self.sock, self.peer = socket.socketpair()
        self.peer.sendall(self._reply)


def test_real_socket_reply_is_read_through_the_bounded_socket() -> None:
    reply = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}"
    for stream in (False, True):
        conn = PairConn(reply)
        out = https_transport(
            _req(stream=stream),
            connection_factory=lambda *_, c=conn: c,
        )
        assert out.status == 200 and out.body == b"{}"


def test_non_transport_exception_after_send_is_classified() -> None:
    class Boom(FakeReply):
        def read1(self, _size: int = -1, /) -> bytes:
            raise ValueError("I/O operation on closed file")

    conn = FakeConnection(Boom(200, iter([])))
    with pytest.raises(TransportError, match="ValueError") as info:
        https_transport(_req(), clock=Clock(), connection_factory=lambda *_: conn)
    assert info.value.partial == b""
    err = error_from_transport("openai", info.value, Redactor())
    assert isinstance(err, ProviderError) and err.kind is ErrorKind.SENT_CHARGE_UNKNOWN


def test_watchdog_thread_is_joined_before_return() -> None:
    import threading

    before = {t.ident for t in threading.enumerate()}
    reply = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}"
    conn = PairConn(reply)
    https_transport(_req(), connection_factory=lambda *_: conn)
    assert [t for t in threading.enumerate() if t.ident not in before and t.is_alive()] == []
