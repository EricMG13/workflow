"""Stage 2: CP-2D connection tests (docs/CP2D-OWNER-LEASE.md; work/build/stage2/brief.md).

First section: the backlog rows (work/build/stage2-backlog.md, [CP-2D]), each written before its
code and watched red. Later sections: the plug-in parts, the store adapter, the registrations,
the bindings and the reader.
"""

from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest
import test_method_cp2d as tm

from deploy_workflow.owners import cp2d

BALANCE = "2025-12-31"

# --- backlog: a sum copy is a dependant gap (addendum 4 (b); cp2d/r13-review.md L4) -----------


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        (
            {"equity_issuance": tm._opd("conflicting")},
            "Not calculable: Equity issuance is conflicting",
        ),
        (
            {"equity_repurchases": tm._opd("not_applicable")},
            "Not calculable: Equity repurchases is not applicable",
        ),
        (
            {"equity_issuance": tm._opd("missing")},
            "Not calculable: Equity issuance is missing",
        ),
        (
            {"equity_issuance": None},
            "Not calculable: Equity issuance is missing",
        ),
    ],
)
def test_backlog_sum_copy_is_a_dependant_gap(changes: dict[str, Any], reason: str) -> None:
    cell = tm._cells(cp2d.compute(tm._op_inputs(**changes)))["T2E.1.r05"]
    assert (cell.state, cell.reason, cell.amount, cell.period) == ("gap", reason, None, None)
    assert (cell.cp1_operand, cell.cp1_unit) == ("equity_issuance+equity_repurchases", "currency")
    assert cell.value_class == "calculated"


def test_backlog_single_copy_keeps_the_cp1_status_and_limitation() -> None:
    cell = tm._cells(cp2d.compute(tm._op_inputs(cfo=tm._opd("conflicting", "CP-1 says: x"))))[
        "T2E.1.r02"
    ]
    assert (cell.state, cell.reason) == ("conflicting", "CP-1 says: x")


# --- backlog: a recomputed cell takes the balance date (addendum 4 (c), (d)) -------------------

RECOMPUTED = ("T2E.2.r05", "T2E.2.r06", "T2E.2.r07", "T2E.2.r09", "T2E.5.r02")


def test_backlog_recomputed_cells_take_the_balance_date() -> None:
    cells = tm._cells(cp2d.compute(tm._inputs("positive")))
    for fact_id in RECOMPUTED:
        assert cells[fact_id].state == "known", fact_id
        assert cells[fact_id].period == BALANCE, fact_id
    # the CP-1 tag stays as the twin pointer
    assert cells["T2E.2.r05"].cp1_operand == "undrawn_rcf"
    assert cells["T2E.2.r06"].cp1_operand == "T4.18 commitment - drawn_amount"


def test_backlog_recomputed_cells_have_no_period_invariant() -> None:
    """The CP-1 metric's own period (here an odd string) is not the recomputed cell's."""
    odd = cp2d.Operand("known", Decimal(5), "an odd T4.10 period", None)
    inputs = tm._op_inputs(undrawn_rcf=odd, liquidity=odd, liquidity_to_debt=odd)
    cells = tm._cells(cp2d.compute(inputs))
    for fact_id in ("T2E.2.r05", "T2E.2.r07", "T2E.2.r09", "T2E.5.r02"):
        assert cells[fact_id].period == BALANCE, fact_id


def test_backlog_commitment_less_drawn_ignores_facility_periods() -> None:
    other = replace(tm.LOAN, facility_id="other-loan", period="a different period")
    inputs = tm._with_loan(replace(tm.LOAN, period="a facility period"))
    inputs = replace(inputs, operands=replace(inputs.operands, facilities=(tm.LOAN, other)))
    cells = tm._cells(cp2d.compute(inputs))  # no ValueError: a recomputed cell has no invariant
    assert cells["T2E.2.r06"].period == BALANCE


def test_backlog_copies_keep_the_cp1_period() -> None:
    cells = tm._cells(cp2d.compute(tm._inputs("positive")))
    assert cells["T2E.2.r01"].period == tm._Q4_BALANCE  # cash_bs, a copy
    assert cells["T2E.1.r02"].period == tm._LTM  # cfo, a copy
    assert cells["T2E.4.r01.c1"].period == "q4-2025"  # the facility principal, a copy


# --- backlog: "RCF drawings" takes a plural verb (cp2d/r13-fix1-review.md L1) -------------------


@pytest.mark.parametrize(("status", "word"), tm._NOT_KNOWN)
def test_backlog_rcf_drawings_agree_with_a_plural_verb(
    status: cp2d.OperandStatus, word: str
) -> None:
    operands = tm._ro(tm._operands("fixture_burn"), rcf_drawn=tm._unknown(status))
    result = cp2d.compute(replace(tm._inputs("positive"), operands=operands))
    assert result.bridge.runway_reason == f"Not calculable: RCF drawings are {word}"
    assert _claim_text(result, "CP-2D-LIQ-01").endswith(
        f"needs RCF drawings, which are {word}; cash is {{T2E.2.r01|US$ m}}."
    )
    assert f"because RCF drawings are {word}; cash-only headroom" in _claim_text(
        result, "CP-2D-GAP-01"
    )
    assert f"because RCF drawings are {word}; the cash-only headroom" in "".join(
        result.own_limitations
    )
    for text in (*(c.template for c in result.claims), *result.own_limitations):
        assert "RCF drawings is" not in text and "drawings, which is" not in text


@pytest.mark.parametrize(("status", "word"), tm._NOT_KNOWN)
def test_backlog_rcf_commitment_keeps_the_singular_verb(
    status: cp2d.OperandStatus, word: str
) -> None:
    operands = tm._ro(tm._operands("fixture_burn"), rcf_commitment=tm._unknown(status))
    result = cp2d.compute(replace(tm._inputs("positive"), operands=operands))
    assert result.bridge.runway_reason == f"Not calculable: RCF commitment is {word}"
    assert f"because RCF commitment is {word}; cash-only headroom" in _claim_text(
        result, "CP-2D-GAP-01"
    )


def _claim_text(result: cp2d.Cp2dResult, claim_id: str) -> str:
    return tm._claim(result, claim_id).template


# =============================================================================================
# The connection (docs/CP2D-OWNER-LEASE.md Public API; docs/G1X-OWNER-CORE-PROTOCOL.md §2)
# =============================================================================================
#
# A synthetic store: the real `Execution` journal with CP-0, CP-1, CP-1A and CP-2 settled from
# hand-built modules (test-only), the CP-1 module built from the frozen oracle facts with the
# Stage 1 test's stand-in ids `cp1:<name>` so that the adapter's output can be compared with the
# Stage 1 test's own input object exactly.

import hashlib
import importlib
import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import cast

from deploy_vii.contracts import Citation, Fact, Module, Run
from deploy_vii.execution import (
    Attempt,
    Execution,
    Qualification,
    head_of,
)
from deploy_vii.preparation import PreparedPack
from deploy_vii.prose import prose_issues
from deploy_vii.registry import step_chain
from deploy_workflow.financial_workflow import _FrozenExecution

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
runs: Any = importlib.import_module("s1a_runs")

UPSTREAM = ("CP-0", "CP-1", "CP-1A", "CP-2")
QUOTE = "Cash and cash equivalents  15  16.25  17.50  18.75  20.00  20.00"


def _pack() -> PreparedPack:
    pack = runs.make_pack("positive")
    document = json.loads(pack.run.model_dump_json())
    document["run_id"] = tm.MANIFEST["run"]["run_id"]
    document["pathway"] = tm.MANIFEST["run"]["pathway"]
    document["requested_modules"] = tm.MANIFEST["run"]["requested_modules"]
    return PreparedPack(run=Run.model_validate_json(json.dumps(document)), sources=pack.sources)


PACK = _pack()
FINANCIAL = next(s for s in PACK.sources if s.source_id == "financial")
CITATION = Citation(
    source_id="financial", source_sha256=cast(str, FINANCIAL.sha256), locator="page:4", quote=QUOTE
)
FACILITY_FIELDS = (
    "principal",
    "maturity_date",
    "commitment",
    "drawn_amount",
    "annual_amortisation",
)
USED = [
    "opening_cash",
    "cfo",
    "investing",
    "net_debt_issuance",
    "equity_issuance",
    "equity_repurchases",
    "dividends_paid",
    "other_investing_financing",
    "financing",
    "fx_effect",
    "closing_cash",
    "cash_bs",
    "restricted_cash",
    "rcf_commitment",
    "rcf_drawn",
    "total_debt_bs",
    "cash_closing",
    "total_debt",
    "undrawn_rcf",
    "liquidity",
    "liquidity_to_debt",
]


def _stand_in(name: str) -> str:
    return "cp1:" + name.replace(" ", "_")


def _cp1_fact(name: str, operand: cp2d.Operand | None) -> Fact:
    """The CP-1 fact the binding of `name` selects, as CP-1 writes it (observed on the real
    promoted head: T4.5/T4.6 unit `currency`, T4.10 `MILLIONS`/`PERCENT`, USD, scale 1e6)."""
    binding = cp2d.FACT_BINDINGS[name]
    if binding.table_id == "T4.10":
        shape: dict[str, Any] = (
            {"unit": "PERCENT"}
            if name == "liquidity_to_debt"
            else {"unit": "MILLIONS", "currency": "USD", "scale": Decimal(1000000)}
        )
    else:
        shape = {"unit": "currency", "currency": "USD", "scale": Decimal(1000000)}
    if operand is None:
        operand = cp2d.Operand("known", Decimal(7), binding.period, None)
    base: dict[str, Any] = {
        "fact_id": _stand_in(name),
        "label": binding.label,
        "table_id": binding.table_id,
        "row_id": "row-" + name,
        "field": "value",
        "period": binding.period,
        "citations": (CITATION,),
        "value_class": "calculated" if binding.table_id == "T4.5" else "source",
    }
    if operand.status == "known":
        return Fact(**base, amount=operand.amount, status="known", **shape)
    return Fact(**base, status=operand.status, limitation=operand.limitation, **shape)


def _row_facts(
    row: str, period: str, values: dict[str, Any], ids: str, currency: str = "USD"
) -> list[Fact]:
    """One T4.18 row's facts. `values` maps a field to an amount, a text, or an Operand-like
    non-known marker (a str starting with "!" is a missing fact with that limitation)."""
    out: list[Fact] = []
    for field, value in values.items():
        fact_id = _stand_in("T4.18 " + field) if ids == "plain" else f"cp1:{row}:{field}"
        base: dict[str, Any] = {
            "fact_id": fact_id,
            "label": field,
            "table_id": "T4.18",
            "row_id": row,
            "field": field,
            "period": period,
            "citations": (CITATION,),
            "value_class": "source",
        }
        money: dict[str, Any] = {
            "unit": "MILLIONS",
            "currency": currency,
            "scale": Decimal(1000000),
        }
        if isinstance(value, str) and value.startswith("!"):
            out.append(Fact(**base, status="missing", limitation=value[1:]))
        elif isinstance(value, Decimal):
            out.append(Fact(**base, amount=value, status="known", **money))
        else:
            out.append(Fact(**base, text=str(value), status="known"))
    return out


def _facility_values(f: cp2d.Facility) -> dict[str, Any]:
    missing = "!CP-1 did not offer this term"
    return {
        "facility_id": f.facility_id,
        "facility_name": f.name,
        "currency": missing if f.currency is None else f.currency,
        "principal": missing if f.principal is None else f.principal,
        "maturity_date": missing if f.maturity_date is None else f.maturity_date.isoformat(),
        "commitment": missing if f.commitment is None else f.commitment,
        "drawn_amount": missing if f.drawn_amount is None else f.drawn_amount,
        "annual_amortisation": missing if f.annual_amortisation is None else f.annual_amortisation,
    }


def _period_rows(end: str = "2025-12-31") -> list[Fact]:
    facts: list[Fact] = []
    for pid, kind in (("q4-2025", "QUARTER"), ("fy-2025", "FY")):
        for field, text in (("period_id", pid), ("period_type", kind), ("end_date", end)):
            facts.append(
                Fact(
                    fact_id=f"cp1:T4.14:{pid}:{field}",
                    label=field,
                    table_id="T4.14",
                    row_id="period-" + pid,
                    field=field,
                    text=text,
                    period=pid,
                    citations=(CITATION,),
                    value_class="source",
                )
            )
    return facts


def cp1_module(
    operands: cp2d.Operands,
    run: Run | None = None,
    *,
    ids: str = "plain",
    end: str = "2025-12-31",
) -> Module:
    """A CP-1 module holding the facts the CP-2D bindings select, from Stage 1 operands."""
    facts = [_cp1_fact(name, cast("cp2d.Operand | None", getattr(operands, name))) for name in USED]
    facts += [
        _cp1_fact("cfo_reported", None),
        _cp1_fact("debt_issuance", None),
        _cp1_fact("debt_repayment", None),
        _cp1_fact(
            "fcf_unlevered", cp2d.Operand("missing", None, None, "Free cash flow is not derived")
        ),
    ]
    facts += _period_rows(end)
    for facility in operands.facilities or ():
        for period in ("q4-2025", "fy-2025"):
            row = f"{facility.facility_id}-{period}"
            tag = "plain" if (period == "q4-2025" and ids == "plain") else "row"
            facts += _row_facts(
                row, period, _facility_values(facility), tag, facility.currency or "USD"
            )
    pack = run or PACK.run
    return Module(
        run_id=pack.run_id,
        issuer_id=pack.issuer_id,
        as_of=pack.as_of,
        module_id="CP-1",
        facts=tuple(facts),
        limitations=("CP-1 synthetic limitation",),
    )


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
        for m in ("CP-1", "CP-1A", "CP-2", "CP-2D")
    )


def _settle(store: Execution, module_id: str, body: Module | None = None) -> Attempt:
    attempt = store.begin(module_id)
    run = store.read().run
    base = body or Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=module_id,
        limitations=(f"{module_id} synthetic limitation",),
        facts=_commands() if module_id == "CP-0" else (),
    )
    candidate = base.model_copy(update={"inputs": attempt.inputs, "attempt": attempt.number})
    return store.finish(
        attempt.ticket_id,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("differs",),
        qualification=Qualification(implementation="implemented"),
    )


def make_store(root: Path, cp1: Module) -> Execution:
    store = Execution.create(root / "store", PACK)
    for module_id in UPSTREAM:
        _settle(store, module_id, cp1 if module_id == "CP-1" else None)
    return store


def make_upstream(root: Path, case: str = "positive") -> tuple[Execution, Attempt]:
    store = make_store(root, cp1_module(tm._operands(case)))
    return store, store.begin("CP-2D")


def _literal(case: str) -> str:
    return json.dumps(tm._bind(tm.SUBMISSIONS["cp2d"][case]))


@pytest.fixture
def upstream(tmp_path: Path) -> tuple[Execution, Attempt]:
    return make_upstream(tmp_path)


# --- plug-in parts ----------------------------------------------------------------------------


def test_plug_in_parts_are_the_g1x_protocol_surface() -> None:
    assert cp2d.STEP_ID == "liquidity_bridge" and cp2d.STEP_IDS == ("liquidity_bridge",)
    assert isinstance(cp2d.STEP_IDS, tuple)
    assert dict(cp2d.SCHEMAS) == {"liquidity_bridge": cp2d.LiquidityBridgeSubmission}
    assert cp2d.QUALIFICATION == Qualification(implementation="implemented")
    for name in ("probe", "view", "submit", "cp2d_reader", "ENTRY_VALIDATOR", "cp2d_upstream"):
        assert callable(getattr(cp2d, name)), name


def test_fact_bindings_are_the_manifest_bindings() -> None:
    manifest = tm.MANIFEST["fact_bindings"]
    assert list(cp2d.BINDING_NAMES) == list(manifest)
    for name, want in manifest.items():
        if name.startswith("T4.18 "):
            assert name.removeprefix("T4.18 ") in cp2d.FACILITY_FIELDS
            assert (want["table_id"], want["period"]) == ("T4.18", cp2d.SCHEDULE_PERIOD), name
            continue
        got = cp2d.FACT_BINDINGS[name]
        assert (got.table_id, got.period, got.label) == (
            want["table_id"],
            want["period"],
            want["label"],
        ), name


def test_schema_round_trips_and_gives_the_tail_digest() -> None:
    for case in tm.PACK_CASES:
        payload = _literal(case)
        submission = cp2d.SCHEMAS["liquidity_bridge"].model_validate_json(payload)
        again = cp2d.SCHEMAS["liquidity_bridge"].model_validate_json(submission.model_dump_json())
        assert again == submission and again.content_hash() == submission.content_hash()
        assert (
            submission.content_hash()
            == hashlib.sha256(submission.model_dump_json().encode()).hexdigest()
        )


# --- the store adapter ------------------------------------------------------------------------


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_adapter_returns_exactly_the_stage1_input_object(tmp_path: Path, case: str) -> None:
    store, attempt = make_upstream(tmp_path, case)
    submission = tm._submission(tm.SUBMISSIONS["cp2d"][case])
    got = cp2d._inputs(store, attempt, submission)
    assert got == tm._inputs(case)


def test_adapter_reads_each_operand_from_its_own_fact(tmp_path: Path) -> None:
    """A distinct amount planted per name lands in that name's field and no other."""
    planted = {name: Decimal(100 + i) + Decimal("0.5") for i, name in enumerate(USED, start=1)}
    operands = tm._ro(tm._base_operands(), **{n: planted[n] for n in planted})
    store = make_store(tmp_path, cp1_module(operands))
    attempt = store.begin("CP-2D")
    submission = tm._submission(tm.SUBMISSIONS["cp2d"]["positive"])
    got = cp2d._inputs(store, attempt, submission).operands
    for name in USED:
        operand = getattr(got, name)
        assert (operand.status, operand.amount) == ("known", planted[name]), name
        assert operand.period == cp2d.FACT_BINDINGS[name].period, name


def test_adapter_reads_each_facility_term_from_its_own_fact(tmp_path: Path) -> None:
    loan = replace(
        tm.LOAN,
        facility_id="a-loan",
        name="A Loan",
        principal=Decimal("11.5"),
        commitment=Decimal("12.5"),
        drawn_amount=Decimal("13.5"),
        annual_amortisation=Decimal("14.5"),
        maturity_date=date(2031, 3, 31),
    )
    operands = replace(tm._base_operands(), facilities=(loan,))
    store = make_store(tmp_path, cp1_module(operands, ids="row"))
    attempt = store.begin("CP-2D")
    submission = tm._submission(tm.SUBMISSIONS["cp2d"]["positive"])
    inputs = cp2d._inputs(store, attempt, submission)
    assert inputs.operands.facilities == (loan,)
    assert inputs.maturity_date_refs == frozenset({"cp1:a-loan-q4-2025:maturity_date"})


@pytest.mark.parametrize("status", ["missing", "conflicting", "not_applicable"])
def test_adapter_keeps_a_non_known_operand_as_its_status_never_zero(
    tmp_path: Path, status: cp2d.OperandStatus
) -> None:
    operands = tm._ro(
        tm._base_operands(),
        cfo=cp2d.Operand(status, None, None, "CP-1 limitation text"),
        rcf_commitment=cp2d.Operand(status, None, None, "RCF limitation"),
    )
    store = make_store(tmp_path, cp1_module(operands))
    attempt = store.begin("CP-2D")
    submission = tm._submission(tm.SUBMISSIONS["cp2d"]["positive"])
    got = cp2d._inputs(store, attempt, submission).operands
    assert got.cfo == cp2d.Operand(status, None, None, "CP-1 limitation text")
    assert got.rcf_commitment == cp2d.Operand(status, None, None, "RCF limitation")
    assert got.cfo is not None and got.cfo.amount is None


def _without(module: Module, predicate: Callable[[Fact], bool]) -> Module:
    return module.model_copy(update={"facts": tuple(f for f in module.facts if not predicate(f))})


def test_adapter_refuses_zero_or_several_facts_for_a_name(tmp_path: Path) -> None:
    good = cp1_module(tm._base_operands())
    gone = _without(good, lambda f: f.fact_id == "cp1:cfo")
    twice = good.model_copy(
        update={
            "facts": (
                *good.facts,
                next(f for f in good.facts if f.fact_id == "cp1:cfo").model_copy(
                    update={"fact_id": "cp1:cfo-again"}
                ),
            )
        }
    )
    for bad, match in ((gone, "0 facts"), (twice, "2 facts")):
        selection = bad
        with pytest.raises(ValueError, match=f"CP-2D: CP-1 offers {match} for cfo"):
            cp2d.select_cp1(selection)


def test_adapter_refuses_a_fact_that_is_not_us_dollar_millions() -> None:
    good = cp1_module(tm._base_operands())
    for update in ({"scale": Decimal(1)}, {"currency": "EUR"}):
        facts = tuple(
            f.model_copy(update=update) if f.fact_id == "cp1:cash_bs" else f for f in good.facts
        )
        with pytest.raises(ValueError, match="cash_bs is not in US dollars millions"):
            cp2d.select_cp1(good.model_copy(update={"facts": facts}))


def test_adapter_schedule_absent_is_none_and_no_facility_is_empty() -> None:
    good = cp1_module(tm._base_operands())
    no_t418 = _without(good, lambda f: f.table_id == "T4.18")
    assert cp2d.select_cp1(no_t418).operands.facilities is None
    no_rows = _without(good, lambda f: f.table_id == "T4.18" and f.period == "q4-2025")
    no_rows = _without(no_rows, lambda f: f.table_id == "T4.18")
    other = good.model_copy(
        update={
            "facts": (
                *no_rows.facts,
                *_row_facts("old-row", "q3-2025", {"facility_id": "old"}, "row"),
            )
        }
    )
    assert cp2d.select_cp1(other).operands.facilities == ()


def test_adapter_refuses_a_facility_alias_that_disagrees() -> None:
    good = cp1_module(tm._base_operands())
    facts = tuple(
        f.model_copy(update={"amount": Decimal(49)})
        if f.table_id == "T4.18" and f.period == "fy-2025" and f.field == "principal"
        else f
        for f in good.facts
    )
    with pytest.raises(ValueError, match="alias"):
        cp2d.select_cp1(good.model_copy(update={"facts": facts}))


def test_adapter_balance_date_is_the_schedule_period_end() -> None:
    assert cp2d.select_cp1(cp1_module(tm._base_operands())).balance_date == date(2025, 12, 31)


# --- validation -------------------------------------------------------------------------------


def _upstream_of(store: Execution, attempt: Attempt) -> cp2d.Upstream:
    return cp2d.cp2d_upstream(store=store, attempt=attempt)


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_validate_accepts_the_oracle_literals(tmp_path: Path, case: str) -> None:
    store, attempt = make_upstream(tmp_path, case)
    submission = cp2d.LiquidityBridgeSubmission.model_validate_json(_literal(case))
    issues = cp2d.validate_liquidity_bridge(
        submission=submission, upstream=_upstream_of(store, attempt)
    )
    assert issues == ()


@pytest.mark.parametrize("name", list(tm.EXPECTED["refusals"]))
def test_validate_reproduces_the_oracle_refusals(
    upstream: tuple[Execution, Attempt], name: str
) -> None:
    store, attempt = upstream
    entry = tm.SUBMISSIONS["refusal_inputs"][name]
    submission = cp2d.LiquidityBridgeSubmission.model_validate_json(
        json.dumps(tm._bind(entry["payload"]))
    )
    issues = cp2d.validate_liquidity_bridge(
        submission=submission, upstream=_upstream_of(store, attempt)
    )
    assert issues == (tm.EXPECTED["refusals"][name],)


def test_validate_reports_a_stale_input_set(tmp_path: Path) -> None:
    store, attempt = make_upstream(tmp_path)
    good = _upstream_of(store, attempt)
    submission = cp2d.LiquidityBridgeSubmission.model_validate_json(_literal("positive"))
    refused = "Required upstream is unrun, stale or blocked"
    issues = cp2d.validate_liquidity_bridge(
        submission=submission, upstream=replace(good, current=refused)
    )
    assert issues == (f"Stale inputs: {refused}",)
    moved = tuple(
        i.model_copy(update={"sha256": "0" * 64}) if i.input_id == "CP-2" else i for i in good.bound
    )
    issues = cp2d.validate_liquidity_bridge(
        submission=submission, upstream=replace(good, current=moved)
    )
    assert len(issues) == 1 and issues[0].startswith("Stale input CP-2: bound ")
    assert cp2d.validate_liquidity_bridge(submission=submission, upstream=good) == ()


def test_validate_refuses_a_cp1_that_is_not_the_bound_input(tmp_path: Path) -> None:
    store, attempt = make_upstream(tmp_path)
    good = _upstream_of(store, attempt)
    other = good.cp1.model_copy(update={"limitations": ("another",)})
    forged = replace(good, cp1=other)
    submission = cp2d.LiquidityBridgeSubmission.model_validate_json(_literal("positive"))
    issues = cp2d.validate_liquidity_bridge(submission=submission, upstream=forged)
    assert "Upstream CP-1: the supplied module is not the bound input" in issues


# --- the composed module ----------------------------------------------------------------------


def _report(store: Execution, attempt: Attempt, case: str) -> cp2d.LiquidityBridgeReport:
    submission = cp2d.LiquidityBridgeSubmission.model_validate_json(_literal(case))
    return cp2d.liquidity_bridge(
        pack=store.pack(), submission=submission, upstream=_upstream_of(store, attempt)
    )


def _module(store: Execution, attempt: Attempt, case: str) -> Module:
    report = _report(store, attempt, case)
    return cp2d.cp2d_module(report=report, inputs=attempt.inputs, attempt=attempt.number)


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_module_tables_facts_claims_and_limitations_equal_the_oracle(
    tmp_path: Path, case: str
) -> None:
    store, attempt = make_upstream(tmp_path, case)
    module = _module(store, attempt, case)
    want = tm.CASES[case]
    assert module.module_id == "CP-2D" and module.status == "candidate"
    assert [t.table_id for t in module.tables] == tm.EXPECTED["cp2d_module"]["table_ids"]
    assert prose_issues(module, names=(store.read().run.issuer_name,)) == ()
    facts = {f.fact_id: f for f in module.facts}
    assert len(facts) == len(module.facts)
    for table_id, table in want["tables"].items():
        got = next(t for t in module.tables if t.table_id == table_id)
        assert got.title == table["title"] and got.row_header == table["row_header"]
        assert [c.label for c in got.columns] == table["columns"]
        assert [r.label for r in got.rows] == [r[0] for r in table["rows"]]
        for row, (_, cells) in zip(got.rows, table["rows"], strict=True):
            for fact_id, cell in zip(
                row.fact_ids, cells if isinstance(cells, list) else [cells], strict=True
            ):
                assert fact_id == cell["fact_id"]
                _assert_fact(facts[fact_id], cell, case)
    assert list(module.limitations) == want["own_limitations"]
    assert [c.claim_id for c in module.claims] == [c["claim_id"] for c in want["claims"]]
    assert [c.text for c in module.claims] == [c["template"] for c in want["claims"]]
    assert module.inputs[-1] == cp2d_tail(store, attempt, case)
    assert module.inputs[:-1] == attempt.inputs


def cp2d_tail(store: Execution, attempt: Attempt, case: str) -> Any:
    from deploy_vii.contracts import Input

    submission = cp2d.LiquidityBridgeSubmission.model_validate_json(_literal(case))
    return Input(input_id="liquidity-bridge-submission", sha256=submission.content_hash())


_STATUS = {
    "known": "known",
    "gap": "missing",
    "conflicting": "conflicting",
    "not_applicable": "not_applicable",
}


def _assert_fact(fact: Fact, cell: dict[str, Any], case: str) -> None:
    where = cell["fact_id"]
    assert fact.status == _STATUS[cell["state"]], where
    assert fact.value_class == cell.get("value_class", tm.GAP_VALUE_CLASS_DELTA.get((case, where)))
    if cell["state"] != "known":
        assert fact.amount is None and fact.text is None and fact.limitation == cell["reason"]
        return
    if cell.get("amount") is not None:
        assert tm._num_equal(fact.amount, cell["amount"]), where
        assert fact.unit == cell["unit"] and fact.period, where
    else:
        assert fact.text == cell["shown"] and fact.amount is None, where
    copy = cell.get("cp1_operand") is not None and cell["cp1_operand"] not in cp2d.RECOMPUTED_TAGS
    if copy and "+" not in cell["cp1_operand"]:
        assert fact.citations and fact.calculation_id is None, where
    elif cell.get("value_class") != "analyst_judgment":
        assert fact.calculation_id and fact.formula, where


def test_module_computed_cells_carry_a_calculation_and_a_formula(tmp_path: Path) -> None:
    store, attempt = make_upstream(tmp_path)
    module = _module(store, attempt, "positive")
    by_id = {f.fact_id: f for f in module.facts}
    assert by_id["T2E.3.r08"].formula and by_id["T2E.3.r08"].calculation_id == "calc:T2E.3.r08"
    assert by_id["T2E.2.r01"].calculation_id is None  # a copy keeps its CP-1 citations
    assert by_id["T2E.2.r01"].citations == (CITATION,)
    assert by_id["T2E.1.r05"].citations and by_id["T2E.1.r05"].formula  # a sum copy: both
    assert by_id["T2E.3.r03"].value_class == "analyst_judgment" and not by_id["T2E.3.r03"].citations
    assert by_id["T2E.4.r01.c1"].citations  # the facility principal is a copy of the T4.18 fact


def test_module_scale_unit_currency_of_each_cell_class(tmp_path: Path) -> None:
    store, attempt = make_upstream(tmp_path)
    by_id = {f.fact_id: f for f in _module(store, attempt, "positive").facts}
    money = by_id["T2E.2.r07"]
    assert (money.unit, money.currency, money.scale) == ("MILLIONS", "USD", Decimal(1000000))
    ratio = by_id["T2E.2.r09"]
    assert (ratio.unit, ratio.currency, ratio.scale) == ("PERCENT", None, Decimal(1))
    months = by_id["T2E.3.r03"]
    assert (months.unit, months.amount, months.period) == ("months", Decimal(24), BALANCE)


def test_module_gap_facts_have_no_value_and_a_limitation(tmp_path: Path) -> None:
    store, attempt = make_upstream(tmp_path, "gap_minimum_cash")
    by_id = {f.fact_id: f for f in _module(store, attempt, "gap_minimum_cash").facts}
    gap = by_id["T2E.5.r07"]
    assert (gap.status, gap.amount, gap.limitation) == (
        "missing",
        None,
        "Not calculable: minimum cash not assessed",
    )


def test_module_trace_lists_every_offered_cp1_fact(tmp_path: Path) -> None:
    store, attempt = make_upstream(tmp_path)
    module = _module(store, attempt, "positive")
    table = next(t for t in module.tables if t.table_id == "T2E.9")
    assert [c.field for c in table.columns] == ["ref", "table", "period", "shown"]
    assert len(table.rows) == len(cp2d.BINDING_NAMES)
    by_id = {f.fact_id: f for f in module.facts}
    fcf = next(r for r in table.rows if r.label == "fcf_unlevered")
    assert by_id[fcf.fact_ids[0]].text == "cp1:fcf_unlevered"
    assert by_id[fcf.fact_ids[3]].text == "missing"  # a gap word, never a number
    cfo = next(r for r in table.rows if r.label == "cfo")
    assert by_id[cfo.fact_ids[3]].text == "19 US$"  # the product spelling of a CP-1 fact


def test_module_status_ledger_rows_follow_the_oracle(tmp_path: Path) -> None:
    store, attempt = make_upstream(tmp_path)
    module = _module(store, attempt, "positive")
    ledgers = {t.table_id: t for t in module.tables}
    by_id = {f.fact_id: f for f in module.facts}
    for table_id, key in (("T2E.6", "T2E.6_rows"), ("T2E.7", "T2E.7_rows")):
        rows = ledgers[table_id].rows
        want = tm.CASES["positive"][key]
        assert [r.label for r in rows] == [w[0] for w in want]
        assert [by_id[r.fact_ids[0]].text for r in rows] == [w[1] for w in want]


def test_report_refuses_what_validation_refuses(upstream: tuple[Execution, Attempt]) -> None:
    store, attempt = upstream
    entry = tm.SUBMISSIONS["refusal_inputs"]["horizon_zero"]["payload"]
    submission = cp2d.LiquidityBridgeSubmission.model_validate_json(json.dumps(tm._bind(entry)))
    with pytest.raises(ValueError, match="horizon_months must be between 1 and 60"):
        cp2d.liquidity_bridge(
            pack=store.pack(), submission=submission, upstream=_upstream_of(store, attempt)
        )


# --- the read view ----------------------------------------------------------------------------

FORBIDDEN_KEYS = set(tm.MANIFEST["view_tree_draft"]["forbidden_keys"])


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def test_view_body_matches_the_frozen_tree_draft(upstream: tuple[Execution, Attempt]) -> None:
    store, attempt = upstream
    digest, body = cp2d.view(store, attempt)
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    document = json.loads(body)
    tree = tm.MANIFEST["view_tree_draft"]
    assert list(document) == tree["top_level_keys_in_order"]
    assert not FORBIDDEN_KEYS & _keys(document)
    assert QUOTE not in body and "Cash and cash equivalents  15" not in body
    assert document["bounds"] == {
        "horizon_months": [1, 60],
        "minimum_cash": "decimal >= 0 in US$ m, or null with minimum_cash_absence",
    }
    assert [u["module_id"] for u in document["upstream"]] == ["CP-0", "CP-1", "CP-2"]
    assert {u["status"] for u in document["upstream"]} == {"restricted"}
    entries = document["cp1_facts"]
    assert all(
        list(e) == ["ref", "name", "label", "period", "unit", "shown", "status", "limitation"]
        for e in entries
    )
    assert [e["name"] for e in entries] == sorted(e["name"] for e in entries)
    assert {e["name"] for e in entries} == set(cp2d.BINDING_NAMES)


def test_view_offers_a_missing_fact_with_its_status_and_a_gap_word(
    upstream: tuple[Execution, Attempt],
) -> None:
    store, attempt = upstream
    entries = {e["name"]: e for e in json.loads(cp2d.view(store, attempt)[1])["cp1_facts"]}
    fcf = entries["fcf_unlevered"]
    assert (fcf["status"], fcf["limitation"]) == ("missing", "Free cash flow is not derived")
    assert fcf["shown"] == "missing" and fcf["ref"] == "cp1:fcf_unlevered"
    cfo = entries["cfo"]
    assert (cfo["status"], cfo["limitation"], cfo["shown"]) == ("known", None, "19 US$")
    assert cfo["period"] == cp2d.FACT_BINDINGS["cfo"].period and cfo["unit"] == "US$"


def test_view_inherits_the_limitations_settlement_will_carry(
    upstream: tuple[Execution, Attempt],
) -> None:
    store, attempt = upstream
    document = json.loads(cp2d.view(store, attempt)[1])
    from deploy_vii.execution import inherited_limitations

    want = inherited_limitations(store.read(), attempt, (), store.head_module)
    assert document["inherited_limitations"] == list(want) and len(want) >= 3


def test_view_is_deterministic_over_a_frozen_view(upstream: tuple[Execution, Attempt]) -> None:
    store, attempt = upstream
    frozen = _FrozenExecution(store, store.read())
    assert cp2d.view(frozen, attempt) == cp2d.view(store, attempt)


# --- the journal: submit, probe, settle -------------------------------------------------------


def _submit(store: Execution, attempt: Attempt, payload: str) -> Any:
    return cp2d.submit(store, attempt.ticket_id, "liquidity_bridge", payload, None)


def _finished(store: Execution, ticket: str) -> Attempt:
    return next(a for a in store.read().attempts if a.ticket_id == ticket)


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_submit_settles_a_restricted_head_that_probe_accepts(tmp_path: Path, case: str) -> None:
    store, attempt = make_upstream(tmp_path, case)
    payload = _literal(case)
    done = _submit(store, attempt, payload)
    assert done.payload == payload and done.nulls_resolved == () and done.prefilled == ()
    assert done.journal.status == "finished" and not done.journal.issues
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == "CP-2D")
    assert head.status == "restricted" and head.qualification == cp2d.QUALIFICATION
    module = store.head_module(head)
    submission = cp2d.LiquidityBridgeSubmission.model_validate_json(payload)
    assert module.inputs[-1].input_id == "liquidity-bridge-submission"
    assert module.inputs[-1].sha256 == submission.content_hash()
    assert head == head_of(module, cp2d.QUALIFICATION)
    finished = _finished(store, attempt.ticket_id)
    cp2d.probe(store, snapshot, finished)  # raises WorkflowError unless the head rebuilds
    assert list(module.limitations)[:1] == tm.CASES[case]["own_limitations"][:1]


def test_probe_refuses_a_head_that_does_not_rebuild(tmp_path: Path) -> None:
    store, attempt = make_upstream(tmp_path)
    _submit(store, attempt, _literal("positive"))
    snapshot = store.read()
    finished = _finished(store, attempt.ticket_id)
    from deploy_workflow.workflow import WorkflowError

    # a different retained step output: the recomputation no longer equals what the step kept
    forged = finished.model_copy(
        update={"steps": (finished.steps[0].model_copy(update={"output_sha256": "0" * 64}),)}
    )
    with pytest.raises((WorkflowError, ValueError)):
        cp2d.probe(store, snapshot, forged)
    with pytest.raises(WorkflowError):
        cp2d.probe(store, snapshot, finished.model_copy(update={"steps": ()}))


def test_entry_validator_is_the_step_validator(upstream: tuple[Execution, Attempt]) -> None:
    store, attempt = upstream
    step = store.submit_step(
        attempt.ticket_id,
        "CP-2D",
        cp2d.STEP_IDS,
        "liquidity_bridge",
        _literal("positive"),
        lambda pack, current: cp2d.ENTRY_VALIDATOR(store, pack, current),
    )
    assert step.steps[0].status == "valid" and step.steps[0].output_sha256 is not None
    report = cp2d.LiquidityBridgeReport.model_validate_json(
        store.step_output(step.steps[0].output_sha256)
    )
    assert (
        report.submission_sha256
        == cp2d.LiquidityBridgeSubmission.model_validate_json(_literal("positive")).content_hash()
    )


def test_submit_blocks_after_two_invalid_attempts_and_the_head_has_no_figures(
    upstream: tuple[Execution, Attempt],
) -> None:
    store, attempt = upstream
    blocked = tm.SUBMISSIONS["cp2d_blocked"]
    first = _submit(store, attempt, json.dumps(tm._bind(blocked["attempt_0"])))
    assert first.journal.status == "finished" and first.journal.number == 0
    assert (
        list(first.journal.steps[0].issues)
        == (tm.EXPECTED["negative_cases"]["blocked_cp2d"]["attempt_0"]["issues"])
    )
    assert not any(h.module_id == "CP-2D" for h in store.read().heads)
    again = store.begin("CP-2D")
    assert again.number == 1 and again.repair_of == attempt.ticket_id
    second = _submit(store, again, json.dumps(tm._bind(blocked["attempt_1"])))
    assert second.journal.number == 1
    head = next(h for h in store.read().heads if h.module_id == "CP-2D")
    assert head.status == "blocked" and head.qualification is None
    module = store.head_module(head)
    assert not module.facts and not module.tables and not module.claims
    read = cp2d.cp2d_reader(store, head)
    assert read.status == "blocked" and read.head_sha256 == head.result_sha256
    assert (read.horizon_months, read.minimum_cash, read.funding_gap, read.wall) == (
        None,
        None,
        None,
        (),
    )


def test_submit_refuses_rules_a_wrong_step_and_a_different_retained_response(
    upstream: tuple[Execution, Attempt],
) -> None:
    store, attempt = upstream
    payload = _literal("positive")
    with pytest.raises(ValueError, match="no tool-loop rules"):
        cp2d.submit(store, attempt.ticket_id, "liquidity_bridge", payload, lambda text: ())
    with pytest.raises(ValueError, match="CP-2D has one step"):
        cp2d.submit(store, attempt.ticket_id, "other_step", payload, None)
    assert _finished(store, attempt.ticket_id).steps == ()  # nothing was journaled


def test_submit_normalises_nulls_through_the_schema(upstream: tuple[Execution, Attempt]) -> None:
    store, attempt = upstream
    document = json.loads(_literal("positive"))
    document["assessments"][0]["limitation"] = None
    done = _submit(store, attempt, json.dumps(document))
    assert done.journal.status == "finished" and done.nulls_resolved == ()


# --- the reader -------------------------------------------------------------------------------


def _head(store: Execution) -> Any:
    return next(h for h in store.read().heads if h.module_id == "CP-2D")


def test_reader_exposes_what_the_lease_pins(tmp_path: Path) -> None:
    store, attempt = make_upstream(tmp_path)
    _submit(store, attempt, _literal("positive"))
    head = _head(store)
    read = cp2d.cp2d_reader(store, head)
    assert (read.status, read.head_sha256) == ("restricted", head.result_sha256)
    assert read.horizon_months == 24
    assert (read.minimum_cash, read.minimum_cash_absent) == (Decimal(10), None)
    assert read.funding_gap == Decimal(0) and read.funding_gap is not None  # a known zero
    assert read.funding_gap_missing is None
    assert read.wall == (
        cp2d.WallRead(
            facility="Northbridge Term Loan (term-loan)",
            principal=Decimal(50),
            maturity_date=date(2029, 12, 31),
            months_to_maturity=Decimal(48),
            inside_horizon=False,
            share_of_total_debt=Decimal(1),
            cumulative_share=Decimal(1),
        ),
    )


def test_reader_exposes_a_missing_gap_and_the_absence(tmp_path: Path) -> None:
    store, attempt = make_upstream(tmp_path, "gap_minimum_cash")
    _submit(store, attempt, _literal("gap_minimum_cash"))
    read = cp2d.cp2d_reader(store, _head(store))
    assert read.minimum_cash is None and read.minimum_cash_absent == "Minimum cash not assessed"
    assert read.funding_gap is None
    assert read.funding_gap_missing == "Not calculable: minimum cash not assessed"


def test_reader_refuses_another_modules_head(upstream: tuple[Execution, Attempt]) -> None:
    store, _ = upstream
    cp1 = next(h for h in store.read().heads if h.module_id == "CP-1")
    with pytest.raises(ValueError, match="not a CP-2D head"):
        cp2d.cp2d_reader(store, cp1)


# --- registrations (lease Files; protocol section 2) -------------------------------------------


def test_registration_rows_equal_the_lease() -> None:
    assert owner._CORES["CP-2D"] is cp2d
    assert "CP-2D" in owner.SUPPORTED_ANALYTICAL
    assert owner._QUALIFICATION["CP-2D"] == cp2d.QUALIFICATION
    assert owner._PROBES["CP-2D"] is cp2d.probe
    assert owner._VIEWS["liquidity_bridge"] is cp2d.view
    assert owner._ENTRY_VALIDATORS["CP-2D"] is cp2d.ENTRY_VALIDATOR
    assert "CP-2D" not in owner._PRECHECKS  # no precheck: failures journal as invalid steps
    spec = owner.OWNER_SPECS["CP-2D"]
    assert (spec.module_id, spec.entry, spec.kind, spec.publish) == (
        "CP-2D",
        "owner_core",
        "analytical",
        None,
    )
    (step,) = spec.steps
    assert (step.step_id, step.schema, step.sources, step.extract) == (
        "liquidity_bridge",
        cp2d.LiquidityBridgeSubmission,
        False,
        False,
    )
    assert (step.upstream_grant, step.inputs, step.rules) == (None, "module_context", "none")
    owner._check_steps("CP-2D", spec)
    with pytest.raises(ValueError, match="no live step contract"):
        step_chain("CP-2D")


def test_registrations_are_appended_after_the_shipped_rows() -> None:
    assert list(owner.OWNER_SPECS)[:5] == ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL"]
    assert list(owner.OWNER_SPECS).index("CP-2D") >= 5
    assert list(owner._PROBES)[:4] == ["CP-0", "CP-1", "CP-1A", "CP-2"]
    assert list(owner._ENTRY_VALIDATORS)[:2] == ["CP-1A", "CP-2"]
    assert next(iter(owner._VIEWS)) == "credit_synthesis"


# --- bindings and _Spec rows (lease Rendered sections) ------------------------------------------


def test_bindings_follow_the_lease() -> None:
    from deploy_vii.bindings.cp2d import CP2D
    from deploy_vii.bindings.shipped import SHIPPED_MAPS

    ids = [m.module_id for m in SHIPPED_MAPS]
    assert ids.index("CP-2D") == ids.index("CP-2") + 1
    got = {(e.fact_coord.table_id, e.block_id, e.label) for e in CP2D.entries}
    assert got == {
        ("T2E.3", "liquidity-runway", "Cash runway"),
        ("T2E.1", "liquidity-runway", "Sources and uses"),
        ("T2E.4", "maturity-wall", "Maturity wall"),
        ("T2E.5", "funding-gap", "Funding gap"),
        ("T2E.2", "funding-gap", "Liquidity position"),
        ("T2E.6", "evidence", "Analyst judgments"),
        ("T2E.9", "evidence", "CP-1 source trace"),
        ("T2E.7", "limitations", "Gaps ledger"),
    }
    assert all(e.cell_slot.startswith("cp2d-") for e in CP2D.entries)
    assert len({e.slot for e in CP2D.entries}) == len(CP2D.entries)
    assert next(e for e in CP2D.entries if e.fact_coord.table_id == "T2E.3").slot == (
        "liquidity-runway",
        "cp2d-t2e-3",
    )


def test_validate_bindings_over_the_settled_tables_is_clean(tmp_path: Path) -> None:
    from deploy_vii.bindings import validate_bindings
    from deploy_vii.bindings.shipped import SHIPPED_MAPS

    store, attempt = make_upstream(tmp_path)
    _submit(store, attempt, _literal("positive"))
    view = store.view()
    only = view.model_copy(
        update={"modules": tuple(m for m in view.modules if m.module_id == "CP-2D")}
    )
    assert only.modules[0].facts
    assert validate_bindings(only, SHIPPED_MAPS) == ()


def test_spec_rows_serve_the_three_blocks() -> None:
    from deploy_vii.report_view import _spec_of

    for block, title in (
        ("liquidity-runway", "Liquidity and cash runway"),
        ("maturity-wall", "Maturity wall"),
        ("funding-gap", "Funding gap"),
    ):
        spec = _spec_of(block)
        assert (spec.title, spec.owner, spec.kind, spec.producers, spec.route_label) == (
            title,
            "CP-2D",
            "dense",
            ("CP-2D",),
            "Full analysis",
        )


# --- the run driver (its runs are deferred; its assembly is cheap) -----------------------------


def test_run_driver_assembles_the_oracle_run() -> None:
    drive: Any = importlib.import_module("cp2d_runs")
    oracle = drive.oracle()
    pack = drive.make_pack()
    assert pack.run.run_id == "slice-cp2d-positive"
    assert pack.run.pathway == "covenant_refinancing"
    assert list(pack.run.requested_modules) == oracle["manifest"]["run"]["requested_modules"]
    consumers = json.loads(drive.cp0_text(pack))["consumers"]
    assert consumers[-1]["module_id"] == "CP-2D" and len(consumers) >= 2
    assert drive.CASES == tm.PACK_CASES


@pytest.mark.parametrize("currency", ["EUR", None])
def test_adapter_reads_the_facility_currency_as_stated_or_not_stated(
    tmp_path: Path, currency: str | None
) -> None:
    loan = replace(tm.LOAN, currency=currency)
    operands = replace(tm._base_operands(), facilities=(loan,))
    store = make_store(tmp_path, cp1_module(operands))
    attempt = store.begin("CP-2D")
    submission = tm._submission(tm.SUBMISSIONS["cp2d"]["positive"])
    got = cp2d._inputs(store, attempt, submission).operands.facilities
    assert got == (loan,) and got[0].currency == currency


# --- fix round 1: M1 (a facility in another currency), M2 (the alias both ways), M4 -----------


def _facts_of(module: Module, table: str, **where: str) -> list[Fact]:
    return [
        f
        for f in module.facts
        if f.table_id == table and all(getattr(f, k) == v for k, v in where.items())
    ]


def _swap_facts(module: Module, change: Callable[[Fact], Fact | None]) -> Module:
    facts = [x for f in module.facts if (x := change(f)) is not None]
    return module.model_copy(update={"facts": tuple(facts)})


def test_a_facility_in_another_currency_takes_the_lease_fx_path() -> None:
    """Lease Reuse (Facility FX) and ruling A5: CP-1 writes the money terms in the row's own
    currency; the row and every total are then missing with the limitation, not a refusal."""
    loan = replace(tm.LOAN, currency="EUR")
    operands = replace(tm._base_operands(), facilities=(loan,))
    selection = cp2d.select_cp1(cp1_module(operands))
    assert selection.operands.facilities == (loan,)
    submission = tm._submission(tm.SUBMISSIONS["cp2d"]["positive"])
    result = cp2d.compute(
        cp2d.Cp2dInputs(
            operands=selection.operands,
            balance_date=selection.balance_date,
            submission=submission,
            offered_refs=tm.OFFERED,
            maturity_date_refs=tm.MATURITY_REFS,
        )
    )
    cells = tm._cells(result)
    reason = "Not calculable: facility term-loan is in EUR, not USD; no FX conversion is applied"
    assert (cells["T2E.4.r01.c1"].state, cells["T2E.4.r01.c1"].reason) == ("gap", reason)
    assert cells["T2E.3.r07"].state == "gap" and cells["T2E.5.r07"].state == "gap"


def test_a_facility_money_fact_must_agree_with_the_rows_stated_currency() -> None:
    good = cp1_module(replace(tm._base_operands(), facilities=(replace(tm.LOAN, currency="EUR"),)))
    forged = _swap_facts(
        good,
        lambda f: (
            f.model_copy(update={"currency": "USD"})
            if f.table_id == "T4.18" and f.field == "principal"
            else f
        ),
    )
    with pytest.raises(ValueError, match="principal is not in the facility's stated currency"):
        cp2d.select_cp1(forged)


def test_a_facility_money_fact_must_be_in_millions() -> None:
    good = cp1_module(tm._base_operands())
    forged = _swap_facts(
        good,
        lambda f: (
            f.model_copy(update={"scale": Decimal(1)})
            if f.table_id == "T4.18" and f.field == "commitment"
            else f
        ),
    )
    with pytest.raises(ValueError, match="T4.18 commitment is not in millions"):
        cp2d.select_cp1(forged)


def _alias_only_facility() -> Module:
    good = cp1_module(tm._base_operands())
    extra = [
        f.model_copy(
            update={
                "fact_id": f.fact_id + "-b",
                "row_id": f.row_id + "-b",
                **({"text": "bridge-loan"} if f.field == "facility_id" else {}),
            }
        )
        for f in _facts_of(good, "T4.18", period="fy-2025")
    ]
    return good.model_copy(update={"facts": (*good.facts, *extra)})


def test_alias_check_runs_both_ways() -> None:
    with pytest.raises(ValueError, match="bridge-loan has a fy-2025 row but no q4-2025 row"):
        cp2d.select_cp1(_alias_only_facility())


def test_alias_check_refuses_a_facility_without_its_alias_row() -> None:
    good = cp1_module(tm._base_operands())
    forged = _swap_facts(
        good, lambda f: None if f.table_id == "T4.18" and f.period == "fy-2025" else f
    )
    with pytest.raises(ValueError, match="term-loan lacks its fy-2025 alias row"):
        cp2d.select_cp1(forged)


def test_alias_check_compares_a_term_present_in_only_one_row() -> None:
    good = cp1_module(tm._base_operands())
    forged = _swap_facts(
        good,
        lambda f: (
            None
            if f.table_id == "T4.18" and f.period == "fy-2025" and f.field == "annual_amortisation"
            else f
        ),
    )
    # annual_amortisation is a required term for the facility itself; the alias lacks it
    with pytest.raises(ValueError, match="annual_amortisation differs between"):
        cp2d.select_cp1(forged)


def test_alias_check_compares_the_basis() -> None:
    good = cp1_module(tm._base_operands())
    forged = _swap_facts(
        good,
        lambda f: (
            f.model_copy(update={"basis": "IFRS · borrower"})
            if f.table_id == "T4.18" and f.period == "fy-2025" and f.field == "principal"
            else f
        ),
    )
    with pytest.raises(ValueError, match="principal differs between"):
        cp2d.select_cp1(forged)


def test_adapter_refuses_two_rows_of_a_facility_in_one_period() -> None:
    good = cp1_module(tm._base_operands())
    twin = [
        f.model_copy(update={"fact_id": f.fact_id + "-twin", "row_id": f.row_id + "-twin"})
        for f in _facts_of(good, "T4.18", period="q4-2025")
    ]
    with pytest.raises(ValueError, match="term-loan has two T4.18 rows in q4-2025"):
        cp2d.select_cp1(good.model_copy(update={"facts": (*good.facts, *twin)}))


def test_adapter_refuses_a_duplicate_coordinate() -> None:
    good = cp1_module(tm._base_operands())
    first = _facts_of(good, "T4.18", period="q4-2025", field="principal")[0]
    dup = first.model_copy(update={"fact_id": first.fact_id + "-dup"})
    with pytest.raises(ValueError, match="duplicate CP-1 coordinate T4.18/"):
        cp2d.select_cp1(good.model_copy(update={"facts": (*good.facts, dup)}))


def test_adapter_refuses_a_known_numeric_fact_that_has_no_amount() -> None:
    good = cp1_module(tm._base_operands())
    forged = _swap_facts(
        good,
        lambda f: (
            f.model_copy(update={"amount": None, "text": "19"}) if f.fact_id == "cp1:cfo" else f
        ),
    )
    with pytest.raises(ValueError, match="cfo is known without an amount and a period"):
        cp2d.select_cp1(forged)


@pytest.mark.parametrize(
    ("name", "update", "message"),
    [
        ("liquidity_to_debt", {"unit": "MULTIPLE"}, "liquidity_to_debt is not a percent fraction"),
        ("cash_bs", {"unit": "PERCENT"}, "cash_bs is not in US dollars millions"),
        ("liquidity", {"unit": "PERCENT"}, "liquidity is not in US dollars millions"),
    ],
)
def test_adapter_checks_the_unit_class_of_each_amount(
    name: str, update: dict[str, Any], message: str
) -> None:
    good = cp1_module(tm._base_operands())
    forged = _swap_facts(
        good, lambda f: f.model_copy(update=update) if f.fact_id == _stand_in(name) else f
    )
    with pytest.raises(ValueError, match=message):
        cp2d.select_cp1(forged)


@pytest.mark.parametrize("end", ["2025-12-30", "2026-03-31", "2024-02-29"])
def test_balance_date_is_the_schedule_period_end_whatever_it_is(end: str) -> None:
    got = cp2d.select_cp1(cp1_module(tm._base_operands(), end=end))
    assert got.balance_date == date.fromisoformat(end)


def test_balance_date_is_refused_when_cp1_states_none() -> None:
    good = cp1_module(tm._base_operands())
    forged = _swap_facts(good, lambda f: None if f.table_id == "T4.14" else f)
    with pytest.raises(ValueError, match="states no end date for q4-2025"):
        cp2d.select_cp1(forged)


def test_view_refuses_a_cp1_module_of_another_run(upstream: tuple[Execution, Attempt]) -> None:
    store, attempt = upstream
    other = PreparedPack(
        run=PACK.run.model_copy(update={"run_id": "another-run"}), sources=PACK.sources
    )
    with pytest.raises(ValueError, match="belongs to another run"):
        cp2d.context_block(pack=other, upstream=_upstream_of(store, attempt))


# --- the reader on varied heads ---------------------------------------------------------------


def test_reader_reads_the_long_horizon_head(tmp_path: Path) -> None:
    store, attempt = make_upstream(tmp_path, "long_horizon")
    _submit(store, attempt, _literal("long_horizon"))
    read = cp2d.cp2d_reader(store, _head(store))
    assert read.horizon_months == 60 and read.minimum_cash == Decimal(10)
    assert read.funding_gap == Decimal(40)
    (row,) = read.wall
    assert row.inside_horizon is True and row.months_to_maturity == Decimal(48)


def test_reader_exposes_status_and_hash_only_for_a_stale_head(tmp_path: Path) -> None:
    from deploy_vii.execution import staled

    store, attempt = make_upstream(tmp_path)
    _submit(store, attempt, _literal("positive"))
    stale = staled(_head(store), "Prepared pack changed; rerun required")
    read = cp2d.cp2d_reader(store, stale)
    assert (read.status, read.head_sha256) == ("stale", stale.result_sha256)
    assert (read.horizon_months, read.minimum_cash, read.minimum_cash_absent) == (None, None, None)
    assert (read.wall, read.funding_gap, read.funding_gap_missing) == ((), None, None)


def test_reader_checks_the_head_against_its_blob_before_the_status(tmp_path: Path) -> None:
    store, attempt = make_upstream(tmp_path)
    _submit(store, attempt, _literal("positive"))
    forged = _head(store).model_copy(update={"inputs": ()})
    with pytest.raises(ValueError, match="does not match its result blob"):
        cp2d.cp2d_reader(store, forged)


def _two_facility_operands() -> cp2d.Operands:
    early = replace(
        tm.LOAN,
        facility_id="a-note",
        name="A Note",
        principal=Decimal(30),
        commitment=Decimal(30),
        drawn_amount=Decimal(30),
        maturity_date=date(2027, 6, 30),
    )
    late = replace(
        tm.LOAN,
        facility_id="b-loan",
        name="B Loan",
        principal=Decimal(20),
        commitment=Decimal(20),
        drawn_amount=Decimal(20),
        maturity_date=date(2031, 3, 31),
    )
    return replace(tm._base_operands(), facilities=(late, early))


def test_reader_reads_two_facilities_in_maturity_order(tmp_path: Path) -> None:
    store = make_store(tmp_path, cp1_module(_two_facility_operands(), ids="row"))
    attempt = store.begin("CP-2D")
    payload = _literal("positive").replace(
        "cp1:T4.18_maturity_date", "cp1:a-note-q4-2025:maturity_date"
    )
    done = _submit(store, attempt, payload)
    assert not done.journal.issues, done.journal.steps[0].issues
    read = cp2d.cp2d_reader(store, _head(store))
    first, second = read.wall
    assert (first.facility, first.principal, first.maturity_date) == (
        "A Note (a-note)",
        Decimal(30),
        date(2027, 6, 30),
    )
    assert (first.months_to_maturity, first.inside_horizon) == (Decimal(18), True)
    assert (first.share_of_total_debt, first.cumulative_share) == (Decimal("0.6"), Decimal("0.6"))
    assert (second.facility, second.principal) == ("B Loan (b-loan)", Decimal(20))
    assert (second.months_to_maturity, second.inside_horizon) == (Decimal(63), False)
    assert (second.share_of_total_debt, second.cumulative_share) == (Decimal("0.4"), Decimal(1))
    # cash 20 at 24 months, less the 30 maturing inside it: resources -10, minimum cash 10 -> 20
    assert read.funding_gap == Decimal(20) and read.horizon_months == 24
