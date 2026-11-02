"""Bounded https transport: connect, idle and overall limits; https only; no redirect followed.

Error messages name the exception type and never carry a header, body or URL query, so a key
cannot reach them. A timeout error keeps the bytes read so far in ``partial`` so the caller
can settle a cut stream from a usage event that already arrived.
"""

from __future__ import annotations

import http.client
import io
import socket
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, cast
from urllib.parse import urlsplit

CONNECT_S = 30.0
IDLE_S = 120.0  # spec §8
OVERALL_S = 1800.0  # PF-R13: Deploy VII sol-high took 692 s for 55K output tokens (limits.json)
READ_CHUNK_BYTES = 64 * 1024


class TransportError(Exception):
    """The request could not complete. The message never holds a key."""

    def __init__(self, message: str, partial: bytes = b"") -> None:
        super().__init__(message)
        self.partial = partial


class InsecureUrl(TransportError):
    """Refused before any connection: not https."""


class ConnectTimeout(TransportError):
    """No connection within ``connect_s``."""


class IdleTimeout(TransportError):
    """No byte for ``idle_s`` on a streamed reply."""


class OverallTimeout(TransportError):
    """The wall-clock deadline ``overall_s`` passed."""


@dataclass(frozen=True)
class Request:
    url: str
    headers: Mapping[str, str] = field(repr=False)
    body: bytes = field(repr=False)
    connect_s: float = CONNECT_S
    idle_s: float = IDLE_S
    overall_s: float = OVERALL_S
    stream: bool = False


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes = field(repr=False)
    headers: Mapping[str, str] = field(default_factory=dict, repr=False)  # lower-case names


Transport = Callable[[Request], Response]


class _Reply(Protocol):
    status: int

    def read1(self, size: int = -1, /) -> bytes: ...
    def getheaders(self) -> list[tuple[str, str]]: ...


class _Connection(Protocol):
    sock: Any

    def connect(self) -> None: ...
    def request(self, method: str, url: str, body: bytes, headers: Mapping[str, str]) -> None: ...
    def getresponse(self) -> _Reply: ...
    def close(self) -> None: ...


class _Timer(Protocol):
    def start(self) -> None: ...
    def cancel(self) -> None: ...
    def join(self) -> None: ...


ConnectionFactory = Callable[[str, int, float], _Connection]
TimerFactory = Callable[[float, Callable[[], None]], _Timer]


def _default_connection(host: str, port: int, timeout: float) -> _Connection:
    return cast(_Connection, http.client.HTTPSConnection(host, port, timeout=timeout))


def _default_timer(interval: float, function: Callable[[], None]) -> _Timer:
    timer = threading.Timer(interval, function)
    timer.daemon = True
    return timer


class _Deadline:
    """Shared state of one call: the wall-clock deadline and the watchdog's verdict."""

    def __init__(self, request: Request, clock: Callable[[], float]) -> None:
        self.request = request
        self.clock = clock
        self.at = clock() + request.overall_s
        self.expired = threading.Event()

    def remaining(self) -> float:
        return self.at - self.clock()

    def per_read(self) -> float:
        """The socket timeout for the next read: idle (streaming) capped by what is left."""
        left = max(self.remaining(), 0.001)
        return min(self.request.idle_s, left) if self.request.stream else left

    def overall_timeout(self, partial: bytes = b"") -> OverallTimeout:
        return OverallTimeout(
            f"wall-clock deadline of {self.request.overall_s} s exceeded", partial
        )


class _BoundedRaw(io.RawIOBase):
    """Raw reader over the socket's own file: before every socket read it refuses past the
    deadline and sets the timeout to what is left, so a header or chunk-size trickle ends
    at the overall limit."""

    def __init__(self, inner: Any, sock: Any, deadline: _Deadline) -> None:
        super().__init__()
        self._inner, self._sock, self._deadline = inner, sock, deadline

    def readable(self) -> bool:
        return True

    def readinto(self, b: Any) -> int | None:
        if self._deadline.expired.is_set() or self._deadline.remaining() <= 0:
            raise self._deadline.overall_timeout()
        self._sock.settimeout(self._deadline.per_read())
        return cast(int | None, self._inner.readinto(b))

    def close(self) -> None:
        self._inner.close()
        super().close()


class _BoundedSocket:
    """The connection's socket with `makefile` bounded by the deadline; the rest delegates."""

    def __init__(self, sock: Any, deadline: _Deadline) -> None:
        self._sock, self._deadline = sock, deadline

    def makefile(self, mode: str = "rb") -> io.BufferedReader:
        # buffering=0 is the SocketIO itself: keeping only `.raw` of a buffered file would let
        # the dropped wrapper close the shared SocketIO when it is garbage-collected.
        raw = self._sock.makefile(mode, buffering=0)
        return io.BufferedReader(_BoundedRaw(raw, self._sock, self._deadline))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sock, name)


def https_transport(
    request: Request,
    *,
    clock: Callable[[], float] = time.monotonic,
    connection_factory: ConnectionFactory = _default_connection,
    timer_factory: TimerFactory = _default_timer,
) -> Response:
    """One bounded call. The overall limit is hard: a watchdog shuts the socket at the
    deadline (a timer shutdown is an OverallTimeout), every socket read is given only the
    time left, and the deadline is checked after every read."""
    parts = urlsplit(request.url)
    if parts.scheme != "https" or not parts.hostname:
        raise InsecureUrl("only https endpoints are permitted")
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    deadline = _Deadline(request, clock)
    conn = connection_factory(parts.hostname, parts.port or 443, request.connect_s)
    chunks: list[bytes] = []
    watchdog: _Timer | None = None
    try:
        try:
            conn.connect()
        except TimeoutError:
            raise ConnectTimeout(f"no connection within {request.connect_s} s") from None
        except OSError as error:
            raise TransportError(f"connection failed: {type(error).__name__}") from None
        raw_sock = conn.sock
        per_read = deadline.per_read()
        raw_sock.settimeout(per_read)
        conn.sock = _BoundedSocket(raw_sock, deadline)

        def expire() -> None:
            deadline.expired.set()
            try:
                raw_sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass  # already closed or never connected: the flag above still ends the call

        timer = timer_factory(max(deadline.remaining(), 0.0), expire)
        timer.start()
        watchdog = timer
        timeout_error: type[TransportError] = IdleTimeout if request.stream else OverallTimeout
        try:
            conn.request("POST", path, request.body, request.headers)
            reply = conn.getresponse()
            while chunk := reply.read1(READ_CHUNK_BYTES):
                chunks.append(chunk)
                if deadline.expired.is_set() or deadline.remaining() < 0:
                    raise deadline.overall_timeout(b"".join(chunks))
        except TransportError as error:
            error.partial = error.partial or b"".join(chunks)
            raise
        except TimeoutError:
            if deadline.expired.is_set() or deadline.remaining() <= 0:
                raise deadline.overall_timeout(b"".join(chunks)) from None
            raise timeout_error(f"no byte within {per_read} s", b"".join(chunks)) from None
        except OSError as error:
            if deadline.expired.is_set():
                raise deadline.overall_timeout(b"".join(chunks)) from None
            raise TransportError(
                f"network error: {type(error).__name__}", b"".join(chunks)
            ) from None
        except http.client.HTTPException as error:
            if deadline.expired.is_set():
                raise deadline.overall_timeout(b"".join(chunks)) from None
            raise TransportError(f"http error: {type(error).__name__}", b"".join(chunks)) from None
        except (
            ValueError,
            RuntimeError,
            TypeError,
            AttributeError,
            LookupError,
            EOFError,
        ) as error:
            # Anything else after the send (e.g. ValueError from a closed file) may have reached
            # the provider: it becomes a named TransportError, so the caller classifies it
            # SentChargeUnknown. Not swallowed: the type is kept in the message.
            if deadline.expired.is_set():
                raise deadline.overall_timeout(b"".join(chunks)) from None
            raise TransportError(
                f"unexpected error: {type(error).__name__}", b"".join(chunks)
            ) from None
        if deadline.expired.is_set() or deadline.remaining() < 0:
            raise deadline.overall_timeout(b"".join(chunks))
        headers: dict[str, str] = {}
        for name, value in reply.getheaders():
            key = name.lower()
            headers[key] = f"{headers[key]}, {value}" if key in headers else value
        return Response(reply.status, b"".join(chunks), headers)
    finally:
        if watchdog is not None:
            watchdog.cancel()
            watchdog.join()  # no watchdog thread outlives the call
        conn.close()
