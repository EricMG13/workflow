"""CP-3D Stage 2: the connections of the market-implied owner core, against the frozen oracle.

Fast tests only (no store run): the backlog rows, the plug-in parts of `docs/G1X-OWNER-CORE-
PROTOCOL.md` §2, the store adapter over `Module` objects built from the oracle's own CP-0 facts,
the `owner_workflow` registration rows, the bindings and `_Spec` row, and the reader. Every
expected value is read from `cases/cp3d-owner/` (never derived here). The store runs live in
`tests/test_owner_cp3d.py` (Stage 5).
"""

import copy
import hashlib
import importlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from deploy_vii import registry
from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import (
    Fact,
    Input,
    Module,
    ModuleView,
    Run,
    Source,
    Span,
    View,
)
from deploy_vii.execution import Head, head_of
from deploy_vii.live.tools import Seen
from deploy_vii.preparation import PreparedPack
from deploy_vii.quotes import quoted
from deploy_vii.report_view import _RELATIVE_VALUE, _Spec, _spec_of, fact_spelling
from deploy_workflow import host
from deploy_workflow.owners import cp3d
from deploy_workflow.workflow import WorkflowError

base: Any = importlib.import_module("test_method_cp3d")
owner: Any = importlib.import_module("deploy_workflow.owner_workflow")

POSITIVE = base.SUBMISSIONS["positive"]
ZWSP = "\u200b"  # one zero-width space: `is_blank`, yet a one-character page substring


def _context_with(char: str) -> cp3d.MarketContext:
    """The positive context with `char` appended to every page, so a one-character quote of it
    occurs on its page (the shape that reached the occurrence check before the blank check)."""
    ctx = base._context("positive")
    pages = {sid: {loc: text + char for loc, text in by.items()} for sid, by in ctx.pages.items()}
    return cp3d.MarketContext(
        pages=pages,
        names=ctx.names,
        third_party=ctx.third_party,
        published=ctx.published,
        run_as_of=ctx.run_as_of,
    )


# The positive literal with a quoted reference rate level, so every quote site is present.
WITH_LEVEL = base._edited(
    POSITIVE,
    [
        ["terms.reference_rate.absence", None],
        [
            "terms.reference_rate.level",
            {
                "quote": {
                    "source_id": "financial",
                    "locator": "page:5",
                    "quote": "The SOFR reference rate level is 4.30 percent.",
                },
                "percent_text": "4.30",
            },
        ],
    ],
)

# (edit path of the quote text, the issue path the validator prefixes)
QUOTE_SITES = (
    ("observations.0.quote", "observations[0]"),
    ("instrument.quote.quote", "instrument.quote"),
    ("terms.maturity.quote.quote", "maturity"),
    ("terms.margin.quote.quote", "margin"),
    ("terms.amortisation.quote.quote", "amortisation"),
    ("terms.reference_rate.quote.quote", "reference_rate.quote"),
    ("terms.reference_rate.level.quote.quote", "reference_rate.level.quote"),
    ("technicals.1.basis.0.quote", "technicals[1].basis[0]"),
)


@pytest.mark.parametrize(("edit", "path"), QUOTE_SITES, ids=[s[0] for s in QUOTE_SITES])
def test_backlog_blank_quote_is_refused_as_empty_text(edit: str, path: str) -> None:
    """Round 13 addendum 3: a quote that `is_blank` gets `<path>: empty text` before the page
    check, even when the page holds that one character."""
    raw = base._edited(WITH_LEVEL, [[edit, ZWSP]])
    issues = cp3d.submission_issues(submission=base._submission(raw), context=_context_with(ZWSP))
    assert f"{path}: empty text" in issues
    assert not any("quote not found" in i and i.startswith(path) for i in issues)


def test_backlog_blank_quote_site_inventory_is_complete() -> None:
    """Every `quote` string of the positive literal is covered by a site above (a new quote
    field would fail here until it is listed)."""
    found: list[str] = []

    def walk(node: Any, trail: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{trail}.{key}" if trail else key)
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{trail}.{i}")
        elif trail.endswith("quote") and isinstance(node, str):
            found.append(trail)

    walk(copy.deepcopy(WITH_LEVEL), "")
    listed = {site for site, _ in QUOTE_SITES}
    kinds = {
        "observations.1.quote": "observations.0.quote",
        "observations.2.quote": "observations.0.quote",
    }
    for site in found:
        generic = site if site in listed else kinds.get(site)
        if generic is None and ".basis." in site:
            generic = "technicals.1.basis.0.quote"
        assert generic in listed, site


def test_backlog_signed_value_text_is_matched_on_the_plain_reading_only() -> None:
    """r12 Info: `margin -\\n425 bps` with value `-425` fails closed (the plain reading prints
    `- 425`); the unsigned `425` is never taken instead, so the sign cannot flip."""
    ctx = base._context("positive")
    page = ctx.pages["financial"]["page:5"]
    quote = "spread -\n425 basis points"
    pages = {**ctx.pages, "financial": {**ctx.pages["financial"], "page:5": page + "\n" + quote}}
    context = cp3d.MarketContext(
        pages=pages,
        names=ctx.names,
        third_party=ctx.third_party,
        published=ctx.published,
        run_as_of=ctx.run_as_of,
    )
    for text in ("-425", "425"):
        raw = base._edited(
            POSITIVE,
            [["terms.margin.quote.quote", quote], ["terms.margin.bps_text", text]],
        )
        issues = cp3d.submission_issues(submission=base._submission(raw), context=context)
        assert issues, text
        assert all(i.startswith("margin: bps_text") for i in issues), issues


def test_backlog_raw_value_is_compared_with_the_normalised_quote() -> None:
    """Info (CP-2E, CP-3D, predates): the name is tested against `normalise(quote)`, which maps
    U+2212 to `-`, so a name holding U+2212 never occurs. It fails closed."""
    ctx = _context_with("")
    name = "Northbridge Term−Loan"
    page = ctx.pages["market"]["page:1"].replace("Term Loan", "Term−Loan", 1)
    pages = {**ctx.pages, "market": {**ctx.pages["market"], "page:1": page}}
    context = cp3d.MarketContext(
        pages=pages,
        names=ctx.names,
        third_party=ctx.third_party,
        published=ctx.published,
        run_as_of=ctx.run_as_of,
    )
    quote = POSITIVE["instrument"]["quote"]["quote"].replace("Term Loan", "Term−Loan", 1)
    raw = base._edited(
        POSITIVE,
        [["instrument.name", name], ["instrument.quote.quote", quote]],
    )
    issues = cp3d.submission_issues(submission=base._submission(raw), context=context)
    assert "instrument: name does not occur in the quote" in issues
    assert json.dumps(issues)  # fail closed: refused, never accepted


# The accepted costs `methods/cp3d.md` records: (value_text, quote, page, occurs_whole).
GUARD_COSTS = (
    # rule W: the second figure of a spaced range and a dash bullet are cut on the page
    ("96", "96 percent", "rate 95 - 96 percent now", False),
    ("25", "25 basis points", "items\n- 25 basis points\n", False),
    ("25", "25 percent", "A-\n25 percent here", True),  # a hyphen wrap stays a wrap
    # item 8: a grouped figure, a decimal comma, a comma-space list, a figure after a year, and
    # the day of a `Month D, YYYY` date are no figure
    ("1250", "fee 1,250 usd", "fee 1,250 usd", False),
    ("25", "fee 25,5 usd", "fee 25,5 usd", False),
    ("25", "a 25, 5 b", "a 25, 5 b", False),
    ("31", "in 2029, 31 loans", "in 2029, 31 loans", False),
    ("31", "December 31, 2029", "December 31, 2029", False),
    ("25", "up, 25 now", "up, 25 now", True),  # a comma before a letter is not a run
    ("25", "25, a", "25, a", True),
)


@pytest.mark.parametrize(("value", "quote", "page", "whole"), GUARD_COSTS)
def test_backlog_guard_limit_costs_are_as_the_method_note_records(
    value: str, quote: str, page: str, whole: bool
) -> None:
    assert (cp3d._token_once(value, quote) and cp3d._whole_on_page(value, quote, page)) is whole


def test_backlog_method_note_records_every_guard_limit() -> None:
    note = (Path(cp3d.__file__).parents[2] / "deploy_vii" / "methods" / "cp3d.md").read_text(
        encoding="utf-8"
    )
    for marker in (
        "Rule W",
        "spaced range",
        "dash bullet",
        "Item 8 comma costs",
        "grouped figure",
        "decimal comma",
        "comma-space list",
        "follows a year",
        "`Month D, YYYY`",
        "Round 10 sign rule",
        "Unsigned grammar",
        "negative",
        "signed `value_text`",
        "normalised quote",
        "Blank quotes",
    ):
        assert marker in note, marker


# --- the oracle's pack, CP-0 head and report ---------------------------------------------------

CASES = base.CASES
EXPECTED = base.EXPECTED
STEP = "market_implied"


def _pack(case: str) -> PreparedPack:
    """The case's pack from the manifest's source list and the pinned page bytes."""
    meta = base._manifest_case(case)
    pages = base._all_pages()
    sources = tuple(
        Source(
            source_id=s["source_id"],
            name=s["name"],
            status=s["status"],
            sha256=s["sha256"],
            spans=tuple(
                Span(locator=loc, text=text) for loc, text in pages[s["source_id"]].items()
            ),
            extraction_status="complete",
        )
        for s in meta["pack_sources"]
    )
    return PreparedPack(run=Run.model_validate_json(json.dumps(meta["run"])), sources=sources)


def _cp0(case: str) -> Module:
    """A settled restricted CP-0 head built from the oracle's own CP-0 facts and limitations."""
    oracle = EXPECTED["cp0"][case]
    run = base._manifest_case(case)["run"]
    return Module(
        run_id=run["run_id"],
        issuer_id=run["issuer_id"],
        as_of=date.fromisoformat(run["as_of"]),
        module_id="CP-0",
        status="restricted",
        facts=tuple(
            Fact(fact_id=f["fact_id"], label=f["fact_id"], text=f["text"]) for f in oracle["facts"]
        ),
        limitations=tuple(oracle["limitations"]),
    )


def _upstream(case: str) -> cp3d.Upstream:
    return cp3d.upstream_of(pack=_pack(case), cp0=_cp0(case))


def _report(case: str) -> cp3d.MarketImpliedReport:
    return cp3d.market_implied(
        pack=_pack(case),
        submission=base._submission(base.SUBMISSIONS[case]),
        upstream=_upstream(case),
    )


def _inputs(case: str) -> tuple[Input, ...]:
    return (
        Input(input_id="prepared-pack", sha256=_pack(case).content_hash()),
        Input(input_id="CP-0", sha256=_cp0(case).content_hash(), status="restricted"),
    )


def _module(case: str) -> Module:
    return cp3d.cp3d_module(report=_report(case), inputs=_inputs(case), attempt=0)


# --- the store adapter -------------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_adapter_returns_the_stage_1_context_object(case: str) -> None:
    """`MarketContext` equals the Stage 1 test's own object field by field (pages, names, the
    CP-0 third_party set, the page publication dates and the run as-of date)."""
    assert _upstream(case).context == base._context(case)


@pytest.mark.parametrize("case", CASES)
def test_adapter_inherits_the_cp0_limitations_then_its_inherited_ones(case: str) -> None:
    sub = base._submission(base.SUBMISSIONS[case])
    up = _upstream(case)
    own = cp3d.own_limitations(sub)
    expected = EXPECTED["cases"][case]
    assert (
        list(cp3d.inherited_limitations(own=own, upstream=up.inherited))
        == expected["inherited_limitations"]
    )


def test_adapter_reads_inherited_limitations_in_order_without_repeats() -> None:
    cp0 = _cp0("positive").model_copy(
        update={"limitations": ("a", "b"), "inherited_limitations": ("b", "c")}
    )
    assert cp3d.upstream_of(pack=_pack("positive"), cp0=cp0).inherited == ("a", "b", "c")


def test_adapter_third_party_follows_the_cp0_t3_authority_text() -> None:
    cp0 = _cp0("positive")
    facts = tuple(
        f.model_copy(update={"text": "issuer"}) if f.fact_id == "T3.market.authority" else f
        for f in cp0.facts
    )
    up = cp3d.upstream_of(pack=_pack("positive"), cp0=cp0.model_copy(update={"facts": facts}))
    assert up.context.third_party == frozenset()


class _Store:
    """A test-only store: the pack and the settled modules a hash names."""

    def __init__(self, pack: PreparedPack, modules: dict[str, Module]) -> None:
        self._pack, self._modules = pack, modules

    def pack(self) -> PreparedPack:
        return self._pack

    def result(self, sha256: str) -> Module:
        return self._modules[sha256]


def _attempt(case: str, inputs: tuple[Input, ...] | None = None) -> Any:
    return SimpleNamespace(inputs=_inputs(case) if inputs is None else inputs, number=0)


def test_cp3d_upstream_reads_the_bound_cp0_head_from_the_store() -> None:
    cp0 = _cp0("positive")
    store = _Store(_pack("positive"), {cp0.content_hash(): cp0})
    got = cp3d.cp3d_upstream(store=cast(Any, store), attempt=_attempt("positive"))
    assert got == _upstream("positive")


@pytest.mark.parametrize("drop", ["CP-0", "twice"])
def test_cp3d_upstream_refuses_a_missing_or_doubled_cp0_binding(drop: str) -> None:
    cp0 = _cp0("positive")
    store = _Store(_pack("positive"), {cp0.content_hash(): cp0})
    inputs = _inputs("positive")
    bad = (
        tuple(i for i in inputs if i.input_id != "CP-0") if drop == "CP-0" else (*inputs, inputs[1])
    )
    with pytest.raises(WorkflowError) as error:
        cp3d.cp3d_upstream(store=cast(Any, store), attempt=_attempt("positive", bad))
    assert error.value.args[0] == "identity_mismatch"


# --- the report and the module -----------------------------------------------------------------


def _fact_view(fact: Fact) -> dict[str, Any]:
    return {
        "amount": None if fact.amount is None else format(fact.amount, "f"),
        "unit": fact.unit,
        "decimals": fact.decimals,
        "text": fact.text,
        "status": fact.status,
        "period": fact.period,
        "value_class": fact.value_class,
        "calculation_id": fact.calculation_id,
        "formula": fact.formula,
        "limitation": fact.limitation,
        "cites": [[c.source_id, c.locator] for c in fact.citations],
    }


def _expected_view(cell: dict[str, Any]) -> dict[str, Any]:
    return {
        "amount": cell["amount"],
        "unit": cell["unit"],
        "decimals": cell["decimals"],
        "text": cell["text"],
        "status": cell["status"],
        "period": cell["period"],
        "value_class": cell["value_class"],
        "calculation_id": cell["calculation_id"],
        "formula": cell["formula"],
        "limitation": cell["limitation"],
        "cites": cell["cites"],
    }


@pytest.mark.parametrize("case", CASES)
def test_module_tables_facts_and_spelling_equal_the_oracle(case: str) -> None:
    module = _module(case)
    facts = {f.fact_id: f for f in module.facts}
    tables = EXPECTED["cases"][case]["tables"]
    assert [t.table_id for t in module.tables] == [t["table_id"] for t in tables]
    seen: list[str] = []
    for table, want in zip(module.tables, tables, strict=True):
        assert (table.title, table.row_header) == (want["title"], want["row_header"])
        assert [(c.field, c.label) for c in table.columns] == [
            (c["field"], c["label"]) for c in want["columns"]
        ]
        assert [(r.row_id, r.label) for r in table.rows] == [
            (r["row_id"], r["label"]) for r in want["rows"]
        ]
        for row, want_row in zip(table.rows, want["rows"], strict=True):
            assert list(row.fact_ids) == [c["fact_id"] for c in want_row["facts"]]
            for fact_id, cell in zip(row.fact_ids, want_row["facts"], strict=True):
                fact = facts[fact_id]
                seen.append(fact_id)
                assert (fact.table_id, fact.row_id) == (table.table_id, row.row_id)
                assert fact.label == f"{row.label} · {cell['column']}"
                assert _fact_view(fact) == _expected_view(cell), fact_id
                shown = fact_spelling(fact, "G1")[2]
                assert shown == cell["shown"].replace("G#", "G1"), fact_id
    assert seen == [f.fact_id for f in module.facts]


@pytest.mark.parametrize("case", CASES)
def test_module_claims_limitations_and_inputs_equal_the_oracle(case: str) -> None:
    module, want = _module(case), EXPECTED["cases"][case]
    assert [(c.claim_id, c.text) for c in module.claims] == [
        (c["claim_id"], c["text"]) for c in want["claims"]
    ]
    assert [[[x.source_id, x.locator] for x in c.citations] for c in module.claims] == [
        c["cites"] for c in want["claims"]
    ]
    assert list(module.limitations) == want["own_limitations"]
    assert list(module.inherited_limitations) == want["inherited_limitations"]
    assert [i.input_id for i in module.inputs] == want["module_inputs"]
    submission = base._submission(base.SUBMISSIONS[case])
    assert module.inputs[-1].sha256 == submission.content_hash()
    assert module.module_id == "CP-3D" and module.attempt == 0


@pytest.mark.parametrize("case", CASES)
def test_every_citation_quote_is_verbatim_on_its_pack_page(case: str) -> None:
    pack = _pack(case)
    sha = {s.source_id: s.sha256 for s in pack.sources}
    pages = {s.source_id: {p.locator: p.text for p in s.spans} for s in pack.sources}
    module = _module(case)
    cites = [c for f in module.facts for c in f.citations] + [
        c for claim in module.claims for c in claim.citations
    ]
    assert cites
    for c in cites:
        assert c.source_sha256 == sha[c.source_id]
        assert quoted(c.quote, pages[c.source_id][c.locator]), (c.source_id, c.locator)


def test_market_implied_refuses_a_submission_the_validator_refuses() -> None:
    raw = base._edited(POSITIVE, [["observations.0.level_text", "98.60"]])
    with pytest.raises(ValueError, match="does not occur"):
        cp3d.market_implied(
            pack=_pack("positive"), submission=base._submission(raw), upstream=_upstream("positive")
        )


def test_report_round_trips_through_its_json() -> None:
    report = _report("positive")
    assert cp3d.MarketImpliedReport.model_validate_json(report.model_dump_json()) == report
    assert report.submission_sha256 == base._submission(POSITIVE).content_hash()
    assert report.pack_sha256 == _pack("positive").content_hash()


def test_a_cell_without_a_quote_on_its_page_fails_closed() -> None:
    """A cite whose page the cell has no submitted quote for has no citation text: never invented."""
    with pytest.raises(ValueError, match="no quote"):
        cp3d.cite_of(_pack("positive"), cp3d.Cites(), ("market", "page:1"))


def test_cites_compare_as_the_page_pairs_and_keep_each_pages_quotes_in_order() -> None:
    refs = [
        cp3d._Ref("market", "page:1", "a"),
        cp3d._Ref("financial", "page:5", "b"),
        cp3d._Ref("market", "page:1", "c"),
        cp3d._Ref("market", "page:1", "a"),
    ]
    cites = cp3d.Cites(refs)
    assert tuple(cites) == (("market", "page:1"), ("financial", "page:5"))
    assert dict(cites.quotes) == {("market", "page:1"): ("a", "c"), ("financial", "page:5"): ("b",)}
    merged = cp3d.Cites.merged([cp3d.Cites(refs[:1]), cp3d.Cites(refs[1:])])
    assert dict(merged.quotes) == dict(cites.quotes)


def _quote_of(fact: Fact) -> list[str]:
    return [c.quote for c in fact.citations]


def test_each_fact_cites_the_quote_that_supports_it() -> None:
    """M1: terms facts cite their own quote, not the first quote on their page."""
    facts = {f.fact_id: f for f in _module("positive").facts}
    t, pos = POSITIVE["terms"], POSITIVE
    assert _quote_of(facts["T3E.4.r02.value"]) == [t["reference_rate"]["quote"]["quote"]]
    assert _quote_of(facts["T3E.4.r03.value"]) == [t["maturity"]["quote"]["quote"]]
    assert _quote_of(facts["T3E.4.r04.value"]) == [t["amortisation"]["quote"]["quote"]]
    assert _quote_of(facts["T3E.4.r05.value"]) == [pos["instrument"]["quote"]["quote"]]
    obs = {o["kind"]: o["quote"] for o in pos["observations"]}
    assert _quote_of(facts["T3E.1.r01.level"]) == [obs["bid"]]
    assert _quote_of(facts["T3E.1.r02.level"]) == [obs["offer"]]
    assert _quote_of(facts["T3E.1.r03.level"]) == [obs["indicative_talk"]]
    assert _quote_of(facts["T3E.3.r02.mid"]) == [t["margin"]["quote"]["quote"]]


def test_a_quoted_reference_rate_level_cites_its_own_quote() -> None:
    level_q = "The SOFR reference rate level is 4.30 percent."
    pack = _pack("positive")
    sources = tuple(
        s.model_copy(
            update={
                "spans": tuple(
                    Span(
                        locator=sp.locator,
                        text=sp.text + "\n" + level_q if sp.locator == "page:5" else sp.text,
                    )
                    for sp in s.spans
                )
            }
        )
        if s.source_id == "financial"
        else s
        for s in pack.sources
    )
    pack = pack.model_copy(update={"sources": sources})
    level = {
        "quote": {"source_id": "financial", "locator": "page:5", "quote": level_q},
        "percent_text": "4.30",
    }
    raw = base._edited(
        POSITIVE, [["terms.reference_rate.absence", None], ["terms.reference_rate.level", level]]
    )
    up = cp3d.upstream_of(pack=pack, cp0=_cp0("positive"))
    report = cp3d.market_implied(pack=pack, submission=base._submission(raw), upstream=up)
    levels = [
        f
        for f in report.facts
        if f.table_id == "T3E.3" and f.value_class == "source" and f.unit == "decimal_fraction"
    ]
    assert levels
    assert all(_quote_of(f) == [level_q] for f in levels)


@pytest.mark.parametrize("case", CASES)
def test_every_citation_quote_is_one_the_submission_gave_for_that_page(case: str) -> None:
    """A derived cell cites an input quote of its own page, never one invented or foreign."""
    submission = base._submission(base.SUBMISSIONS[case])
    given: dict[tuple[str, str], set[str]] = {}
    for ref in cp3d.cited_refs(submission):
        given.setdefault((ref.source_id, ref.locator), set()).add(ref.quote)
    module = _module(case)
    for fact in module.facts:
        for c in fact.citations:
            assert c.quote in given[(c.source_id, c.locator)], fact.fact_id
    for claim in module.claims:
        for c in claim.citations:
            assert c.quote in given[(c.source_id, c.locator)], claim.claim_id


def test_technicals_cite_their_basis_quotes() -> None:
    module = _module("positive")
    cited = {c.quote for f in module.facts if f.table_id == "T3E.6" for c in f.citations}
    basis = {b["quote"] for x in POSITIVE["technicals"] for b in x["basis"]}
    assert cited == basis


def test_a_derived_fact_cites_the_first_input_quote_on_each_page() -> None:
    """The simple discount margin at the mid rests on bid, offer, margin, amortisation and
    maturity quotes; one Citation per page, the first input quote on it (documented, not invented)."""
    fact = next(f for f in _module("positive").facts if f.fact_id == "T3E.3.r03.mid")
    obs = {o["kind"]: o["quote"] for o in POSITIVE["observations"]}
    t = POSITIVE["terms"]
    assert [(c.source_id, c.locator, c.quote) for c in fact.citations] == [
        ("market", "page:1", obs["bid"]),
        ("financial", "page:5", t["margin"]["quote"]["quote"]),
    ]


# --- the plug-in parts -------------------------------------------------------------------------


def test_core_constants_equal_the_lease() -> None:
    assert (cp3d.MODULE_ID, cp3d.STEP_ID, cp3d.STEP_IDS) == ("CP-3D", STEP, (STEP,))
    assert type(cp3d.STEP_IDS) is tuple and all(type(i) is str for i in cp3d.STEP_IDS)
    assert cp3d.SCHEMAS == {STEP: cp3d.MarketImpliedSubmission}
    assert cp3d.QUALIFICATION.implementation == "implemented"
    assert (
        cp3d.SUBMISSION_INPUT
        == STEP.replace("_", "-") + "-submission"
        == ("market-implied-submission")
    )


@pytest.mark.parametrize("case", CASES)
def test_schemas_round_trip_and_give_the_tail_digest(case: str) -> None:
    text = json.dumps(base.SUBMISSIONS[case])
    schema = cp3d.SCHEMAS[STEP]
    parsed = schema.model_validate_json(text)
    assert schema.model_validate_json(parsed.model_dump_json()) == parsed
    digest = hashlib.sha256(parsed.model_dump_json().encode()).hexdigest()
    assert parsed.content_hash() == digest
    assert _report(case).submission_sha256 == digest


def _rules_case(entry: dict[str, Any]) -> tuple[str, Seen]:
    raw = base._edited(POSITIVE, entry.get("edits", []))
    reads = frozenset((s, loc) for s, loc in entry["reads"])
    return json.dumps(raw), Seen(reads, (None,) * entry["searches"])


@pytest.mark.parametrize("entry", base.SUBMISSIONS["tool_use_refusals"], ids=lambda e: e["id"])
def test_rules_reproduce_the_oracle_tool_use_refusals(entry: dict[str, Any]) -> None:
    text, seen = _rules_case(entry)
    assert list(cp3d.RULES(text, seen)) == entry["issues"]
    expected = [e for e in EXPECTED["tool_use_refusals"] if e["id"] == entry["id"]]
    assert expected[0]["issues"] == entry["issues"]


def test_rules_pass_when_every_page_is_read_and_a_search_is_recorded() -> None:
    reads = frozenset({("market", "page:1"), ("market", "page:2"), ("financial", "page:5")})
    assert cp3d.RULES(json.dumps(POSITIVE), Seen(reads, (None,))) == ()


def test_rules_absence_comes_first_then_unread_pages() -> None:
    issues = cp3d.RULES(json.dumps(POSITIVE), Seen(frozenset(), ()))
    assert issues[0] == "Absence claim without a recorded search"
    assert issues[1:] == (
        "Cited page not read through read_pages: financial page:5",
        "Cited page not read through read_pages: market page:1",
        "Cited page not read through read_pages: market page:2",
    )


def test_recovery_absence_is_not_an_absence_object() -> None:
    raw = copy.deepcopy(base.SUBMISSIONS["gap_no_recovery"])
    raw["terms"]["reference_rate"]["absence"] = None
    raw["terms"]["reference_rate"]["level"] = None
    assert raw["recovery_absence"] is not None
    reads = frozenset({("market", "page:1"), ("market", "page:2"), ("financial", "page:5")})
    assert cp3d.RULES(json.dumps(raw), Seen(reads, ())) == ()


@pytest.mark.parametrize("text", ["", "[]", "not json", '{"terms": 3}'])
def test_rules_on_a_payload_that_is_not_a_submission_object_find_nothing_to_back(text: str) -> None:
    """Fail closed elsewhere (the validator refuses the shape); the rules judge only what parses."""
    assert cp3d.RULES(text, Seen(frozenset(), ())) == ()


def test_entry_validator_is_the_step_validator() -> None:
    assert cp3d.ENTRY_VALIDATOR is cp3d._validate_step


def _attempt_with_payload(payload_sha: str, case: str = "positive") -> Any:
    step = SimpleNamespace(step_id=STEP, payload_sha256=payload_sha, inputs=())
    return SimpleNamespace(inputs=_inputs(case), number=0, steps=(step,), module_id="CP-3D")


class _PayloadStore(_Store):
    def __init__(self, case: str, payload: str) -> None:
        cp0 = _cp0(case)
        super().__init__(_pack(case), {cp0.content_hash(): cp0})
        self._payload = payload

    def payload(self, sha256: str) -> str:
        assert sha256 == "p" * 64
        return self._payload


@pytest.mark.parametrize("case", CASES)
def test_entry_validator_outputs_the_report_for_each_oracle_literal(case: str) -> None:
    store = _PayloadStore(case, json.dumps(base.SUBMISSIONS[case]))
    outcome = cp3d.ENTRY_VALIDATOR(
        cast(Any, store), _pack(case), _attempt_with_payload("p" * 64, case)
    )
    assert outcome.issues == ()
    assert outcome.output == _report(case).model_dump_json()


@pytest.mark.parametrize("entry", base.MUTATIONS["entries"], ids=lambda e: e["id"])
def test_entry_validator_reproduces_the_oracle_refusals(entry: dict[str, Any]) -> None:
    raw = base._edited(base.SUBMISSIONS[base.MUTATIONS["base"]], entry["edits"])
    case = base.MUTATIONS["base"]
    store = _PayloadStore(case, json.dumps(raw))
    outcome = cp3d.ENTRY_VALIDATOR(cast(Any, store), _pack(case), _attempt_with_payload("p" * 64))
    expected = entry["issue"]
    assert list(outcome.issues) == [expected]
    assert outcome.output is None


def test_entry_validator_reports_a_malformed_payload_as_shape_issues() -> None:
    store = _PayloadStore("positive", '{"instrument": 3}')
    outcome = cp3d.ENTRY_VALIDATOR(
        cast(Any, store), _pack("positive"), _attempt_with_payload("p" * 64)
    )
    assert outcome.output is None and outcome.issues
    assert all(": " in i for i in outcome.issues)


def test_a_malformed_summary_is_reported_beside_a_content_issue() -> None:
    """The RunText check is unconditional (as CP-2E's): a content issue never masks it."""
    raw = copy.deepcopy(base.SUBMISSIONS["positive"])
    raw["summary"]["text"] = "Undervalued [a"
    issues = cp3d.validate_market_implied(
        submission=cp3d.MarketImpliedSubmission.model_validate_json(json.dumps(raw)),
        upstream=_upstream("positive"),
    )
    assert issues == (
        "summary.text: text carries a prohibited conclusion",
        "summary.text: Value error, Malformed run text: unbalanced or empty reference",
    )
    raw["summary"]["text"] = "A summary with no figure [a"
    only = cp3d.validate_market_implied(
        submission=cp3d.MarketImpliedSubmission.model_validate_json(json.dumps(raw)),
        upstream=_upstream("positive"),
    )
    assert only == issues[1:]


def test_entry_validator_refuses_text_json_object_refuses_even_if_the_schema_parses_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Protocol section 6: the payload is read only through `json_object`. Whatever it refuses is
    refused, even a text the schema alone would parse (as in CP-2D and CP-1D)."""
    calls: list[str] = []

    def refuse(payload: str) -> None:
        calls.append(payload)

    monkeypatch.setattr(cp3d, "json_object", refuse)
    store = _PayloadStore("positive", json.dumps(base.SUBMISSIONS["positive"]))
    outcome = cp3d.ENTRY_VALIDATOR(
        cast(Any, store), _pack("positive"), _attempt_with_payload("p" * 64)
    )
    assert len(calls) == 1
    assert outcome.output is None
    assert outcome.issues == ("(root): not a bounded JSON object",)


@pytest.mark.parametrize("text", ["[]", "[1]", '"x"', "null", '{"a": ' + "[" * 200 + "}"])
def test_entry_validator_reports_non_objects_as_bounded_shape_issues(text: str) -> None:
    """Protocol section 6: text `json_object` refuses never reaches the schema; the issue is the
    one bounded line the other owner cores give."""
    store = _PayloadStore("positive", text)
    outcome = cp3d.ENTRY_VALIDATOR(
        cast(Any, store), _pack("positive"), _attempt_with_payload("p" * 64)
    )
    assert outcome.output is None
    assert len(outcome.issues) >= 1
    assert all(len(line) <= 600 for line in outcome.issues)


class _JournalStore(_PayloadStore):
    """A test-only journal: `submit_step` runs the validator over a one-step attempt and `finish`
    runs the supplied validator over the candidate; nothing is persisted."""

    def __init__(self, case: str, payload: str) -> None:
        super().__init__(case, payload)
        self.case = case
        self.finished: list[tuple[Module, Any]] = []

    def submit_step(
        self,
        ticket_id: str,
        module_id: str,
        sequence: tuple[str, ...],
        step_id: str,
        payload: str,
        validate: Any,
    ) -> Any:
        assert (module_id, sequence, step_id) == ("CP-3D", (STEP,), STEP)
        self._payload = payload
        step = SimpleNamespace(
            step_id=step_id, payload_sha256="p" * 64, status="pending", output_sha256=None
        )
        attempt = SimpleNamespace(
            inputs=_inputs(self.case),
            number=0,
            steps=(step,),
            status="pending",
            module_id=module_id,
        )
        outcome = validate(self._pack, attempt)
        step.issues = outcome.issues
        if outcome.issues:
            step.status, attempt.status = "invalid", "finished"
        else:
            step.status = "valid"
            step.output_sha256 = hashlib.sha256(outcome.output.encode()).hexdigest()
        return attempt

    def finish(self, ticket_id: str, payload: str, validator: Any, *, qualification: Any) -> Any:
        candidate = Module.model_validate_json(payload)
        assert validator(candidate) == ()
        assert validator(candidate.model_copy(update={"attempt": 1})) != ()
        self.finished.append((candidate, qualification))
        return SimpleNamespace(status="finished", steps=(), module_id="CP-3D")


@pytest.mark.parametrize("case", CASES)
def test_submit_journals_the_step_then_settles_the_python_candidate(case: str) -> None:
    store = _JournalStore(case, "")
    payload = json.dumps(base.SUBMISSIONS[case])
    submitted = cp3d.submit(cast(Any, store), "t1", STEP, payload, None)
    assert submitted.payload == payload and submitted.nulls_resolved == ()
    assert (submitted.prefilled, submitted.prefilled_kinds) == ((), ())
    [(candidate, qualification)] = store.finished
    assert candidate == _module(case)
    assert qualification == cp3d.QUALIFICATION


def test_submit_invalid_step_does_not_settle_and_keeps_the_validator_issue() -> None:
    entry = base.MUTATIONS["entries"][0]
    raw = base._edited(base.SUBMISSIONS[base.MUTATIONS["base"]], entry["edits"])
    store = _JournalStore(base.MUTATIONS["base"], "")
    submitted = cp3d.submit(cast(Any, store), "t1", STEP, json.dumps(raw), None)
    assert store.finished == []
    assert submitted.journal.steps[0].status == "invalid"
    assert list(submitted.journal.steps[0].issues) == [entry["issue"]]


def test_submit_appends_the_rule_issues_after_the_validator_issues_without_repeats() -> None:
    entry = base.MUTATIONS["entries"][0]
    raw = base._edited(base.SUBMISSIONS[base.MUTATIONS["base"]], entry["edits"])
    store = _JournalStore(base.MUTATIONS["base"], "")
    seen = Seen(frozenset({("market", "page:2")}), ())
    submitted = cp3d.submit(
        cast(Any, store), "t1", STEP, json.dumps(raw), lambda text: cp3d.RULES(text, seen)
    )
    issues = list(submitted.journal.steps[0].issues)
    assert issues[0] == entry["issue"]
    assert "Absence claim without a recorded search" in issues
    assert len(issues) == len(set(issues))


def test_submit_with_a_failing_rule_alone_is_invalid_and_not_settled() -> None:
    store = _JournalStore("positive", "")
    seen = Seen(frozenset(), (None,))
    submitted = cp3d.submit(
        cast(Any, store), "t1", STEP, json.dumps(POSITIVE), lambda text: cp3d.RULES(text, seen)
    )
    assert store.finished == []
    assert list(submitted.journal.steps[0].issues) == [
        "Cited page not read through read_pages: financial page:5",
        "Cited page not read through read_pages: market page:1",
        "Cited page not read through read_pages: market page:2",
    ]


def test_submit_with_passing_rules_takes_the_path_it_takes_without_rules() -> None:
    reads = frozenset({("market", "page:1"), ("market", "page:2"), ("financial", "page:5")})
    seen = Seen(reads, (None,))
    plain, ruled = _JournalStore("positive", ""), _JournalStore("positive", "")
    payload = json.dumps(POSITIVE)
    cp3d.submit(cast(Any, plain), "t1", STEP, payload, None)
    cp3d.submit(cast(Any, ruled), "t1", STEP, payload, lambda text: cp3d.RULES(text, seen))
    assert plain.finished == ruled.finished and len(plain.finished) == 1


def test_submit_refuses_a_step_that_is_not_its_own() -> None:
    with pytest.raises(ValueError, match="one step"):
        cp3d.submit(cast(Any, _JournalStore("positive", "")), "t1", "research", "{}", None)


def test_precheck_and_view_are_absent_as_the_lease_says() -> None:
    assert not hasattr(cp3d, "precheck") and not hasattr(cp3d, "view")
    assert callable(cp3d.submit) and callable(cp3d.probe)


# --- L1: rules per absence path, the reader's refusals, settle and third_party -----------------

ABSENCE = {"reason": "none stated", "follow_up": "supply it"}
ABSENCE_DOCS = {
    "market_absence": {"market_absence": ABSENCE},
    "maturity": {"terms": {"maturity": {"absence": ABSENCE}}},
    "margin": {"terms": {"margin": {"absence": ABSENCE}}},
    "amortisation": {"terms": {"amortisation": {"absence": ABSENCE}}},
    "reference_rate": {"terms": {"reference_rate": {"absence": ABSENCE}}},
}


@pytest.mark.parametrize("name", ABSENCE_DOCS)
def test_each_absence_object_alone_needs_a_recorded_search(name: str) -> None:
    text = json.dumps(ABSENCE_DOCS[name])
    assert cp3d.RULES(text, Seen(frozenset(), ())) == ("Absence claim without a recorded search",)
    assert cp3d.RULES(text, Seen(frozenset(), (None,))) == ()


def test_reader_refuses_a_head_that_lacks_a_pinned_fact_rather_than_defaulting() -> None:
    module = _module("positive")
    for missing in (
        cp3d.READ_DM_MID,
        cp3d.READ_LAMBDA_MID,
        cp3d.READ_PD_MID,
        cp3d.READ_RECOVERY,
    ):
        short = module.model_copy(
            update={
                "facts": tuple(f for f in module.facts if f.fact_id != missing),
                "tables": (),
            }
        )
        head = head_of(short.model_copy(update={"status": "restricted"}), cp3d.QUALIFICATION)
        with pytest.raises(WorkflowError) as error:
            cp3d.cp3d_reader(
                cast(Any, _HeadStore(short.model_copy(update={"status": "restricted"}))), head
            )
        assert error.value.args[0] == "identity_mismatch", missing


def test_reader_refuses_another_modules_head_even_when_the_facts_are_there() -> None:
    module = _module("positive").model_copy(update={"status": "restricted"})
    head = head_of(module, cp3d.QUALIFICATION).model_copy(update={"module_id": "CP-0"})
    with pytest.raises(WorkflowError) as error:
        cp3d.cp3d_reader(cast(Any, _HeadStore(module)), head)
    assert error.value.args[0] == "identity_mismatch"


def test_settle_refuses_a_step_output_that_differs_from_the_trusted_validation() -> None:
    class Corrupt(_JournalStore):
        def submit_step(self, *args: Any, **kwargs: Any) -> Any:
            attempt = super().submit_step(*args, **kwargs)
            attempt.steps[0].output_sha256 = "0" * 64
            return attempt

    store = Corrupt("positive", "")
    with pytest.raises(ValueError, match="differs from trusted validation"):
        cp3d.submit(cast(Any, store), "t1", STEP, json.dumps(POSITIVE), None)
    assert store.finished == []


def test_third_party_reads_only_the_t3_authority_fact() -> None:
    cp0 = _cp0("positive")
    extra = Fact(fact_id="T3.identity.family", label="x", text="third_party")
    up = cp3d.upstream_of(
        pack=_pack("positive"), cp0=cp0.model_copy(update={"facts": (*cp0.facts, extra)})
    )
    assert up.context.third_party == frozenset({"market"})


# --- registration rows -------------------------------------------------------------------------


def _lease_spec() -> Any:
    """The lease's `OWNER_SPECS["CP-3D"]` line, written out."""
    return owner.OwnerSpec(
        "CP-3D",
        (
            owner.StepSpec(
                "market_implied",
                cp3d.MarketImpliedSubmission,
                sources=True,
                extract=False,
                upstream_grant=None,
                inputs="none",
                rules="journaled",
            ),
        ),
        "owner_core",
        "analytical",
        None,
    )


def test_owner_specs_row_equals_the_lease() -> None:
    assert owner.OWNER_SPECS["CP-3D"] == _lease_spec()


def test_every_owner_workflow_row_is_registered_for_cp3d() -> None:
    assert owner._CORES["CP-3D"] is cp3d
    assert "CP-3D" in owner.SUPPORTED_ANALYTICAL
    assert owner._QUALIFICATION["CP-3D"] == cp3d.QUALIFICATION
    assert owner._PROBES["CP-3D"] is cp3d.probe
    assert owner._ENTRY_VALIDATORS["CP-3D"] is cp3d.ENTRY_VALIDATOR
    assert STEP not in owner._VIEWS and "CP-3D" not in owner._PRECHECKS


def test_registrations_were_appended_not_reordered() -> None:
    assert "CP-3D" in owner._CORES
    specs = list(owner.OWNER_SPECS)
    assert specs[:5] == ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL"]
    assert "CP-3D" in specs[5:]


def test_check_steps_passes_for_the_registered_spec() -> None:
    owner._check_steps("CP-3D", owner.OWNER_SPECS["CP-3D"])


def test_check_steps_refuses_a_spec_that_differs_in_its_source_flag() -> None:
    spec = owner.OWNER_SPECS["CP-3D"]
    step = spec.steps[0]
    for bad in (
        owner.StepSpec(step.step_id, step.schema, False, False, None, "none", "journaled"),
        owner.StepSpec(step.step_id, step.schema, True, True, None, "none", "journaled"),
    ):
        with pytest.raises(WorkflowError):
            owner._check_steps(
                "CP-3D", owner.OwnerSpec("CP-3D", (bad,), "owner_core", "analytical", None)
            )


def test_the_h1_scope_row_agrees_with_the_spec_and_excludes_identity() -> None:
    assert host._SOURCE_STEPS["CP-3D"] == (STEP,)
    assert ("CP-3D", STEP) in host._OWNER_SCOPES
    assert owner.OWNER_SPECS["CP-3D"].steps[0].sources is True
    scope = host._OWNER_SCOPES[("CP-3D", STEP)](_pack("positive"))
    assert scope == ("financial", "market")
    assert host._OWNER_SCOPES[("CP-3D", STEP)](_pack("gap_no_market")) == ("financial",)


def test_registry_has_no_live_contract_and_plans_cp0_then_cp3d() -> None:
    with pytest.raises(ValueError, match="no live step contract"):
        registry.step_chain("CP-3D")
    assert registry.plan(("CP-3D",)) == ("CP-0", "CP-3D")


# --- bindings and the `_Spec` row --------------------------------------------------------------

BLOCK = "market-against-fundamentals"
RENDER = EXPECTED["render"]


def _binding_map() -> Any:
    maps = [m for m in SHIPPED_MAPS if m.module_id == "CP-3D"]
    assert len(maps) == 1
    return maps[0]


def test_binding_rows_follow_the_oracle_render_section() -> None:
    entries = _binding_map().entries
    block = RENDER["blocks"][BLOCK]
    tabs = [(e.fact_coord.table_id, e.label) for e in entries if e.block_id == BLOCK]
    assert tabs == [tuple(t) for t in block["tabs"]]
    assert tabs[0][0] == block["primary"]
    assert [e.fact_coord.table_id for e in entries if e.block_id == "evidence"] == RENDER["blocks"][
        "evidence rail"
    ]
    assert [e.fact_coord.table_id for e in entries if e.block_id == "limitations"] == RENDER[
        "blocks"
    ]["limitations rail"]
    assert {e.block_id for e in entries} == {BLOCK, "evidence", "limitations"}
    assert all(e.cell_slot.startswith(RENDER["slot_prefix"]) for e in entries)
    assert all(e.fact_coord.module_id == "CP-3D" for e in entries)
    assert all(e.fact_coord.row_id is None and e.fact_coord.fact_id is None for e in entries)


def test_shipped_maps_place_cp3d_after_cp3() -> None:
    order = [m.module_id for m in SHIPPED_MAPS]
    assert order.index("CP-3D") == order.index("CP-3") + 1


def test_relative_value_composition_holds_the_one_block_and_can_take_more() -> None:
    assert next(iter(_RELATIVE_VALUE)) == BLOCK  # the creator's row first; later rows append
    spec = _spec_of(BLOCK)
    assert spec == _Spec(
        "Market against fundamentals", "CP-3D", "dense", ("CP-3D",), route_label="Full analysis"
    )
    block = RENDER["blocks"][BLOCK]
    assert (spec.owner, spec.kind, spec.route_label) == (
        block["owner"],
        "dense",
        block["route_label"],
    )
    assert _spec_of("instrument-levels").owner == "Unbound"  # CP-3's, deferred
    assert _spec_of("yield-against-maturity").owner == "Unbound"  # CP-3D's own, deferred


@pytest.mark.parametrize("case", CASES)
def test_validate_bindings_over_the_expected_tables_is_empty(case: str) -> None:
    module = _module(case)
    pack = _pack(case)
    view = View(
        run=pack.run,
        mode="candidate",
        modules=(
            ModuleView(
                module_id="CP-3D",
                title="Market implied risk",
                aliases=(),
                status="candidate",
                artifact_sha256=module.content_hash(),
                facts=module.facts,
                tables=module.tables,
                claims=module.claims,
                limitations=module.limitations,
            ),
        ),
    )
    assert validate_bindings(view, SHIPPED_MAPS) == ()
    assert {t.table_id for t in module.tables} == {
        e.fact_coord.table_id for e in _binding_map().entries
    } - {"T3E.10"}


# --- the reader (D3 stays OPEN) ----------------------------------------------------------------


class _HeadStore:
    def __init__(self, module: Module) -> None:
        self.module = module

    def head_module(self, head: Head) -> Module:
        assert head.result_sha256 == self.module.content_hash()
        return self.module


def _read(case: str, status: str = "restricted") -> tuple[Any, Head]:
    module = _module(case).model_copy(update={"status": status})
    head = head_of(module, cp3d.QUALIFICATION)
    return cp3d.cp3d_reader(cast(Any, _HeadStore(module)), head), head


def test_reader_exposes_what_the_oracle_pins_for_cp3c() -> None:
    pinned = EXPECTED["consumption"]["reader_pinned_for_cp3c"]
    got, head = _read("positive")
    assert pinned["function"] == "cp3d_reader(store, head)"
    assert got.head_sha256 == head.result_sha256 and got.status == "restricted"
    assert (got.discount_margin_mid.fact_id, got.discount_margin_mid.status) == (
        "T3E.3.r03.mid",
        "known",
    )
    assert format(got.discount_margin_mid.amount, "f") == pinned["positive_values"]["dm_mid"]
    assert format(got.intensity_mid.amount, "f") == pinned["positive_values"]["lam_mid"]
    assert format(got.probability_mid.amount, "f") == pinned["positive_values"]["pd_mid"]
    assert (got.recovery.fact_id, got.recovery.status) == ("T3E.4.r01.value", "known")
    assert got.recovery.amount == Decimal("0.7")
    assert list(got.own_limitations) == EXPECTED["cases"]["positive"]["own_limitations"]


def test_reader_exposes_a_missing_figure_as_missing_never_zero() -> None:
    got, _ = _read("gap_no_recovery")
    assert got.discount_margin_mid.status == "known"
    for reading in (got.intensity_mid, got.probability_mid, got.recovery):
        assert reading.status == "missing" and reading.amount is None
    none, _ = _read("gap_no_market")
    assert none.discount_margin_mid.status == "missing" and none.discount_margin_mid.amount is None


def test_reader_refuses_another_modules_head() -> None:
    module = _cp0("positive")
    head = Head(
        module_id="CP-0", status="restricted", result_sha256=module.content_hash(), inputs=()
    )
    with pytest.raises(WorkflowError) as error:
        cp3d.cp3d_reader(cast(Any, _HeadStore(module)), head)
    assert error.value.args[0] == "identity_mismatch"


def test_reader_fields_are_exactly_the_pinned_exposure() -> None:
    names = {f for f in cp3d.Cp3dHead.__dataclass_fields__}
    assert names == {
        "head_sha256",
        "status",
        "discount_margin_mid",
        "intensity_mid",
        "probability_mid",
        "recovery",
        "own_limitations",
    }
    assert len(EXPECTED["consumption"]["reader_pinned_for_cp3c"]["exposes"]) == 7


def test_d3_stays_open_and_no_consumer_core_reads_cp3d() -> None:
    """The lease claims no completion: the oracle records OPEN and no other core reads it."""
    assert EXPECTED["consumption"]["status"] == "OPEN"
    owners = Path(cp3d.__file__).parent
    readers = [
        p.name
        for p in owners.glob("*.py")
        if p.name != "cp3d.py" and "cp3d_reader" in p.read_text(encoding="utf-8")
    ]
    assert readers == []
