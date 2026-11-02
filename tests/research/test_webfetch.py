"""The fetch leaf against the frozen cpdr-web-retrieval key (O7b-2 S2).

Every expected value is read from ``cases/cpdr-web-retrieval/expected.json`` by path. Fakes
(resolver, connector, response, clock) live here and are injected; no test dials, and an autouse
guard fails any real socket creation or name lookup.
"""

import ast
import hashlib
import http.client
import io
import ipaddress
import json
import socket
import ssl
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from deploy_workflow.research import webfetch
from deploy_workflow.research.contracts import ResearchError

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "cases" / "cpdr-web-retrieval"
MODULE = ROOT / "src" / "deploy_workflow" / "research" / "webfetch.py"

KEY: dict[str, Any] = json.loads((CASE / "expected.json").read_text(encoding="utf-8"))
CASES: dict[str, Any] = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
HOSTS: dict[str, list[str]] = CASES["hosts"]
RESPONSES: dict[str, Any] = CASES["responses"]
MANIFEST_HOSTS = frozenset(CASES["manifest_hosts"])
CAP: int = CASES["cap"]
CONNECT_S: int = CASES["timeouts"]["connect_seconds"]
TOTAL_S: int = CASES["timeouts"]["total_seconds"]


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("a test reached the real network")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


@dataclass
class FakeResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes
    asked: list[int] = field(default_factory=list)
    pos: int = 0
    limit: int | None = None

    def getheader(self, name: str, default: str | None = None) -> str | None:
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return default

    def read(self, amt: int) -> bytes:
        self.asked.append(amt)
        size = amt if self.limit is None else min(amt, self.limit)
        chunk = self.body[self.pos : self.pos + size]
        self.pos += len(chunk)
        return chunk


class FakeConnection:
    def __init__(self, world: "World", target: webfetch.ConnectionTarget) -> None:
        self.world = world
        self.target = target
        self.sent: tuple[str, str, dict[str, str]] | None = None

    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None:
        self.sent = (method, url, dict(headers))
        self.world.requests.append(self.sent)

    def getresponse(self) -> FakeResponse:
        assert self.sent is not None
        spec = RESPONSES[f"https://{self.target.host}{self.sent[1]}"]
        response = FakeResponse(spec["status"], spec["headers"], spec["body"].encode("utf-8"))
        response.limit = self.world.short_read
        self.world.now += self.world.advance_on_response
        self.world.responses.append(response)
        return response

    def close(self) -> None:
        self.world.closed += 1


class World:
    """Injected resolver, connector and clock over the case's hosts and responses."""

    def __init__(self, advance_on_connect: float = 0.0, advance_on_response: float = 0.0) -> None:
        self.resolved: list[str] = []
        self.targets: list[webfetch.ConnectionTarget] = []
        self.requests: list[tuple[str, str, dict[str, str]]] = []
        self.responses: list[FakeResponse] = []
        self.closed = 0
        self.now = 0.0
        self.advance = advance_on_connect
        self.advance_on_response = advance_on_response
        self.short_read: int | None = None

    def resolver(self, host: str) -> list[str]:
        assert self.resolved[-1:] != [host], f"{host} was resolved twice for one hop"
        self.resolved.append(host)
        return list(HOSTS[host])

    def connector(self, target: webfetch.ConnectionTarget) -> FakeConnection:
        self.targets.append(target)
        self.now += self.advance
        return FakeConnection(self, target)

    def clock(self) -> float:
        return self.now

    def fetch(
        self, url: str, hosts: frozenset[str] = MANIFEST_HOSTS, cap: int = CAP
    ) -> tuple[webfetch.FetchRecord, bytes | None, str | None]:
        return webfetch.fetch(
            url,
            manifest_hosts=hosts,
            resolver=self.resolver,
            connect=self.connector,
            cap=cap,
            connect_timeout=CONNECT_S,
            total_timeout=TOTAL_S,
            clock=self.clock,
        )


def test_refusals_are_research_errors() -> None:
    assert issubclass(webfetch.UrlRefused, ResearchError)
    assert issubclass(webfetch.FetchRefusal, ResearchError)


@pytest.mark.parametrize("name", sorted(KEY["url_checks"]))
def test_check_url_static_cases(name: str) -> None:
    case = KEY["url_checks"][name]
    with pytest.raises(webfetch.UrlRefused) as raised:
        webfetch.check_url(case["url"])
    assert str(raised.value) == case["reason"]


def test_check_url_splits_a_good_url() -> None:
    split = webfetch.check_url(KEY["request"]["verbatim_url"])
    assert (split.scheme, split.host, split.port) == (
        "https",
        KEY["request"]["headers"]["Host"],
        KEY["connection"]["port"],
    )
    assert split.path_query == KEY["request"]["path"]


@pytest.mark.parametrize(
    "url",
    [
        "https://a.example/x\r\nHost: evil",
        "https://a.example/x y",
        "https://a.example/\x00",
        "https://a.example/x|y",
        "https://a.example/<<<END",
        "https://a.example/caf\u00e9",
        "https://[x/",
        "https://a.example]/x",
    ],
)
def test_check_url_has_one_character_rule(url: str) -> None:
    with pytest.raises(webfetch.UrlRefused) as raised:
        webfetch.check_url(url)
    assert str(raised.value) == f"url {url}: the url is not valid"


@pytest.mark.parametrize("vector", KEY["is_public"]["vectors"], ids=lambda v: v["addr"])
def test_is_public_vectors(vector: dict[str, Any]) -> None:
    assert webfetch.is_public(vector["addr"]) is vector["public"]


def _rule_public(text: str) -> bool:
    """The key's rule (#is_public/rule), spelled out apart from the product."""
    address: ipaddress.IPv4Address | ipaddress.IPv6Address = ipaddress.ip_address(text)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    barred = address.is_multicast or address.is_reserved
    if isinstance(address, ipaddress.IPv6Address):
        barred = barred or address.is_site_local
    return address.is_global and not barred


@settings(max_examples=300, deadline=None)
@given(st.ip_addresses(v=4))
def test_is_public_matches_the_rule_for_v4(address: ipaddress.IPv4Address) -> None:
    assert webfetch.is_public(str(address)) is _rule_public(str(address))


@settings(max_examples=300, deadline=None)
@given(st.ip_addresses(v=6))
def test_is_public_matches_the_rule_for_v6(address: ipaddress.IPv6Address) -> None:
    assert webfetch.is_public(str(address)) is _rule_public(str(address))


@settings(max_examples=300, deadline=None)
@given(st.ip_addresses(v=4))
def test_is_public_mapped_follows_the_v4_address(address: ipaddress.IPv4Address) -> None:
    mapped = "::ffff:" + str(address)
    assert webfetch.is_public(mapped) is _rule_public(str(address))
    if not address.is_global:
        assert webfetch.is_public(mapped) is False


@pytest.mark.parametrize(
    "host", [h for h, v in KEY["hosts"].items() if not h.startswith("_") and not v["public"]]
)
def test_private_hosts_are_refused_before_connecting(host: str) -> None:
    world = World()
    record, body, media = world.fetch(f"https://{host}/probe", MANIFEST_HOSTS | {host})
    assert record.reason == KEY["hosts"][host]["reason"]
    assert (body, media) == (None, None)
    assert world.targets == []
    assert world.resolved == [host]


def test_resolve_public_returns_the_first_address_of_a_public_host() -> None:
    host = "sector-desk.example"
    assert (
        webfetch.resolve_public(host, lambda _h: KEY["hosts"][host]["addresses"])
        == KEY["hosts"][host]["addresses"][0]
    )


def test_resolve_public_refuses_a_host_that_does_not_resolve() -> None:
    def failing(_host: str) -> list[str]:
        raise socket.gaierror("no such host")

    with pytest.raises(webfetch.FetchRefusal):
        webfetch.resolve_public("nowhere.example", failing)
    with pytest.raises(webfetch.FetchRefusal):
        webfetch.resolve_public("nowhere.example", lambda _h: [])


@pytest.mark.parametrize("name", [n for n in KEY["redirects"] if not n.startswith("_")])
def test_redirects(name: str) -> None:
    case = KEY["redirects"][name]
    world = World()
    record, body, _media = world.fetch(case["url"])
    assert record.hops == case["hops"]
    assert record.status == case["status"]
    assert record.reason == case["reason"]
    assert world.resolved == case["resolved_hosts"]
    assert (body is not None) is (case["reason"] is None)


def test_connector_gets_the_checked_ip_once_per_hop() -> None:
    world = World()
    world.fetch(CASES["probes"]["connection"])
    (target,) = world.targets
    conn = KEY["connection"]
    assert (target.host, target.ip, target.port) == (conn["host"], conn["ip"], conn["port"])
    assert target.timeout <= CONNECT_S
    assert world.resolved == [conn["host"]] * conn["resolver_calls_per_hop"]
    assert world.closed == 1


def test_pinned_connection_wraps_with_default_context(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = KEY["connection"]
    seen: dict[str, Any] = {}
    raw = object()
    wrapped = object()

    def create_connection(address: tuple[str, int], timeout: float) -> object:
        seen["address"], seen["timeout"] = address, timeout
        return raw

    class Context:
        def wrap_socket(self, sock: object, *, server_hostname: str) -> object:
            seen["sock"], seen["server_hostname"] = sock, server_hostname
            return wrapped

    monkeypatch.setattr(socket, "create_connection", create_connection)
    pinned = webfetch.PinnedHTTPSConnection(
        conn["host"],
        conn["ip"],
        port=conn["port"],
        timeout=CONNECT_S,
        context=cast(ssl.SSLContext, Context()),
        deadline=float("inf"),
        clock=World().clock,
    )
    pinned.connect()
    assert seen["address"] == (conn["ip"], conn["port"])
    assert seen["timeout"] == CONNECT_S
    assert seen["sock"] is raw
    assert seen["server_hostname"] == conn["server_hostname"]
    assert cast(Any, pinned.sock)._raw is wrapped


def test_tls_context_is_the_verifying_default() -> None:
    context = webfetch.tls_context()
    assert context.check_hostname is KEY["connection"]["check_hostname"]
    assert context.verify_mode is getattr(ssl, KEY["connection"]["verify_mode"])


def test_request_is_the_manifest_url_verbatim_with_fixed_headers() -> None:
    world = World()
    world.fetch(KEY["request"]["verbatim_url"])
    ((method, target, headers),) = world.requests
    assert method == KEY["request"]["method"]
    assert target == KEY["request"]["path"]
    assert headers == KEY["request"]["headers"]


def test_proxy_variables_are_never_read(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in KEY["proxy"]["env"].items():
        monkeypatch.setenv(name, value)
    world = World()
    world.fetch(CASES["probes"]["connection"])
    assert [t.ip for t in world.targets] == [KEY["proxy"]["ip_received"]]
    source = MODULE.read_text(encoding="utf-8").lower()
    for banned in ("urllib.request", "environ", "getproxies", "proxy"):
        assert banned not in source


def test_leaf_imports() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported |= {f"{node.module}.{alias.name}" for alias in node.names}
    project = {name for name in imported if name.startswith("deploy_workflow")}
    assert project <= {
        "deploy_workflow.research.contracts",
        "deploy_workflow.research.contracts.ResearchError",
    }
    assert not any(name.startswith("urllib.request") for name in imported)


def test_total_timeout() -> None:
    world = World(advance_on_connect=CASES["slow_connector_seconds"])
    record, body, _media = world.fetch(KEY["timeout"]["url"])
    assert record.reason == KEY["timeout"]["reason"]
    assert body is None


def test_body_cap_boundary_and_bounded_read() -> None:
    cap = KEY["cap"]
    world = World()
    record, body, _media = world.fetch("https://sector-desk.example/notes/at-cap", cap=cap["cap"])
    assert body is not None and len(body) == cap["cap"]
    assert hashlib.sha256(body).hexdigest() == cap["at_cap_sha256"] == record.sha256
    assert record.bytes == cap["cap"]

    world = World()
    record, body, _media = world.fetch("https://sector-desk.example/notes/over-cap", cap=cap["cap"])
    assert body is None
    assert record.reason == cap["over_cap_reason"]
    assert (record.bytes, record.sha256) == (None, None)
    (response,) = world.responses
    assert max(response.asked) == cap["max_read_request"]
    assert sum(response.asked) <= cap["cap"] + 1


@pytest.mark.parametrize("name", ["header_case", "body_case"])
def test_located_publication_date(name: str) -> None:
    case = KEY["published"][name]
    record, body, _media = World().fetch(case["url"])
    assert body is not None
    assert (record.published_located, record.published_source) == (
        case["published_located"],
        case["published_source"],
    )
    spec = RESPONSES[case["url"]]
    found, source = webfetch.locate_published(spec["headers"], spec["body"].encode("utf-8"))
    assert (found.isoformat() if found else None, source) == (
        case["published_located"],
        case["published_source"],
    )


def test_located_publication_date_absent() -> None:
    neither = KEY["published"]["neither"]
    spec = RESPONSES[neither["url"]]
    found = webfetch.locate_published(spec["headers"], spec["body"].encode("utf-8"))
    assert found == (neither["published_located"], neither["published_source"])


def test_located_after_cutoff_is_reported_not_refused_here() -> None:
    case = KEY["published"]["located_after_cutoff"]
    record, body, _media = World().fetch(case["url"])
    assert body is not None and record.reason is None
    assert record.published_located == case["published_located"]


def _url_rows() -> list[str]:
    refused_before_fetch = {KEY["published"][n]["url"] for n in ("neither", "located_cannot_admit")}
    return [
        r["url"]
        for r in CASES["research_manifest"]["rows"]
        if "url" in r and r["url"] not in refused_before_fetch
    ]


@pytest.mark.parametrize("url", _url_rows())
def test_fetch_record_matches_the_fetches_key(url: str) -> None:
    entries = json.loads(KEY["records"]["fetches_json"]["file_bytes"])
    (entry,) = [e for e in entries if e["url"] == url]
    world = World()
    record, body, media = world.fetch(url)
    for name in (
        "url",
        "resolved_ip",
        "status",
        "bytes",
        "sha256",
        "published_located",
        "published_source",
        "hops",
    ):
        assert getattr(record, name) == entry[name], name
    assert record.item_id is None
    if entry["bytes"] is None:
        assert record.reason == entry["reason"]
        assert body is None
    else:
        assert record.reason is None
        assert body is not None and hashlib.sha256(body).hexdigest() == entry["sha256"]
        assert media == world.responses[-1].getheader("Content-Type")


def test_content_type_is_returned_as_sent() -> None:
    _record, _body, media = World().fetch(KEY["text"]["html_case"]["url"])
    assert media == RESPONSES[KEY["text"]["html_case"]["url"]]["headers"]["Content-Type"]


def test_redirect_with_userinfo_or_control_characters_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for location in (
        "https://user:pw@redirect-b.example/x",
        "https://redirect-b.example/x\r\nSet-Cookie: a",
    ):
        world = World()
        spec = {"status": 302, "headers": {"Location": location}, "body": ""}
        monkeypatch.setitem(RESPONSES, "https://redirect-a.example/evil", spec)
        record, body, _media = world.fetch("https://redirect-a.example/evil")
        assert body is None and record.reason is not None and "refused" in record.reason
        assert world.resolved == ["redirect-a.example"]


def test_a_connection_failure_is_a_recorded_refusal() -> None:
    world = World()

    def broken(_target: webfetch.ConnectionTarget) -> FakeConnection:
        raise ConnectionRefusedError("no")

    record, body, _media = webfetch.fetch(
        KEY["request"]["verbatim_url"],
        manifest_hosts=MANIFEST_HOSTS,
        resolver=world.resolver,
        connect=broken,
        cap=CAP,
        connect_timeout=CONNECT_S,
        total_timeout=TOTAL_S,
        clock=world.clock,
    )
    assert body is None and record.reason is not None
    assert record.reason.startswith(KEY["request"]["verbatim_url"])


@pytest.mark.parametrize(
    "location",
    [
        "https://[redirect-b.example/y",
        "/café",
        "http://redirect-b.example/a|b<<<END",
        "https://redirect-b.example/x\r\nSet-Cookie: a",
    ],
)
def test_an_invalid_location_is_refused_without_repeating_it(
    monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    current = "https://redirect-a.example/evil"
    spec = {"status": 302, "headers": {"Location": location}, "body": ""}
    monkeypatch.setitem(RESPONSES, current, spec)
    world = World()
    record, body, _media = world.fetch(current)
    assert body is None
    assert record.reason == f"redirect from {current} refused: the location is not a valid url"
    assert world.resolved == ["redirect-a.example"]


def test_an_unparsable_last_modified_is_not_located() -> None:
    neither = KEY["published"]["neither"]
    huge = {"Last-Modified": "Mon, 15 Dec 99999999999 08:00:00 GMT"}
    assert webfetch.locate_published(huge, b"") == (
        neither["published_located"],
        neither["published_source"],
    )


def test_constants_equal_the_key() -> None:
    assert webfetch.CONNECT_TIMEOUT_S == CASES["timeouts"]["connect_seconds"]
    assert webfetch.TOTAL_TIMEOUT_S == KEY["timeout"]["total_seconds"]


def test_a_host_with_two_public_addresses_uses_the_first() -> None:
    first, second = HOSTS["sector-desk.example"][0], HOSTS["redirect-a.example"][0]
    assert webfetch.resolve_public("two.example", lambda _h: [first, second]) == first


def test_a_short_read_fake_is_never_asked_for_more_than_cap_plus_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://sector-desk.example/notes/huge"
    spec = {"status": 200, "headers": {"Content-Type": "text/plain"}, "body": "x" * (CAP * 8)}
    monkeypatch.setitem(RESPONSES, url, spec)
    world = World()
    world.short_read = KEY["cap"]["cap"] // 6
    record, body, _media = world.fetch(url)
    assert body is None and record.reason == f"{url} body is larger than the {CAP}-byte cap"
    assert world.responses[0].pos == KEY["cap"]["max_read_request"]


class SimSock:
    """A kernel socket that never blocks: each receive or send costs ``step`` on the clock, or the
    socket timeout (and raises TimeoutError) when that is shorter."""

    def __init__(
        self,
        clock: World,
        step: float,
        data: bytes = b"",
        *,
        eof: bool = False,
        max_chunk: int | None = None,
    ) -> None:
        self.eof = eof
        self.max_chunk = max_chunk
        self.closed = False
        self.clock = clock
        self.step = step
        self.data = data
        self.timeout: float | None = None
        self.set_at: list[tuple[float, float | None]] = []
        self.calls = 0

    def settimeout(self, value: float | None) -> None:
        self.timeout = value
        self.set_at.append((self.clock.now, value))

    def gettimeout(self) -> float | None:
        return self.timeout

    def _spend(self) -> None:
        if self.closed:
            raise OSError("bad file descriptor")
        self.calls += 1
        if self.timeout is not None and self.step > self.timeout:
            self.clock.now += self.timeout
            raise TimeoutError("timed out")
        self.clock.now += self.step

    def recv_into(self, buffer: bytearray, nbytes: int = 0) -> int:
        self._spend()
        if self.eof and not self.data:
            return 0
        size = min(len(buffer), len(self.data)) if self.data else 1
        size = min(size, self.max_chunk or size)
        buffer[:size] = self.data[:size] or b"x"
        self.data = self.data[size:]
        return size

    def recv(self, count: int) -> bytes:
        buffer = bytearray(count)
        return bytes(buffer[: self.recv_into(buffer)])

    def sendall(self, data: bytes) -> None:
        self._spend()

    def _decref_socketios(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


def _budgeted(
    monkeypatch: pytest.MonkeyPatch, sim: SimSock, world: World
) -> webfetch.PinnedHTTPSConnection:
    conn = KEY["connection"]
    monkeypatch.setattr(socket, "create_connection", lambda address, timeout: sim)

    class Context:
        def wrap_socket(self, sock: object, *, server_hostname: str) -> object:
            return sock

    return webfetch.PinnedHTTPSConnection(
        conn["host"],
        conn["ip"],
        port=conn["port"],
        timeout=CONNECT_S,
        context=cast(ssl.SSLContext, Context()),
        deadline=world.now + TOTAL_S,
        clock=world.clock,
    )


def test_every_receive_is_bounded_by_the_remaining_total(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World()
    sim = SimSock(world, step=9.0)
    pinned = _budgeted(monkeypatch, sim, world)
    pinned.connect()
    assert pinned.sock is not None
    for _ in range(20):
        try:
            pinned.sock.recv(1)
        except TimeoutError:
            break
    assert world.now <= KEY["timeout"]["total_seconds"]
    assert sim.set_at
    for at, value in sim.set_at:
        assert value == min(CONNECT_S, TOTAL_S - at)
    calls = sim.calls
    with pytest.raises(TimeoutError):
        pinned.sock.recv(1)
    with pytest.raises(TimeoutError):
        pinned.sock.sendall(b"x")
    assert sim.calls == calls


def test_a_response_is_read_through_the_bounded_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World()
    reply = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nhi"
    sim = SimSock(world, step=1.0, data=reply)
    pinned = _budgeted(monkeypatch, sim, world)
    pinned.connect()
    pinned.request("GET", "/x", headers={"Host": "h"})
    response = pinned.getresponse()
    assert response.read(10) == b"hi"
    assert sim.set_at and all(value == min(CONNECT_S, TOTAL_S - at) for at, value in sim.set_at)


def test_a_response_that_arrives_after_the_total_is_refused() -> None:
    world = World(advance_on_response=CASES["slow_connector_seconds"])
    record, body, _media = world.fetch(KEY["timeout"]["url"])
    assert body is None
    assert record.reason == KEY["timeout"]["reason"]


def test_a_per_operation_timeout_inside_the_total_is_not_called_a_total_timeout() -> None:
    world = World()

    class Stalled(FakeConnection):
        def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None:
            raise TimeoutError("timed out")

    url = KEY["timeout"]["url"]
    record, body, _media = webfetch.fetch(
        url,
        manifest_hosts=MANIFEST_HOSTS,
        resolver=world.resolver,
        connect=lambda target: Stalled(world, target),
        cap=CAP,
        connect_timeout=CONNECT_S,
        total_timeout=TOTAL_S,
        clock=world.clock,
    )
    assert body is None
    assert record.reason == f"{url} could not be fetched: TimeoutError"


class _BytesSock:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def makefile(self, mode: str) -> io.BufferedReader:
        return io.BufferedReader(io.BytesIO(self.data))


class _RealResponseConnection:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None:
        return None

    def getresponse(self) -> http.client.HTTPResponse:
        response = http.client.HTTPResponse(
            cast(socket.socket, _BytesSock(self.data)), method="GET"
        )
        response.begin()
        return response

    def close(self) -> None:
        return None


def test_a_body_shorter_than_its_content_length_is_refused() -> None:
    world = World()
    head = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 500\r\n\r\n"
    data = head + b"only forty bytes of a five-hundred body."
    url = KEY["request"]["verbatim_url"]
    record, body, _media = webfetch.fetch(
        url,
        manifest_hosts=MANIFEST_HOSTS,
        resolver=world.resolver,
        connect=lambda _target: _RealResponseConnection(data),
        cap=CAP,
        connect_timeout=CONNECT_S,
        total_timeout=TOTAL_S,
        clock=world.clock,
    )
    assert body is None
    assert record.reason == f"{url} body ended after 40 of 500 bytes"
    assert (record.bytes, record.sha256) == (None, None)


def test_the_production_connector_pins_the_checked_address_and_verifies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = KEY["connection"]
    seen: dict[str, Any] = {}

    def create_connection(address: tuple[str, int], timeout: float) -> object:
        seen["address"] = address
        return object()

    def wrap_socket(self: ssl.SSLContext, sock: object, *, server_hostname: str) -> object:
        seen["server_hostname"] = server_hostname
        seen["check_hostname"] = self.check_hostname
        seen["verify_mode"] = self.verify_mode
        return sock

    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", wrap_socket)
    target = webfetch.ConnectionTarget(
        conn["host"], conn["ip"], conn["port"], CONNECT_S, float("inf"), World().clock
    )
    pinned = webfetch.pinned_connection(target)
    assert isinstance(pinned, webfetch.PinnedHTTPSConnection)
    pinned.connect()
    assert seen["address"] == (conn["ip"], conn["port"])
    assert seen["server_hostname"] == conn["server_hostname"]
    assert seen["check_hostname"] is conn["check_hostname"]
    assert seen["verify_mode"] is getattr(ssl, conn["verify_mode"])


class _CaptureSock:
    def __init__(self) -> None:
        self.sent = b""

    def sendall(self, data: bytes) -> None:
        self.sent += bytes(data)

    def close(self) -> None:
        return None


def test_the_wire_carries_exactly_the_key_headers() -> None:
    req = KEY["request"]
    conn = KEY["connection"]
    pinned = webfetch.PinnedHTTPSConnection(
        conn["host"],
        conn["ip"],
        port=conn["port"],
        timeout=CONNECT_S,
        context=webfetch.tls_context(),
        deadline=float("inf"),
        clock=World().clock,
    )
    capture = _CaptureSock()
    pinned.sock = cast(socket.socket, capture)
    pinned.request("GET", req["path"], headers=req["headers"])
    lines = capture.sent.decode("ascii").split("\r\n")
    assert lines[0] == f"{req['method']} {req['path']} HTTP/1.1"
    assert [line for line in lines[1:] if line] == [f"{k}: {v}" for k, v in req["headers"].items()]


def test_the_production_connector_carries_the_targets_deadline() -> None:
    conn = KEY["connection"]
    world = World()
    target = webfetch.ConnectionTarget(
        conn["host"], conn["ip"], conn["port"], CONNECT_S, deadline=world.now, clock=world.clock
    )
    pinned = webfetch.pinned_connection(target)
    assert isinstance(pinned, webfetch.PinnedHTTPSConnection)
    with pytest.raises(TimeoutError):
        pinned.connect()


def test_a_connection_close_body_in_two_reads_survives_the_wrappers_close() -> None:
    world = World()
    body = b"y" * 300
    head = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\nContent-Length: 300\r\n\r\n"
    sim = SimSock(world, step=0.1, data=head + body, eof=True, max_chunk=100)
    with pytest.MonkeyPatch.context() as patch:
        pinned = _budgeted(patch, sim, world)
        pinned.connect()
        pinned.request("GET", "/x", headers={"Host": "h"})
        response = pinned.getresponse()
        assert not sim.closed
        assert response.read() == body
        response.close()
    assert sim.closed


def test_a_close_delimited_body_is_read_to_its_end() -> None:
    world = World()
    sim = SimSock(
        world,
        step=0.1,
        data=b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nhello world",
        eof=True,
        max_chunk=7,
    )
    with pytest.MonkeyPatch.context() as patch:
        pinned = _budgeted(patch, sim, world)
        pinned.connect()
        pinned.request("GET", "/x", headers={"Host": "h"})
        response = pinned.getresponse()
        assert response.read() == b"hello world"
        response.close()
    assert sim.closed


@pytest.mark.parametrize("value", ["\xb2", "\xb9", "1\xb2"])
def test_a_non_ascii_digit_content_length_is_treated_as_absent(value: str) -> None:
    world = World()
    head = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {value}\r\n\r\n"
    url = KEY["request"]["verbatim_url"]
    record, body, _media = webfetch.fetch(
        url,
        manifest_hosts=MANIFEST_HOSTS,
        resolver=world.resolver,
        connect=lambda _t: _RealResponseConnection(head.encode("latin-1") + b"hello"),
        cap=CAP,
        connect_timeout=CONNECT_S,
        total_timeout=TOTAL_S,
        clock=world.clock,
    )
    assert record.reason is None
    assert body == b"hello"


def _through_production_connector(
    monkeypatch: pytest.MonkeyPatch, world: World, sim: SimSock, cap: int = CAP
) -> tuple[webfetch.FetchRecord, bytes | None, str | None]:
    class Context:
        def wrap_socket(self, sock: object, *, server_hostname: str) -> object:
            return sock

    monkeypatch.setattr(socket, "create_connection", lambda address, timeout: sim)
    monkeypatch.setattr(webfetch, "tls_context", lambda: Context())
    return webfetch.fetch(
        KEY["request"]["verbatim_url"],
        manifest_hosts=MANIFEST_HOSTS,
        resolver=world.resolver,
        connect=webfetch.pinned_connection,
        cap=cap,
        connect_timeout=CONNECT_S,
        total_timeout=TOTAL_S,
        clock=world.clock,
    )


def test_a_trickling_peer_is_refused_by_the_total_through_the_production_connector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = World()
    reply = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 40\r\n\r\n" + b"x" * 40
    sim = SimSock(world, step=9.0, data=reply, eof=True, max_chunk=1)
    record, body, _media = _through_production_connector(monkeypatch, world, sim)
    assert body is None
    assert record.reason is not None
    assert world.now <= KEY["timeout"]["total_seconds"]


def test_a_prompt_peer_succeeds_through_the_production_connector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = World()
    reply = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 5\r\n\r\nhello"
    sim = SimSock(world, step=0.1, data=reply, eof=True)
    record, body, _media = _through_production_connector(monkeypatch, world, sim)
    assert record.reason is None
    assert body == b"hello"
    assert [at for at, _t in sim.set_at]  # the fetch's own clock reached the socket


def test_an_empty_body_that_ends_after_the_total_is_refused() -> None:
    world = World()

    class LateEnd(FakeResponse):
        def read(self, amt: int) -> bytes:
            world.now += CASES["slow_connector_seconds"]
            return b""

    class Conn(FakeConnection):
        def getresponse(self) -> FakeResponse:
            return LateEnd(200, {"Content-Type": "text/plain"}, b"")

    record, body, _media = webfetch.fetch(
        KEY["timeout"]["url"],
        manifest_hosts=MANIFEST_HOSTS,
        resolver=world.resolver,
        connect=lambda target: Conn(world, target),
        cap=CAP,
        connect_timeout=CONNECT_S,
        total_timeout=TOTAL_S,
        clock=world.clock,
    )
    assert body is None
    assert record.reason == KEY["timeout"]["reason"]


def test_a_redirect_that_arrives_after_the_total_is_not_followed() -> None:
    world = World(advance_on_response=CASES["slow_connector_seconds"])
    url = KEY["redirects"]["three_hops_ok"]["url"]
    record, body, _media = world.fetch(url)
    assert body is None
    assert record.reason == f"{url} took longer than {KEY['timeout']['total_seconds']} seconds"
    assert world.resolved == ["redirect-a.example"]
