"""`line:N` locators in the live tools (O2 Task 7, user ruling B22).

A prepared text pack locates spans as `line:N`. `read_pages` reads them by line number,
`extract_statements` takes `line:N-M` ranges and `seen_tables` rebases each range's rows to their
own `line:K`. A page pack's tool output is pinned byte-for-byte by ``PAGE_GOLDEN`` (captured at
BASE 63a5bbb8, before the change).
"""

import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import o2_case
import pytest
import test_financial_workflow as page_fixture

from deploy_vii.contracts import Span
from deploy_vii.live import tools as live_tools
from deploy_vii.live.tools import PackTools, ToolError, seen_tables
from deploy_vii.preparation import PreparedPack, load_pack
from deploy_workflow import financial_workflow as fw
from deploy_workflow.model.adapter import recorded_adapter
from deploy_workflow.workflow import SourceEvidence

FIN = "financial"
WINDOW_KEY = Path(__file__).parents[1] / "cases" / "pilot-fixes" / "read-window.json"
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


def _window() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(WINDOW_KEY.read_text(encoding="utf-8"))
    return loaded


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
    key = _window()
    long_lines = _line_spans(["x" * 2000] * (key["max_spans_per_read"] + 1))
    assert sum(len(sp.text.encode()) for sp in long_lines) > key["max_line_read_bytes"]
    capped = PackTools(_with_spans(long_lines), sources=(FIN,))
    with pytest.raises(ToolError, match=re.escape(key["line_refusal"])):
        capped.read_pages({"source_id": FIN, "first_page": 1, "last_page": len(long_lines)})
    assert capped.read == set()


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


H_IS, H_BS = "CONSOLIDATED INCOME STATEMENT", "CONSOLIDATED BALANCE SHEET"
HEADER = "Period  Q1 2025  Q2 2025  Q3 2025  Q4 2025  FY 2025"
ROWS = ["Revenue  30  30  30  30  120", "Cost of sales  15  15  15  15  60"]
UNMEASURED = "Statement extraction is unmeasured; empty tables do not establish coverage"
NOT_EXTRACTED = "Financials must extract every located statement page in this epoch"


def _with_spans(spans: list[Span]) -> PreparedPack:
    base: PreparedPack = make_pack()
    return base.model_copy(
        update={
            "sources": tuple(
                s.model_copy(update={"spans": tuple(spans)}) if s.source_id == FIN else s
                for s in base.sources
            )
        }
    )


def _line_spans(lines: list[str]) -> list[Span]:
    return [Span(locator=f"line:{i}", text=text) for i, text in enumerate(lines, 1)]


def _issues(
    monkeypatch: pytest.MonkeyPatch, pack: PreparedPack, *, extract_all: bool = True
) -> tuple[dict[str, str], list[str]]:
    """`_statement_units` of the financial source and `_evidence_issues` after extracting each."""
    financial = next(s for s in pack.sources if s.source_id == FIN)
    units = fw._statement_units(financial.spans)
    tools = PackTools(pack, sources=(FIN,))
    if extract_all:
        for locator in units:
            tools.extract_statements({"source_id": FIN, "locators": [locator]})
    evidence = SourceEvidence(
        read=tuple(sorted(tools.read)), extracted=tuple(sorted(tools.extracted))
    )
    context = o2_case.payload_for("source_context")
    store = SimpleNamespace(
        read=lambda: SimpleNamespace(
            attempts=[SimpleNamespace(ticket_id="t", steps=[SimpleNamespace(payload_sha256="c")])]
        ),
        payload=lambda _sha: context,
        pack=lambda: pack,
    )
    monkeypatch.setattr(
        fw,
        "FinancialSubmission",
        SimpleNamespace(
            model_validate_json=lambda _s: SimpleNamespace(financial=SimpleNamespace(books=[]))
        ),
    )
    binding = SimpleNamespace(step_id="financials", ticket_id="t")
    return units, list(fw._evidence_issues(cast(Any, store), cast(Any, binding), "x", evidence))


def test_adjacent_headings_form_one_unit_that_is_measured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # L1
    pack = _with_spans(_line_spans([H_IS, H_IS, HEADER, *ROWS]))
    units, issues = _issues(monkeypatch, pack)
    assert list(units) == ["line:1-5"]
    assert UNMEASURED not in issues and NOT_EXTRACTED not in issues


def test_a_line_source_with_no_heading_line_has_no_units() -> None:
    spans = _line_spans(["Consolidated Balance Sheets", ROWS[0], ROWS[1]])  # title case
    assert fw._statement_units(spans) == {}


def test_a_no_heading_line_source_gets_the_named_refusal_not_a_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pack = _with_spans(_line_spans(["Consolidated Balance Sheets", HEADER, *ROWS]))
    units, issues = _issues(monkeypatch, pack)
    assert units == {}
    assert NOT_EXTRACTED in issues


def test_a_unit_runs_to_the_line_before_the_next_non_adjacent_heading() -> None:
    spans = _line_spans([H_IS, H_IS, HEADER, ROWS[0], H_BS, H_BS, HEADER, ROWS[1]])
    assert list(fw._statement_units(spans)) == ["line:1-4", "line:5-8"]


def _numbered_pack(count: int) -> PreparedPack:
    return _with_spans(_line_spans([f"Row {n}  1  2" for n in range(1, count + 1)]))


def _extract(pack: PreparedPack, locators: list[str]) -> PackTools:
    tools = PackTools(pack, sources=(FIN,))
    tools.extract_statements({"source_id": FIN, "locators": locators})
    return tools


def test_an_extract_of_exactly_the_line_cap_passes_and_one_more_is_refused() -> None:  # L2
    cap = live_tools.MAX_LINES_PER_EXTRACT
    pack = _numbered_pack(cap + 10)
    tools = _extract(pack, [f"line:1-{cap // 2}", f"line:{cap // 2 + 1}-{cap}"])
    assert (FIN, f"line:1-{cap // 2}") in tools.extracted
    with pytest.raises(ToolError, match=f"at most {cap} lines"):
        _extract(pack, [f"line:1-{cap // 2}", f"line:{cap // 2 + 1}-{cap + 1}"])


def test_exactly_the_range_cap_passes_and_one_more_is_refused() -> None:  # L2
    cap = live_tools.MAX_PAGES_PER_EXTRACT
    pack = _numbered_pack(cap + 1)
    tools = _extract(pack, [f"line:{n}-{n}" for n in range(1, cap + 1)])
    assert {loc for _, loc in tools.extracted if "-" in loc} == {
        f"line:{n}-{n}" for n in range(1, cap + 1)
    }
    with pytest.raises(ToolError, match=f"at most {cap} ranges"):
        _extract(pack, [f"line:{n}-{n}" for n in range(1, cap + 2)])


def test_a_valid_range_then_one_failing_in_the_table_records_nothing() -> None:  # L2
    tools = PackTools(_numbered_pack(10), sources=(FIN,))
    with pytest.raises(ToolError, match="line:11"):
        tools.extract_statements({"source_id": FIN, "locators": ["line:1-3", "line:9-12"]})
    assert evidence(tools) == (set(), set(), set(), [])


def _mixed_pack(*locators: str) -> PreparedPack:
    return _with_spans(
        [
            Span(locator=loc, text=f"{H_IS}" if n == 0 else "Revenue  1  2")
            for n, loc in enumerate(locators)
        ]
    )


@pytest.mark.parametrize("locators", [("line:1", "sheet:A", "line:2"), ("page:1", "line:2")])
def test_a_mixed_source_takes_the_page_or_other_path(locators: tuple[str, ...]) -> None:  # L3
    pack = _mixed_pack(*locators)
    tools = PackTools(pack, sources=(FIN,))
    assert FIN not in tools.lines
    with pytest.raises(ToolError, match="locators must be a list of page:N locators"):
        tools.extract_statements({"source_id": FIN, "locators": ["line:1-2"]})
    financial = next(s for s in pack.sources if s.source_id == FIN)
    assert fw._statement_units(financial.spans) == {locators[0]: H_IS}


def test_a_row_whose_caption_names_no_statement_takes_the_unit_heading_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # L4
    """Under a statement heading every row has a caption (the heading itself is one), so the
    fallback to the unit's heading text shows on a row whose caption names no statement."""
    lines = [H_IS, "OPERATING ITEMS", HEADER, *ROWS]
    pack = _with_spans(_line_spans(lines))
    seen: list[tuple[str | None, str, str | None]] = []
    real = fw._statement

    def spy(caption: str | None, text: str) -> str | None:
        seen.append((caption, text, real(caption, text)))
        return real(caption, text)

    monkeypatch.setattr(fw, "_statement", spy)
    _issues(monkeypatch, pack)
    assert real("OPERATING ITEMS", "") is None
    assert {(caption, text, kind) for caption, text, kind in seen} == {
        ("OPERATING ITEMS", "\n".join(lines), "IS")
    }


# --- PF-R7: the line-source read window (cases/pilot-fixes/read-window.json) ---------------------


def _window_tools(lines: list[str]) -> PackTools:
    return PackTools(_with_spans(_line_spans(lines)), sources=(FIN,))


def test_a_line_read_of_more_than_five_lines_within_the_byte_bound_is_allowed() -> None:  # (h)
    key = _window()
    count = key["max_spans_per_read"] + 3
    tools = _window_tools(["Row 1  2  3"] * count)
    body = tools.read_pages({"source_id": FIN, "first_page": 1, "last_page": count})
    assert sum(len(line.encode()) for line in ["Row 1  2  3"] * count) <= key["max_line_read_bytes"]
    assert body.count("<<<SOURCE ") == count
    assert tools.read == {(FIN, f"line:{n}") for n in range(1, count + 1)}


def test_a_line_read_over_five_lines_and_over_the_byte_bound_is_refused() -> None:  # (i)
    key = _window()
    per_line = key["max_line_read_bytes"] // key["max_spans_per_read"]
    count = key["max_spans_per_read"] + 1
    tools = _window_tools(["y" * per_line] * count)
    with pytest.raises(ToolError) as refused:
        tools.read_pages({"source_id": FIN, "first_page": 1, "last_page": count})
    assert str(refused.value) == key["line_refusal"]
    assert tools.read == set()


def test_a_read_of_five_lines_is_allowed_even_when_one_line_exceeds_the_bound() -> None:  # (j)
    key = _window()
    tools = _window_tools(["z" * (key["max_line_read_bytes"] + 1000), "short"])
    body = tools.read_pages({"source_id": FIN, "first_page": 1, "last_page": 2})
    assert body.count("<<<SOURCE ") == 2
    assert tools.read == {(FIN, "line:1"), (FIN, "line:2")}


def test_a_page_source_still_refuses_six_pages_with_the_old_text() -> None:  # (k)
    tools = PackTools(make_pack(), sources=(FIN,))
    with pytest.raises(ToolError) as refused:
        tools.read_pages({"source_id": FIN, "first_page": 1, "last_page": 6})
    assert str(refused.value) == "bad arguments: at most 5 pages per call"
    assert tools.read == set()


def test_the_read_tool_description_is_the_keys() -> None:  # (l)
    specs = live_tools.tool_specs("source_readiness", "pack")
    read = next(spec for spec in specs if spec["function"]["name"] == live_tools.READ)
    assert read["function"]["description"] == _window()["tool_description"]


def test_a_line_read_naming_more_than_the_line_cap_is_refused_before_measuring() -> None:  # (m)
    key = _window()
    count = key["max_lines_per_line_read"] + 1
    tools = _window_tools(["a"] * count)
    assert count <= key["max_line_read_bytes"]  # the bytes alone would allow it
    with pytest.raises(ToolError, match=re.escape(key["line_refusal"])):
        tools.read_pages({"source_id": FIN, "first_page": 1, "last_page": count})
    assert tools.read == set()


def test_an_unbounded_last_page_on_a_line_source_is_refused_at_once() -> None:  # (n)
    key = _window()
    tools = _window_tools(["a", "b"])
    with pytest.raises(ToolError, match=re.escape(key["line_refusal"])):
        tools.read_pages({"source_id": FIN, "first_page": 1, "last_page": 10**12})
    assert tools.read == set()


def test_a_line_read_of_exactly_the_line_cap_is_allowed() -> None:  # review L2 (mutant A)
    key = _window()
    count = key["max_lines_per_line_read"]
    assert count <= key["max_line_read_bytes"]
    tools = _window_tools(["a"] * count)
    body = tools.read_pages({"source_id": FIN, "first_page": 1, "last_page": count})
    assert body.count("<<<SOURCE ") == count
    assert len(tools.read) == count


def test_a_line_read_totalling_exactly_the_byte_bound_is_allowed() -> None:  # review L2 (mutant C)
    key = _window()
    count = key["max_spans_per_read"] + 1
    bound = key["max_line_read_bytes"]
    lines = ["b" * (bound // count)] * (count - 1)
    lines.append("b" * (bound - sum(len(line) for line in lines)))
    assert count > key["max_spans_per_read"]
    assert sum(len(line.encode("utf-8")) for line in lines) == bound
    tools = _window_tools(lines)
    body = tools.read_pages({"source_id": FIN, "first_page": 1, "last_page": count})
    assert body.count("<<<SOURCE ") == count


def test_the_byte_bound_counts_utf8_bytes_not_characters() -> None:  # review L2 (mutant E)
    key = _window()
    count = key["max_spans_per_read"] + 1
    per_line = key["max_line_read_bytes"] // count  # characters per line, all within the bound
    lines = ["\u00e9" * per_line] * count  # two UTF-8 bytes per character
    assert sum(len(line) for line in lines) <= key["max_line_read_bytes"]
    assert sum(len(line.encode("utf-8")) for line in lines) > key["max_line_read_bytes"]
    tools = _window_tools(lines)
    with pytest.raises(ToolError, match=re.escape(key["line_refusal"])):
        tools.read_pages({"source_id": FIN, "first_page": 1, "last_page": count})
    assert tools.read == set()
