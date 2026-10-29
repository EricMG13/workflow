"""0d-c: the rule issue text a model payload can amplify after the binding write is bounded at
the place it is produced (`ToolRules`, the pre-fill's unbound list), exactly as
`bounded_issues` would show it, so every verifier still replays the run exactly."""

import copy
import importlib
import json
import time
import tracemalloc
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from deploy_vii.execution import (
    MAX_ISSUE_CHARS,
    MAX_ISSUES,
    Execution,
    bounded_issues,
    shortened,
)
from deploy_vii.live.schema import payload_document
from deploy_vii.live.submission import PREFILLED, STEPS, known_bindings, prefill
from deploy_vii.live.tools import (
    RULE_PREFIXES,
    UNBACKED_ABSENCE,
    UNREAD_PAGE,
    Seen,
    ToolRules,
)

fw = importlib.import_module("test_financial_workflow")
te = importlib.import_module("test_earnings_workflow")

ABSENT = UNBACKED_ABSENCE
SEARCH = "; search_pack before claiming it is not disclosed"
KEY = "k" * 20_000
ROWS = 2_000
# The record bound the refusal tests below assert holds for ASCII issue text (0d-c review F1).
# The design's real worst case is higher: both rules at one step, 20 lines of 600 characters each,
# every character an escape of 6 bytes in JSON (`\\u0001`), plus record overhead.
LIMIT = 64 * 1024
WORST_CASE = 2 * MAX_ISSUES * 6 * 600 + 16 * 1024


def _issues(step: str, payload: str) -> tuple[str, ...]:
    return ToolRules().issues(step, payload, seen=Seen(), context=None)


def _rows(key: str, row: str, count: int = ROWS) -> str:
    return '{"' + key + '":[' + ",".join([row] * count) + "]}"


SHAPES = {
    "source_context no_events": (
        "source_context",
        '{"sources":{"'
        + KEY
        + '":['
        + ",".join(['{"event_scan":"no_events_identified","source_id":"z"}'] * ROWS)
        + "]}}",
    ),
    "source_context long source_id": (
        "source_context",
        '{"sources":['
        + ",".join(
            f'{{"event_scan":"no_events_identified","source_id":"{KEY}{i}"}}' for i in range(200)
        )
        + "]}",
    ),
    "financials missing": ("financials", _rows(KEY, '{"status":"missing","observation_id":"o"}')),
    "business_context available No": ("business_context", _rows(KEY, '{"available":"No"}')),
    "legal_covenants threshold_unit": (
        "legal_covenants",
        _rows(KEY, '{"threshold_unit":"not stated"}'),
    ),
    "unread distinct citations": (
        "source_context",
        '{"c":['
        + ",".join(f'{{"source_id":"s","locator":"page:{i}"}}' for i in range(ROWS * 10))
        + "]}",
    ),
    "unread long source_id": (
        "source_context",
        '{"c":['
        + ",".join(f'{{"source_id":"{KEY}","locator":"page:{i}"}}' for i in range(200))
        + "]}",
    ),
}
# How many matches each shape holds, so the summary line can be checked exactly (Q1).
MATCHES = {
    "source_context no_events": ROWS,
    "source_context long source_id": 200,
    "financials missing": ROWS,
    "business_context available No": ROWS,
    "legal_covenants threshold_unit": ROWS,
    "unread distinct citations": ROWS * 10,
    "unread long source_id": 200,
}
SUMMARIES = (
    f"{UNBACKED_ABSENCE}: 2 further absence claims not listed",
    f"{UNREAD_PAGE}: 2 further cited pages not listed",
)


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_rule_issues_are_bounded_on_one_long_key_over_many_rows(name):
    step, payload = SHAPES[name]
    issues = _issues(step, payload)
    assert 0 < len(issues) <= MAX_ISSUES
    assert max(len(line) for line in issues) <= MAX_ISSUE_CHARS
    assert bounded_issues(issues) == issues
    assert all(line.startswith(RULE_PREFIXES) for line in issues)
    left_out = MATCHES[name] - (MAX_ISSUES - 1)
    assert issues[-1] in (
        f"{UNBACKED_ABSENCE}: {left_out} further absence claims not listed",
        f"{UNREAD_PAGE}: {left_out} further cited pages not listed",
    )


def test_rule_issue_lines_are_what_bounded_issues_would_show():
    # Guard: 20 rows list as today.
    twenty = _issues("business_context", json.dumps({"rows": [{"available": "No"}] * 20}))
    assert twenty == tuple(f"{ABSENT}: rows.{i}.available No{SEARCH}" for i in range(20))
    # 21 rows: the first 19, then the count of the 2 left out.
    twenty_one = _issues("business_context", json.dumps({"rows": [{"available": "No"}] * 21}))
    assert twenty_one == (
        *(f"{ABSENT}: rows.{i}.available No{SEARCH}" for i in range(19)),
        "Absence claim without a recorded search: 2 further absence claims not listed",
    )
    # 21 unread pages: sorted lines, the 19th is `s page:7`.
    pages = json.dumps({"c": [{"source_id": "s", "locator": f"page:{i}"} for i in range(1, 22)]})
    unread = _issues("source_context", pages)
    assert len(unread) == 20
    assert unread[18] == "Cited page not read through read_pages: s page:7"
    assert unread[0] == "Cited page not read through read_pages: s page:1"
    assert unread[19] == "Cited page not read through read_pages: 2 further cited pages not listed"
    # A 700-character key: the line HEAD built whole, cut as bounded_issues cuts it.
    long_key = "k" * 700
    (line,) = _issues("business_context", json.dumps({long_key: [{"available": "No"}]}))
    assert line == shortened(f"{ABSENT}: {long_key}.0.available No{SEARCH}")
    assert len(line) == MAX_ISSUE_CHARS
    # Empty keys keep HEAD's dotted quirks.
    empty = '{"": {"": [{"available":"No"}]}, "a": {"": {"status":"Not disclosed"}}}'
    assert _issues("business_context", empty) == (
        f"{ABSENT}: 0.available No{SEARCH}",
        f"{ABSENT}: a..status Not disclosed{SEARCH}",
    )


def _peak(call) -> int:
    tracemalloc.start()
    try:
        call()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


@pytest.mark.parametrize(
    "name",
    [
        "source_context no_events",
        "source_context long source_id",
        "financials missing",
        "business_context available No",
    ],
)
def test_rule_issues_peak_memory_is_bounded(name):
    step, payload = SHAPES[name]
    parse = _peak(lambda: payload_document(payload, exact=False))
    peak = _peak(lambda: _issues(step, payload))
    assert peak <= 4 * parse + (1 << 20)


@pytest.mark.parametrize("step", ["source_context", "financials", "business_context"])
def test_rule_walk_does_not_copy_a_long_key_per_row(step):
    key = "k" * 2_000_000
    rows = ",".join(['{"x":1}'] * 40_000)
    payload = (
        '{"sources":{"' + key + '":[' + rows + "]}}"
        if step == "source_context"
        else '{"' + key + '":[' + rows + "]}"
    )
    started = time.perf_counter()
    issues = _issues(step, payload)
    assert issues == ()
    assert time.perf_counter() - started < 1.5


N = 2_000


def _p1(base, ident):
    doc = copy.deepcopy(base)
    book = doc["financial"]["books"][0]
    book["book_id"] = ident
    doc["binding"]["books"][0]["book_id"] = ident
    template = dict(
        book["periods"][0],
        start_date="1990-01-01",
        end_date="1990-12-31",
        citations=[fw.cite("financial", 1, "x")],
    )
    book["periods"] += [dict(template, period_id=f"x{i}") for i in range(N)]
    return doc


def _p2(base, ident):
    doc = copy.deepcopy(base)
    book = doc["financial"]["books"][0]
    period = book["periods"][0]["period_id"]
    book["audit_basis_explanations"] = [
        {
            "explanation_id": ident,
            "annual_period_id": period,
            "metric_id": "no-such-metric",
            "quarter_period_ids": [period] * N,
            "explanation": "x",
            "citations": [fw.cite("financial", 1, "x")],
        }
    ]
    return doc


def _prefill(workflow, doc):
    known = known_bindings(workflow._store, workflow._binding.ticket_id, "financials")
    text = json.dumps(doc, ensure_ascii=False)
    return prefill(STEPS["financials"].schema, text, known, PREFILLED["financials"])


def _prefill_peak(workflow, doc):
    holder = []
    peak = _peak(lambda: holder.append(_prefill(workflow, doc)))
    return holder[0], peak


@pytest.mark.parametrize("build", [_p1, _p2], ids=["no_scope", "stale_observation"])
def test_prefill_unbound_issues_do_not_copy_a_long_id(tmp_path, build):
    workflow, pack = fw.before_financials(tmp_path / "s")
    base = fw.financials(pack)
    peaks = []
    for ident in ("i" * 10, "i" * 20_000):
        filled, peak = _prefill_peak(workflow, build(base, ident))
        peaks.append(peak)
        assert all(len(issue) <= MAX_ISSUE_CHARS for _, issue in filled.unbound)
    assert peaks[1] <= peaks[0] + (4 << 20)
    if build is _p2:
        assert len(filled.unbound) == 2


def test_prefill_unbound_wording_is_unchanged_for_short_ids(tmp_path):
    workflow, pack = fw.before_financials(tmp_path / "s")
    base = fw.financials(pack)
    p1 = copy.deepcopy(base)
    book = p1["financial"]["books"][0]
    book["periods"] += [
        dict(
            book["periods"][0],
            period_id=f"x{i}",
            start_date="1990-01-01",
            end_date="1990-12-31",
            citations=[fw.cite("financial", 1, "x")],
        )
        for i in range(30)
    ]
    p1["binding"]["books"].append({"book_id": "other", "entity_id": "nobody"})
    unbound = _prefill(workflow, p1).unbound
    assert isinstance(unbound, tuple)
    assert unbound == tuple(
        (
            f"financial.books.0.periods.{6 + i}",
            f"No matching entity/date/basis source scope: consolidated x{i} financial",
        )
        for i in range(30)
    )
    p2 = copy.deepcopy(base)
    book2 = p2["financial"]["books"][0]
    book2["audit_basis_explanations"] = [
        {
            "explanation_id": "e1",
            "annual_period_id": book2["periods"][0]["period_id"],
            "metric_id": "m",
            "quarter_period_ids": [book2["periods"][0]["period_id"]] * 6,
            "explanation": "x",
            "citations": [dict(fw.cite("financial", 1, "x"), source_id="nosuch")],
        }
    ]
    explained = "financial.books.0.audit_basis_explanations.0"
    assert _prefill(workflow, p2).unbound == (
        (f"{explained}.citations.0.source_sha256", "Unavailable or changed source: nosuch"),
        (
            f"{explained}.annual_observation_sha256",
            "Stale audit explanation observation: e1 opening-2024",
        ),
        (
            f"{explained}.quarter_observation_sha256",
            "Stale audit explanation observation: e1 opening-2024",
        ),
    )


@given(
    st.lists(st.text(max_size=300), max_size=12),
    st.integers(min_value=1, max_value=700),
)
def test_clipped_and_listed_issues_properties(parts, limit):
    from deploy_vii.execution import clipped

    assert clipped(parts, limit) == shortened("".join(parts), limit)


@given(st.lists(st.text(max_size=900), max_size=60))
def test_listed_issues_is_bounded_a_fixed_point_and_identity_when_short(items):
    from deploy_vii.execution import listed_issues

    def rest(n):
        return f"{n} further things not listed"

    lines = listed_issues(items, lambda item: (item,), rest)
    assert len(lines) <= MAX_ISSUES
    assert bounded_issues(lines) == lines
    if len(items) <= MAX_ISSUES:
        assert lines == tuple(shortened(item) for item in items)
    else:
        assert lines[-1] == rest(len(items) - (MAX_ISSUES - 1))
        assert lines[:-1] == tuple(shortened(item) for item in items[: MAX_ISSUES - 1])


PAYLOAD = (
    '{"x":['
    + ",".join(f'{{"source_id":"identity","locator":"page:{n}"}}' for n in range(2, 5002))
    + "]}"
)


def _largest(directory: Path) -> int:
    return max((p.stat().st_size for p in directory.iterdir()), default=0)


def test_unread_refusal_is_bounded_and_verifies_financial(tmp_path):
    from deploy_workflow import financial_workflow as fin

    w, pack = fw.start(tmp_path, gap=True)
    fw.read_sources(w, gap=True)
    out = w.submit_review(PAYLOAD)
    assert out["status"] == "refused"
    assert 0 < len(out["issues"]) <= MAX_ISSUES
    assert _largest(fin._audit(w._store, "submissions", "x").parent) <= LIMIT
    assert len(json.dumps(out["issues"], ensure_ascii=False).encode()) <= LIMIT
    fw.read_sources(w, gap=True)
    assert w.submit_review(fw.readiness(pack, gap=True))["status"] == "valid"
    w.publish_model()
    receipt = w.write_receipt(tmp_path / "receipt.json")
    fin.verify_financial_slice_receipt(Execution(tmp_path / "store"), receipt, model_directory=None)


def test_unread_refusal_is_bounded_and_verifies_owner(tmp_path):
    owner = importlib.import_module("deploy_workflow.owner_workflow")
    pack = fw.make_pack(gap=True)
    w = owner.OwnerWorkflow.create(
        tmp_path / "store", pack, publication_directory=tmp_path / "model"
    )
    fw.read_sources(w, gap=True)
    out = w.submit_review(PAYLOAD)
    assert out["status"] == "refused"
    assert 0 < len(out["issues"]) <= MAX_ISSUES
    assert _largest(owner._audit(w._store, "submissions", "x").parent) <= LIMIT
    assert len(json.dumps(out["issues"], ensure_ascii=False).encode()) <= LIMIT
    fw.read_sources(w, gap=True)
    assert w.submit_review(fw.readiness(pack, gap=True))["status"] == "valid"
    assert w.publish()["status"] == "refused"
    receipt = w.write_receipt(tmp_path / "receipt.json")
    owner.verify_owner_run_receipt(
        Execution(tmp_path / "store"), receipt, publication_directory=None
    )


def test_unread_refusal_is_bounded_and_verifies_earnings(tmp_path):
    core = te.api()
    pack = te.pack_for("E-REQUIRED-CP1-MISSING")
    w = core.EarningsWorkflow.create(
        tmp_path / "owner", pack, case_manifest=te.CASE_MANIFEST, case_id="E-REQUIRED-CP1-MISSING"
    )

    def read():
        for source in ("identity", "financial"):
            w.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})

    read()
    out = w.submit_review(PAYLOAD)
    assert out.disposition == "refused"
    folder = core._audit(w._store, "outcomes", "x").parent
    stored = [json.loads(p.read_bytes()) for p in folder.iterdir()]
    assert 0 < max(len(o["issues"]) for o in stored) <= MAX_ISSUES
    assert _largest(folder) <= LIMIT
    assert len(json.dumps(list(out.error_codes)).encode()) <= LIMIT
    read()
    assert w.submit_review(te.foundation_review(pack, True)).disposition == "valid"
    receipt = w.write_receipt(tmp_path / "receipt.json")
    core.verify_earnings_owner_receipt(Execution(tmp_path / "owner"), receipt)


def test_source_context_amplification_refusal_is_bounded(tmp_path):
    from deploy_workflow import financial_workflow as fin

    w, pack = fw.start(tmp_path / "c")
    fw.read_sources(w)
    assert w.submit_review(fw.readiness(pack))["status"] == "valid"
    for source in ("identity", "financial"):
        w.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})
    w.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})
    rows = ",".join(['{"event_scan":"no_events_identified","source_id":"z"}'] * ROWS)
    amplified = '{"sources":{"' + KEY + '":[' + rows + "]}}"
    out = w.submit_review(amplified)
    assert out["status"] == "refused"
    assert _largest(fin._audit(w._store, "submissions", "x").parent) <= LIMIT
    assert len(json.dumps(out, ensure_ascii=False).encode()) <= LIMIT


def test_the_real_worst_case_record_bound_holds_for_escaped_characters():
    """F1: a control-character id is stored as six bytes a character, so two rules at one step
    exceed the 64 KiB the ASCII tests assert, and stay within `WORST_CASE`."""
    ident = "\x01" * 700
    absence = [
        {"event_scan": "no_events_identified", "source_id": f"{ident}{i}"} for i in range(30)
    ]
    pages = [{"source_id": ident, "locator": f"page:{i}"} for i in range(30)]
    payload = json.dumps({"sources": absence, "c": pages})
    issues = _issues("source_context", payload)
    assert len(issues) == 2 * MAX_ISSUES
    assert max(len(line) for line in issues) <= MAX_ISSUE_CHARS
    size = len(json.dumps(issues).encode())
    assert LIMIT < size <= WORST_CASE
