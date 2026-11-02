"""Fetch one https URL safely: public addresses only, pinned TLS, bounded redirects and reads.

A leaf: it imports no project module but ``research.contracts`` and consults no process-level settings.
The resolver, the connector and the clock are injected; ``system_resolver`` and
``pinned_connection`` are the production values. Every address a host resolves to is checked
before any connection, and the connection is made to the address that was checked, so a second
lookup cannot change where the request goes. A refused fetch is recorded on the returned
``FetchRecord`` (its ``reason``); nothing is filled in and no body of a refused fetch is returned.
"""

import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from email.utils import parsedate_to_datetime
from typing import Protocol
from urllib.parse import SplitResult, urljoin, urlsplit

from deploy_workflow.research.contracts import ResearchError

MAX_REDIRECTS = 3
CONNECT_TIMEOUT_S = 10
TOTAL_TIMEOUT_S = 30
HEADERS: Mapping[str, str] = {
    "User-Agent": "deploy-workflow-cpdr",
    "Accept": "text/html, text/plain",
}
SOURCE_HEADER = "header:last-modified"
SOURCE_BODY = "body:published-line"

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_PUBLISHED_LINE = re.compile(r"^Published:[ \t]*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
_UNSAFE = re.compile(r"[\x00-\x20\x7f]")


class UrlRefused(ResearchError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class FetchRefusal(ResearchError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class SplitUrl:
    scheme: str
    host: str
    port: int
    path_query: str


@dataclass(frozen=True)
class ConnectionTarget:
    host: str
    ip: str
    port: int
    timeout: float


@dataclass(frozen=True)
class FetchRecord:
    url: str
    resolved_ip: str | None
    status: int | None
    bytes: int | None
    sha256: str | None
    published_located: str | None
    published_source: str | None
    hops: int
    item_id: str | None
    reason: str | None


FetchOutcome = FetchRecord


class ResponseLike(Protocol):
    status: int

    def getheader(self, name: str, /) -> str | None: ...

    def read(self, amt: int) -> bytes: ...


class ConnectionLike(Protocol):
    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None: ...

    def getresponse(self) -> ResponseLike: ...

    def close(self) -> None: ...


Resolver = Callable[[str], Sequence[str]]
Connector = Callable[[ConnectionTarget], ConnectionLike]


def _problem(parts: SplitResult) -> str | None:
    """Why a split URL is not an acceptable https target, or None."""
    if parts.scheme.lower() != "https":
        return "the scheme must be https"
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        return "a user name or password is not allowed"
    try:
        host, _port = parts.hostname, parts.port
    except ValueError:
        return "the port is not valid"
    if not host:
        return "the host is missing"
    return None


def _split(url: str, refuse: Callable[[str], UrlRefused]) -> SplitUrl:
    if _UNSAFE.search(url):
        raise refuse("control characters and spaces are not allowed")
    parts = urlsplit(url)
    problem = _problem(parts)
    if problem is not None:
        raise refuse(problem)
    path = parts.path or "/"
    return SplitUrl(
        "https",
        parts.hostname or "",
        parts.port or 443,
        f"{path}?{parts.query}" if parts.query else path,
    )


def check_url(url: str) -> SplitUrl:
    """The static shape of a manifest URL, or ``UrlRefused`` naming why not."""
    return _split(url, lambda problem: UrlRefused(f"url {url}: {problem}"))


def is_public(addr: str) -> bool:
    """ipaddress is_global after unwrapping ::ffff:a.b.c.d, and not multicast, reserved or site-local."""
    try:
        address: ipaddress.IPv4Address | ipaddress.IPv6Address = ipaddress.ip_address(addr)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    barred = address.is_multicast or address.is_reserved
    if isinstance(address, ipaddress.IPv6Address):
        barred = barred or address.is_site_local
    return address.is_global and not barred


def resolve_public(host: str, resolver: Resolver) -> str:
    """Resolve once; every address must be public. Returns the first address."""
    try:
        addresses = list(resolver(host))
    except OSError as error:
        raise FetchRefusal(f"host {host} did not resolve: {type(error).__name__}") from error
    if not addresses:
        raise FetchRefusal(f"host {host} did not resolve")
    for address in addresses:
        if not is_public(address):
            raise FetchRefusal(f"host {host} resolves to {address}, which is not a public address")
    return addresses[0]


def system_resolver(host: str) -> list[str]:
    """Every address the system resolver returns for the host, in order, without repeats."""
    found = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(str(entry[4][0]) for entry in found))


def tls_context() -> ssl.SSLContext:
    return ssl.create_default_context()


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """An https connection to a given address that verifies the certificate for the host name."""

    def __init__(
        self, host: str, ip: str, *, port: int, timeout: float, context: ssl.SSLContext
    ) -> None:
        super().__init__(host, port=port, timeout=timeout, context=context)
        self._pinned_ip = ip
        self._tls = context

    def connect(self) -> None:
        sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        try:
            self.sock = self._tls.wrap_socket(sock, server_hostname=self.host)
        except OSError:
            sock.close()
            raise


def pinned_connection(target: ConnectionTarget) -> ConnectionLike:
    return PinnedHTTPSConnection(
        target.host, target.ip, port=target.port, timeout=target.timeout, context=tls_context()
    )


def locate_published(headers: Mapping[str, str], body: bytes) -> tuple[date | None, str | None]:
    """A publication date found in ``Last-Modified`` or a ``Published: YYYY-MM-DD`` body line.

    Only reported: the manifest row's own date decides admission (D6). An unparsable value is
    "not located".
    """
    for name, value in headers.items():
        if name.lower() == "last-modified":
            try:
                return parsedate_to_datetime(value).date(), SOURCE_HEADER
            except (TypeError, ValueError, IndexError):
                break
    match = _PUBLISHED_LINE.search(body.decode("utf-8", errors="replace"))
    if match:
        try:
            return date.fromisoformat(match.group(1)), SOURCE_BODY
        except ValueError:
            return None, None
    return None, None


@dataclass
class _Trace:
    resolved_ip: str | None = None
    status: int | None = None
    hops: int = 0


@dataclass(frozen=True)
class _Limits:
    manifest_hosts: frozenset[str]
    resolver: Resolver
    connect: Connector
    cap: int
    connect_timeout: float
    total_timeout: float
    clock: Callable[[], float]
    started: float


def _host_header(split: SplitUrl) -> str:
    host = f"[{split.host}]" if ":" in split.host else split.host
    return host if split.port == 443 else f"{host}:{split.port}"


def _next_hop(
    url: str, current: SplitUrl, location: str | None, trace: _Trace, limits: _Limits
) -> SplitUrl:
    """The checked target of a redirect; counts the hop once it has passed the checks."""
    if not location:
        raise FetchRefusal(f"{url} redirected without a location")
    target = urljoin(f"https://{_host_header(current)}{current.path_query}", location)
    nxt = _split(target, lambda problem: UrlRefused(f"redirect to {target} refused: {problem}"))
    if nxt.host.lower() not in limits.manifest_hosts:
        raise FetchRefusal(f"redirect to host {nxt.host} refused: not a host named in the manifest")
    if trace.hops >= MAX_REDIRECTS:
        raise FetchRefusal(f"{url} redirected more than {MAX_REDIRECTS} times")
    trace.hops += 1
    return nxt


def _check_time(url: str, limits: _Limits) -> None:
    if limits.clock() - limits.started > limits.total_timeout:
        raise FetchRefusal(f"{url} took longer than {limits.total_timeout:g} seconds")


def _read_bounded(url: str, response: ResponseLike, limits: _Limits) -> bytes:
    """At most ``cap + 1`` bytes in total; one byte over the cap is a refusal, never a truncation."""
    chunks: list[bytes] = []
    got = 0
    while got <= limits.cap:
        chunk = response.read(limits.cap + 1 - got)
        if not chunk:
            break
        chunks.append(chunk)
        got += len(chunk)
        _check_time(url, limits)
    if got > limits.cap:
        raise FetchRefusal(f"{url} body is larger than the {limits.cap}-byte cap")
    return b"".join(chunks)


def _exchange(
    url: str, split: SplitUrl, trace: _Trace, limits: _Limits
) -> tuple[SplitUrl | None, bytes, str | None, dict[str, str]]:
    """One hop: resolve, check, connect to the checked address, request. Returns the next hop
    (when redirected) or the body, the Content-Type and the headers worth keeping."""
    trace.resolved_ip = resolve_public(split.host, limits.resolver)
    target = ConnectionTarget(split.host, trace.resolved_ip, split.port, limits.connect_timeout)
    connection = limits.connect(target)
    try:
        _check_time(url, limits)
        connection.request(
            "GET", split.path_query, headers={"Host": _host_header(split), **HEADERS}
        )
        response = connection.getresponse()
        trace.status = response.status
        if response.status in _REDIRECT_STATUSES:
            return (
                _next_hop(url, split, response.getheader("Location"), trace, limits),
                b"",
                None,
                {},
            )
        if response.status != 200:
            raise FetchRefusal(f"{url} answered status {response.status}")
        body = _read_bounded(url, response, limits)
        media = response.getheader("Content-Type")
        modified = response.getheader("Last-Modified")
        return None, body, media, ({"Last-Modified": modified} if modified else {})
    finally:
        connection.close()


def _follow(url: str, trace: _Trace, limits: _Limits) -> tuple[bytes, str | None, dict[str, str]]:
    split: SplitUrl | None = check_url(url)
    while split is not None:
        split, body, media, headers = _exchange(url, split, trace, limits)
    return body, media, headers


def _refused(url: str, trace: _Trace, reason: str) -> tuple[FetchRecord, None, None]:
    return (
        FetchRecord(
            url, trace.resolved_ip, trace.status, None, None, None, None, trace.hops, None, reason
        ),
        None,
        None,
    )


def fetch(
    url: str,
    *,
    manifest_hosts: frozenset[str],
    resolver: Resolver,
    connect: Connector,
    cap: int,
    connect_timeout: float = CONNECT_TIMEOUT_S,
    total_timeout: float = TOTAL_TIMEOUT_S,
    clock: Callable[[], float],
) -> tuple[FetchRecord, bytes | None, str | None]:
    """Fetch ``url``: the record, the retained raw body and the Content-Type value.

    A refusal returns a record with ``reason`` set and no body. Network failures (``OSError``,
    ``http.client.HTTPException``) are refusals too, recorded with the exception class name only.
    """
    trace = _Trace()
    limits = _Limits(
        manifest_hosts, resolver, connect, cap, connect_timeout, total_timeout, clock, clock()
    )
    try:
        body, media, headers = _follow(url, trace, limits)
    except (UrlRefused, FetchRefusal) as refusal:
        return _refused(url, trace, refusal.reason)
    except TimeoutError:
        return _refused(url, trace, f"{url} took longer than {total_timeout:g} seconds")
    except (OSError, http.client.HTTPException) as error:
        return _refused(url, trace, f"{url} could not be fetched: {type(error).__name__}")
    located, source = locate_published(headers, body)
    record = FetchRecord(
        url,
        trace.resolved_ip,
        trace.status,
        len(body),
        hashlib.sha256(body).hexdigest(),
        located.isoformat() if located else None,
        source,
        trace.hops,
        None,
        None,
    )
    return record, body, media
