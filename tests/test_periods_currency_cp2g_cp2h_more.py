"""Phase 8 Task 5, fix round 1: refusals, views, the store adapters and the branches the first
file left unkilled. The answer key is `cases/periods-currency-owner/` (loaded at run time):
`expected.json#module_oracles/CP-2G@EUR`, `#module_oracles/CP-2H@EUR`, `#period_basis/EUR` and
`#runs/*`; the helpers are the first file's.

Non-calendar bases (ruling P8T5-R1) have no key: the expected issue text below is built from the
base year's own dates, written in this file.
"""

import dataclasses
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2h as connect
import test_method_cp2g as g
import test_method_cp2h as h
import test_period_basis as pb
import test_periods_currency_cp2g_cp2h as t

from deploy_vii.contracts import Fact, Input
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow.owners import cp2g, cp2h
from deploy_workflow.owners.period_basis import DEFAULT_BASIS, PeriodRefused, period_basis

# (name, base-year start, base-year end, Q4 start): the bases `period_basis` accepts by design
# (tests/test_period_basis.py: test_non_calendar_derived_fields, test_53_week_year_derived_fields).
NON_CALENDAR = (
    ("July-June", "2025-07-01", "2026-06-30", "2026-04-01"),
    ("April-March", "2026-04-01", "2027-03-31", "2027-01-01"),
    ("53-week", "2025-12-28", "2027-01-02", "2026-09-27"),
    # one edge off a calendar year each: 364 days, still a year `period_basis` accepts
    ("starts 2 January", "2026-01-02", "2026-12-31", "2026-10-01"),
    ("ends 30 December", "2026-01-01", "2026-12-30", "2026-10-01"),
)
BOUND = (
    Input(input_id="CP-1", sha256="1" * 64, status="accepted"),
    Input(input_id="CP-2A", sha256="2" * 64, status="accepted"),
)


def _basis(start: str, end: str, q4: str) -> Any:
    facts = pb._two("2026", q4, end, start, end, currency="EUR")
    return period_basis(pb._context("fy-2026", "EUR"), facts)


def _issue(start: str, end: str) -> str:
    return (
        "forecast years need a calendar fiscal year (1 January to 31 December), but CP-1 T4.14 "
        f"dates the base year {start} to {end}"
    )


def _pack_of(context: dict[str, Any], run_context: dict[str, Any] | None = None) -> PreparedPack:
    """A pack carrying `context`; its run agrees with `run_context` (default: the context)."""
    source = prepare_source(
        SourceRequest(source_id="context", path="context.json", media_type="text/plain"),
        json.dumps(context).encode(),
    )
    ratings = t._h_pack().sources[0]
    return PreparedPack(
        run=t._run_of(run_context or context, ("CP-2H",)), sources=(ratings, source)
    )


def _context(period: str, prior: str, currency: str = "EUR") -> dict[str, Any]:
    context: dict[str, Any] = json.loads(json.dumps(t.SUBS["contexts"]["R2"]))
    context["run"].update(current_period=period, prior_period=prior, reporting_currency=currency)
    return context


def _g_upstream(register: tuple[Fact, ...]) -> cp2g.Upstream:
    inputs = t._g_inputs()
    return cp2g.Upstream(
        bound=BOUND,
        current=BOUND,
        cp1=(*inputs.context.cp1_facts, *register),
        cp2a=inputs.context.cp2a,
        cp1d=inputs.context.cp1d,
    )


def _h_submission(store: Any) -> cp2h.TriggerSubmission:
    head = store.head_module(connect._head(store, "CP-1"))
    payload = t._bound(
        t.SUBS["modules"]["CP-2H@EUR"]["submission"]["rating_triggers"], t._h_ids(head.facts)
    )
    return cp2h.TriggerSubmission.model_validate_json(json.dumps(payload))


def _h_upstream(tmp: Path, pack: PreparedPack, register: tuple[Fact, ...]) -> Any:
    store, stored, attempt = t._seed_cp2h(
        tmp, pack, (*t._h_cp1_facts(), *register), t._h_cp2g_facts()
    )
    return store, stored, cp2h.cp2h_upstream(store=store, attempt=attempt)


# --- F2 / P8T5-R1: a base year that is not a calendar year is refused ---------------------------


@pytest.mark.parametrize(("name", "start", "end", "q4"), NON_CALENDAR)
def test_require_calendar_names_the_dates(name: str, start: str, end: str, q4: str) -> None:
    with pytest.raises(PeriodRefused) as caught:
        cp2g.require_calendar(_basis(start, end, q4))
    assert str(caught.value) == _issue(start, end), name
    cp2g.require_calendar(t.EUR)
    cp2g.require_calendar(DEFAULT_BASIS)


@pytest.mark.parametrize(("name", "start", "end", "q4"), NON_CALENDAR)
def test_stage1_cp2g_and_cp2h_refuse_a_non_calendar_basis(
    name: str, start: str, end: str, q4: str
) -> None:
    basis = _basis(start, end, q4)
    with pytest.raises(PeriodRefused, match="calendar fiscal year"):
        cp2g.compute(t._g_inputs(basis))
    with pytest.raises(PeriodRefused, match="calendar fiscal year"):
        cp2h.Cp2gMetrics.select(t._h_cp2g_facts(), basis)
    unchecked = cp2h.Cp2gMetrics.select(t._h_cp2g_facts(), None)
    with pytest.raises(PeriodRefused, match="calendar fiscal year"):
        cp2h.TriggerUpstream(
            bound=h.BOUND, current=h.BOUND, cp1_facts=(), cp2g=unchecked, basis=basis
        )


@pytest.mark.parametrize(("name", "start", "end", "q4"), NON_CALENDAR)
def test_entry_validators_and_views_refuse_a_non_calendar_basis(
    name: str, start: str, end: str, q4: str, tmp_path: Path
) -> None:
    issue = _issue(start, end)
    register = tuple(pb._two("2026", q4, end, start, end, currency="EUR"))
    pack = _pack_of(_context("fy-2026", "fy-2025"))
    inputs = t._g_inputs()
    upstream = _g_upstream(register)
    got = cp2g.validate_forward(pack=pack, submission=inputs.submission, upstream=upstream)
    assert got == (issue,), name
    assert cp2g.context_block(pack=pack, upstream=upstream)["context_issue"] == issue
    store, stored, h_upstream = _h_upstream(tmp_path, pack, register)
    assert h_upstream.basis_refusal == issue
    submission = _h_submission(store)
    assert cp2h.validate_triggers(pack=stored, submission=submission, upstream=h_upstream) == (
        issue,
    )
    assert cp2h.context_block(pack=stored, upstream=h_upstream)["context_issue"] == issue


# --- P8-R5: a refused context, period or currency offers nothing and carries the issue ----------


def test_views_offer_nothing_under_a_refusal() -> None:
    refusal = t._refusal_text()
    upstream = _g_upstream(t._register())
    view = cp2g.context_block(pack=t._h2_pack(), upstream=upstream)
    assert view == {
        "upstream": [{"module_id": i.input_id, "status": i.status} for i in BOUND],
        "context_issue": refusal,
        "inherited_limitations": [],
    }


def test_a_blank_base_in_euro_is_refused_in_the_view_and_the_validator() -> None:
    context = _context("", "")
    issue = "run.current_period is blank and run.reporting_currency is EUR"
    pack = _pack_of(context)
    upstream = _g_upstream(t._register())
    got = cp2g.validate_forward(pack=pack, submission=t._g_inputs().submission, upstream=upstream)
    assert len(got) == 1 and got[0].startswith(issue)
    assert cp2g.context_block(pack=pack, upstream=upstream)["context_issue"] == got[0]


# --- both ContextRefused branches ---------------------------------------------------------------


def _disagreeing_pack() -> tuple[PreparedPack, str]:
    """A pack whose run is dated a day after its context: `context_facts` refuses it."""
    context = _context("q4-2026", "q3-2026")
    run_context = json.loads(json.dumps(context))
    run_context["run"]["as_of"] = str(date.fromisoformat(context["run"]["as_of"]).replace(day=11))
    issue = (
        "Context refused: run.as_of: context has "
        f"'{context['run']['as_of']}' but the run has '{run_context['run']['as_of']}'"
    )
    return _pack_of(context, run_context), issue


def test_cp2g_reports_a_refused_context_in_the_validator_and_the_view() -> None:
    pack, issue = _disagreeing_pack()
    upstream = _g_upstream(t._register())
    got = cp2g.validate_forward(pack=pack, submission=t._g_inputs().submission, upstream=upstream)
    assert got == (issue,)
    assert cp2g.context_block(pack=pack, upstream=upstream)["context_issue"] == issue


def test_cp2h_reports_a_refused_context_in_the_validator_and_the_view(tmp_path: Path) -> None:
    pack, issue = _disagreeing_pack()
    store, stored, upstream = _h_upstream(tmp_path, pack, t._register())
    assert upstream.basis_refusal == issue
    got = cp2h.validate_triggers(pack=stored, submission=_h_submission(store), upstream=upstream)
    assert got == (issue,)
    assert cp2h.context_block(pack=stored, upstream=upstream)["context_issue"] == issue


def test_cp2h_staleness_comes_before_a_refusal(tmp_path: Path) -> None:
    store, stored, upstream = _h_upstream(tmp_path, t._h2_pack(), t._register())
    stale = dataclasses.replace(upstream, current="the CP-2G head is gone")
    got = cp2h.validate_triggers(pack=stored, submission=_h_submission(store), upstream=stale)
    assert got == cp2h.stale_issues(bound=stale.bound, current=stale.current)
    assert t._refusal_text() not in got


# --- F1 / L2: Stage 1 types tie the basis ---------------------------------------------------------


def test_trigger_upstream_refuses_metrics_checked_under_another_basis() -> None:
    stale = cp2h.Cp2gMetrics.select(tuple(h._cp2g_fact(r) for r in h.CP2G["cases"]["gap"]["facts"]))
    with pytest.raises(ValueError, match="another basis"):
        cp2h.TriggerUpstream(
            bound=h.BOUND,
            current=h.BOUND,
            cp1_facts=t._h_cp1_facts(),
            cp2g=stale,
            basis=t.EUR,
        )
    unchecked = cp2h.Cp2gMetrics.select(t._h_cp2g_facts(), None)
    ok = cp2h.TriggerUpstream(
        bound=h.BOUND,
        current=h.BOUND,
        cp1_facts=(),
        cp2g=unchecked,
        basis_refusal="refused",
    )
    assert ok.basis is DEFAULT_BASIS


# --- F3: the accepted 2026 context through the store adapters and the views ---------------------


def test_cp2g_store_adapter_reads_the_basis_of_an_accepted_context() -> None:
    pack = t._eur_pack()
    upstream = _g_upstream(t._register())
    inputs = cp2g._inputs(pack, t._g_inputs().submission, upstream)
    assert inputs.context.basis == t.EUR
    assert {f.label.split(" · ")[0] for f in inputs.context.cp1_facts} == {t.EUR.ltm_column}
    assert cp2g.validate_forward(pack=pack, submission=inputs.submission, upstream=upstream) == ()
    report = cp2g.forward_model(pack=pack, submission=inputs.submission, upstream=upstream)
    own = [f.fact_id for f in report.facts if f.table_id.startswith("T2H.")]
    assert own == [f["fact_id"] for f in t.G_EUR["facts"]]


def test_cp2g_view_on_an_accepted_context_offers_the_oracle_periods() -> None:
    key = t.EXP["period_basis"]["EUR"]
    view = cp2g.context_block(pack=t._eur_pack(), upstream=_g_upstream(t._register()))
    assert "context_issue" not in view
    base: Any = view["base"]
    assert base["period"] == key["ltm_period"]
    assert base["forecast_periods"] == key["year_labels"]
    assert set(base["operands"]) | set(base["ratios"]) == set(t.G_EUR["cp1_inputs"])


def test_cp2h_view_on_an_accepted_context_offers_its_register(tmp_path: Path) -> None:
    store, stored, upstream = _h_upstream(tmp_path, t._eur_pack(), t._register())
    assert upstream.basis_refusal is None and upstream.basis == t.EUR
    view: Any = cp2h.context_block(pack=stored, upstream=upstream)
    assert "context_issue" not in view
    assert [r["row"] for r in view["cp2g"]["rows"]] == list(cp2h.CP2G_ROWS)
    assert {r["row"] for r in view["triggers"]} == {
        f"t{n:02d}" for n in range(1, len(view["triggers"]) + 1)
    }
    ratios = {f["ref"] for f in view["cp1_facts"]}
    assert ratios == {f.fact_id for f in cp2h.select_cp1(upstream.cp1, t.EUR).values()}
    del store


# --- F3: CP-2G break reproduction and a bound CP-1D head, on the EUR basis ----------------------


def test_cp2g_break_metric_that_does_not_reproduce_cp2a_is_an_issue_on_the_eur_basis() -> None:
    inputs = t._g_inputs()
    assert cp2g.content_issues(inputs) == ()
    sub = inputs.submission
    moved = tuple(
        m.model_copy(update={"metric": "net_leverage"}) if m.break_id == "b03" else m
        for m in sub.break_metrics
    )
    bad = dataclasses.replace(inputs, submission=sub.model_copy(update={"break_metrics": moved}))
    assert any(
        "does not reproduce the CP-2A required decline" in i for i in cp2g.content_issues(bad)
    )


def _cp1d_head(period: str, currency: str) -> cp2g.Cp1dHead:
    """The frozen CP-1D oracle's supported figures, restated for `period` and `currency`."""
    case = g.EXPECTED["cases"]["positive"]["cp1d_head"]
    source = case["source"].removeprefix("cases/cp1d-owner/expected.json cases.")
    facts = {f["fact_id"]: g._fact(f) for f in g.CP1D_EXP["cases"][source]["facts"]}
    ids = g.CP1D_IDS
    update: dict[str, Any] = {"period": period}

    def restated(fid: str) -> Fact:
        fact: Fact = facts[fid]
        change = dict(update)
        if fact.currency:
            change["currency"] = currency
        return fact.model_copy(update=change)

    return cp2g.Cp1dHead(
        status="accepted",
        supported=restated(ids[0]),
        total_leverage=restated(ids[1]),
        net_leverage=restated(ids[2]),
    )


def _with_cp1d(head: cp2g.Cp1dHead) -> cp2g.ForwardInputs:
    inputs = t._g_inputs()
    return dataclasses.replace(inputs, context=dataclasses.replace(inputs.context, cp1d=head))


def test_bound_cp1d_on_the_basis_period_is_compared() -> None:
    head = _cp1d_head(t.EUR.ltm_period, "EUR")
    result = cp2g.compute(_with_cp1d(head))
    supported = head.facts()
    assert supported is not None and supported[0].amount is not None
    cell = next(c for c in result.cells if c.fact.fact_id == "T2H.8.base.ebitda_fy26_vs_supported")
    first_year_ebitda = t.G_EUR["forecast"]["base"][0]["E"]
    assert cell.fact.status == "known"
    assert cell.fact.amount == Decimal(first_year_ebitda) - supported[0].amount
    assert cell.fact.label == f"{t.EUR.year_labels[0]} EBITDA less CP-1D supported EBITDA"
    assert not any("CP-1D is bound but its" in line for line in result.own_limitations)


def test_bound_cp1d_on_another_period_is_not_compared() -> None:
    other = DEFAULT_BASIS.ltm_period
    head = _cp1d_head(other, "EUR")
    result = cp2g.compute(_with_cp1d(head))
    cell = next(c for c in result.cells if c.fact.fact_id == "T2H.8.base.ebitda_fy26_vs_supported")
    assert cell.fact.status != "known"
    assert f"is for {other}, not {t.EUR.ltm_period}" in str(cell.fact.limitation)
    lines = [x for x in result.own_limitations if "CP-1D is bound but its" in x]
    assert lines and all(f"is not a known {t.EUR.ltm_period} figure" in x for x in lines)


def test_bound_cp1d_in_another_currency_fails_closed() -> None:
    head = _cp1d_head(t.EUR.ltm_period, "USD")
    with pytest.raises(ValueError, match="must be EUR MILLIONS at scale 1000000, not USD"):
        cp2g.compute(_with_cp1d(head))


def test_stage1_validate_and_the_adapter_hold_a_refusal_alone(tmp_path: Path) -> None:
    """`validate` and `_adapted` carry a refused basis without reading CP-1 on the placeholder
    basis: the 2026 CP-1 never meets the default LTM column."""
    refusal = t._refusal_text()
    store, stored, upstream = _h_upstream(tmp_path, t._h2_pack(), t._register())
    assert upstream.basis_refusal == refusal
    scope, trigger = cp2h._adapted(stored, upstream)
    assert trigger.basis_refusal == refusal
    assert trigger.cp1_facts == ()
    inputs = cp2h.TriggerInputs(pack=scope, upstream=trigger, submission=_h_submission(store))
    assert cp2h.validate(inputs) == (refusal,)


def test_cp2g_unverified_ebitda_cause_names_the_basis_period() -> None:
    """A zero base EBITDA leaves the leverage breaks unverifiable; the cause names the run's LTM
    period (the template is `test_method_cp2g._unverified`'s, with the key's EUR period)."""
    inputs = t._g_inputs()
    facts = tuple(
        f.model_copy(update={"amount": Decimal(0)}) if f.row_id == "ebitda" else f
        for f in inputs.context.cp1_facts
    )
    zero = dataclasses.replace(inputs, context=dataclasses.replace(inputs.context, cp1_facts=facts))
    period = t.EXP["period_basis"]["EUR"]["ltm_period"]
    cause = f"base EBITDA is zero or negative in CP-1 for {period} (ZERO_OR_NEGATIVE_DENOMINATOR)"
    lines = cp2g.compute(zero).own_limitations
    for row in ("b03", "b04", "b05"):
        assert (
            f"The metric named for CP-2A break {row} could not be checked against its CP-2A "
            f"required decline: {cause}."
        ) in lines


def test_cp2h_unsettled_actual_keeps_the_basis_label_and_period(tmp_path: Path) -> None:
    """A CP-2G base-year metric that is missing is a gap cell labelled and dated by the basis,
    as the oracle's settled cell is (`T2R.4.t01.actual`)."""
    want = next(f for f in t.H_EUR["facts"] if f["fact_id"] == "T2R.4.t01.actual")
    facts = tuple(
        f.model_copy(update={"status": "missing", "amount": None, "limitation": "not stated"})
        if f.fact_id == "T2H.6.a25.total_leverage"
        else f
        for f in t._h_cp2g_facts()
    )
    inputs = dataclasses.replace(t.H_INPUTS, upstream=t._h_upstream(facts, t.EUR))
    ratings, source, citations = cp2h.register_source(inputs.pack)
    book, _ = cp2h._compose(ratings, source, inputs.upstream, None, citations)
    cell = next(c for c in book.cells if c.fact.fact_id == "T2R.4.t01.actual")
    assert cell.fact.status == "missing"
    assert (cell.fact.label, cell.fact.period) == (want["label"], want["period"])
