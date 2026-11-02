"""Phase 8 Task 7: CP-1B, CP-2A, CP-2E and CP-L10 take the run's period and currency.

Every expected value is read at run time from the frozen oracle
`cases/periods-currency-owner/expected.json` (`module_oracles/*`, `runs/*`, `period_basis/*`);
nothing here copies one.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from deploy_vii import report_view
from deploy_vii.contracts import Fact, Module, ModuleView, Run, Source, Span
from deploy_vii.execution import Attempt, Execution, StepSubmission
from deploy_vii.preparation import PreparedPack
from deploy_workflow import earnings_workflow as ew
from deploy_workflow.earnings import EarningsDeltaReport, build_earnings_delta_in
from deploy_workflow.owners import cp1b, cp2a, cp2e, cpl10, period_basis

ROOT = Path(__file__).parents[1]
KEY: dict[str, Any] = json.loads((ROOT / "cases/periods-currency-owner/expected.json").read_text())


# --- the T4.14 reader (P8-P17) ----------------------------------------------------------------


def test_cpl10_reads_the_register_with_the_period_basis_reader() -> None:
    assert cpl10._period_register is period_basis._period_register


# --- the report view's chart cell takes the run's currency (ruling P8-R2, B31a) ------------------


def _chart_money(currency: str | None) -> Fact:
    return Fact(
        fact_id="chart-money",
        label="Chart money",
        table_id="T1B.1",
        row_id="revenue",
        field="current",
        amount=Decimal(30),
        unit="MILLIONS",
        currency=currency,
        period="Q4 26: 2026-10-01 to 2026-12-31",
        scale=Decimal(1000000),
    )


@pytest.mark.parametrize("currency", ["USD", "EUR", "GBP"])
def test_chart_cell_accepts_a_money_fact_in_any_iso_shaped_currency(currency: str) -> None:
    cell = report_view._chart_fact_cell(_chart_money(currency), "amount", ("K1",))
    assert cell.unit_class == "amount" and cell.ref_id == "K1"


@pytest.mark.parametrize("currency", [None, "", " ", "usd", "US$", "EURO", "€", "EUR\n", "123"])
def test_chart_cell_refuses_a_money_fact_without_an_iso_shaped_currency(
    currency: str | None,
) -> None:
    with pytest.raises(ValueError, match="CP1 chart point has unsupported numeric dimensions"):
        report_view._chart_fact_cell(_chart_money(currency), "amount", ("K1",))


# --- CP-1B: the 2026 register in EUR or USD (oracle CP-1B@EUR, CP-1B@USD, R3, R5b) ----------------

_YEAR = re.compile(r"(?<![0-9A-Za-z])(2024|2025)(?![0-9A-Za-z])")
_SHORT = re.compile(r"\b(Q[1-4] |FY)25\b")


def shifted(currency: str, *, opening: bool = False) -> Module:
    """The literal A1 register (`test_owner_cp1b._producer`) with every year +1, so the pair is
    q3-2026 -> q4-2026 as in the oracle, and the money facts in `currency`."""
    own: Any = importlib.import_module("test_owner_cp1b")
    a1: Any = importlib.import_module("test_earnings")
    text = own._producer(opening=opening).model_dump_json()
    text = _SHORT.sub(lambda m: f"{m[1]}26", _YEAR.sub(lambda m: str(int(m[1]) + 1), text))
    for old, new, kind in (
        ("q3-2025", "q3-2026", "QUARTER"),
        ("q4-2025", "q4-2026", "QUARTER"),
        ("fy-2025", "fy-2026", "FY"),
    ):
        text = text.replace(a1.BASES[old], own._basis_of(new, kind))
    return Module.model_validate_json(text.replace('"USD"', f'"{currency}"'))


def _report(currency: str, run_currency: str | None = None) -> EarningsDeltaReport:
    producer = shifted(currency)
    return build_earnings_delta_in(
        cp1b.cp1_view(producer), "q3-2026", "q4-2026", run_currency or currency
    )


def _points(report: EarningsDeltaReport) -> list[dict[str, Any]]:
    return [
        {
            "measure_id": p.measure_id,
            "prior_value": None if p.prior_value is None else str(p.prior_value),
            "current_value": None if p.current_value is None else str(p.current_value),
            "unit": p.unit,
            "currency": p.currency,
            "scale": str(p.scale),
            "delta_unit": p.delta_unit,
        }
        for p in report.points
    ]


def _oracle_points(name: str) -> list[dict[str, Any]]:
    keep = ("measure_id", "prior_value", "current_value", "unit", "currency", "scale", "delta_unit")
    return [
        {
            k: Decimal(p[k]).__format__("f")
            if k in {"prior_value", "current_value"} and p[k]
            else p[k]
            for k in keep
        }
        for p in KEY["module_oracles"][name]["points"]
    ]


@pytest.mark.parametrize("currency", ["EUR", "USD"])
def test_delta_report_equals_the_oracle_points(currency: str) -> None:
    got = _points(_report(currency))
    want = _oracle_points(f"CP-1B@{currency}")
    for g, w in zip(got, want, strict=True):
        for name in ("measure_id", "unit", "currency", "scale", "delta_unit"):
            assert g[name] == w[name], (g["measure_id"], name)
        for name in ("prior_value", "current_value"):
            assert (g[name] is None) == (w[name] is None)
            assert g[name] is None or Decimal(g[name]) == Decimal(w[name]), (g["measure_id"], name)


def test_a_usd_run_over_a_eur_head_is_incompatible_dimensions() -> None:
    with pytest.raises(ValueError, match="^incompatible_dimensions$"):
        _report("EUR", run_currency="USD")
    with pytest.raises(ValueError, match="^incompatible_dimensions$"):
        _report("USD", run_currency="EUR")


@pytest.mark.parametrize("currency", ["", "eur", "US$", "EURO", "EUR\n"])
def test_the_delta_core_refuses_a_non_iso_run_currency(currency: str) -> None:
    producer = shifted("EUR")
    with pytest.raises(ValueError, match="^incompatible_dimensions$"):
        build_earnings_delta_in(cp1b.cp1_view(producer), "q3-2026", "q4-2026", currency)


def _compose(currency: str, *, owner: bool = False) -> tuple[Module, EarningsDeltaReport]:
    own: Any = importlib.import_module("test_owner_cp1b")
    producer = shifted(currency)
    report = _report(currency)
    module = ew.compose_delta(
        producer,
        report,
        ew._operands(producer, report),
        (),
        ew._own_limits(report, owner=owner),
        own._attempt(producer),
        own._run(),
    )
    return module, report


def _row_labels(module: Module) -> dict[str, dict[str, str]]:
    return {t.table_id: {r.row_id: r.label for r in t.rows} for t in module.tables}


@pytest.mark.parametrize("currency", ["EUR", "USD"])
def test_composed_row_labels_equal_the_oracle(currency: str) -> None:
    module, _ = _compose(currency)
    want = KEY["module_oracles"][f"CP-1B@{currency}"]["row_labels"]
    got = _row_labels(module)
    for table_id, rows in want.items():
        assert got[table_id] == {r["row_id"]: r["label"] for r in rows}, table_id


def test_every_money_fact_label_states_the_run_unit() -> None:
    """The report view does not compare `Fact.label`, so the composer must (adversary I2)."""
    module, _ = _compose("EUR")
    for fact in module.facts:
        if fact.table_id in {"T1B.1", "T1B.2"}:
            assert "US$" not in fact.label and "USD" not in fact.label, fact.fact_id
    revenue = next(f for f in module.facts if f.fact_id == "cp1b:T1B.1:revenue:current")
    assert revenue.label == "Revenue (EUR m) · current"


@pytest.mark.parametrize("currency", ["EUR", "USD"])
def test_composed_prose_equals_the_oracle(currency: str) -> None:
    module, report = _compose(currency)
    want = KEY["module_oracles"][f"CP-1B@{currency}"]
    assert list(ew._own_limits(report)) == want["own_limitations"]
    (claim,) = module.claims
    assert claim.text == want["claim_text"] and claim.limitation == want["claim_limitation"]
    assessments = {f.row_id: f for f in module.facts if f.table_id == "T1B.3"}
    for row in want["assessments"]:
        fact = assessments[row["row_id"]]
        assert fact.status == row["status"], row["row_id"]
        if row["text"] is not None and row["text"] != "canonical_lineage_json":
            assert fact.text == row["text"], row["row_id"]
        if row["limitation"] is not None:
            assert fact.limitation == row["limitation"], row["row_id"]


def test_eur_module_carries_no_us_dollar_token() -> None:
    module, _ = _compose("EUR")
    text = module.model_dump_json()
    for token in KEY["runs"]["R3"]["modules"]["CP-1B"]["forbidden_tokens"]:
        assert token not in text, token
    assert KEY["runs"]["R3"]["modules"]["CP-1B"]["money_unit"] in text


def test_eur_money_facts_carry_the_eur_dimensions() -> None:
    module, _ = _compose("EUR")
    want = KEY["module_oracles"]["CP-1B@EUR"]["money_fact_currency"]
    for fact in module.facts:
        if fact.row_id in want["rows"] and fact.field in want["fields"]:
            assert (fact.currency, fact.unit, str(fact.scale)) == (
                want["currency"],
                want["unit"],
                want["scale"],
            ), fact.fact_id


def test_the_layout_check_accepts_the_eur_module() -> None:
    module, _ = _compose("EUR")
    view = ModuleView(
        module_id="CP-1B",
        title="Earnings update",
        aliases=(),
        status="restricted",
        artifact_sha256="a" * 64,
        facts=module.facts,
        tables=module.tables,
        claims=module.claims,
        limitations=module.limitations,
    )
    report_view._validate_cp1b_layout(view)


def test_eur_evidence_states_the_currency_and_usd_keeps_its_bytes() -> None:
    def evidence(currency: str) -> dict[str, Any]:
        module, _ = _compose(currency)
        fact = next(f for f in module.facts if f.row_id == "evidence.inputs")
        parsed: dict[str, Any] = json.loads(fact.text or "")
        return parsed

    assert evidence("EUR")["currency"] == "EUR"
    assert "currency" not in evidence("USD")  # the pinned USD bytes


# --- CP-1B owner core: the pins follow the register year (P8-P6) -----------------------------------


def _compute(
    module: Module, prior: str, current: str, comparison: str, currency: str
) -> cp1b.Computation:
    own: Any = importlib.import_module("test_owner_cp1b")
    return cp1b.compute(
        cp1b.cp1_view(module), own.review(prior, current, comparison), currency=currency
    )


def test_r3_flat_pair_settles_under_eur() -> None:
    found = _compute(shifted("EUR"), "q3-2026", "q4-2026", "flat_sequential", "EUR")
    assert found.issues == () and found.report is not None
    assert {p.currency for p in found.report.points if p.unit == "MILLIONS"} == {"EUR"}


def test_a_usd_run_over_the_eur_head_is_refused_with_the_core_code() -> None:
    found = _compute(shifted("EUR"), "q3-2026", "q4-2026", "flat_sequential", "USD")
    assert found.issues == ("incompatible_dimensions",) and found.report is None


def test_the_gap_pair_follows_the_register_year() -> None:
    module = shifted("EUR", opening=True)
    found = _compute(module, "fy-2025", "fy-2026", "comparative_not_supplied", "EUR")
    assert found.issues == () and found.report is not None and found.report.prior_basis_id is None
    # The 2025 pair is no longer the one the 2026 register supports.
    stale = _compute(module, "fy-2024", "fy-2025", "comparative_not_supplied", "EUR")
    assert stale.report is None and stale.issues in {
        ("unsupported_pair",),
        ("incomplete_register",),
    }


def test_the_gap_pair_needs_the_opening_row_of_its_own_year() -> None:
    found = _compute(shifted("EUR"), "fy-2025", "fy-2026", "comparative_not_supplied", "EUR")
    assert found.report is None and found.issues == ("unsupported_pair",)


def test_a_duration_row_of_the_prior_year_or_earlier_refuses_the_pair() -> None:
    base = shifted("EUR")
    changed = {
        "period_id": "q4-2025",
        "fiscal_year": "2025",
        "start_date": "2025-10-01",
        "end_date": "2025-12-31",
    }
    older = tuple(
        f.model_copy(
            update={
                "fact_id": f.fact_id.replace("q4-2026", "q4-2025"),
                "row_id": "period.q4-2025",
                "period": "q4-2025",
                "text": changed.get(f.field, f.text),
            }
        )
        for f in base.facts
        if f.row_id == "period.q4-2026"
    )
    assert len(older) == 10
    moved = base.model_copy(update={"facts": (*base.facts, *older)})
    found = _compute(moved, "q3-2026", "q4-2026", "flat_sequential", "EUR")
    assert found.report is None and found.issues == ("unsupported_pair",)


def test_the_2025_pair_is_unsupported_over_the_2026_register() -> None:
    found = _compute(shifted("EUR"), "q3-2025", "q4-2025", "flat_sequential", "EUR")
    assert found.report is None and found.issues in {
        ("unsupported_pair",),
        ("incomplete_register",),
    }


def test_r5b_q3_base_cp1b_keeps_its_raw_day_refusal() -> None:
    """R5b: a q3 base is not a currency refusal; CP-1B refuses `incompatible_periods` as today
    (the 91-day against the 92-day quarter, `earnings.py` raw-day check)."""
    want = KEY["runs"]["R5b"]["modules"]["CP-1B"]
    assert want["outcome"] == "refused" and want["error"] == "incompatible_periods"
    module = shifted("USD")
    short = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"text": "2026-09-29"})
                if f.row_id == "period.q3-2026" and f.field == "end_date"
                else f
                for f in module.facts
            )
        }
    )
    found = _compute(short, "q3-2026", "q4-2026", "flat_sequential", "USD")
    assert found.issues == (want["issue_contains"],) and found.report is None


# --- CP-1B on the owner path under a run context ---------------------------------------------------


def _eur_context(currency: str) -> Any:
    own: Any = importlib.import_module("test_owner_cp1b")

    def edit(document: dict[str, Any]) -> None:
        document["run"].update(
            current_period="q4-2026", prior_period="q3-2026", reporting_currency=currency
        )

    return own._ctx_pack("ctx-match", edit)


def _owner_step(producer: Module, pack: Any) -> Any:
    own: Any = importlib.import_module("test_owner_cp1b")
    step = StepSubmission(step_id="earnings_delta", inputs=(), payload_sha256="b" * 64)
    payload = own._payload("q3-2026", "q4-2026", "flat_sequential")
    return cp1b._validate_step(
        own._Store(producer, payload, pack), pack, own._attempt(producer, step)
    )


def _owner_view(producer: Module, pack: Any) -> dict[str, Any]:
    own: Any = importlib.import_module("test_owner_cp1b")
    text = cp1b.view(own._Store(producer, "", pack), own._attempt(producer))[1]
    body: dict[str, Any] = json.loads(text)
    return body


def test_owner_walk_settles_the_eur_head_under_an_eur_context() -> None:
    producer, pack = shifted("EUR"), _eur_context("EUR")
    body = _owner_view(producer, pack)
    assert [(p["prior_period_id"], p["current_period_id"]) for p in body["pairs"]] == [
        ("q3-2026", "q4-2026")
    ]
    outcome = _owner_step(producer, pack)
    assert outcome.issues == () and outcome.output is not None
    head = Module.model_validate_json(outcome.output)
    text = head.model_dump_json()
    assert "EUR m" in text and "US$" not in text and "USD" not in text
    assert any("in EUR millions" in x for x in head.limitations)


def test_owner_walk_refuses_a_usd_context_over_the_eur_head() -> None:
    producer, pack = shifted("EUR"), _eur_context("USD")
    body = _owner_view(producer, pack)
    assert body["pairs"] == [] and body["context_issue"].startswith("incompatible_dimensions")
    outcome = _owner_step(producer, pack)
    assert outcome.output is None
    assert len(outcome.issues) == 1 and outcome.issues[0].startswith("incompatible_dimensions")


def test_owner_walk_refuses_an_eur_context_over_the_usd_head() -> None:
    producer, pack = shifted("USD"), _eur_context("EUR")
    outcome = _owner_step(producer, pack)
    assert outcome.output is None and outcome.issues[0].startswith("incompatible_dimensions")


# --- CP-2A: the currency of the run (oracle CP-2A@EUR / CP-2A@USD, R2, R5b) -------------------------

_M2A: Any = importlib.import_module("test_method_cp2a")
EUR_LTM = KEY["module_oracles"]["CP-2A@EUR"]["expected"]["base_period"]


def _y26(text: str) -> str:
    return text.replace("US$ m", "EUR m").replace("Q4 25", "Q4 26").replace("2025", "2026")


def _cp2a_facts(currency: str) -> tuple[Fact, ...]:
    """The oracle's CP-2A@EUR `cp1_inputs` as CP-1 T4.10 facts, money facts in `currency`."""
    out = []
    records = KEY["module_oracles"]["CP-2A@EUR"]["expected"]["cp1_inputs"]
    for n, (metric, record) in enumerate(records.items(), 1):
        fact = _M2A.cp1_fact(metric, {**record, "period": _M2A.LTM}, n)
        out.append(
            fact.model_copy(
                update={
                    "label": record["label"],
                    "period": record["period"],
                    "field": "ltm",
                    "currency": currency if fact.currency else None,
                }
            )
        )
    return tuple(out)


def _cp2a_inputs(currency: str, base: str = EUR_LTM) -> cp2a.Inputs:
    facts = _cp2a_facts(currency)
    ids = {
        name: next(f for f in facts if f.label == _y26(fig["cp1_label"])).fact_id
        for name, fig in _M2A.FIGURES.items()
        if any(f.label == _y26(fig["cp1_label"]) for f in facts)
    }
    raw = json.dumps(_M2A.SUBMISSIONS["positive"]["downside_pathway"])
    payload = json.loads(_M2A.bind(_y26(raw), ids))
    submission = cp2a.DownsideSubmission.model_validate_json(json.dumps(payload))
    unit_currency = currency
    return cp2a.Inputs(
        submission=submission,
        cp1_facts=facts,
        offered_periods=(base,),
        names=(_M2A.ISSUER,),
        currency=unit_currency,
    )


def test_cp2a_eur_claims_and_limitations_equal_the_oracle() -> None:
    inputs = _cp2a_inputs("EUR")
    result = cp2a.compute(inputs)
    want = KEY["module_oracles"]["CP-2A@EUR"]["expected"]
    ids = {f.label: f.fact_id for f in inputs.cp1_facts}
    figs = {
        name: ids[_y26(fig["cp1_label"])]
        for name, fig in _M2A.FIGURES.items()
        if _y26(fig["cp1_label"]) in ids
    }
    assert [c.claim_id for c in result.claims] == [c["claim_id"] for c in want["claims"]]
    for claim, exp in zip(result.claims, want["claims"], strict=True):
        assert claim.text == _M2A.bind(exp["text"], figs), claim.claim_id
    assert list(result.limitations) == want["own_limitations"]


def test_cp2a_eur_amount_facts_carry_eur_and_no_us_dollar_token() -> None:
    result = cp2a.compute(_cp2a_inputs("EUR"))
    money = [f for f in result.facts if f.unit == "MILLIONS"]
    assert money and {f.currency for f in money} == {"EUR"}
    text = json.dumps([f.model_dump(mode="json") for f in result.facts])
    text += json.dumps([c.model_dump(mode="json") for c in result.claims])
    for token in KEY["runs"]["R2"]["modules"]["CP-2A"]["forbidden_tokens"]:
        assert token not in text, token


def test_cp2a_offers_the_eur_operands_under_eur_and_not_under_usd() -> None:
    facts = _cp2a_facts("EUR")
    assert [b.period for b in cp2a.offered_bases(facts, "EUR")] == [EUR_LTM]
    assert cp2a.offered_bases(facts, "USD") == ()
    usd = _cp2a_facts("USD")
    assert [b.period for b in cp2a.offered_bases(usd)] == [EUR_LTM]  # default is USD
    assert cp2a.offered_bases(usd, "EUR") == ()


def test_cp2a_offers_a_q3_base_whatever_the_currency() -> None:
    """R5b: a q3 base is not a refusal for a currency-only module (M3)."""
    want = KEY["runs"]["R5b"]["modules"]["CP-2A"]
    assert want["outcome"] == "settled"
    q3 = "Q3 26: 2026-07-01 to 2026-09-30"
    facts = tuple(
        f.model_copy(
            update={
                "label": f.label.replace(
                    "LTM Q4 26 (2026-01-01 to 2026-12-31)", "Q3 26 (2026-07-01 to 2026-09-30)"
                ),
                "period": q3,
            }
        )
        for f in _cp2a_facts("USD")
    )
    assert [b.period for b in cp2a.offered_bases(facts, "USD")] == [q3]


def _cp2a_upstream(register_currency: str) -> cp2a.Upstream:
    register = tuple(f for f in shifted(register_currency).facts if f.table_id == "T4.14")
    return cp2a.Upstream(bound=(), current=(), cp1=(*_cp2a_facts(register_currency), *register))


def test_cp2a_validation_follows_the_context_currency() -> None:
    submission = _cp2a_inputs("EUR").submission
    ok = cp2a.validate_downside(
        pack=_eur_context("EUR"), submission=submission, upstream=_cp2a_upstream("EUR")
    )
    assert ok == ()
    refused = cp2a.validate_downside(
        pack=_eur_context("USD"), submission=submission, upstream=_cp2a_upstream("EUR")
    )
    assert len(refused) == 1 and refused[0].startswith("Currency refused: ")
    report = cp2a.downside_report(
        pack=_eur_context("EUR"), submission=submission, upstream=_cp2a_upstream("EUR")
    )
    assert {f.currency for f in report.facts if f.unit == "MILLIONS"} == {"EUR"}


def test_cp2a_view_offers_no_base_when_the_context_contradicts_cp1() -> None:
    body = cp2a.context_block(pack=_eur_context("USD"), upstream=_cp2a_upstream("EUR"))
    assert body["base_periods"] == [] and str(body["context_issue"]).startswith("Currency refused")
    good = cp2a.context_block(pack=_eur_context("EUR"), upstream=_cp2a_upstream("EUR"))
    assert [b["period"] for b in cast(list[dict[str, Any]], good["base_periods"])] == [EUR_LTM]
    assert "context_issue" not in good


# --- CP-2E: its own basis from the run context and the statement header (P8-P18) -------------------

_YEAR4 = re.compile(r"(?<![0-9.,])((?:19|20)[0-9]{2})(?![0-9])")
CP2E_EUR = KEY["module_oracles"]["CP-2E@EUR"]["expected"]


def _shift_text(text: str, currency: str) -> str:
    """The builder's mapping rules: every calendar year +1, `US$` and `USD` spelled `currency`."""
    shifted_years = _YEAR4.sub(lambda m: str(int(m[1]) + 1), text)
    return shifted_years.replace("US$", currency).replace("USD", currency)


def _cp2e_pages(currency: str) -> dict[str, str]:
    fin: Any = importlib.import_module("test_method_cp2e")
    return {k: _shift_text(v, currency) for k, v in fin._pages("positive").items()}


def _cp2e_submission(currency: str) -> dict[str, Any]:
    fin: Any = importlib.import_module("test_method_cp2e")
    document: dict[str, Any] = json.loads(
        _shift_text(json.dumps(fin.SUBMISSIONS["positive"]), currency)
    )
    return document


def _cp2e_pack(base: str, currency: str = "EUR", as_of: str = "2027-01-10") -> PreparedPack:
    pages = _cp2e_pages(currency)
    spans = tuple(Span(locator=k, text=v) for k, v in pages.items())
    financial = Source(
        source_id="financial",
        name="Unaudited statements",
        status="ready",
        sha256=hashlib.sha256("\f".join(s.text for s in spans).encode()).hexdigest(),
        spans=spans,
        extraction_status="complete",
    )
    run = Run.model_validate_json(json.dumps({**CP2E_EUR["run"], "as_of": as_of}))
    own: Any = importlib.import_module("test_owner_cp1b")

    def edit(document: dict[str, Any]) -> None:
        document["run"].update(
            current_period=base, prior_period="", reporting_currency=currency, as_of=as_of
        )

    context = own._ctx_pack("ctx-l10", edit).sources[0]
    return PreparedPack(run=run, sources=(financial, context))


def _cp2e_report(base: str) -> cp2e.MacroFxReport:
    pack = _cp2e_pack(base)
    submission = cp2e.MacroFxSubmission.model_validate_json(json.dumps(_cp2e_submission("EUR")))
    return cp2e.macro_fx(pack=pack, submission=submission)


def test_cp2e_pack_pages_are_the_oracle_pages() -> None:
    """The mapping used here reproduces the oracle's financial source byte for byte."""
    (financial,) = [s for s in CP2E_EUR["pack_sources"] if s["source_id"] == "financial"]
    assert _cp2e_pack("fy-2026").sources[0].sha256 == financial["sha256"]


@pytest.mark.parametrize("base", ["fy-2026", "q4-2026"])
def test_cp2e_periods_equal_the_oracle(base: str) -> None:
    pack = _cp2e_pack(base)
    got = cp2e.periods_of(pack)
    want = KEY["period_basis"]["EUR"]["cp2e_periods"]
    run = KEY["runs"]["R2"]["modules"]["CP-2E"]["periods"]["run"]
    # The key's `shock` is the year label the shock period begins with; the full string is
    # compared with the oracle tables in `test_cp2e_report_equals_the_oracle_tables_and_claims`.
    assert (got.flow, got.bal, got.label, got.run) == (
        want["flow"],
        want["balance"],
        want["shock"],
        run,
    )
    assert got.shock.startswith(want["shock"])


def test_cp2e_report_equals_the_oracle_tables_and_claims() -> None:
    report = _cp2e_report("fy-2026")
    facts = {f.fact_id: f for f in report.facts}
    for table in CP2E_EUR["tables"]:
        for row in table["rows"]:
            for want in row["facts"]:
                fact = facts[want["fact_id"]]
                assert (fact.period, fact.text, fact.currency, fact.unit, fact.status) == (
                    want["period"],
                    want["text"],
                    want["currency"],
                    want["unit"],
                    want["status"],
                ), want["fact_id"]
    assert [c.claim_id for c in report.claims] == [c["claim_id"] for c in CP2E_EUR["claims"]]
    for claim, want_claim in zip(report.claims, CP2E_EUR["claims"], strict=True):
        assert claim.text == want_claim["text"], claim.claim_id
    assert list(report.limitations) == CP2E_EUR["own_limitations"]


def test_cp2e_report_carries_no_us_dollar_token() -> None:
    text = _cp2e_report("fy-2026").model_dump_json()
    for token in KEY["runs"]["R2"]["modules"]["CP-2E"]["forbidden_tokens"]:
        assert token not in text, token


def test_cp2e_run_period_is_the_run_date() -> None:
    report = _cp2e_report("fy-2026")
    assert any(f.period == "Run as of 2027-01-10" for f in report.facts)
    assert not any(f.period == "Run as of 2026-01-10" for f in report.facts)


# --- CP-2E validation: header year, currency, base kind --------------------------------------------


def _cp2e_issues(base: str, *, currency: str = "EUR", pages_currency: str = "EUR") -> Any:
    from types import SimpleNamespace

    pack = _cp2e_pack(base, currency)
    document = _cp2e_submission(pages_currency)
    payload = json.dumps(document)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    store = SimpleNamespace(payload=lambda sha: payload if sha == digest else "")
    attempt = SimpleNamespace(steps=(SimpleNamespace(payload_sha256=digest),), number=0)
    return cp2e._validate_step(cast(Execution, store), pack, cast(Attempt, attempt))


def test_cp2e_accepts_the_fy_2026_header_under_fy_2026_and_q4_2026() -> None:
    for base in ("fy-2026", "q4-2026"):
        outcome = _cp2e_issues(base)
        assert outcome.issues == () and outcome.output is not None, base


def test_cp2e_refuses_the_fy_2025_header_under_fy_2026() -> None:
    pack = _cp2e_pack("fy-2026")
    pages = {s.locator: s.text for s in pack.sources[0].spans}
    old = {k: v.replace("FY 2026", "FY 2025") for k, v in pages.items()}
    issues = cp2e.validate_macro_fx(
        submission=_cp2e_submission("EUR"), pages=old, periods=cp2e.periods_of(pack)
    )
    assert issues and all("page header does not end in the FY column" in x for x in issues)


def test_cp2e_refuses_a_half_year_base_with_no_cp1_input() -> None:
    outcome = _cp2e_issues("h2-2026")
    assert outcome.output is None
    assert len(outcome.issues) == 1 and outcome.issues[0].startswith("Period refused: ")


def test_cp2e_refuses_statements_in_another_currency_than_the_run() -> None:
    outcome = _cp2e_issues("fy-2026", currency="USD", pages_currency="EUR")
    assert outcome.output is None
    assert any(
        x == "reporting_currency: the statements state EUR, the run context states USD"
        for x in outcome.issues
    )


# --- CP-L10: the currency token of the run (oracle CP-L10@EUR; Phase 2 owns the offering) ------------

L10_EUR = KEY["module_oracles"]["CP-L10@EUR"]["expected"]
_QUARTER_LABEL = re.compile(r"\b(Q[1-4]) 25\b")


def _l10_shift(text: str, currency: str) -> str:
    return _QUARTER_LABEL.sub(r"\1 26", _shift_text(text, currency))


def _l10_upstream(currency: str = "EUR") -> cpl10.Upstream:
    own: Any = importlib.import_module("test_owner_cpl10")
    method: Any = importlib.import_module("test_method_cpl10")
    register = own._t414_rows(*((2026, q) for q in (1, 2, 3, 4)))
    quarters = cpl10.context_quarters("q4-2026", register)
    relabel = {old.column: new for old, new in zip(cpl10.QUARTERS, quarters, strict=True)}
    old_period = {old.column: old.period for old in cpl10.QUARTERS}
    facts = []
    for fact in method._cp1_facts():
        column, metric = fact.label.split(" · ")
        new = relabel[column]
        facts.append(
            fact.model_copy(
                update={
                    "label": f"{new.column} · {metric}",
                    "period": new.period if fact.period == old_period[column] else fact.period,
                    "currency": currency if fact.currency else None,
                }
            )
        )
    base = cpl10.Upstream(
        issuer_name=method.UPSTREAM.issuer_name,
        as_of=method.UPSTREAM.as_of,
        cp0_status_word=method.UPSTREAM.cp0_status_word,
        cp0_result_sha256=method.UPSTREAM.cp0_result_sha256,
        cp1_status_word=method.UPSTREAM.cp1_status_word,
        cp1_result_sha256=method.UPSTREAM.cp1_result_sha256,
        cp1_facts=cpl10.bind_operands(facts, quarters),
        quarters=quarters,
    )
    return cpl10.RunUpstream(
        **{f: getattr(base, f) for f in base.__dataclass_fields__},
        run_currency=period_basis._currency(currency),
    )


def _l10_payload() -> str:
    method: Any = importlib.import_module("test_method_cpl10")
    return _l10_shift(method._bind_run(method._payload("positive")), "EUR")


def test_cpl10_view_equals_the_oracle_in_eur() -> None:
    block = cpl10.context_block(upstream=_l10_upstream())
    assert block["topics"] == L10_EUR["view_topics"]
    assert block["pair_screens"] == L10_EUR["view_pair_screens"]


def test_cpl10_screen_equals_the_oracle_in_eur() -> None:
    upstream = _l10_upstream()
    payload = _l10_payload()
    assert cpl10.validate_screen(submission=payload, upstream=upstream) == ()
    result = cpl10.change_screen(submission=payload, upstream=upstream)
    facts = {c.fact.fact_id: c.fact for c in result.cells}
    for want in L10_EUR["facts"]:
        fact = facts[want["fact_id"]]
        assert (fact.status, fact.unit, fact.currency, fact.period) == (
            want["status"],
            want.get("unit"),
            want.get("currency"),
            want.get("period"),
        ), want["fact_id"]
    assert [c.claim_id for c in result.claims] == [c["claim_id"] for c in L10_EUR["claims"]]
    for claim, want_claim in zip(result.claims, L10_EUR["claims"], strict=True):
        assert claim.text == want_claim["text"], claim.claim_id
    text = json.dumps([c.fact.model_dump(mode="json") for c in result.cells])
    text += json.dumps([c.text for c in result.claims])
    for token in KEY["runs"]["R2"]["modules"]["CP-L10"]["forbidden_tokens"]:
        assert token not in text, token


def test_cpl10_usd_upstream_keeps_the_us_dollar_token() -> None:
    method: Any = importlib.import_module("test_method_cpl10")
    block = cpl10.context_block(upstream=method.UPSTREAM)
    units = {t["unit"] for t in cast(list[dict[str, Any]], block["topics"])}
    assert "US$ m" in units and "EUR m" not in units


# --- a blank base (ruling P8-R3) --------------------------------------------------------------------


def test_blank_base_usd_context_keeps_the_default_and_other_currencies_refuse() -> None:
    no_register: tuple[Fact, ...] = ()
    assert cp2a._run_currency(_cp2e_pack("", "USD"), no_register) == "USD"
    with pytest.raises(period_basis.PeriodRefused, match="blank"):
        cp2a._run_currency(_cp2e_pack("", "EUR"), no_register)
    assert cp2e.periods_of(_cp2e_pack("", "USD")).year == 2025
    with pytest.raises(cp2e.PeriodRefused, match="blank"):
        cp2e.periods_of(_cp2e_pack("", "EUR"))
