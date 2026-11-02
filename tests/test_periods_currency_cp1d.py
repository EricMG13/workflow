"""CP-1D takes its bridge basis line, CP-1 column and money unit from the run (Phase 8 Task 3).

The answer key is the frozen oracle `cases/periods-currency-owner/` (`expected.json`,
`manifest.json`, `t414.json`, `submissions.json`), loaded at run time; no value is copied here.
The 2025 USD behaviour stays pinned by `tests/test_method_cp1d.py` and `tests/test_connect_cp1d.py`.
"""

from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp1d as conn
import test_method_cp1d as stage1
from test_period_basis import _context, _oracle_facts

from deploy_vii.contracts import Fact, Input, Module, Run, Source
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow.owners import cp1d
from deploy_workflow.owners.period_basis import DEFAULT_BASIS, PeriodBasis, period_basis

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "periods-currency-owner"


def _load(name: str) -> Any:
    return json.loads((CASE / name).read_text(encoding="utf-8"))


EXPECTED = _load("expected.json")
MANIFEST = _load("manifest.json")
SUBMISSIONS = _load("submissions.json")
T414 = _load("t414.json")
ORACLE = EXPECTED["module_oracles"]["CP-1D@EUR"]["expected"]
FIGURES = SUBMISSIONS["modules"]["CP-1D@EUR"]["figures"]
KEY = EXPECTED["period_basis"]["EUR"]
EUR_PAGES = [p["text"] for p in MANIFEST["sources"]["bridge@EUR"]["pages"]]
R3 = SUBMISSIONS["contexts"]["R3"]


def _eur_basis(period: str = "q4-2026") -> PeriodBasis:
    return period_basis(_context(period, "EUR"), _oracle_facts(T414["contexts"]["R2"]["rows"]))


def _source(key: str) -> Source:
    s = MANIFEST["sources"][key]
    return stage1._source(s["source_id"], s["name"], s["pages"], s["sha256"])


def _eur_sources() -> tuple[Source, ...]:
    return (_source("identity"), _source("financial@EUR"), _source("bridge@EUR"))


def _eur_cp1() -> cp1d.Cp1Operands:
    figures = {
        name: cp1d.Cp1Figure(
            fact_id=f"cp1:{name}",
            figure=name,
            label=f["label"],
            unit=f["unit"],
            period=f["period"],
            amount=Decimal(f["amount_exact"]),
            value_class=f["value_class"],
            currency="EUR" if f["unit"] == "MILLIONS" else None,
        )
        for name, f in FIGURES.items()
    }
    return cp1d.Cp1Operands(
        adjusted_ebitda=figures["adjusted_ebitda_ltm"],
        ebitda=figures["ebitda_ltm"],
        cfo=figures["cfo_ltm"],
        total_debt=figures["total_debt_ltm"],
        net_debt=figures["net_debt_ltm"],
        total_leverage=figures["total_leverage_adjusted"],
        net_leverage=figures["net_leverage_adjusted"],
    )


def _eur_inputs(basis: PeriodBasis) -> cp1d.EarningsQualityInputs:
    payload = SUBMISSIONS["modules"]["CP-1D@EUR"]["submission"]["earnings_quality"]
    return cp1d.EarningsQualityInputs(
        sources=_eur_sources(),
        cp1=_eur_cp1(),
        submission=cp1d.EarningsQualitySubmission.model_validate_json(json.dumps(payload)),
        basis=basis,
    )


# --- (a) the frozen 2025 bridge and the default line ---------------------------------------------


def test_frozen_bridge_parses_with_the_default_line() -> None:
    pages = [p["text"] for p in stage1.MANIFEST["synthetic_source"]["positive"]["pages"]]
    assert cp1d.parse_bridge(pages) is not None
    assert cp1d.parse_bridge(pages, DEFAULT_BASIS.bridge_basis_line) is not None
    assert cp1d.parse_bridge(pages, KEY["bridge_basis_line"]) is None


# --- (b) a 2026 bridge parses under the run's line only ------------------------------------------


@pytest.mark.parametrize("period", ["fy-2026", "q4-2026"])
def test_2026_bridge_parses_under_the_run_line_not_the_default(period: str) -> None:
    basis = _eur_basis(period)
    assert basis.bridge_basis_line == KEY["bridge_basis_line"]
    assert any(line.startswith(basis.bridge_basis_line) for line in EUR_PAGES[0].split("\n"))
    bridge = cp1d.parse_bridge(EUR_PAGES, basis.bridge_basis_line)
    assert bridge is not None
    assert [i.row_id for i in bridge.items] == [
        r["row_id"] for r in ORACLE["tables"][0]["rows"][:4]
    ]
    assert cp1d.parse_bridge(EUR_PAGES) is None


# --- (c), (e) the money unit and the claim text --------------------------------------------------


def test_eur_claims_equal_the_oracle_and_carry_no_dollar_sign() -> None:
    result = cp1d.compute(_eur_inputs(_eur_basis()))
    got = {c.claim_id: c.text for c in result.claims}
    want = {c["claim_id"]: c["text"] for c in ORACLE["claims"]}
    assert got == want
    assert "EUR m" in got["T1D.3.restated"]
    assert not any("US$" in c.text or "USD" in c.text for c in result.claims)


def test_usd_default_claim_keeps_the_dollar_unit() -> None:
    result = cp1d.compute(stage1._case_inputs("positive"))
    text = next(c.text for c in result.claims if c.claim_id == "T1D.3.restated")
    want = next(
        c["text"]
        for c in stage1.EXPECTED["cases"]["positive"]["claims"]
        if c["claim_id"] == "T1D.3.restated"
    )
    assert text == want
    assert "US$ m" in text and "EUR" not in text


def test_eur_compute_equals_the_oracle_facts_tables_and_limitations() -> None:
    result = cp1d.compute(_eur_inputs(_eur_basis()))
    stage1._assert_facts(result, ORACLE["facts"])
    assert stage1._tables(result) == ORACLE["tables"]
    assert stage1._cp1_refs(result) == ORACLE["cp1_references"]
    assert stage1._operands(result) == ORACLE["operands"]
    assert list(result.limitations) == ORACLE["own_limitations"]


def test_eur_compute_refuses_a_bridge_with_the_other_years_line() -> None:
    frozen = _eur_inputs(DEFAULT_BASIS)
    assert any("Bridge table not found" in i for i in cp1d.validation_issues(frozen))
    assert cp1d.validation_issues(_eur_inputs(_eur_basis())) == ()


# --- (d) the CP-1 column -------------------------------------------------------------------------


def _t410(period: str, column: str, scale: int = 0, currency: str = "EUR") -> list[Fact]:
    facts = []
    for number, metric in enumerate(cp1d._CP1_METRICS.values()):
        facts.append(
            Fact(
                fact_id=f"t410-{scale}-{number}",
                label=f"{column} · {metric}",
                table_id="T4.10",
                row_id=metric,
                field="value",
                amount=Decimal(10 + number + scale),
                unit="MULTIPLE" if "leverage" in metric else "MILLIONS",
                currency=None if "leverage" in metric else currency,
                period=period,
                value_class="calculated",
            )
        )
    return facts


def _head(*groups: list[Fact]) -> Module:
    return Module(
        run_id="cp1d-p8t3",
        issuer_id="northbridge-synthetic",
        as_of=date(2027, 1, 10),
        module_id="CP-1",
        status="restricted",
        facts=tuple(f for group in groups for f in group),
        limitations=("CP-1 note",),
    )


def test_cp1_facts_select_the_run_column() -> None:
    basis = _eur_basis()
    head = _head(
        _t410(DEFAULT_BASIS.ltm_period, DEFAULT_BASIS.ltm_column, 100),
        _t410(basis.ltm_period, basis.ltm_column),
    )
    picked = cp1d._cp1_facts(head, basis)
    assert set(picked) == set(cp1d._CP1_METRICS)
    assert {f.period for f in picked.values()} == {KEY["ltm_period"]}
    assert {f.amount for f in picked.values()} == {Decimal(10 + n) for n in range(7)}
    assert {f.period for f in cp1d._cp1_facts(head).values()} == {DEFAULT_BASIS.ltm_period}


def test_cp1_facts_without_the_run_column_fail_with_zero_facts() -> None:
    head = _head(_t410(DEFAULT_BASIS.ltm_period, DEFAULT_BASIS.ltm_column))
    with pytest.raises(ValueError, match="0 facts"):
        cp1d._cp1_facts(head, _eur_basis())
    other = _head(_t410(KEY["ltm_period"], KEY["ltm_column"]))
    with pytest.raises(ValueError, match="0 facts"):
        cp1d._cp1_facts(other)


# --- the store adapter reads the basis from the pack's context and the CP-1 register ------------


def _context_source() -> Source:
    request = SourceRequest(source_id="context", path="context.json", media_type="text/plain")
    return prepare_source(request, json.dumps(R3).encode("utf-8"))


def _eur_pack() -> PreparedPack:
    run = Run.model_validate_json(
        json.dumps({**stage1.MANIFEST["cases"]["positive"]["run"], "as_of": R3["run"]["as_of"]})
    )
    return PreparedPack(run=run, sources=(*_eur_sources(), _context_source()))


def _eur_upstream() -> cp1d.Upstream:
    basis = _eur_basis()
    rows = _oracle_facts(T414["contexts"]["R2"]["rows"])
    figures = [
        Fact(
            fact_id=f"t410-{name}",
            label=f["label"],
            table_id="T4.10",
            row_id=name,
            field="value",
            amount=Decimal(f["amount_exact"]),
            unit=f["unit"],
            currency="EUR" if f["unit"] == "MILLIONS" else None,
            period=f["period"],
            value_class=f["value_class"],
            calculation_id=f"calc:{name}",
            scale=Decimal(1000000) if f["unit"] == "MILLIONS" else Decimal(1),
            decimals=2,
        )
        for name, f in FIGURES.items()
    ]
    assert figures[0].period == basis.ltm_period
    cp1 = _head(figures, rows)
    cp0 = _head().model_copy(update={"module_id": "CP-0"})
    bound = tuple(
        Input(input_id=m.module_id, sha256=m.content_hash(), status="restricted")
        for m in (cp0, cp1)
    )
    return cp1d.Upstream(bound=bound, current=bound, cp0=cp0, cp1=cp1, cp1b=None, inherited=())


def test_adapter_reads_the_basis_from_the_context_and_register() -> None:
    inputs, facts = cp1d._inputs(_eur_pack(), _eur_inputs(_eur_basis()).submission, _eur_upstream())
    assert inputs.basis == _eur_basis()
    assert {f.period for f in facts.values()} == {KEY["ltm_period"]}
    assert {f.currency for f in facts.values() if f.unit == "MILLIONS"} == {"EUR"}


def test_context_block_bridge_and_facts_follow_the_run_basis() -> None:
    block: Any = cp1d.context_block(pack=_eur_pack(), upstream=_eur_upstream())
    bridge = block["bridge"]
    assert bridge["state"] == "present"
    assert [i["row"] for i in bridge["items"]] == [
        r["row_id"] for r in ORACLE["tables"][0]["rows"][:4]
    ]
    assert {f["period"] for f in block["cp1_facts"]} == {KEY["ltm_period"]}
    assert "context_issue" not in block


def test_adapter_refuses_a_context_whose_currency_the_register_does_not_state() -> None:
    usd = json.loads(json.dumps(R3))
    usd["run"]["reporting_currency"] = "USD"
    request = SourceRequest(source_id="context", path="context.json", media_type="text/plain")
    pack = _eur_pack()
    mismatched = PreparedPack(
        run=pack.run,
        sources=(*_eur_sources(), prepare_source(request, json.dumps(usd).encode("utf-8"))),
    )
    submission = _eur_inputs(_eur_basis()).submission
    issues, report = cp1d._checked(mismatched, submission, _eur_upstream())
    assert report is None
    assert any(i.startswith("Period basis refused: ") and "EUR" in i for i in issues)


def test_eur_run_composes_through_the_validator_with_the_oracle_claims() -> None:
    text = json.dumps(SUBMISSIONS["modules"]["CP-1D@EUR"]["submission"]["earnings_quality"])
    bound = re.sub(r"\{\{FIG:([a-z_]+)\|([^}]+)\}\}", r"{t410-\1|\2}", text)
    submission = cp1d.EarningsQualitySubmission.model_validate_json(bound)
    report = cp1d.earnings_quality(
        pack=_eur_pack(), submission=submission, upstream=_eur_upstream()
    )
    want = {c["claim_id"]: c["text"] for c in ORACLE["claims"]}
    got = {c.claim_id: c.text for c in report.claims}
    for claim_id, text_want in want.items():
        assert "US$" not in got[claim_id]
        if "{{FIG" not in text_want:
            assert got[claim_id] == text_want
    assert {f.period for f in report.facts if f.unit == "MILLIONS"} == {KEY["ltm_period"]}


def test_blank_base_context_follows_run_basis_ruling_p8_r3() -> None:
    usd = json.loads(json.dumps(R3))
    usd["run"].update(
        run_type="research", current_period="", prior_period="", reporting_currency="USD"
    )
    request = SourceRequest(source_id="context", path="context.json", media_type="text/plain")
    pack = PreparedPack(
        run=_eur_pack().run,
        sources=(*_eur_sources(), prepare_source(request, json.dumps(usd).encode("utf-8"))),
    )
    inputs, _ = cp1d._inputs(pack, _eur_inputs(_eur_basis()).submission, _eur_upstream_2025())
    assert inputs.basis == DEFAULT_BASIS


def _eur_upstream_2025() -> cp1d.Upstream:
    head = _head(_t410(DEFAULT_BASIS.ltm_period, DEFAULT_BASIS.ltm_column, currency="USD"))
    return cp1d.Upstream(bound=(), current=(), cp0=head, cp1=head, cp1b=None, inherited=())


# --- fix round 1: the view carries a refusal (P8-R5); mutant tests -------------------------------


def _pack_with_context(pack: PreparedPack, **run: str) -> PreparedPack:
    document = json.loads(json.dumps(R3))
    document["run"].update(run)
    request = SourceRequest(source_id="context", path="context.json", media_type="text/plain")
    held = prepare_source(request, json.dumps(document).encode("utf-8"))
    kept = tuple(s for s in pack.sources if s.source_id != "context")
    return PreparedPack(run=pack.run, sources=(*kept, held))


_REFUSING = {
    "q3 base": ({"current_period": "q3-2026", "prior_period": "q2-2026"}, "Period basis refused: "),
    "USD context over an EUR register": ({"reporting_currency": "USD"}, "Period basis refused: "),
    "blank base, EUR": (
        {"run_type": "research", "current_period": "", "prior_period": ""},
        "Period basis refused: ",
    ),
    "as_of disagrees with the run": ({"as_of": "2027-01-11"}, "Context refused: "),
}


@pytest.mark.parametrize("label", list(_REFUSING))
def test_view_carries_a_refused_basis_as_context_issue(label: str) -> None:
    overrides, prefix = _REFUSING[label]
    pack = _pack_with_context(_eur_pack(), **overrides)
    upstream = _eur_upstream()
    issues, report = cp1d._checked(pack, _eur_inputs(_eur_basis()).submission, upstream)
    assert report is None and len(issues) == 1 and issues[0].startswith(prefix)
    block: Any = cp1d.context_block(pack=pack, upstream=upstream)
    assert block["context_issue"] == issues[0]
    assert block["bridge"]["items"] == [] and block["bridge"]["totals"] is None
    assert block["cp1_facts"] == []


def test_blank_base_usd_view_equals_the_no_context_view() -> None:
    plain = conn._pack("positive")
    run = plain.run
    blank = _pack_with_context(
        plain,
        run_type="research",
        current_period="",
        prior_period="",
        reporting_currency="USD",
        as_of=run.as_of.isoformat(),
        case_kind=run.case_kind,
        pathway=run.pathway,
    )
    document = json.loads(json.dumps(R3))
    document["identity"].update(issuer_name=run.issuer_name, issuer_id=run.issuer_id)
    blank = PreparedPack(run=run, sources=(*plain.sources, _identity_context(blank, document)))
    assert cp1d.context_block(pack=blank, upstream=conn._upstream()) == cp1d.context_block(
        pack=plain, upstream=conn._upstream()
    )


def _identity_context(pack: PreparedPack, document: dict[str, Any]) -> Source:
    held = next(s for s in pack.sources if s.source_id == "context")
    merged = json.loads("\n".join(span.text for span in held.spans))
    merged["identity"] = document["identity"]
    request = SourceRequest(source_id="context", path="context.json", media_type="text/plain")
    return prepare_source(request, json.dumps(merged).encode("utf-8"))


def test_checked_maps_only_the_refusals_to_the_basis_lines() -> None:
    only_2026 = _head(_t410(KEY["ltm_period"], KEY["ltm_column"]))
    issues, report = cp1d._checked(
        conn._pack("positive"), conn._submission("positive"), conn._upstream(only_2026)
    )
    assert report is None
    assert len(issues) == 1 and issues[0].startswith("CP-1 operands unavailable: ")
    assert "refused" not in issues[0]


def test_entry_refuses_cp1_amounts_in_another_currency_than_the_basis() -> None:
    cp1 = conn._cp1_module()
    eur = cp1.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"currency": "EUR"}) if f.currency == "USD" else f
                for f in cp1.facts
            )
        }
    )
    issues, report = cp1d._checked(
        conn._pack("positive"), conn._submission("positive", eur), conn._upstream(eur)
    )
    assert report is None
    assert issues == ("Period basis refused: run.reporting_currency USD, but CP-1 reports EUR",)
