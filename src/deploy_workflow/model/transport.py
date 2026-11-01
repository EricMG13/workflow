"""Bounded https transport: connect, idle and overall limits; https only; no redirect followed.

Error messages name the exception type and never carry a header, body or URL query, so a key
cannot reach them. A timeout error keeps the bytes read so far in ``partial`` so the caller
can settle a cut stream from a usage event that already arrived.
"""

from __future__ import annotations

import http.client
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, cast
from urllib.parse import urlsplit

CONNECT_S = 30.0
IDLE_S = 120.0  # spec §8
OVERALL_S = 900.0  # Q3
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


ConnectionFactory = Callable[[str, int, float], _Connection]


def _default_connection(host: str, port: int, timeout: float) -> _Connection:
    return cast(_Connection, http.client.HTTPSConnection(host, port, timeout=timeout))


def https_transport(
    request: Request,
    *,
    clock: Callable[[], float] = time.monotonic,
    connection_factory: ConnectionFactory = _default_connection,
) -> Response:
    parts = urlsplit(request.url)
    if parts.scheme != "https" or not parts.hostname:
        raise InsecureUrl("only https endpoints are permitted")
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    deadline = clock() + request.overall_s
    conn = connection_factory(parts.hostname, parts.port or 443, request.connect_s)
    chunks: list[bytes] = []
    try:
        try:
            conn.connect()
        except TimeoutError:
            raise ConnectTimeout(f"no connection within {request.connect_s} s") from None
        except OSError as error:
            raise TransportError(f"connection failed: {type(error).__name__}") from None
        per_read = request.idle_s if request.stream else max(deadline - clock(), 0.001)
        conn.sock.settimeout(per_read)
        timeout_error: type[TransportError] = IdleTimeout if request.stream else OverallTimeout
        try:
            conn.request("POST", path, request.body, request.headers)
            reply = conn.getresponse()
            while chunk := reply.read1(READ_CHUNK_BYTES):
                chunks.append(chunk)
                if clock() > deadline:
                    raise OverallTimeout(
                        f"wall-clock deadline of {request.overall_s} s exceeded",
                        b"".join(chunks),
                    )
        except TimeoutError:
            raise timeout_error(f"no byte within {per_read} s", b"".join(chunks)) from None
        except OSError as error:
            raise TransportError(
                f"network error: {type(error).__name__}", b"".join(chunks)
            ) from None
        except http.client.HTTPException as error:
            raise TransportError(f"http error: {type(error).__name__}", b"".join(chunks)) from None
        if clock() > deadline:
            raise OverallTimeout(
                f"wall-clock deadline of {request.overall_s} s exceeded", b"".join(chunks)
            )
        headers: dict[str, str] = {}
        for name, value in reply.getheaders():
            key = name.lower()
            headers[key] = f"{headers[key]}, {value}" if key in headers else value
        return Response(reply.status, b"".join(chunks), headers)
    finally:
        conn.close()
