"""CP-3C Stage 2: the connection of the Stage 1 core to the store, the registrations, the
bindings, the reader and the fast consumption proof (`docs/CP3C-OWNER-LEASE.md`,
`docs/G1X-OWNER-CORE-PROTOCOL.md`, `work/build/stage2/brief.md`).

Expectations come from the lease, `cases/cp3c-owner/{manifest,submissions,expected}.json` and the
pinned CP-2D oracle, never from the code under test. The stores here are real `Execution` stores
whose CP-0, CP-1, CP-1A and CP-2 heads are settled through `begin`/`finish` from records built
for the CP-2D and CP-3C bindings, and whose CP-2D head is settled by the real CP-2D core, so no
CP-1 promotion runs: the genuine runs are `tests/test_owner_cp3c.py` and `tests/cp3c_runs.py`
(deferred). The fixtures vary the CP-1 amounts and statuses, the CP-2D case (minimum cash
assessed or not, horizon), the as-of date and the case kind, so a constant equal to the oracle
cannot pass; the CP-1 facility principal and a foreign-run module are varied the same way.

First section: the backlog rows (work/build/stage2-backlog.md, CP-3C Infos 1-3 as ruled in
docs/rulings/2026-10-28-stage2.md round 5 item 7, and the caller-quoting f-string sites of the
0d-c audit), each written before its code and watched red. Second section: the connection (the
plug-in parts, the store adapter, validation, the journal, the composed module, the view, the
registrations, the bindings, the reader and the fast D3 proof), written before its code.
"""

import hashlib
import importlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import pytest
import test_connect_cp2d as tc2d
import test_method_cp2d as tm2d
import test_method_cp3c as tm
from defect_classes import (
    MODEL_TEXT_HOSTILE,
    assert_hostile_refused,
    free_text_paths,
    path_matches,
    with_text,
)

from deploy_vii import prose
from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Fact, Input, Module, ModuleView, Run, View
from deploy_vii.execution import MAX_ISSUE_CHARS, Attempt, Execution, Head, Qualification
from deploy_vii.preparation import PreparedPack
from deploy_vii.report_view import fact_spelling, figure_unit
from deploy_workflow.financial_workflow import _FrozenExecution
from deploy_workflow.owners import cp2d, cp3c
from deploy_workflow.workflow import WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")

MODULE = "CP-3C"
STEP = "refinancing_risk"
UNSOURCED = (
    "CP-3C: the reporting currency is not sourced: cash_closing is not known and no known "
    "US$ m fact states a currency"
)


# --- backlog Info 1: the unsourced reporting currency is an invariant raise ----------------------


def _missing(fact: Any) -> Any:
    return replace(fact, status="missing", amount=None, text=None, reason="Not stated")


def _without_cash(inputs: cp3c.Cp3cInputs) -> cp3c.Cp3cInputs:
    return replace(inputs, cp1=replace(inputs.cp1, cash_closing=_missing(inputs.cp1.cash_closing)))


def _every_millions_fact(inputs: cp3c.Cp3cInputs, change: Any) -> cp3c.Cp3cInputs:
    """`change` applied to every US$ m fact CP-3C reads besides cash_closing."""
    cp1, cp2d = inputs.cp1, inputs.cp2d
    terms = tuple(
        replace(t, annual_amortisation=change(t.annual_amortisation)) for t in cp1.facilities
    )
    cp1 = replace(
        cp1,
        undrawn_rcf=change(cp1.undrawn_rcf),
        adjusted_ebitda=change(cp1.adjusted_ebitda),
        cash_interest=change(cp1.cash_interest),
        facilities=terms,
    )
    wall = tuple(replace(r, principal=change(r.principal)) for r in cp2d.wall)
    cp2d = replace(
        cp2d,
        run_rate=change(cp2d.run_rate),
        minimum_cash=change(cp2d.minimum_cash),
        funding_gap=change(cp2d.funding_gap),
        wall=wall,
    )
    return replace(inputs, cp1=cp1, cp2d=cp2d)


@pytest.mark.parametrize("blank", ["", " ", None])
def test_info1_cash_missing_and_every_other_currency_blank_is_unsourced(blank: str | None) -> None:
    inputs = _every_millions_fact(
        _without_cash(tm._inputs("positive")), lambda f: replace(f, currency=blank)
    )
    with pytest.raises(ValueError, match=f"^{re.escape(UNSOURCED)}$"):
        cp3c.compute(replace(inputs, currency=blank or ""))
    with pytest.raises(ValueError, match=f"^{re.escape(UNSOURCED)}$"):
        cp3c.reporting_currency(cp1=inputs.cp1, cp2d=inputs.cp2d)


def test_info1_cash_missing_and_no_other_known_millions_fact_is_unsourced() -> None:
    inputs = _every_millions_fact(_without_cash(tm._inputs("positive")), _missing)
    for currency in ("USD", "EUR"):
        with pytest.raises(ValueError, match=f"^{re.escape(UNSOURCED)}$"):
            cp3c.check_currency(cp1=inputs.cp1, cp2d=inputs.cp2d, currency=currency)
    with pytest.raises(ValueError, match=f"^{re.escape(UNSOURCED)}$"):
        cp3c.reporting_currency(cp1=inputs.cp1, cp2d=inputs.cp2d)


def test_info1_cash_missing_takes_the_currency_the_known_facts_state() -> None:
    inputs = _without_cash(tm._inputs("positive"))
    assert cp3c.reporting_currency(cp1=inputs.cp1, cp2d=inputs.cp2d) == "USD"
    euro = _every_millions_fact(inputs, lambda f: replace(f, currency="EUR"))
    assert cp3c.reporting_currency(cp1=euro.cp1, cp2d=euro.cp2d) == "EUR"
    cp3c.check_currency(cp1=euro.cp1, cp2d=euro.cp2d, currency="EUR")  # sourced: no raise
    # One known US$ m fact is enough to source it; the rest may be gaps.
    one = _every_millions_fact(inputs, _missing)
    one = replace(one, cp2d=replace(one.cp2d, run_rate=inputs.cp2d.run_rate))
    assert cp3c.reporting_currency(cp1=one.cp1, cp2d=one.cp2d) == "USD"


def test_info1_the_reporting_currency_is_cash_closings_when_it_is_known() -> None:
    inputs = tm._inputs("positive")
    cash = replace(inputs.cp1.cash_closing, currency="GBP")
    cp1 = replace(inputs.cp1, cash_closing=cash)
    assert cp3c.reporting_currency(cp1=cp1, cp2d=inputs.cp2d) == "GBP"
    for unset in (None, "", " "):
        cp1 = replace(inputs.cp1, cash_closing=replace(cash, currency=unset))
        with pytest.raises(ValueError, match=r"^CP-3C cash_closing: currency is not set$"):
            cp3c.reporting_currency(cp1=cp1, cp2d=inputs.cp2d)


# --- backlog Info 2: a conflicting status takes the conflicting frame ---------------------------

_UNSETTLED = ("conflicting", "not_applicable")
_WORD = {"conflicting": "conflicting", "not_applicable": "not applicable"}


def _unsettled(fact: Any, status: str) -> Any:
    return replace(fact, status=status, amount=None, text=None, reason="CP-1 says so")


def _cells(result: cp3c.Cp3cResult) -> dict[str, cp3c.Cell]:
    return {c.fact_id: c for t in result.tables for r in t.rows for c in r.cells}


@pytest.mark.parametrize("status", _UNSETTLED)
def test_info2_minimum_cash_dependants_name_its_status(status: str) -> None:
    inputs = tm._inputs("positive")
    cp2d = replace(inputs.cp2d, minimum_cash=_unsettled(inputs.cp2d.minimum_cash, status))
    result = cp3c.compute(replace(inputs, cp2d=cp2d))
    reason = f"Not calculable: minimum cash is {_WORD[status]}"
    cells = _cells(result)
    for fact_id in ("T3D.1.r01.c7", "T3D.1.r01.c9", "T3D.2.r02", "T3D.2.r03", "T3D.2.r09"):
        assert (cells[fact_id].status, cells[fact_id].reason) == ("missing", reason), fact_id
    (need,) = (c for c in result.claims if c.claim_id == "CP-3C-NEED-01")
    assert f"because minimum cash is {_WORD[status]}." in need.template


def test_info2_a_missing_minimum_cash_keeps_the_oracle_reason() -> None:
    result = cp3c.compute(tm._inputs("gap_minimum_cash"))
    assert _cells(result)["T3D.2.r03"].reason == "Not calculable: minimum cash not assessed"


_TERMS = [
    ("cp1", "seniority", "seniority", "T3D.4.r01.c5"),
    ("cp1", "secured_status", "secured status", "T3D.4.r01.c5"),
    ("cp1", "annual_amortisation", "annual amortisation", "T3D.1.r01.c6"),
    ("cp2d", "principal", "principal", "T3D.1.r01.c6"),
    ("cp2d", "maturity_date", "maturity date", "T3D.2.r05"),
]


def _with_term(inputs: cp3c.Cp3cInputs, side: str, name: str, status: str) -> cp3c.Cp3cInputs:
    if side == "cp1":
        (terms,) = inputs.cp1.facilities
        terms = replace(terms, **{name: _unsettled(getattr(terms, name), status)})
        return replace(inputs, cp1=replace(inputs.cp1, facilities=(terms,)))
    (row,) = inputs.cp2d.wall
    fact = replace(_unsettled(getattr(row, name), status), period=None)
    return replace(inputs, cp2d=replace(inputs.cp2d, wall=(replace(row, **{name: fact}),)))


@pytest.mark.parametrize("status", _UNSETTLED)
@pytest.mark.parametrize(("side", "name", "term", "fact_id"), _TERMS)
def test_info2_facility_term_dependants_name_its_status(
    side: str, name: str, term: str, fact_id: str, status: str
) -> None:
    result = cp3c.compute(_with_term(tm._inputs("positive"), side, name, status))
    cell = _cells(result)[fact_id]
    assert cell.reason == f"Not calculable: facility term-loan {term} is {_WORD[status]}"


@pytest.mark.parametrize(("side", "name", "term", "fact_id"), _TERMS)
def test_info2_a_missing_facility_term_stays_not_stated(
    side: str, name: str, term: str, fact_id: str
) -> None:
    result = cp3c.compute(_with_term(tm._inputs("positive"), side, name, "missing"))
    assert (
        _cells(result)[fact_id].reason == f"Not calculable: facility term-loan {term} is not stated"
    )


def test_info2_a_not_stated_flag_stays_not_stated() -> None:
    inputs = tm._inputs("positive")
    (terms,) = inputs.cp1.facilities
    terms = replace(terms, seniority=replace(terms.seniority, text="NOT_STATED"))
    result = cp3c.compute(replace(inputs, cp1=replace(inputs.cp1, facilities=(terms,))))
    reason = "Not calculable: facility term-loan seniority is not stated"
    assert _cells(result)["T3D.4.r01.c5"].reason == reason


# --- backlog Info 3: the `_check_value` frame is CP-3C's ----------------------------------------


def test_info3_check_value_messages_are_in_the_cp3c_frame() -> None:
    with pytest.raises(ValueError, match=r"^CP-3C T4\.10: a known fact carries exactly one "):
        cp3c.Cp1Fact(table_id="T4.10", period="p", status="known")
    with pytest.raises(ValueError, match=r"^CP-3C T2E\.3\.r01: a missing fact carries a reason "):
        cp3c.Cp2dFact(fact_id="T2E.3.r01", status="missing", amount=Decimal(1), reason="r")
    with pytest.raises(ValueError, match=r"^CP-3C T4\.18: a known fact carries no reason$"):
        cp3c.Cp1Fact(table_id="T4.18", period="p", status="known", text="x", reason="r")


# --- backlog: caller-quoting lines are clipped (protocol section 6; 0d-c audit cp3c sites) ------

LONG = "X" * 5000


def test_an_unknown_ranking_flag_is_clipped() -> None:
    inputs = tm._inputs("positive")
    (terms,) = inputs.cp1.facilities
    terms = replace(terms, seniority=replace(terms.seniority, text=LONG))
    with pytest.raises(ValueError) as raised:
        cp3c.compute(replace(inputs, cp1=replace(inputs.cp1, facilities=(terms,))))
    message = str(raised.value)
    assert message.startswith("CP-3C term-loan: unknown ranking flag 'XXX")
    assert len(message) <= MAX_ISSUE_CHARS


def test_an_inside_horizon_flag_is_clipped() -> None:
    (row,) = tm._inputs("positive").cp2d.wall
    flag = replace(row.inside_horizon, text=LONG)
    with pytest.raises(ValueError) as raised:
        cp3c._flag(flag)
    message = str(raised.value)
    assert message.startswith("CP-3C T2E.4.r01.c4: inside-horizon flag 'XXX")
    assert len(message) <= MAX_ISSUE_CHARS


def test_claim_figure_and_chip_refusals_are_clipped() -> None:
    cells = tm._cells_of(cp3c.compute(tm._inputs("positive")))
    known, gap = cells["T3D.2.r01"], cells["T3D.5.r01.c2"]
    long_id = "T3D.2." + "r" * 3000
    claims = cp3c._Claims({long_id: known, "gap" + long_id: gap})
    with pytest.raises(ValueError) as chip:
        claims.chip(long_id)
    with pytest.raises(ValueError) as fig:
        claims.fig("gap" + long_id)
    for raised in (chip, fig):
        assert str(raised.value).startswith("CP-3C claim")
        assert len(str(raised.value)) <= MAX_ISSUE_CHARS


def test_an_invalid_submission_raise_is_bounded() -> None:
    payload = tm._bind(tm.SUBMISSIONS["cp3c"]["positive"])
    payload["paths"] = [
        {**path, "text": path["text"] + " 1"} for path in payload["paths"] * 30
    ]  # 150 rows, each with a figure: many issues
    inputs = replace(tm._inputs("positive"), submission=tm._submission(payload))
    with pytest.raises(ValueError) as raised:
        cp3c.compute(inputs)
    assert str(raised.value).count("; ") <= 21 and "further issues not listed" in str(raised.value)


# =============================================================================================
# Second section: the connection, test-first (lease Public API; G1-X protocol sections 2-6)
# =============================================================================================

# The free-text paths of a CP-3C payload and their sinks (Stage 2 round 5 item 10): none is built
# as `RunText` or `Claim.text`. `repricing.rationale` and `repricing_absence.*` are kept only in
# the retained submission; each path's `text` and `credit_implication` is a T3D.6 `Fact.text`;
# each path's `limitation` is an own limitation (`Module.limitations`, a T3D.8 row).
CP3C_VERBATIM: frozenset[tuple[str | int, ...]] = frozenset(
    {
        ("repricing", "rationale"),
        ("repricing_absence", "reason"),
        ("repricing_absence", "follow_up"),
        ("paths", "*", "text"),
        ("paths", "*", "credit_implication"),
        ("paths", "*", "limitation"),
    }
)


def test_model_text_is_stored_verbatim_on_every_free_text_path() -> None:
    """Round 3 item 2 and round 5 item 10 at the validator and the composer (the run-level form
    with the wedge check is `test_owner_cp3c.py`): a hostile value on any free-text path passes
    the validator and lands, verbatim, in its sink."""
    for case in ("positive", "gap_no_repricing"):
        payload = tm._bind(tm.SUBMISSIONS["cp3c"][case])
        paths = free_text_paths(payload, cp3c.RefinancingRiskSubmission)
        assert paths and all(any(path_matches(p, path) for p in CP3C_VERBATIM) for path in paths)
        for path in paths:
            for value in MODEL_TEXT_HOSTILE:
                submission, shape = cp3c._parsed(json.dumps(with_text(payload, path, value)))
                assert shape == () and submission is not None, (path, value)
                assert cp3c.submission_issues(submission=submission, offered=tm.OFFERED) == ()
                result = cp3c.compute(replace(tm._inputs(case), submission=submission))
                texts = {c.text for t in result.tables for r in t.rows for c in r.cells}
                if path[0] == "paths":
                    assert value in {*texts, *result.own_limitations}, (path, value)
                else:
                    assert value in submission.model_dump_json(), (path, value)


def test_payload_text_is_parsed_through_json_object(monkeypatch: pytest.MonkeyPatch) -> None:
    """Protocol section 6: the schema validates the bounded `json_object` document's exact
    re-serialisation, never the raw text; hostile text is a bounded shape issue."""
    seen: list[str] = []
    real = cp3c.RefinancingRiskSubmission.model_validate_json

    def spy(text: str | bytes, **kwargs: Any) -> cp3c.RefinancingRiskSubmission:
        seen.append(str(text))
        return real(text, **kwargs)

    monkeypatch.setattr(cp3c.RefinancingRiskSubmission, "model_validate_json", spy)
    spaced = json.dumps(tm._bind(tm.SUBMISSIONS["cp3c"]["positive"]), indent=2)
    submission, shape = cp3c._parsed(spaced)
    assert shape == () and submission is not None and seen and spaced not in seen
    for hostile in ('{"a": "\\ud800"}', "[" * 5000 + "]" * 5000, '{"x": NaN}'):
        submission, shape = cp3c._parsed(hostile)
        assert submission is None and shape, hostile
        assert all(len(i) <= MAX_ISSUE_CHARS for i in shape), hostile


def test_shared_hostile_text_set_over_the_schemas() -> None:
    """Rulings stage2 Q5: the schema refuses the hostile set only with `ValueError`."""
    for schema in cp3c.SCHEMAS.values():
        assert_hostile_refused(schema)


# --- the plug-in parts that need no store (protocol section 2) ---------------------------------

TREE = tm.MANIFEST["view_tree_draft"]


def test_core_attributes_match_the_lease() -> None:
    assert (cp3c.MODULE_ID, cp3c.STEP_ID, cp3c.STEP_IDS) == (MODULE, STEP, (STEP,))
    assert cp3c.QUALIFICATION == Qualification(implementation="implemented")
    assert dict(cp3c.SCHEMAS) == {STEP: cp3c.RefinancingRiskSubmission}
    assert cp3c.SUBMISSION_INPUT == "refinancing-risk-submission"
    assert cp3c.EDGES == tuple(tm.MANIFEST["edges"]["required"]) == ("CP-0", "CP-1", "CP-2D")
    assert cp3c.UNREAD_OPTIONAL_EDGES == tuple(TREE["unread_optional_edges"])
    assert set(cp3c.UNREAD_OPTIONAL_EDGES) == set(tm.MANIFEST["optional_edges"]["unread"])
    for name in ("probe", "view", "submit", "ENTRY_VALIDATOR", "cp3c_reader", "cp3c_upstream"):
        assert callable(getattr(cp3c, name)), name
    for name in ("context_block", "cp3c_module", "validate_refinancing", "refinancing_risk"):
        assert callable(getattr(cp3c, name)), name
    # Rule mode `none`, no precheck (lease Module kind): nothing to register for either.
    assert not hasattr(cp3c, "RULES") and not hasattr(cp3c, "precheck")


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_schemas_round_trip_and_give_the_tail_digest(case: str) -> None:
    text = json.dumps(tm._bind(tm.SUBMISSIONS["cp3c"][case]))
    parsed = cp3c.SCHEMAS[STEP].model_validate_json(text)
    assert cp3c.SCHEMAS[STEP].model_validate_json(parsed.model_dump_json()) == parsed
    assert parsed.content_hash() == hashlib.sha256(parsed.model_dump_json().encode()).hexdigest()


def test_fact_bindings_are_the_manifest_bindings() -> None:
    """The CP-1 predicates (table, period, label) and the CP-2D stable ids are the manifest's;
    the per-facility names follow its `<facility>.<term>` and `cp2d.<facility>.<field>` forms."""
    bindings = tm.MANIFEST["fact_bindings"]
    for name in cp3c.CP1_METRICS:
        b = bindings[name]
        assert (b["source"], cp3c.FACT_BINDINGS[name]) == (
            "CP-1",
            cp2d.FactBinding(b["table_id"], b["period"], b["label"]),
        )
    for name, fact_id in cp3c.CP2D_FACTS.items():
        assert (bindings[name]["source"], bindings[name]["fact_id"]) == ("CP-2D", fact_id)
    t418 = {n: b for n, b in bindings.items() if b.get("table_id") == "T4.18"}
    assert set(cp3c.FACILITY_TERMS) == {b["field"] for b in t418.values()}
    assert {b["period"] for b in t418.values()} == {cp3c.SCHEDULE_PERIOD}
    assert all(n == f"{b['facility_id']}.{b['field']}" for n, b in t418.items())
    wall = {n.rsplit(".", 1)[1]: b["fact_id"] for n, b in bindings.items() if n.count(".") == 2}
    assert {f: wall[f].rsplit(".", 1)[1] for f in cp3c.WALL_FIELDS} == {
        "principal": "c1",
        "maturity_date": "c2",
        "months": "c3",
        "inside_horizon": "c4",
    }
    walled = {n for n in bindings if n.count(".") == 2}
    assert {*cp3c.CP1_METRICS, *cp3c.CP2D_FACTS, *t418, *walled} == set(bindings)


# --- a real store: CP-0, CP-1, CP-1A, CP-2 settled from records, CP-2D by its own core ----------

T410_PERIOD = tm.MANIFEST["fact_bindings"]["cash_closing"]["period"]
UPSTREAM = ("CP-0", "CP-1", "CP-1A", "CP-2")
SYNTHETIC = "Synthetic case; not real issuer qualification"
CaseKind = Literal["public", "private", "synthetic"]
CP2D_CASE = {
    "positive": "positive",
    "gap_no_repricing": "positive",
    "gap_minimum_cash": "gap_minimum_cash",
}
TERMS = {"secured_status": "SECURED", "seniority": "SENIOR", "rate_type": "FLOATING"}


def _run(*, as_of: str | None = None, case_kind: CaseKind = "synthetic") -> Run:
    document = dict(tm.MANIFEST["run"])
    document["case_kind"] = case_kind
    if as_of is not None:
        document["as_of"] = as_of
    return Run.model_validate_json(json.dumps(document))


def make_pack(*, as_of: str | None = None, case_kind: CaseKind = "synthetic") -> PreparedPack:
    return PreparedPack(run=_run(as_of=as_of, case_kind=case_kind), sources=tc2d.PACK.sources)


def _t410(name: str, amount: Decimal) -> Fact:
    """A CP-1 T4.10 LTM metric as the promoted head writes it (a calculated US$ m fact)."""
    return Fact(
        fact_id=f"cp1:{name}",
        label=f"LTM Q4 25 (2025-01-01 to 2025-12-31) · {name}",
        table_id="T4.10",
        row_id="row-" + name,
        field="value",
        amount=amount,
        unit="MILLIONS",
        currency="USD",
        scale=Decimal(1000000),
        period=T410_PERIOD,
        citations=(tc2d.CITATION,),
        calculation_id=f"calc:{name}",
        value_class="calculated",
    )


def cp1_module(run: Run, *, terms: dict[str, str] | None = None) -> Module:
    """The CP-1 head both consumers bind: the CP-2D records (`test_connect_cp2d.cp1_module` over
    the CP-2D positive operands) with T4.10 written as calculated metrics, the two LTM metrics
    CP-3C adds (adjusted EBITDA 30.0, cash interest -5.00: the manifest's observed values) and,
    on every T4.18 row of either period, the ranking flags and the rate type."""
    base = tc2d.cp1_module(tm2d._operands("positive"), run)
    facts = [
        f.model_copy(update={"value_class": "calculated"}) if f.table_id == "T4.10" else f
        for f in base.facts
    ]
    facts += [_t410("adjusted_ebitda", Decimal("30.0")), _t410("cash_interest", Decimal("-5.00"))]
    keys = [f for f in base.facts if f.table_id == "T4.18" and f.field == "facility_id"]
    for key in keys:
        for field, text in (TERMS | (terms or {})).items():
            facts.append(
                Fact(
                    fact_id=f"cp1:{key.row_id}:{field}",
                    label=field,
                    table_id="T4.18",
                    row_id=key.row_id,
                    field=field,
                    text=text,
                    period=key.period,
                    citations=(tc2d.CITATION,),
                    value_class="source",
                )
            )
    return base.model_copy(update={"facts": tuple(facts)})


def swap(module: Module, fact_id: str, **update: Any) -> Module:
    """`module` with one fact changed (validated as a new Fact)."""
    facts = tuple(
        Fact.model_validate({**f.model_dump(), **update}) if f.fact_id == fact_id else f
        for f in module.facts
    )
    assert facts != module.facts, fact_id
    return Module.model_validate({**module.model_dump(), "facts": facts})


def _without(module: Module, drop: Callable[[Fact], bool]) -> Module:
    facts = tuple(f for f in module.facts if not drop(f))
    return Module.model_validate({**module.model_dump(), "facts": facts})


def _commands() -> tuple[Fact, ...]:
    return tuple(
        Fact(
            fact_id=f"T8.{m}.exact_command",
            label="Exact command",
            table_id="T8",
            row_id=m,
            field="exact_command",
            text=f"Run {m}",
        )
        for m in ("CP-1", "CP-1A", "CP-2", "CP-2D", "CP-3C")
    )


def _settle(store: Execution, module_id: str, body: Module | None, notes: bool) -> None:
    attempt = store.begin(module_id)
    run = store.read().run
    base = body or Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=module_id,
        facts=_commands() if module_id == "CP-0" else (),
    )
    candidate = base.model_copy(
        update={
            "inputs": attempt.inputs,
            "attempt": attempt.number,
            "limitations": (f"{module_id} synthetic limitation",) if notes else (),
        }
    )
    store.finish(
        attempt.ticket_id,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("differs",),
        qualification=Qualification(implementation="implemented"),
    )


def make_store(
    root: Path,
    case: str = "positive",
    *,
    cp1: Module | None = None,
    as_of: str | None = None,
    case_kind: CaseKind = "synthetic",
    notes: bool = True,
    cp2d_literals: tuple[str, ...] | None = None,
) -> tuple[Execution, PreparedPack]:
    """A real store with CP-0, CP-1, CP-1A and CP-2 settled from records and CP-2D settled by the
    real CP-2D core over its frozen literal for `case` (or over `cp2d_literals`, one per
    attempt)."""
    pack = make_pack(as_of=as_of, case_kind=case_kind)
    store = Execution.create(root / "store", pack)
    for module_id in UPSTREAM:
        body = (cp1 or cp1_module(pack.run)) if module_id == "CP-1" else None
        _settle(store, module_id, body, notes)
    for text in cp2d_literals or (tc2d._literal(CP2D_CASE[case]),):
        ticket = store.begin("CP-2D")
        done = cp2d.submit(store, ticket.ticket_id, "liquidity_bridge", text, None)
        assert done.journal.status == "finished"
    return store, pack


def seed(
    root: Path, case: str = "positive", **kwargs: Any
) -> tuple[Execution, PreparedPack, Attempt]:
    """`make_store`, then CP-3C begun."""
    store, pack = make_store(root, case, **kwargs)
    assert head(store, "CP-2D").status == "restricted"
    return store, pack, store.begin(MODULE)


def head(store: Execution, module_id: str) -> Head:
    return next(h for h in store.read().heads if h.module_id == module_id)


def finished(store: Execution, attempt: Attempt) -> Attempt:
    return next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)


def upstream_of(store: Execution, attempt: Attempt) -> "cp3c.Upstream":
    return cp3c.cp3c_upstream(store=store, attempt=attempt)


def refs(store: Execution, attempt: Attempt) -> dict[str, str]:
    """Binding name -> the ref the view offers for it."""
    return dict(cp3c.select(upstream_of(store, attempt)).refs)


def bound_payload(payload: Any, names: dict[str, str]) -> Any:
    """`{{FACT:name}}` -> the offered ref (an unbound name keeps the Stage 1 stand-in)."""
    if isinstance(payload, str):
        return tm.TOKEN.sub(lambda m: names.get(m.group(1), f"unbound:{m.group(1)}"), payload)
    if isinstance(payload, list):
        return [bound_payload(v, names) for v in payload]
    if isinstance(payload, dict):
        return {k: bound_payload(v, names) for k, v in payload.items()}
    return payload


def literal(store: Execution, attempt: Attempt, case: str = "positive") -> str:
    return json.dumps(bound_payload(tm.SUBMISSIONS["cp3c"][case], refs(store, attempt)))


def submission_of(
    store: Execution, attempt: Attempt, case: str = "positive"
) -> cp3c.RefinancingRiskSubmission:
    return cp3c.RefinancingRiskSubmission.model_validate_json(literal(store, attempt, case))


# --- the store adapter (one adapter for submit, probe and view) ----------------------------------


def _stage1_expectation(
    case: str, store: Execution, attempt: Attempt, submission: cp3c.RefinancingRiskSubmission
) -> cp3c.Cp3cInputs:
    """The Stage 1 test's input object for `case` with the run-time refs."""
    stage1 = tm._inputs(case)
    names = refs(store, attempt)
    offered = {names[name]: name for name in stage1.offered.values()}
    return replace(stage1, offered=offered, submission=submission)


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_adapter_returns_the_stage_1_input_object(case: str, tmp_path: Path) -> None:
    """Over heads settled from the oracles' own records (CP-2D by its own core), the adapter
    returns exactly the Stage 1 test's input object, with the run-time refs."""
    store, _, attempt = seed(tmp_path, case)
    submission = submission_of(store, attempt, case)
    got = cp3c._inputs(store, attempt, submission)
    assert got == _stage1_expectation(case, store, attempt, submission)


def test_the_oracle_carries_the_principal_period_and_the_gap_currency() -> None:
    """Stage 2 close re-pin: the principal copies keep CP-1's T4.18 period, and the CP-2D gap
    twins (T2E.5.r04, T2E.5.r07) carry the currency USD in the CP-2D oracle."""
    for case in tm.PACK_CASES:
        cells = tm._cells(tm.EXPECTED["cases"][case]["tables"])
        for fact_id in ("T3D.1.r01.c1", "T3D.4.r01.c3"):
            assert cells[fact_id]["period"] == "q4-2025"
    cp2d_cells = tm._cells(tm.CP2D_EXPECTED["cases"]["gap_minimum_cash"]["tables"])
    for fact_id in ("T2E.5.r04", "T2E.5.r07"):
        assert cp2d_cells[fact_id]["state"] != "known" and cp2d_cells[fact_id]["currency"] == "USD"


def test_adapter_follows_the_heads_not_the_oracle(tmp_path: Path) -> None:
    run = make_pack(as_of="2026-02-14").run
    module = swap(cp1_module(run), "cp1:cash_closing", amount=Decimal(35))
    module = swap(module, "cp1:adjusted_ebitda", amount=Decimal("12.5"))
    store, _, attempt = seed(tmp_path, "gap_minimum_cash", cp1=module, as_of="2026-02-14")
    got = cp3c._inputs(store, attempt, tm._inputs("positive").submission)
    assert got.cp1.cash_closing.amount == Decimal(35)
    assert got.cp1.adjusted_ebitda.amount == Decimal("12.5")
    assert got.as_of.isoformat() == "2026-02-14"
    assert got.cp2d.horizon.amount == Decimal(24) and got.cp2d.minimum_cash.status == "missing"


@pytest.mark.parametrize("status", ["missing", "conflicting", "not_applicable"])
def test_adapter_keeps_an_unsettled_cp1_fact_as_its_status(status: str, tmp_path: Path) -> None:
    module = swap(
        cp1_module(make_pack().run),
        "cp1:adjusted_ebitda",
        amount=None,
        status=status,
        limitation="CP-1: not derived",
        calculation_id=None,
    )
    store, _, attempt = seed(tmp_path, cp1=module)
    fact = cp3c._inputs(store, attempt, tm._inputs("positive").submission).cp1.adjusted_ebitda
    assert (fact.status, fact.amount, fact.reason, fact.unit, fact.value_class) == (
        status,
        None,
        "CP-1: not derived",
        "MILLIONS",
        "calculated",
    )


def test_adapter_reads_each_facility_term_from_its_own_row() -> None:
    changed = {"secured_status": "UNSECURED", "seniority": "JUNIOR"}
    (terms,) = cp3c.select_cp1(cp1_module(make_pack().run, terms=changed)).operands.facilities
    assert (terms.secured_status.text, terms.seniority.text) == ("UNSECURED", "JUNIOR")
    assert (terms.facility_name.text, terms.currency) == ("Northbridge Term Loan", "USD")
    assert terms.annual_amortisation.unit == "MILLIONS"


def test_adapter_refuses_a_facility_alias_that_disagrees() -> None:
    module = swap(cp1_module(make_pack().run), "cp1:term-loan-fy-2025:seniority", text="JUNIOR")
    with pytest.raises(ValueError, match="^CP-3C: facility term-loan seniority differs between"):
        cp3c.select_cp1(module)


def test_adapter_refuses_a_facility_without_a_term() -> None:
    gone = _without(cp1_module(make_pack().run), lambda f: f.field == "seniority")
    with pytest.raises(ValueError, match="^CP-3C: facility term-loan has no CP-1 seniority fact$"):
        cp3c.select_cp1(gone)


def test_adapter_refuses_zero_or_several_facts_for_a_metric() -> None:
    base = cp1_module(make_pack().run)
    gone = _without(base, lambda f: f.fact_id == "cp1:cash_interest")
    with pytest.raises(ValueError, match="^CP-3C: CP-1 offers 0 facts for cash_interest"):
        cp3c.select_cp1(gone)
    twin = _t410("cash_interest", Decimal(1)).model_copy(
        update={"fact_id": "cp1:cash_interest-2", "row_id": "row-2"}
    )
    twice = Module.model_validate({**base.model_dump(), "facts": (*base.facts, twin)})
    with pytest.raises(ValueError, match="^CP-3C: CP-1 offers 2 facts for cash_interest"):
        cp3c.select_cp1(twice)


@pytest.mark.parametrize("update", [{"scale": Decimal(1000)}, {"unit": "PERCENT"}])
def test_adapter_refuses_an_amount_that_is_not_in_millions(update: dict[str, Any]) -> None:
    module = swap(cp1_module(make_pack().run), "cp1:adjusted_ebitda", **update)
    with pytest.raises(ValueError, match="^CP-3C adjusted_ebitda: not an amount in millions$"):
        cp3c.select_cp1(module)


def test_adapter_refuses_a_normalized_fact() -> None:
    module = swap(cp1_module(make_pack().run), "cp1:cash_closing", value_class="normalized")
    with pytest.raises(ValueError, match="^CP-3C cash_closing: a normalized fact is not read$"):
        cp3c.select_cp1(module)


def _alias_fact(module: Module, field: str) -> Fact:
    """The fy-2025 alias row's fact for `field` (the quarter row stays the schedule row)."""
    return next(
        f
        for f in module.facts
        if f.table_id == "T4.18" and f.period == "fy-2025" and f.field == field
    )


def test_adapter_refuses_an_alias_only_facility() -> None:
    """A facility with a fy-2025 row and no q4-2025 row is refused, never silently dropped from
    the refinancing need (the CP-2D review M2 class)."""
    base = cp1_module(make_pack().run)
    extra = tuple(
        f.model_copy(
            update={
                "fact_id": f.fact_id + "-b",
                "row_id": f.row_id + "-b",
                **({"text": "bridge-loan"} if f.field == "facility_id" else {}),
            }
        )
        for f in base.facts
        if f.table_id == "T4.18" and f.period == "fy-2025"
    )
    alias_only = Module.model_validate({**base.model_dump(), "facts": (*base.facts, *extra)})
    with pytest.raises(
        ValueError, match="^CP-3C: the fy-2025 T4.18 rows are not the q4-2025 rows$"
    ):
        cp3c.select_cp1(alias_only)


@pytest.mark.parametrize(
    ("field", "update", "term"),
    [
        ("currency", {"text": "EUR"}, "currency"),
        ("rate_type", {"text": "FIXED"}, "rate_type"),
        ("annual_amortisation", {"scale": Decimal(1000)}, "annual_amortisation"),
        ("annual_amortisation", {"amount": Decimal("7.5")}, "annual_amortisation"),
        ("facility_name", {"text": "Another Loan"}, "facility_name"),
        ("secured_status", {"text": "UNSECURED"}, "secured_status"),
    ],
)
def test_adapter_compares_every_alias_term(field: str, update: dict[str, Any], term: str) -> None:
    """The alias must agree on currency, rate type and scale as well as the amounts and texts."""
    base = cp1_module(make_pack().run)
    module = swap(base, _alias_fact(base, field).fact_id, **update)
    pattern = f"^CP-3C: facility term-loan {term} differs between its q4-2025 row and its fy-2025"
    with pytest.raises(ValueError, match=pattern):
        cp3c.select_cp1(module)


def test_cp2d_fact_refuses_a_scale_that_is_not_millions(tmp_path: Path) -> None:
    """A CP-2D head fact (a real one, settled by the CP-2D core) at another scale is refused."""
    store, _, _ = seed(tmp_path)
    facts = store.head_module(head(store, "CP-2D")).facts
    real = next(f for f in facts if f.fact_id == "T2E.3.r01")
    assert cp3c._cp2d_fact(real).unit == "MILLIONS"
    with pytest.raises(ValueError, match="^CP-3C T2E.3.r01: not an amount in millions$"):
        cp3c._cp2d_fact(real.model_copy(update={"scale": Decimal(1000)}))


def test_view_refuses_a_bound_module_of_another_run(tmp_path: Path) -> None:
    store, pack, attempt = seed(tmp_path)
    upstream = upstream_of(store, attempt)
    assert cp3c.context_block(pack=pack, upstream=upstream)["facts"]
    other = {"run_id": "another-run"}
    foreign_cp1 = Module.model_validate({**upstream.cp1.model_dump(), **other})
    foreign_cp2d = Module.model_validate({**upstream.cp2d.model_dump(), **other})
    for moved in (replace(upstream, cp1=foreign_cp1), replace(upstream, cp2d=foreign_cp2d)):
        module_id = "CP-1" if moved.cp1 is foreign_cp1 else "CP-2D"
        message = f"^CP-3C: the bound {module_id} module belongs to another run$"
        with pytest.raises(ValueError, match=message):
            cp3c.context_block(pack=pack, upstream=moved)


def test_adapter_balance_date_is_cp1s_schedule_period_end() -> None:
    assert cp3c.select_cp1(cp1_module(make_pack().run)).balance_date == tm.BALANCE_DATE
    moved = swap(cp1_module(make_pack().run), "cp1:T4.14:q4-2025:end_date", text="2025-12-30")
    assert cp3c.select_cp1(moved).balance_date.isoformat() == "2025-12-30"  # no FY alias then
    gone = _without(cp1_module(make_pack().run), lambda f: f.table_id == "T4.14")
    with pytest.raises(ValueError, match="^CP-3C: CP-1 states no end date for q4-2025$"):
        cp3c.select_cp1(gone)


def test_adapter_reads_cp2d_through_its_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D3: the CP-2D figures come through `cp2d_reader` on the bound head, and a reader that
    disagrees with the head's cells refuses (fail closed)."""
    store, _, attempt = seed(tmp_path)
    calls: list[str] = []
    real = cp2d.cp2d_reader

    def spy(s: Execution, h: Head) -> cp2d.Cp2dHead:
        calls.append(h.result_sha256)
        return real(s, h)

    monkeypatch.setattr(cp2d, "cp2d_reader", spy)
    upstream = upstream_of(store, attempt)
    bound = next(i for i in attempt.inputs if i.input_id == "CP-2D")
    assert calls == [bound.sha256] == [upstream.cp2d_read.head_sha256]
    lies: dict[str, dict[str, Any]] = {
        "T2E.5.r04": {"minimum_cash": Decimal(11)},
        "T2E.5.r07": {"funding_gap_missing": "invented"},
        "T2E.3.r03": {"horizon_months": 12},
    }
    (row,) = real(store, head(store, "CP-2D")).wall
    for cell, moved in (
        ("c1", replace(row, principal=Decimal(1))),
        ("c2", replace(row, maturity_date=date(2030, 1, 31))),
        ("c3", replace(row, months_to_maturity=Decimal(1))),
        ("c4", replace(row, inside_horizon=True)),
    ):
        lies[f"T2E.4.r01.{cell}"] = {"wall": (moved,)}
    lies["T2E.4"] = {"wall": (replace(row, facility="Another (term-loan)"),)}
    for fact_id, change in lies.items():

        def lying(s: Execution, h: Head, c: dict[str, Any] = change) -> cp2d.Cp2dHead:
            return replace(real(s, h), **c)

        monkeypatch.setattr(cp2d, "cp2d_reader", lying)
        pattern = f"^CP-3C: cp2d_reader and the CP-2D head disagree on {re.escape(fact_id)}$"
        with pytest.raises(ValueError, match=pattern):
            cp3c.select(upstream_of(store, attempt))


# `registry.dependencies` binds an optional edge whose producer the run selects, so this run
# (CP-1A requested) binds CP-1A in CP-3C's attempt inputs, and settlement inherits its limitations;
# expected.json#cp3c_module.attempt_inputs and manifest edges.bound_in_attempt_inputs list it.


def test_upstream_binds_the_attempt_and_reports_the_inputs_now(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    upstream = upstream_of(store, attempt)
    assert upstream.bound == attempt.inputs and upstream.current == attempt.inputs
    inputs = [i.input_id for i in attempt.inputs]
    oracle = tm.EXPECTED["cp3c_module"]["attempt_inputs"]
    assert inputs == oracle and "CP-1A" in oracle
    assert inputs == tm.MANIFEST["edges"]["bound_in_attempt_inputs"][:-1]
    cp1 = next(i.sha256 for i in attempt.inputs if i.input_id == "CP-1")
    assert upstream.cp1.content_hash() == cp1
    cp2d_head = store.head_module(head(store, "CP-2D"))
    cp1a = "CP-1A synthetic limitation"
    notes = ("CP-0 synthetic limitation", SYNTHETIC, "CP-1 synthetic limitation", cp1a)
    assert upstream.inherited == tuple(
        dict.fromkeys((*notes, *cp2d_head.limitations, *cp2d_head.inherited_limitations))
    )
    snapshot = store.read()
    heads = tuple(h for h in snapshot.heads if h.module_id != "CP-2D")
    stale = _FrozenExecution(store, snapshot.model_copy(update={"heads": heads}))
    assert upstream_of(stale, attempt).current == "Required upstream is unrun, stale or blocked"


def test_a_bound_input_of_another_module_is_refused(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    cp1 = next(i for i in attempt.inputs if i.input_id == "CP-1")
    forged = attempt.model_copy(
        update={
            "inputs": tuple(
                i.model_copy(update={"sha256": cp1.sha256}) if i.input_id == "CP-2D" else i
                for i in attempt.inputs
            )
        }
    )
    with pytest.raises(ValueError, match="CP-2D input is a CP-1 module"):
        upstream_of(store, forged)


# --- validation -----------------------------------------------------------------------------------


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_validate_accepts_the_oracle_literals(case: str, tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path, case)
    upstream = upstream_of(store, attempt)
    submission = submission_of(store, attempt, case)
    assert cp3c.validate_refinancing(submission=submission, upstream=upstream) == ()


@pytest.fixture(scope="module")
def upstream_store(tmp_path_factory: pytest.TempPathFactory) -> tuple[Execution, Attempt, Any]:
    store, _, attempt = seed(tmp_path_factory.mktemp("upstream"))
    return store, attempt, refs(store, attempt)


@pytest.mark.parametrize("name", tm.REFUSALS)
def test_validate_reproduces_the_oracle_refusals(name: str, upstream_store: Any) -> None:
    store, attempt, names = upstream_store
    payload = bound_payload(tm.SUBMISSIONS["refusal_inputs"][name]["payload"], names)
    submission = cp3c.RefinancingRiskSubmission.model_validate_json(json.dumps(payload))
    issues = cp3c.validate_refinancing(submission=submission, upstream=upstream_of(store, attempt))
    assert list(issues) == [tm.EXPECTED["refusals"][name]]


def test_validate_reports_a_stale_input_set_alone(upstream_store: Any) -> None:
    store, attempt, names = upstream_store
    good = upstream_of(store, attempt)
    payload = bound_payload(tm.SUBMISSIONS["cp3c_blocked"]["attempt_0"], names)
    bad = cp3c.RefinancingRiskSubmission.model_validate_json(json.dumps(payload))
    refused = "Required upstream is unrun, stale or blocked"
    stale = replace(good, current=refused)
    assert cp3c.validate_refinancing(submission=bad, upstream=stale) == (
        f"Stale inputs: {refused}",
    )
    moved = tuple(
        i.model_copy(update={"sha256": "0" * 64}) if i.input_id == "CP-2D" else i
        for i in good.bound
    )
    (issue,) = cp3c.validate_refinancing(submission=bad, upstream=replace(good, current=moved))
    assert issue.startswith("Stale input CP-2D: bound restricted ")
    long = replace(good, current="Required upstream " + "x" * 5000)
    (issue,) = cp3c.validate_refinancing(submission=bad, upstream=long)
    assert issue.startswith("Stale inputs: Required upstream") and len(issue) <= MAX_ISSUE_CHARS


def test_validate_refuses_an_upstream_that_is_not_the_bound_input(upstream_store: Any) -> None:
    store, attempt, names = upstream_store
    payload = bound_payload(tm.SUBMISSIONS["cp3c"]["positive"], names)
    submission = cp3c.RefinancingRiskSubmission.model_validate_json(json.dumps(payload))
    good = upstream_of(store, attempt)
    other = swap(good.cp1, "cp1:cash_closing", amount=Decimal(21))
    issues = cp3c.validate_refinancing(submission=submission, upstream=replace(good, cp1=other))
    assert issues == ("Upstream CP-1: the supplied module is not the bound input",)
    read = replace(good.cp2d_read, head_sha256="0" * 64)
    issues = cp3c.validate_refinancing(
        submission=submission, upstream=replace(good, cp2d_read=read)
    )
    assert issues == ("Upstream CP-2D: the supplied module is not the bound input",)
    moved = good.cp2d.model_copy(update={"limitations": ("another",)})
    issues = cp3c.validate_refinancing(submission=submission, upstream=replace(good, cp2d=moved))
    assert issues == ("Upstream CP-2D: the supplied module is not the bound input",)


# --- the journal: submit, the entry validator, probe -----------------------------------------------


def _submit(store: Execution, attempt: Attempt, payload: str) -> Any:
    return cp3c.submit(store, attempt.ticket_id, STEP, payload, None)


def settled(
    root: Path, case: str = "positive", **kwargs: Any
) -> tuple[Execution, PreparedPack, Attempt, Any]:
    store, pack, attempt = seed(root, case, **kwargs)
    return store, pack, attempt, _submit(store, attempt, literal(store, attempt, case))


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_submit_settles_the_head_with_the_tail_input(case: str, tmp_path: Path) -> None:
    store, pack, attempt, submitted = settled(tmp_path, case)
    done = finished(store, attempt)
    assert done.status == "finished" and done.issues == ()
    h = head(store, MODULE)
    assert h.status == tm.EXPECTED["cases"][case]["status"] == "restricted"
    assert h.qualification == cp3c.QUALIFICATION
    module = store.head_module(h)
    parsed = cp3c.RefinancingRiskSubmission.model_validate_json(submitted.payload)
    tail = Input(input_id="refinancing-risk-submission", sha256=parsed.content_hash())
    assert module.inputs == (*attempt.inputs, tail)
    upstream = upstream_of(store, attempt)
    report = cp3c.refinancing_risk(pack=pack, submission=parsed, upstream=upstream)
    assert (module.facts, module.tables, module.claims) == (
        report.facts,
        report.tables,
        report.claims,
    )
    assert list(module.limitations) == [*tm.EXPECTED["cases"][case]["own_limitations"], SYNTHETIC]
    assert module.inherited_limitations == tuple(
        n for n in upstream.inherited if n not in module.limitations
    )


def test_a_private_run_settles_without_the_synthetic_line(tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, case_kind="private", as_of="2026-03-31")
    module = store.head_module(head(store, MODULE))
    assert list(module.limitations) == tm.EXPECTED["cases"]["positive"]["own_limitations"]
    step_up = next(f for f in module.facts if f.fact_id == "T3D.3.r04")
    assert step_up.period == "2026-03-31"  # the step-up's period is the run's as-of


def test_probe_rebuilds_the_settled_head_and_writes_nothing(tmp_path: Path) -> None:
    store, _, attempt, _ = settled(tmp_path)
    snapshot = store.read()
    cp3c.probe(store, snapshot, finished(store, attempt))
    assert store.read() == snapshot


def test_probe_refuses_the_tamper_target_in_the_result_module(tmp_path: Path) -> None:
    """expected.json#tamper's target (T3D.2.r02, resources applied 10 -> 11) lives only in the
    result Module, so a head whose Module says otherwise does not rebuild."""
    store, _, attempt, _ = settled(tmp_path)
    snapshot = store.read()
    module = store.head_module(head(store, MODULE))
    tamper = tm.EXPECTED["tamper"]
    target = tamper["target_fact"]
    assert next(f for f in module.facts if f.fact_id == target).amount == Decimal(tamper["from"])
    forged = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"amount": Decimal(tamper["to"])}) if f.fact_id == target else f
                for f in module.facts
            )
        }
    )
    digest = store._store(forged.model_dump_json())
    done = finished(store, attempt).model_copy(update={"result_sha256": digest})
    heads = tuple(
        h.model_copy(update={"result_sha256": digest}) if h.module_id == MODULE else h
        for h in snapshot.heads
    )
    with pytest.raises(WorkflowError) as caught:
        cp3c.probe(store, snapshot.model_copy(update={"heads": heads}), done)
    assert caught.value.code == "identity_mismatch"


def test_probe_refuses_a_journal_that_does_not_rebuild(tmp_path: Path) -> None:
    store, _, attempt, _ = settled(tmp_path)
    snapshot, done = store.read(), finished(store, attempt)
    step = done.steps[0]
    other = json.loads(literal(store, attempt))
    other["repricing"]["bps"] = 300
    another = store._store(json.dumps(other))
    forged_steps = {
        "another step output": (step.model_copy(update={"output_sha256": "0" * 64}),),
        "a step that is not valid": (step.model_copy(update={"status": "invalid"}),),
        "two steps": (step, step),
        "another payload": (step.model_copy(update={"payload_sha256": another}),),
    }
    for name, steps in forged_steps.items():
        with pytest.raises(WorkflowError) as caught:
            cp3c.probe(store, snapshot, done.model_copy(update={"steps": steps}))
        assert caught.value.code == "identity_mismatch", name


def test_entry_validator_is_the_one_submit_journals_with(tmp_path: Path) -> None:
    store, pack, attempt, _ = settled(tmp_path)
    done = finished(store, attempt)
    outcome = cp3c.ENTRY_VALIDATOR(store, pack, done)
    assert outcome.issues == () and outcome.retained_as(done.steps[0])


@pytest.mark.parametrize("name", ["step_up_over_limit", "unknown_basis_ref", "digit_in_text"])
def test_a_refusal_is_a_journaled_invalid_step_with_the_oracle_issue(
    name: str, tmp_path: Path
) -> None:
    store, _, attempt = seed(tmp_path)
    payload = bound_payload(tm.SUBMISSIONS["refusal_inputs"][name]["payload"], refs(store, attempt))
    _submit(store, attempt, json.dumps(payload))
    done = finished(store, attempt)
    assert done.steps[0].status == "invalid"
    assert list(done.issues) == [tm.EXPECTED["refusals"][name]]
    rejected = store.result(done.result_sha256 or "")
    assert rejected.status == "rejected"
    assert not [h for h in store.read().heads if h.module_id == MODULE]


def test_two_refusals_block_the_module_and_the_reader_shows_no_figures(tmp_path: Path) -> None:
    """expected.json#negative_cases.blocked_cp3c."""
    store, _, first = seed(tmp_path)
    names = refs(store, first)
    blocked = tm.EXPECTED["negative_cases"]["blocked_cp3c"]
    attempt = first
    for key in ("attempt_0", "attempt_1"):
        payload = bound_payload(tm.SUBMISSIONS["cp3c_blocked"][key], names)
        _submit(store, attempt, json.dumps(payload))
        done = finished(store, attempt)
        assert done.steps[0].status == blocked[key]["step"]
        assert list(done.issues) == blocked[key]["issues"]
        if key == "attempt_0":
            attempt = store.begin(MODULE)
            assert attempt.number == 1 and attempt.repair_of == first.ticket_id
    h = head(store, MODULE)
    module = store.head_module(h)
    assert h.status == blocked["module_status"] and module.tables == () and module.claims == ()
    assert cp3c.cp3c_reader(store, h) == cp3c.Cp3cHead("blocked", h.result_sha256)


def test_submit_refuses_rules_a_foreign_step_and_a_finished_ticket(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    text = literal(store, attempt)
    with pytest.raises(ValueError, match="rule mode none"):
        cp3c.submit(store, attempt.ticket_id, STEP, text, lambda _t: ())
    with pytest.raises(ValueError, match="one step"):
        cp3c.submit(store, attempt.ticket_id, "liquidity_bridge", text, None)
    other = json.loads(text)
    other["repricing"]["bps"] = 1001
    _submit(store, attempt, json.dumps(other))  # invalid: attempt 0 rejected
    with pytest.raises(ValueError, match="absent, finished or belongs to another module"):
        _submit(store, attempt, text)


# --- the settled head equals the oracle (fast form of acceptance 1 and 2) -------------------------


def _shown(fact: Fact) -> str:
    return fact_spelling(fact, None)[2] if fact.status == "known" else cp3c.GAP_SHOWN[fact.status]


_STATE = {"known": "known", "missing": "gap", "not_applicable": "not_applicable"}


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_settled_tables_equal_the_oracle(case: str, tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, case)
    assert_module_equals_oracle(store.head_module(head(store, MODULE)), case)


def assert_module_equals_oracle(module: Module, case: str) -> None:
    """The settled CP-3C module's tables, cells, ledgers and claims equal the oracle's `case`
    (with the principal-period delta); `test_owner_cp3c` runs it on the closed store heads."""
    facts = {f.fact_id: f for f in module.facts}
    expected = tm.EXPECTED["cases"][case]
    titles = tm.EXPECTED["cp3c_module"]["table_titles"]
    assert [t.table_id for t in module.tables] == tm.EXPECTED["cp3c_module"]["table_ids"]
    tables = {t.table_id: t for t in module.tables}
    for table_id, table in expected["tables"].items():
        report = tables[table_id]
        assert (report.title, report.row_header) == (titles[table_id], table["row_header"])
        assert [c.label for c in report.columns] == table["columns"]
        assert [r.label for r in report.rows] == [label for label, _ in table["rows"]]
    for fact_id, cell in tm._cells(expected["tables"]).items():
        fact = facts[fact_id]
        assert (_STATE[fact.status], _shown(fact), fact.value_class) == (
            cell["state"],
            cell["shown"],
            cell["value_class"],
        ), fact_id
        assert (fact.unit, fact.currency, fact.formula) == (
            cell.get("unit"),
            cell.get("currency"),
            cell.get("formula"),
        ), fact_id
        assert fact.scale == (Decimal(1000000) if fact.unit == "MILLIONS" else 1), fact_id
        if fact.amount is not None:
            assert (fact.amount, fact.period) == (Decimal(cell["amount"]), cell["period"]), fact_id
        assert fact.limitation == cell.get("reason"), fact_id
    for table_id in ("T3D.7", "T3D.8", "T3D.9"):
        rows = [[r.label, *(facts[i].text for i in r.fact_ids)] for r in tables[table_id].rows]
        assert rows == expected[f"{table_id}_rows"], table_id
        assert tables[table_id].title == titles[table_id]
    assert [c.claim_id for c in module.claims] == [c["claim_id"] for c in expected["claims"]]
    assert [c.text for c in module.claims] == [c["template"] for c in expected["claims"]]
    assert [resolved(c.text, facts) for c in module.claims] == [
        c["text"] for c in expected["claims"]
    ]


def resolved(template: str, facts: Mapping[str, Fact]) -> str:
    """A claim's run text as the reader sees it (the oracle's `text`): each figure its settled
    spelling and figure unit, each chip its gap spelling."""
    gaps = {fact_id for fact_id, f in facts.items() if f.status != "known"}
    parts = []
    for run in prose.tokenize(template, gaps=gaps):
        if run.kind == "text":
            parts.append(run.text)
            continue
        fact = facts[run.text]
        unit = figure_unit(fact) if run.figure and fact.unit == "MILLIONS" else None
        parts.append(f"{_shown(fact)} {unit}" if unit else _shown(fact))
    return "".join(parts)


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_copies_cite_their_upstream_and_computed_cells_name_their_calculation(
    case: str, tmp_path: Path
) -> None:
    """Acceptance 1 and manifest fact_copy_rule: a copy keeps its upstream fact's citations and
    calculation id; a known computed cell names its calculation; any other cell has neither;
    a known cell a claim references has one or the other."""
    store, _, attempt, _ = settled(tmp_path, case)
    module = store.head_module(head(store, MODULE))
    facts = {f.fact_id: f for f in module.facts}
    upstream = {f.fact_id: f for f in store.head_module(head(store, "CP-2D")).facts}
    upstream |= {f.fact_id: f for f in upstream_of(store, attempt).cp1.facts}
    names = refs(store, attempt)
    for fact_id, cell in tm._cells(tm.EXPECTED["cases"][case]["tables"]).items():
        fact = facts[fact_id]
        operand = cell.get("cp2d_operand") or cell.get("cp1_operand")
        if operand is not None and cell.get("formula") is None:
            name = operand.removeprefix("T4.18 ").replace(" ", ".")
            twin = upstream[names.get(name, operand)]
            assert (fact.citations, fact.calculation_id) == (twin.citations, twin.calculation_id)
        elif cell.get("formula") is not None and fact.status == "known":
            assert (fact.citations, fact.calculation_id) == ((), f"calc:{fact_id}"), fact_id
        else:
            assert (fact.citations, fact.calculation_id) == ((), None), fact_id
    for claim in tm.EXPECTED["cases"][case]["claims"]:
        for ref in claim["references"]:
            if facts[ref].status == "known":
                assert facts[ref].citations or facts[ref].calculation_id, (claim["claim_id"], ref)


def test_claims_cite_what_their_names_and_cells_cite(tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path)
    claims = {c.claim_id: c for c in store.head_module(head(store, MODULE)).claims}
    assert claims["CP-3C-NEED-01"].citations == (tc2d.CITATION,)
    assert claims["CP-3C-HORIZON-01"].citations == ()  # CP-2D calculations and judgments only


# --- the exact `read_inputs` view -----------------------------------------------------------------

FACT_KEYS = ["ref", "name", "source", "label", "period", "unit", "shown", "status", "limitation"]


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_view_is_the_lease_key_tree_without_quotes(case: str, tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path, case)
    digest, body = cp3c.view(_FrozenExecution(store, store.read()), attempt)
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    tree = json.loads(body)
    assert body == json.dumps(tree, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    assert list(tree) == TREE["top_level_keys_in_order"]
    assert not _keys(tree) & set(TREE["forbidden_keys"])
    assert tree["upstream"] == [{"module_id": m, "status": "restricted"} for m in cp3c.EDGES]
    assert [f["name"] for f in tree["facts"]] == sorted(tm.MANIFEST["fact_bindings"])
    assert all(list(f) == FACT_KEYS for f in tree["facts"])
    by_name = {f["name"]: f for f in tree["facts"]}
    assert {n: f["ref"] for n, f in by_name.items()} == refs(store, attempt)
    sources = {n: b["source"] for n, b in tm.MANIFEST["fact_bindings"].items()}
    assert {n: f["source"] for n, f in by_name.items()} == sources
    assert by_name["cp2d.horizon"]["shown"] == "24 months"
    facility = {"facility_id": "term-loan", "facility_name": "Northbridge Term Loan"} | TERMS
    assert tree["facilities"] == [facility]
    assert tree["unread_optional_edges"] == TREE["unread_optional_edges"]
    assert tree["bounds"] == TREE["bounds"]
    assert tree["inherited_limitations"] == list(upstream_of(store, attempt).inherited)
    quotes = {
        c.quote for h in store.read().heads for f in store.head_module(h).facts for c in f.citations
    }
    assert quotes and not [q for q in quotes if q in body]


TREE_FILE = Path(__file__).resolve().parents[1] / "cases" / "cp3c-owner" / "cp3c-view-tree.json"


def _shape(value: Any) -> Any:
    """The key tree of a JSON value: leaves are type names; a list is the merge of its items."""
    if isinstance(value, dict):
        return {k: _shape(v) for k, v in value.items()}
    if isinstance(value, list):
        merged: Any = None
        for item in value:
            merged = _merge(merged, _shape(item))
        return [] if merged is None else [merged]
    return "null" if value is None else type(value).__name__


def _merge(a: Any, b: Any) -> Any:
    if a is None or a == b:
        return b
    if isinstance(a, dict) and isinstance(b, dict) and list(a) == list(b):
        return {k: _merge(a[k], b[k]) for k in a}
    assert isinstance(a, str) and isinstance(b, str), (a, b)
    return "|".join(sorted({*a.split("|"), *b.split("|")}))


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_view_key_tree_equals_the_committed_tree(case: str, tmp_path: Path) -> None:
    """Stage 2 close release: `cases/cp3c-owner/cp3c-view-tree.json` is the key tree (shape,
    not values) observed on a product-settled head for each pack case."""
    store, _, attempt = seed(tmp_path, case)
    tree = json.loads(cp3c.view(_FrozenExecution(store, store.read()), attempt)[1])
    committed = json.loads(TREE_FILE.read_text())[case]
    assert committed == {"top_level_keys": list(tree), "tree": _shape(tree)}
    assert list(tree) == TREE["top_level_keys_in_order"]


def test_view_offers_a_missing_fact_with_its_status_never_a_number(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path, "gap_minimum_cash")
    tree = json.loads(cp3c.view(store, attempt)[1])
    item = next(f for f in tree["facts"] if f["name"] == "cp2d.min_cash")
    facts = store.head_module(head(store, "CP-2D")).facts
    reason = next(f.limitation for f in facts if f.fact_id == "T2E.5.r04")
    assert (item["status"], item["shown"], item["limitation"]) == ("missing", "missing", reason)


def test_view_is_the_registered_view_and_follows_the_heads(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    frozen = _FrozenExecution(store, store.read())
    assert owner._VIEWS[STEP](frozen, attempt) == cp3c.view(frozen, attempt)
    module = swap(cp1_module(make_pack().run), "cp1:cash_closing", amount=Decimal(35))
    other, _, attempt2 = seed(tmp_path / "other", cp1=module, case_kind="private")
    tree = json.loads(cp3c.view(other, attempt2)[1])
    cash = next(f for f in tree["facts"] if f["name"] == "cash_closing")
    assert cash["shown"] == "35 US$ m"


# --- registrations (lease Files; append-only rows) -------------------------------------------------


def test_registrations_equal_the_lease() -> None:
    expected = owner.OwnerSpec(
        module_id=MODULE,
        steps=(
            owner.StepSpec(
                step_id=STEP,
                schema=cp3c.RefinancingRiskSubmission,
                sources=False,
                extract=False,
                upstream_grant=None,
                inputs="module_context",
                rules="none",
            ),
        ),
        entry="owner_core",
        kind="analytical",
        publish=None,
    )
    assert owner.OWNER_SPECS[MODULE] == expected
    assert MODULE in owner.SUPPORTED_ANALYTICAL
    assert owner._CORES[MODULE] is cp3c
    assert owner._QUALIFICATION[MODULE] is cp3c.QUALIFICATION
    assert owner._PROBES[MODULE] is cp3c.probe
    assert owner._VIEWS[STEP] is cp3c.view
    assert owner._ENTRY_VALIDATORS[MODULE] is cp3c.ENTRY_VALIDATOR
    assert MODULE not in owner._PRECHECKS
    owner._check_steps(MODULE, owner.OWNER_SPECS[MODULE])


def test_registrations_are_appended_after_their_dependencies() -> None:
    """Append-only: the shipped prefix stands, and each CP-3C row comes after the rows of the
    modules it consumes. Later appends are not this test's."""
    assert tuple(owner.OWNER_SPECS)[:5] == ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL")
    assert tuple(owner._QUALIFICATION)[:4] == ("CP-1", "CP-1A", "CP-2", "CP-MODEL")
    assert tuple(owner._PROBES)[:4] == ("CP-0", "CP-1", "CP-1A", "CP-2")
    assert tuple(owner._VIEWS)[:1] == ("credit_synthesis",)
    assert tuple(owner._ENTRY_VALIDATORS)[:2] == ("CP-1A", "CP-2")
    assert tuple(owner._CORES)[:2] == ("CP-DR", "CP-3D")
    for table, key, after in (
        (owner.OWNER_SPECS, MODULE, ("CP-0", "CP-1", "CP-2D")),
        (owner._CORES, MODULE, ("CP-2D",)),
        (owner._QUALIFICATION, MODULE, ("CP-1", "CP-2D")),
        (owner._PROBES, MODULE, ("CP-0", "CP-1", "CP-2D")),
        (owner._ENTRY_VALIDATORS, MODULE, ("CP-2D",)),
        (owner._VIEWS, STEP, ("liquidity_bridge",)),
    ):
        order = list(table)
        assert all(order.index(key) > order.index(a) for a in after), (key, after)


def test_a_plan_with_cp3c_passes_check_specs(tmp_path: Path) -> None:
    planned = owner._check_specs(make_pack(), owner.OWNER_SPECS, None, tmp_path / "plan")
    assert list(planned) == tm.MANIFEST["plan_order_expected"]


# --- bindings (lease Rendered sections) ------------------------------------------------------------

FP04 = tm.EXPECTED["fp04_render"]


def test_shipped_maps_hold_cp3c_once_directly_after_cp2d() -> None:
    ids = [m.module_id for m in SHIPPED_MAPS]
    assert ids.count(MODULE) == 1 and ids.index(MODULE) == ids.index("CP-2D") + 1


def test_spec_rows_serve_the_two_blocks() -> None:
    from deploy_vii.report_view import _spec_of

    for block, title, collapsed in (
        ("refinancing-paths", "Refinancing paths", False),
        ("lme-creditor-exposure", "LME capacity and creditor exposure", True),
    ):
        spec = _spec_of(block)
        assert (spec.title, spec.owner, spec.kind, spec.producers, spec.collapsed) == (
            title,
            "CP-3C",
            "dense",
            ("CP-3C",),
            collapsed,
        )
        assert spec.route_label == "Full analysis"


def test_bindings_follow_the_lease() -> None:
    cp3c_map = next(m for m in SHIPPED_MAPS if m.module_id == MODULE)
    assert all(e.cell_slot.startswith("cp3c-") for e in cp3c_map.entries)
    assert all(e.fact_coord.module_id == MODULE for e in cp3c_map.entries)
    placed: dict[str, list[str | None]] = {}
    for entry in cp3c_map.entries:
        placed.setdefault(entry.block_id, []).append(entry.fact_coord.table_id)
    want = {b: [s["primary_tab"], *s["tabs"]] for b, s in FP04["blocks"].items()}
    assert placed == want | FP04["rails"]
    labels = {e.fact_coord.table_id: e.label for e in cp3c_map.entries}
    assert labels == tm.EXPECTED["cp3c_module"]["table_titles"]


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_validate_bindings_over_the_settled_tables_is_clean(case: str, tmp_path: Path) -> None:
    store, pack, _, _ = settled(tmp_path, case)
    module = store.head_module(head(store, MODULE))
    view = View(
        run=pack.run,
        mode="accepted",
        modules=(
            ModuleView(
                module_id=MODULE,
                title="Refinancing and liability-management risk",
                aliases=(),
                status=module.status,
                artifact_sha256=module.content_hash(),
                facts=module.facts,
                tables=module.tables,
                claims=module.claims,
                limitations=module.limitations,
            ),
        ),
    )
    cp3c_map = next(m for m in SHIPPED_MAPS if m.module_id == MODULE)
    assert validate_bindings(view, (cp3c_map,)) == ()


# --- the reader the lease pins (Public API; expected.json#consumption.cp3c_consumed_by) -----------


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_reader_exposes_what_the_lease_pins(case: str, tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, case)
    h = head(store, MODULE)
    assert cp3c.cp3c_reader(store, h) == expected_read(h, case)


def expected_read(h: Head, case: str) -> cp3c.Cp3cHead:
    """What `cp3c_reader` returns on a settled head of `case`, read from the oracle."""
    expected = tm.EXPECTED["cases"][case]
    cells = tm._cells(expected["tables"])

    def amount(fact_id: str) -> Decimal | None:
        return Decimal(cells[fact_id]["amount"]) if cells[fact_id]["state"] == "known" else None

    paths = {p["kind"]: p["feasibility"] for p in tm.SUBMISSIONS["cp3c"][case]["paths"]}
    (label,) = (row[0] for row in expected["tables"]["T3D.1"]["rows"])
    return cp3c.Cp3cHead(
        status="restricted",
        head_sha256=h.result_sha256,
        total_principal_payable=amount("T3D.2.r01"),
        need=amount("T3D.2.r03"),
        need_missing=cells["T3D.2.r03"].get("reason"),
        need_rows=(
            cp3c.NeedRow(label, amount("T3D.1.r01.c9"), cells["T3D.1.r01.c9"].get("reason")),
        ),
        added_interest=amount("T3D.3.r06"),
        added_interest_missing=cells["T3D.3.r06"].get("reason"),
        base_claims=amount("T3D.5.r01.c1"),
        paths=tuple((k, paths[k]) for k in cp3c.KINDS),
        own_limitations=(*expected["own_limitations"], SYNTHETIC),
    )


def test_reader_follows_the_head_not_the_oracle(tmp_path: Path) -> None:
    module = swap(cp1_module(make_pack().run), "cp1:cash_closing", amount=Decimal(45))
    store, _, attempt = seed(tmp_path, cp1=module)
    _submit(store, attempt, literal(store, attempt))
    read = cp3c.cp3c_reader(store, head(store, MODULE))
    assert (read.need, read.need_rows[0].need) == (Decimal(15), Decimal(15))  # 50 - (45 - 10)


def test_reader_principal_and_base_claims_follow_the_head(tmp_path: Path) -> None:
    """CP-1's facility principal (62.5, not the oracle's 50) flows through the real CP-2D head
    into T3D.2.r01 and T3D.5.r01.c1, and the reader returns those cells."""
    module = cp1_module(make_pack().run)
    for fact_id in ("cp1:T4.18_principal", "cp1:term-loan-fy-2025:principal"):
        module = swap(module, fact_id, amount=Decimal("62.5"))
    store, _, attempt = seed(tmp_path, cp1=module)
    _submit(store, attempt, literal(store, attempt))
    h = head(store, MODULE)
    mine = {f.fact_id: f for f in store.head_module(h).facts}
    read = cp3c.cp3c_reader(store, h)
    assert mine["T3D.2.r01"].amount == mine["T3D.5.r01.c1"].amount == Decimal("62.5")
    assert (read.total_principal_payable, read.base_claims) == (Decimal("62.5"), Decimal("62.5"))
    assert read.need == mine["T3D.2.r03"].amount != Decimal(15)


def test_reader_refuses_another_modules_head_and_shows_a_stale_heads_status_only(
    tmp_path: Path,
) -> None:
    store, _, _, _ = settled(tmp_path)
    with pytest.raises(ValueError, match="not a CP-3C head"):
        cp3c.cp3c_reader(store, head(store, "CP-2D"))
    stale = head(store, MODULE).model_copy(update={"status": "stale"})
    assert cp3c.cp3c_reader(store, stale) == cp3c.Cp3cHead("stale", stale.result_sha256)


# --- consumption (D3): CP-3C reads the settled CP-2D head ------------------------------------------

COPIES = {"T3D.1.r01.c1", "T3D.1.r01.c2", "T3D.1.r01.c3", "T3D.1.r01.c4"}
COPIES |= {"T3D.2.r10", "T3D.2.r11", "T3D.2.r12", "T3D.4.r01.c3"}


@pytest.mark.parametrize("case", ["positive", "gap_minimum_cash"])
def test_d3_cp3c_consumes_the_settled_cp2d_head(case: str, tmp_path: Path) -> None:
    """expected.json#consumption.cp2d_consumed_by_cp3c, fast form: the attempt binds the final
    CP-2D head; T3D.1 c1-c4, T3D.2 r10-r12 and T3D.4 c3 copy that head's cells (value, state and
    value class); CP-3C-HORIZON-01 references the funding-gap copy; in gap_minimum_cash the CP-2D
    gaps arrive as gaps, never 0, and their dependants are gaps."""
    store, _, attempt, _ = settled(tmp_path, case)
    assert_consumes_cp2d(store, attempt, case)


def assert_consumes_cp2d(store: Execution, attempt: Attempt, case: str) -> None:
    """D3 for CP-2D on a settled CP-3C attempt of `case` (`test_owner_cp3c` runs it on the closed
    store heads)."""
    final = head(store, "CP-2D")
    bound = next(i for i in attempt.inputs if i.input_id == "CP-2D")
    assert (bound.sha256, bound.status) == (final.result_sha256, final.status)
    module = store.head_module(head(store, MODULE))
    assert module.inputs[-1].input_id == "refinancing-risk-submission"
    theirs = {f.fact_id: f for f in store.head_module(final).facts}
    mine = {f.fact_id: f for f in module.facts}
    copies = {
        fid: c["cp2d_operand"]
        for fid, c in tm._cells(tm.EXPECTED["cases"][case]["tables"]).items()
        if "cp2d_operand" in c
    }
    assert set(copies) == COPIES
    for fact_id, operand in copies.items():
        a, b = mine[fact_id], theirs[operand]
        assert (a.amount, a.text, a.status, a.value_class) == (
            b.amount,
            b.text,
            b.status,
            b.value_class,
        ), fact_id
    horizon = next(c for c in module.claims if c.claim_id == "CP-3C-HORIZON-01")
    assert "T3D.2.r10" in horizon.text
    if case == "gap_minimum_cash":
        for fact_id in ("T3D.2.r10", "T3D.2.r11", "T3D.2.r02", "T3D.2.r03", "T3D.2.r09"):
            assert mine[fact_id].status == "missing" and mine[fact_id].amount is None, fact_id


# --- methods/cp3c.md (brief: the guard limits and the derived-citation rule) ------------------------

METHODS = Path(__file__).resolve().parents[1] / "src" / "deploy_vii" / "methods" / "cp3c.md"


def test_methods_record_the_guard_limits_and_the_derived_citation_rule() -> None:
    text = " ".join(METHODS.read_text(encoding="utf-8").split())
    passed = [
        p["text"]
        for p in tm.EXPECTED["prohibited_probe"]
        if not p["issues"]
        and p["class"] not in ("product_permitted", "false_positive_in_revision_1")
    ]  # the conclusions the phrase guard passes (a neutral sentence passing is no limit)
    assert len(passed) == 8 and all(f'"{s}"' in text for s in passed), passed
    for note in (
        "calc:<fact_id>",
        "keeps its upstream fact's value, unit, period, value class, citations and calculation id",
        "a ref is matched exactly",
        "Any digit in an analyst text field is refused",
        "`cp2d_reader` and the CP-2D head's cells disagree",
        "never a stamped default",
        "pin_extension_needed",
    ):
        assert note in text, note


# --- the run driver's pure parts (tests/cp3c_runs.py; its store runs are deferred) -------------------

runs: Any = importlib.import_module("cp3c_runs")


def test_driver_reads_the_pinned_oracle_and_binds_every_literal_from_the_view(
    tmp_path: Path,
) -> None:
    oracle = runs.oracle()
    assert (oracle["expected"], oracle["submissions"]) == (tm.EXPECTED, tm.SUBMISSIONS)
    store, _, attempt = seed(tmp_path)
    body = json.loads(cp3c.view(store, attempt)[1])
    names = refs(store, attempt)
    payloads = [tm.SUBMISSIONS["cp3c"][case] for case in tm.PACK_CASES]
    payloads += [tm.SUBMISSIONS["cp3c_blocked"][a] for a in ("attempt_0", "attempt_1")]
    for payload in payloads:
        text = runs.bind_facts(json.dumps(payload, ensure_ascii=False), body)
        assert "{{FACT:" not in text
        assert json.loads(text) == bound_payload(payload, names)
    with pytest.raises(RuntimeError, match="FACT nowhere: not offered by the read view"):
        runs.bind_facts('{"a": "{{FACT:nowhere}}"}', body)


def test_driver_cp0_text_appends_both_consumer_deltas_in_order() -> None:
    document = json.loads(runs.cp0_text(runs.make_pack()))
    deltas = tm.SUBMISSIONS["cp0_consumer_deltas"]
    assert [d["module_id"] for d in deltas] == ["CP-2D", "CP-3C"]
    assert document["consumers"][-2:] == deltas
    assert runs.make_pack().run == _run()
