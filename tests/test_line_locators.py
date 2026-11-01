"""`line:N` locators in the live tools (O2 Task 7, user ruling B22).

A prepared text pack locates spans as `line:N`. `read_pages` reads them by line number,
`extract_statements` takes `line:N-M` ranges and `seen_tables` rebases each range's rows to their
own `line:K`. A page pack's tool output is pinned byte-for-byte by ``PAGE_GOLDEN`` (captured at
BASE 63a5bbb8, before the change).
"""

import hashlib
import json
from types import SimpleNamespace
from typing import Any, cast

import o2_case
import pytest
import test_financial_workflow as page_fixture

from deploy_vii.contracts import Span
from deploy_vii.live import tools as live_tools
from deploy_vii.live.tools import PackTools, ToolError, seen_tables
from deploy_vii.preparation import PreparedPack, load_pack
from deploy_workflow.model.adapter import recorded_adapter

FIN = "financial"
make_pack: Any = page_fixture.make_pack
FIRST_ROW = "24 | Revenue | CONSOLIDATED INCOME STATEMENT | 30 30 30 30 120 | -"

# (kind, sha256 of the text) of each page-pack call, captured at BASE before any code changed.
PAGE_GOLDEN = {
    "read15": ("ok", "d3a23b0f9785c33edb12636e061d9e7d15f6a0d76783aa50bf2d9aa4ce533704"),
    "read_missing": ("ok", "61d81224ecd736b1c89fb91fed5f969b7c5478c1fdde67486d1a2cacd4dc605b"),
    "extract234": ("ok", "390b9c6fc7e43d63569b2362d143ce8a1fca2164233b16f1cc6eff11891c526a"),
    "extract_line_range": (
        "err",
        "6f952e1eccd5641934d0c267afa79063fe82816fe646e13250da966cc3076d6a",
    ),
    "extract_missing": ("err", "ba10327647d6b09481b94c75dbb8e68690b159f93fe2acf6561abace012428ce"),
    "extract_repeat": ("err", "405ea77404be73482a03838de0bc6966a847099ffe1393a2da27c90ac32a78d0"),
    "evidence": ("ok", "d2e4a2cc7c5152ce3ce08ded1bbe30c0cd74885862366988c367879e6c08046e"),
}


@pytest.fixture(scope="module")
def pack(tmp_path_factory: pytest.TempPathFactory) -> PreparedPack:
    root = tmp_path_factory.mktemp("o2-pack")
    (root / "recordings").mkdir()
    _, run_dir = o2_case._prepare(
        root / "prepared", recorded_adapter(o2_case.MODEL, root / "recordings")
    )
    return load_pack(run_dir / "pack")


@pytest.fixture
def tools(pack: PreparedPack) -> PackTools:
    return PackTools(pack, sources=(FIN,))


def evidence(tools: PackTools) -> tuple[Any, ...]:
    return (set(tools.read), set(tools.extracted), set(tools.surfaced), list(tools.searched))


def test_read_pages_reads_line_spans(tools: PackTools) -> None:  # (a)
    body = tools.read_pages({"source_id": FIN, "first_page": 24, "last_page": 25})
    assert body.count("<<<SOURCE ") == 2
    assert "locator=line:24 | Revenue  30  30  30  30  120" in body
    assert "locator=line:25 | Cost of sales" in body
    assert tools.read == {(FIN, "line:24"), (FIN, "line:25")}
    assert tools.extracted == set()


def test_read_pages_names_a_missing_line_and_keeps_the_cap(tools: PackTools) -> None:
    body = tools.read_pages({"source_id": FIN, "first_page": 130, "last_page": 134})
    assert f"line:132 is not a located span of {FIN}." in body
    assert tools.read == {(FIN, "line:130"), (FIN, "line:131")}
    with pytest.raises(ToolError, match="at most 5 pages per call"):
        tools.read_pages({"source_id": FIN, "first_page": 1, "last_page": 6})


def test_extract_statements_rebases_rows_to_their_own_line(tools: PackTools) -> None:  # (b)
    body = tools.extract_statements({"source_id": FIN, "locators": ["line:22-46"]})
    rows = [r for r in body.splitlines() if r.split(" | ")[0].isdigit()]
    assert len(rows) == 21
    assert rows[0] == FIRST_ROW
    assert [int(r.split(" | ")[0]) for r in rows] == list(range(24, 45))
    assert "locator=line:22-46 |" in body
    assert tools.extracted == {(FIN, "line:22-46")} | {(FIN, f"line:{k}") for k in range(24, 45)}
    assert tools.read == set()


@pytest.mark.parametrize(
    "locators",
    [
        ["line:0-3"],
        ["line:01-3"],
        ["line:5-4"],
        ["line:1-201"],  # over MAX_LINES_PER_EXTRACT
        ["line:130-132"],  # past the last line
        ["line:22"],
        ["page:1"],
        ["line:1-3", "line:1-3"],  # repeat
        ["line:1-3", "page:1"],
        [f"line:{n}-{n + 100}" for n in (1, 102)],  # over the cap across ranges (202 lines)
        [f"line:{n}-{n}" for n in range(1, 10)],  # more than MAX_PAGES_PER_EXTRACT ranges
        [],
    ],
)
def test_refused_line_extractions_record_nothing(
    tools: PackTools, locators: list[str]
) -> None:  # (c)
    before = evidence(tools)
    with pytest.raises(ToolError):
        tools.extract_statements({"source_id": FIN, "locators": locators})
    assert evidence(tools) == before == (set(), set(), set(), [])


def test_the_cap_is_200_lines(tools: PackTools) -> None:
    assert live_tools.MAX_LINES_PER_EXTRACT == 200
    with pytest.raises(ToolError, match="at most 200 lines"):
        tools.extract_statements({"source_id": FIN, "locators": ["line:1-201"]})


def test_a_span_with_a_newline_refuses_the_call(pack: PreparedPack) -> None:
    sources = tuple(
        s.model_copy(update={"spans": (*s.spans[:-1], Span(locator="line:131", text="a\nb"))})
        if s.source_id == FIN
        else s
        for s in pack.sources
    )
    tools = PackTools(pack.model_copy(update={"sources": sources}), sources=(FIN,))
    with pytest.raises(ToolError, match="newline"):
        tools.extract_statements({"source_id": FIN, "locators": ["line:130-131"]})
    assert tools.extracted == set()


def test_wrong_kind_arguments_on_a_page_source_give_todays_messages() -> None:
    tools = PackTools(make_pack(), sources=(FIN,))
    with pytest.raises(ToolError, match="locators must be a list of page:N locators"):
        tools.extract_statements({"source_id": FIN, "locators": ["line:1-3"]})
    assert tools.extracted == set()


def page_outputs() -> dict[str, tuple[str, str]]:
    tools = PackTools(make_pack(), sources=(FIN,))
    out: dict[str, tuple[str, str]] = {}

    def call(name: str, method: str, args: dict[str, Any]) -> None:
        try:
            out[name] = ("ok", getattr(tools, method)(args))
        except ToolError as error:
            out[name] = ("err", str(error))

    call("read15", "read_pages", {"source_id": FIN, "first_page": 1, "last_page": 5})
    call("read_missing", "read_pages", {"source_id": FIN, "first_page": 5, "last_page": 9})
    call(
        "extract234",
        "extract_statements",
        {"source_id": FIN, "locators": ["page:2", "page:3", "page:4"]},
    )
    call("extract_line_range", "extract_statements", {"source_id": FIN, "locators": ["line:1-3"]})
    call("extract_missing", "extract_statements", {"source_id": FIN, "locators": ["page:99"]})
    call(
        "extract_repeat", "extract_statements", {"source_id": FIN, "locators": ["page:2", "page:2"]}
    )
    recorded = {
        "read": sorted(map(list, tools.read)),
        "extracted": sorted(map(list, tools.extracted)),
    }
    out["evidence"] = ("ok", json.dumps(recorded))
    return out


def test_a_page_pack_is_byte_identical_to_base() -> None:  # (d)
    found = {
        k: (kind, hashlib.sha256(v.encode()).hexdigest()) for k, (kind, v) in page_outputs().items()
    }
    assert found == PAGE_GOLDEN


def test_seen_tables_returns_the_rebased_range_table(pack: PreparedPack) -> None:  # (e)
    tools = PackTools(pack, sources=(FIN,))
    context = SimpleNamespace(sources=[SimpleNamespace(source_id=FIN, classification="financial")])
    tools.extract_statements({"source_id": FIN, "locators": ["line:47-81", "line:22-46"]})
    tables = seen_tables(tools, tools.seen(), cast(Any, context))
    assert [(t.source_id, t.locator) for t in tables] == [(FIN, "line:22-46"), (FIN, "line:47-81")]
    first = tables[0]
    assert len(first.lines) == 21
    assert (first.lines[0].line_no, first.lines[0].locator) == (24, "line:24")
    assert first.lines[0].label == "Revenue"
    assert first.headers == ("Period  Q1 2025  Q2 2025  Q3 2025  Q4 2025  FY 2025",)
