"""Phase 8 Task 6: CP-4C takes its balance date, forecast years and currency from the run context.

The answer key is the frozen oracle `cases/periods-currency-owner/`, loaded at run time and never
edited: `expected.json#module_oracles/CP-4C@EUR/expected` (facts, tables, claims, own limitations,
waterfall, figures), `#runs/R2/modules/CP-4C` (money unit, required and forbidden tokens, the claim
column and the balance-date limitation), `#runs/R5/modules/CP-4C` (the refusal) and
`#period_basis/<cur>`; `submissions.json#modules/CP-4C@EUR` is the literal analyst submission and
`t414.json` the CP-1 T4.14 register of the shifted pack. The default (no context) output is the
frozen `cases/cp4c-owner/` oracle, read through the Stage 1 builders of `test_method_cp4c`.

The EUR inputs are the frozen CP-4C fixtures restated by the oracle's mapping rule (every
four-digit calendar year +1, the two-digit `Q4 25` label +1, `US$`/`USD` to `EUR`; amounts never
change), the same restatement `test_periods_currency_cp2g_shifted` applies to CP-2G. Every node
drives the core, `_lines`, `validate_restructuring` and `context_block` over hand-built
`Upstream` values, so none runs a store.
"""

import dataclasses
import hashlib
import json
import re
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from functools import cache
from typing import Any

import pytest
import test_cp4c_valuation_context as vc
import test_method_cp4c as m
import test_period_basis as pb
import view_tree

from deploy_vii.contracts import Fact, Source, Span
from deploy_vii.preparation import PreparedPack
from deploy_vii.report_view import fact_spelling, figure_unit
from deploy_workflow.context import ContextRefused, RunContext
from deploy_workflow.owners import cp2g, cp4c
from deploy_workflow.owners.period_basis import (
    DEFAULT_BASIS,
    PeriodBasis,
    PeriodRefused,
    period_basis,
)

EXP: dict[str, Any] = pb._load("expected.json")
SUBS: dict[str, Any] = pb._load("submissions.json")
T414: dict[str, Any] = pb._load("t414.json")
EUR_KEY: dict[str, Any] = EXP["module_oracles"]["CP-4C@EUR"]["expected"]
R2: dict[str, Any] = EXP["runs"]["R2"]["modules"]["CP-4C"]
R5: dict[str, Any] = EXP["runs"]["R5"]["modules"]["CP-4C"]
EUR_SUBMISSION: dict[str, Any] = SUBS["modules"]["CP-4C@EUR"]["submission"]["restructuring_fulcrum"]
FIG = re.compile(r"\{\{FIG:([a-z_0-9]+)\|([^}]*)\}\}")
_YEAR = re.compile(r"(?<!\d)(20\d\d)(?!\d)")
_LABEL = re.compile(r"\b((?:LTM )?Q[1-4]) 25\b")


def shift(text: str) -> str:
    """The oracle's mapping rule (`manifest.json#mapping_rules`): years +1, `Q4 25` +1, EUR."""
    text = _YEAR.sub(lambda hit: str(int(hit[1]) + 1), text)
    text = _LABEL.sub(lambda hit: f"{hit[1]} 26", text)
    return text.replace("US$", "EUR").replace("USD", "EUR")


def _basis(run: str) -> PeriodBasis:
    settings = SUBS["contexts"][run]["run"]
    context = pb._context(settings["current_period"], settings["reporting_currency"])
    return period_basis(context, pb._oracle_facts(T414["contexts"][run]["rows"]))


EUR = _basis("R2")


# --- the EUR 2026 inputs: the frozen fixtures restated by the mapping rule ------------------------


def _shifted(fact: Fact) -> Fact:
    update: dict[str, Any] = {}
    for name in ("label", "period", "limitation", "currency", "text", "formula"):
        value = getattr(fact, name)
        if isinstance(value, str) and shift(value) != value:
            update[name] = shift(value)
    return fact.model_copy(update=update) if update else fact


def _shifted_source(source: Source) -> Source:
    spans = tuple(Span(locator=s.locator, text=shift(s.text)) for s in source.spans)
    digest = hashlib.sha256("\f".join(s.text for s in spans).encode("utf-8")).hexdigest()
    return source.model_copy(update={"spans": spans, "sha256": digest})


def _eur_cp1() -> cp4c.Cp1Head:
    frozen = m._context("positive").cp1
    facts = []
    for metric, record in EUR_KEY["cp1_inputs"].items():
        facts.append(m._cp1_t410(metric, record).model_copy(update={"currency": "EUR"}))
    return dataclasses.replace(
        frozen,
        t410=tuple(facts),
        secured_status=_shifted(frozen.secured_status),
        seniority=_shifted(frozen.seniority),
    )


def _eur_cp2g() -> cp4c.Cp2gHead:
    frozen = m._context("positive").cp2g
    return dataclasses.replace(
        frozen,
        ebitda=tuple(
            dataclasses.replace(e, year=shift(e.year), fact=_shifted(e.fact)) for e in frozen.ebitda
        ),
        base_first=_shifted(frozen.base_first),
        down_first=_shifted(frozen.down_first),
        down_ebitda_source=_shifted(frozen.down_ebitda_source),
        down_interest_source=_shifted(frozen.down_interest_source),
    )


@cache
def eur_context(basis: PeriodBasis = EUR) -> cp4c.Cp4cContext:
    frozen = m._context("positive")
    pack = PreparedPack(
        run=frozen.pack.run, sources=tuple(_shifted_source(s) for s in frozen.pack.sources)
    )
    return dataclasses.replace(
        frozen,
        pack=pack,
        cp1=_eur_cp1(),
        cp2a=dataclasses.replace(frozen.cp2a, facts=tuple(_shifted(f) for f in frozen.cp2a.facts)),
        cp2g=_eur_cp2g(),
        basis=basis,
    )


def _figure_ids() -> dict[str, str]:
    ids = {}
    for name, fig in m.SUBMISSIONS["figures"].items():
        if fig["source"] == "cp1":
            ids[name] = m._cp1_id(EUR_KEY["cp1_inputs"][fig["metric"]]["label"])
        else:
            ids[name] = str(fig["fact_id"])
    return ids


def _bound(obj: Any) -> Any:
    ids = _figure_ids()
    if isinstance(obj, str):
        return FIG.sub(lambda hit: "{" + ids[hit[1]] + "|" + hit[2] + "}", obj)
    if isinstance(obj, list):
        return [_bound(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _bound(v) for k, v in obj.items()}
    return obj


def eur_payload() -> dict[str, Any]:
    payload: dict[str, Any] = _bound(json.loads(json.dumps(EUR_SUBMISSION)))
    return payload


def eur_inputs() -> cp4c.Cp4cInputs:
    return cp4c.Cp4cInputs(context=eur_context(), submission=m._submission(eur_payload()))


@cache
def eur_result() -> cp4c.RestructuringResult:
    return cp4c.compute(eur_inputs())


# --- the basis the tests run on is the oracle's ----------------------------------------------------


def test_the_eur_basis_is_the_oracles() -> None:
    key = EXP["period_basis"]["EUR"]
    assert (EUR.currency, EUR.money_unit) == (key["currency"], key["money_unit"])
    assert list(EUR.year_labels) == key["year_labels"]
    assert (EUR.bs_column, EUR.bs_period) == (key["bs_column"], key["bs_period"])
    assert EUR.balance_date_text == key["balance_date_text"]


# --- (e) the EUR run against the pinned module oracle -----------------------------------------------


def test_eur_facts_equal_the_oracle() -> None:
    got = [m._record(c) for c in eur_result().cells]
    assert [r["fact_id"] for r in got] == [r["fact_id"] for r in EUR_KEY["facts"]]
    for have, want in zip(got, EUR_KEY["facts"], strict=True):
        assert have == want, want["fact_id"]


def test_eur_tables_equal_the_oracle() -> None:
    got = [
        {
            "table_id": t.table_id,
            "title": t.title,
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)} for r in t.rows
            ],
        }
        for t in eur_result().tables
    ]
    assert got == EUR_KEY["tables"]


def test_eur_claims_equal_the_oracle() -> None:
    result = eur_result()
    facts = m._facts_by_id(result)
    ids = _figure_ids()
    assert [c.claim_id for c in result.claims] == [c["claim_id"] for c in EUR_KEY["claims"]]
    for have, want in zip(result.claims, EUR_KEY["claims"], strict=True):
        assert have.text == _bound(want["text"]), want["claim_id"]
        assert have.limitation == want["limitation"], want["claim_id"]
        assert list(have.references) == [ids[n] for n in want["cp1_references"]]
        assert m._render(have.text, facts) == want["text_rendered"], want["claim_id"]


def test_eur_own_limitations_equal_the_oracle() -> None:
    assert list(eur_result().own_limitations) == EUR_KEY["own_limitations"]


def test_eur_waterfall_equals_the_oracle() -> None:
    result = eur_result()
    for case, want in EUR_KEY["waterfall"].items():
        fall = result.waterfalls[case]
        assert result.enterprise_values[case].amount == Decimal(want["ev"]), case
        assert list(fall.value_break or ()) == want["break"], case
        assert m._norm(fall.residual.amount) == want["residual"], case


def test_eur_figures_are_spelled_as_the_oracle_states() -> None:
    facts = m._facts_by_id(eur_result())
    ids = _figure_ids()
    for name, want in EUR_KEY["figures"].items():
        fact = facts[ids[name]]
        _unit_class, _state, shown = fact_spelling(fact, None)
        assert f"{shown} {figure_unit(fact)}" == want["spelled"], name
        assert figure_unit(fact) == want["unit_token"], name


def _strings(result: cp4c.RestructuringResult) -> Iterator[str]:
    for cell in result.cells:
        fact = cell.fact
        for value in (fact.label, fact.text, fact.currency, fact.period, fact.formula):
            if value:
                yield value
        yield cell.shown or ""
    for table in result.tables:
        yield table.title
        for row in table.rows:
            yield row.label
    for claim in result.claims:
        yield claim.text
        yield claim.limitation or ""
    yield from result.own_limitations


def test_eur_run_uses_the_money_unit_and_states_no_dollar() -> None:
    """`runs/R2/modules/CP-4C`: the required tokens appear and the forbidden ones nowhere."""
    text = "\n".join(_strings(eur_result()))
    for token in R2["required_tokens"]:
        assert token in text, token
    for token in R2["forbidden_tokens"]:
        assert token not in text, token
    assert R2["money_unit"] == EUR.money_unit
    amounts = [
        c.fact for c in eur_result().cells if c.fact.unit == "MILLIONS" and c.fact.status == "known"
    ]
    assert amounts and {f.currency for f in amounts} == {EUR.currency}


# --- the balance date and the claim column --------------------------------------------------------


def test_the_balance_date_limitation_states_the_run_balance_date() -> None:
    claims_line = next(x for x in eur_result().own_limitations if x.startswith("Claims are the"))
    assert R2["balance_date_limitation"] in claims_line
    assert "2025" not in claims_line


def test_the_old_claim_column_is_refused_under_a_2026_base() -> None:
    """`runs/R2/modules/CP-4C.claims_period_column`: the 2026 column is the only one a source_row
    claim may name; the frozen 2025 page still has the 2025 column, so the refusal states both."""
    frozen = m._context("positive")
    ctx = dataclasses.replace(eur_context(), pack=frozen.pack)  # the statement still has Q4 2025
    old_column = next(
        c["period_column"] for c in m._payload("positive")["claims"] if c["period_column"]
    )
    assert old_column != R2["claims_period_column"]
    payload = eur_payload()
    for c in payload["claims"]:
        if c["period_column"]:
            c["period_column"] = old_column
    issues = cp4c.payload_issues(json.dumps(payload), ctx)
    want = (
        f"claims[{{i}}].period_column: claims are the {R2['balance_date_limitation']} balances; "
        f"use {R2['claims_period_column']}"
    )
    rows = [i for i, c in enumerate(payload["claims"]) if c["amount_source"] == "source_row"]
    assert rows
    for i in rows:
        assert want.format(i=i) in issues
    assert not any("31 December 2025" in x for x in issues)


def test_the_new_claim_column_is_accepted_under_a_2026_base() -> None:
    column = R2["claims_period_column"]
    sources = [c["period_column"] for c in EUR_SUBMISSION["claims"] if c["period_column"]]
    assert sources and set(sources) == {column}
    assert cp4c.payload_issues(json.dumps(eur_payload()), eur_context()) == ()


# --- (d) the forecast years -------------------------------------------------------------------------


def test_the_forecast_years_are_the_bases_three() -> None:
    labels = EXP["period_basis"]["EUR"]["year_labels"]
    years = {v["ebitda_year"] for v in EUR_SUBMISSION["valuation"]}
    assert years <= set(labels)
    cp2g_years = {e.year for e in eur_context().cp2g.ebitda}
    assert cp2g_years == set(labels)


@pytest.mark.parametrize("year", ["FY2026", "FY2030"])
def test_a_year_outside_the_forecast_is_refused_alone(year: str) -> None:
    """The base year (and one past the last) is no forecast year. The key states no issue text
    for it (UNPINNED): the frozen r06 frame is `valuation.<i>.ebitda_year: Input should be ...`,
    here over the basis's year labels."""
    payload = eur_payload()
    payload["valuation"][0]["ebitda_year"] = year
    issues = cp4c.payload_issues(json.dumps(payload), eur_context())
    labels = EXP["period_basis"]["EUR"]["year_labels"]
    assert len(issues) == 1
    assert issues[0].startswith("valuation.0.ebitda_year: ")
    assert all(f"'{label}'" in issues[0] for label in labels)
    assert year not in issues[0]


def test_the_default_year_refusal_is_the_frozen_one() -> None:
    refusal = next(r for r in m.EXPECTED["refusals"] if r["id"] == "r06")
    got = cp4c.payload_issues(m._refusal_text("r06"), m._context("positive"))
    assert list(got) == refusal["expected_issues"]


# --- the default output is the frozen oracle --------------------------------------------------------


@pytest.mark.parametrize("case", m.RUNS)
def test_the_default_output_is_the_frozen_oracle(case: str) -> None:
    ctx = m._context(case)
    assert ctx.basis is DEFAULT_BASIS
    result = m._result(case)
    assert m._records(result) == m._oracle_records(case)
    assert list(result.own_limitations) == m.EXPECTED["cases"][case]["own_limitations"]
    assert cp4c.LTM_COLUMN == DEFAULT_BASIS.ltm_column
    assert cp4c.LTM_PERIOD == DEFAULT_BASIS.ltm_period


def test_the_default_view_equals_the_committed_view_tree() -> None:
    ctx = m._context("positive")
    upstream = dataclasses.replace(
        vc.upstream_of(None), inherited=("An inherited limitation, as a settled store gives",)
    )  # the committed tree holds one inherited limitation
    body = json.dumps(cp4c.context_block(pack=ctx.pack, upstream=upstream), ensure_ascii=False)
    assert view_tree.entry(body) == view_tree.load("cp4c")["positive"]
    assert "context_issue" not in json.loads(body)


# --- the reader is year-neutral, the basis picks the column ----------------------------------------


def _other_year(facts: tuple[Fact, ...]) -> tuple[Fact, ...]:
    return tuple(_shifted(f).model_copy(update={"fact_id": f.fact_id + ":26"}) for f in facts)


def test_the_reader_keeps_every_ltm_column_and_the_basis_selects_one() -> None:
    frozen = m._context("positive").cp1.t410
    both = (*frozen, *eur_context().cp1.t410)
    kept = cp4c._ltm_facts((*both, frozen[0].model_copy(update={"label": "T4.10 other"})))
    assert {f.label for f in kept} == {f.label for f in both}
    assert cp4c.select_cp1(kept)["ebitda"].label == frozen[1].label
    assert cp4c.select_cp1(kept, EUR)["ebitda"].label == EUR_KEY["cp1_inputs"]["ebitda"]["label"]
    assert [f.label.rsplit(" · ", 1)[-1] for f in cp4c._ltm_facts(both)] == [
        "total_debt",
        "total_debt",
        "ebitda",
        "ebitda",
    ]


def test_the_cp2g_reader_takes_the_year_from_the_fact_not_a_fixed_list() -> None:
    eur = eur_context().cp2g
    read = cp2g.Cp2gHead(
        status="restricted",
        head_sha256="0" * 64,
        facts=(
            *(e.fact for e in eur.ebitda),
            eur.base_first,
            eur.down_first,
            eur.down_ebitda_source,
            eur.down_interest_source,
        ),
    )
    got = cp4c.cp2g_of(read)
    assert [e.year for e in got.ebitda] == [e.year for e in eur.ebitda]
    assert {e.year for e in got.ebitda} == set(EXP["period_basis"]["EUR"]["year_labels"])
    assert got.of("base", EUR.year_labels[0], EUR).fact.fact_id == "T2H.4.b26.ebitda"
    with pytest.raises(ValueError, match="CP-4C needs exactly one CP-2G EBITDA"):
        got.of("base", "FY2026", EUR)


# --- the run's basis through the validator and the view --------------------------------------------


def _upstream(
    ctx: cp4c.Cp4cContext, register: list[Fact] | None = None, key: str = "R2"
) -> cp4c.Upstream:
    base = vc.upstream_of(None)
    rows = pb._oracle_facts(T414["contexts"][key]["rows"]) if register is None else register
    return dataclasses.replace(
        base, cp1=ctx.cp1, cp2a=ctx.cp2a, cp2g=ctx.cp2g, cp4=ctx.cp4, register=tuple(rows)
    )


def _with_context(monkeypatch: pytest.MonkeyPatch, context: RunContext | None) -> None:
    monkeypatch.setattr(cp4c, "context_facts", lambda pack: context)


def _eur_pack_context(period: str = "q4-2026", currency: str = "EUR") -> RunContext:
    return pb._context(period, currency)


def test_a_2026_context_reads_the_oracle_basis_and_composes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = eur_context()
    _with_context(monkeypatch, _eur_pack_context())
    upstream = _upstream(ctx)
    sub = m._submission(eur_payload())
    assert cp4c._basis_of(ctx.pack, upstream) == EUR
    assert cp4c._lines(ctx.pack, sub, upstream) == ()
    assert cp4c._inputs(ctx.pack, sub, upstream).context.basis == EUR


def test_the_view_offers_the_2026_facts_on_the_2026_basis(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = eur_context()
    _with_context(monkeypatch, _eur_pack_context())
    block: Any = cp4c.context_block(pack=ctx.pack, upstream=_upstream(ctx))
    assert "context_issue" not in block
    assert {f["period"] for f in block["cp1_facts"]} == {EUR.ltm_period}
    assert [e["year"] for e in block["ebitda_offered"]][:3] == list(EUR.year_labels)
    assert all(EUR.money_unit not in f["shown"] or "EUR" in f["shown"] for f in block["cp1_facts"])


def test_an_unsupported_period_is_one_issue_line_and_an_empty_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`runs/R5/modules/CP-4C`: refused at the entry validator with the key's text; the view
    never raises and carries the same line, offering nothing."""
    ctx = eur_context()
    _with_context(monkeypatch, pb._context("h2-2026", "USD"))
    upstream = _upstream(ctx)
    sub = m._submission(eur_payload())
    for issues in (
        cp4c.validate_restructuring(pack=ctx.pack, submission=sub, upstream=upstream),
        cp4c._lines(ctx.pack, sub, upstream),
    ):
        assert len(issues) == 1
        assert R5["issue_contains"] in issues[0]
    assert R5["figures_produced"] is False
    block: Any = cp4c.context_block(pack=ctx.pack, upstream=upstream)
    assert set(block) == {"upstream", "context_issue", "inherited_limitations"}
    assert R5["issue_contains"] in block["context_issue"]
    with pytest.raises(ValueError, match="h2-2026"):
        cp4c._inputs(ctx.pack, sub, upstream)


def test_a_currency_the_register_does_not_report_is_one_issue_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = eur_context()
    _with_context(monkeypatch, pb._context("fy-2026", "EUR"))
    upstream = _upstream(ctx, key="R1")  # R1's register reports USD
    sub = m._submission(eur_payload())
    issues = cp4c._lines(ctx.pack, sub, upstream)
    assert len(issues) == 1 and "reporting_currency EUR, but CP-1 reports USD" in issues[0]
    block: Any = cp4c.context_block(pack=ctx.pack, upstream=upstream)
    assert block["context_issue"] == issues[0] and "claims_offered" not in block


def test_a_non_calendar_base_year_is_refused_like_cp2g(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ruling P8T6-R1 (no key states a non-calendar forecast window): a July-June base year is
    one `PeriodRefused` line, the same refusal CP-2G gives (P8T5-R1), carried by the view."""
    ctx = eur_context()
    register = pb._two("FY2026", "2026-04-01", "2026-06-30", "2025-07-01", "2026-06-30")
    _with_context(monkeypatch, pb._context("fy-2026", "USD"))
    upstream = _upstream(ctx, register)
    assert period_basis(pb._context("fy-2026"), register).ltm_end == date(2026, 6, 30)
    with pytest.raises(PeriodRefused) as refused:
        cp2g.require_calendar(period_basis(pb._context("fy-2026"), register))
    sub = m._submission(eur_payload())
    issues = cp4c._lines(ctx.pack, sub, upstream)
    assert issues == (str(refused.value),)
    assert "calendar fiscal year" in issues[0]
    assert cp4c.context_block(pack=ctx.pack, upstream=upstream)["context_issue"] == issues[0]


def test_a_refused_context_keeps_the_frozen_line_and_the_view_offers_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P8T4-R2: the view carries `Context refused: ...` and offers what the default basis
    selects when the CP-1 is the default year; the validator keeps its single frozen line."""
    ctx = m._context("positive")
    upstream = vc.upstream_of(None)

    def refuse(pack: PreparedPack) -> RunContext:
        raise ContextRefused(["run.current_period: not a period"])

    monkeypatch.setattr(cp4c, "context_facts", refuse)
    monkeypatch.setattr(cp4c, "pins_of", lambda module, pack: refuse(pack))  # the pin lines' read
    block: Any = cp4c.context_block(pack=ctx.pack, upstream=upstream)
    assert block["context_issue"] == "Context refused: run.current_period: not a period"
    assert block["claims_offered"] and block["cp1_facts"]
    assert cp4c._basis_of(ctx.pack, upstream) is DEFAULT_BASIS
    sub = m._submission(m._bind_all(m._payload("positive")))
    assert cp4c._lines(ctx.pack, sub, upstream)[-1] == block["context_issue"]


def test_a_refused_context_over_a_2026_cp1_offers_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = eur_context()

    def refuse(pack: PreparedPack) -> RunContext:
        raise ContextRefused(["run.current_period: not a period"])

    monkeypatch.setattr(cp4c, "context_facts", refuse)
    block: Any = cp4c.context_block(pack=ctx.pack, upstream=_upstream(ctx))
    assert set(block) == {"upstream", "context_issue", "inherited_limitations"}
    assert block["context_issue"].startswith("Context refused: ")


def test_a_blank_usd_base_keeps_the_default_basis(monkeypatch: pytest.MonkeyPatch) -> None:
    """P8-R3: a context with no base period under USD is the frozen Phase 6 behaviour."""
    ctx = m._context("positive")
    _with_context(monkeypatch, pb._context("", "USD"))
    assert cp4c._basis_of(ctx.pack, vc.upstream_of(None)) is DEFAULT_BASIS
