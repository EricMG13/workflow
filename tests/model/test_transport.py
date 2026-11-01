"""F9 transport limits with an injected clock and fake connection. No network."""

import http.client
import socket
from collections.abc import Iterator

import pytest

from deploy_workflow.model.transport import (
    ConnectTimeout,
    IdleTimeout,
    InsecureUrl,
    OverallTimeout,
    Request,
    TransportError,
    https_transport,
)


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

    def settimeout(self, value: float) -> None:
        self.timeouts.append(value)


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
        self.sock = FakeSock()
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
    assert conn.sock.timeouts == [120.0]
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
    assert conn.sock.timeouts == [900.0]
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
