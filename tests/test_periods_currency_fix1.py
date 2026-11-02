"""Phase 8 Task 7, fix round 1: CP-L10's run currency over a store, the P8-R5 views, the receipt
path's context lookup and the liquidity chart axis.

Answer keys are read at run time from `cases/periods-currency-owner/expected.json`; the helpers of
`test_periods_currency_misc` build the shifted EUR inputs.
"""

from __future__ import annotations

import importlib
import json
from types import SimpleNamespace
from typing import Any, cast

import pytest
from chart_wiring_c import cp2d_view, cp3c_view

from deploy_vii.contracts import Fact
from deploy_vii.execution import Attempt, Execution, StepSubmission
from deploy_workflow import earnings, liquidity_series
from deploy_workflow import earnings_workflow as ew
from deploy_workflow.owners import cp1b, cp2a, cpl10

misc: Any = importlib.import_module("test_periods_currency_misc")
own: Any = importlib.import_module("test_owner_cp1b")
own_l10: Any = importlib.import_module("test_owner_cpl10")
KEY = misc.KEY
VIEW_TOPICS = KEY["module_oracles"]["CP-L10@EUR"]["expected"]["view_topics"]


def _pack(
    currency: str,
    *,
    current: str = "q4-2026",
    prior: str = "q3-2026",
    issuer: str | None = None,
    name: str = "ctx-match",
) -> Any:
    def edit(document: dict[str, Any]) -> None:
        document["run"].update(
            current_period=current, prior_period=prior, reporting_currency=currency
        )
        if issuer is not None:
            document["identity"]["issuer_name"] = issuer

    return own._ctx_pack(name, edit)


# --- CP-L10 over a store: the run currency, the register and P8-R5 ---------------------------------


def _register(currency: str | None) -> list[Fact]:
    rows: list[Fact] = own_l10._t414_rows(*((2026, q) for q in (1, 2, 3, 4)))
    if currency is None:
        return rows
    extra = [
        Fact(
            fact_id=f"{pid}:{field}",
            label=field,
            table_id="T4.14",
            row_id=pid,
            field=field,
            text=text,
        )
        for pid in {f.row_id for f in rows}
        for field, text in (("currency", currency), ("unit", "MILLIONS"))
    ]
    return [*rows, *extra]


class _L10Store:
    def __init__(self, pack: Any, facts: list[Fact], payload: str = "") -> None:
        self._pack, self._facts, self._payload = pack, facts, payload
        self.head_module = None

    def read(self) -> Any:
        return SimpleNamespace(
            run=SimpleNamespace(issuer_name="Northbridge", as_of=None, case_kind="synthetic")
        )

    def pack(self, snapshot: Any = None) -> Any:
        return self._pack

    def payload(self, sha: str) -> str:
        return self._payload


@pytest.fixture
def l10_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    head = SimpleNamespace(status="accepted", sha256="0" * 64)

    def bound(store: _L10Store, attempt: Any, module_id: str) -> Any:
        return head, SimpleNamespace(facts=tuple(store._facts))

    monkeypatch.setattr(cpl10, "_bound", bound)
    monkeypatch.setattr(cpl10, "inherited_limitations", lambda *a, **k: ())


def _l10_facts(operand_currency: str, register: list[Fact]) -> list[Fact]:
    operands: list[Fact] = list(misc._l10_upstream(operand_currency).cp1_facts.values())
    return [*register, *operands]


def _l10_read(pack: Any, facts: list[Fact], payload: str = "") -> Any:
    store = cast(Execution, _L10Store(pack, facts, payload))
    attempt = cast(Attempt, SimpleNamespace(inputs=()))
    return store, attempt


def test_l10_store_eur_context_reads_the_oracle_view(l10_bound: None) -> None:
    store, attempt = _l10_read(
        _pack("EUR", name="ctx-l10", prior=""), _l10_facts("EUR", _register("EUR"))
    )
    upstream = cpl10.cpl10_upstream(store, attempt)
    assert isinstance(upstream, cpl10.RunUpstream) and upstream.currency.money_unit == "EUR m"
    body = json.loads(cpl10.view(store, attempt)[1])
    assert body["topics"] == VIEW_TOPICS
    assert "context_issue" not in body


def test_l10_store_usd_context_over_the_eur_register_is_a_context_issue(l10_bound: None) -> None:
    facts = _l10_facts("EUR", _register("EUR"))
    store, attempt = _l10_read(_pack("USD", name="ctx-l10", prior=""), facts, misc._l10_payload())
    body = json.loads(cpl10.view(store, attempt)[1])
    assert body["periods"] == [] and body["topics"] == []
    assert body["context_issue"] == "run.reporting_currency USD, but CP-1 reports EUR"
    step = SimpleNamespace(payload_sha256="x")
    outcome = cpl10._validate_step(
        store, _pack("USD", name="ctx-l10", prior=""), cast(Attempt, SimpleNamespace(steps=(step,)))
    )
    assert outcome.issues == (f"CP-L10: {body['context_issue']}",)


def test_l10_blank_base_eur_is_a_context_issue(l10_bound: None) -> None:
    store, attempt = _l10_read(
        _pack("EUR", current="", prior="", name="ctx-l10"), _l10_facts("EUR", _register("EUR"))
    )
    body = json.loads(cpl10.view(store, attempt)[1])
    assert body["periods"] == [] and "blank" in body["context_issue"]


def test_l10_register_without_a_currency_field_follows_the_run_currency(l10_bound: None) -> None:
    """Ruling P8T7-R6: a USD run keeps the parent's behaviour; any other currency refuses."""
    facts = _l10_facts("USD", _register(None))
    store, attempt = _l10_read(_pack("USD", name="ctx-l10", prior=""), facts)
    upstream = cpl10.cpl10_upstream(store, attempt)
    assert type(upstream) is cpl10.Upstream and upstream.context_issue is None
    assert [q.period[:5] for q in upstream.quarters] == ["Q1 26", "Q2 26", "Q3 26", "Q4 26"]
    store, attempt = _l10_read(
        _pack("EUR", name="ctx-l10", prior=""), _l10_facts("EUR", _register(None))
    )
    refused = cpl10.cpl10_upstream(store, attempt).context_issue
    assert refused is not None and "reports no currency" in refused


def test_l10_run_upstream_refuses_an_operand_in_another_currency() -> None:
    up = misc._l10_upstream("EUR")
    usd = {
        k: f.model_copy(update={"currency": "USD"}) if f.currency else f
        for k, f in up.cp1_facts.items()
    }
    fields = {f: getattr(up, f) for f in up.__dataclass_fields__}
    fields["cp1_facts"] = usd
    with pytest.raises(cpl10.UpstreamError, match="operand currency USD is not EUR"):
        cpl10.RunUpstream(**fields)


# --- CP-2A: a refused context is one line in both the view and the validator ----------------------


def test_cp2a_refused_context_is_one_line_in_view_and_validator() -> None:
    pack = _pack("EUR", issuer="Somebody Else")
    upstream = misc._cp2a_upstream("EUR")
    body = cp2a.context_block(pack=pack, upstream=upstream)
    issues = cp2a.validate_downside(
        pack=pack, submission=misc._cp2a_inputs("EUR").submission, upstream=upstream
    )
    assert str(body["context_issue"]).startswith("Context refused: identity.issuer_name")
    assert body["base_periods"] == [] and issues == (body["context_issue"],)


# --- CP-1B: the view and the validator agree ----------------------------------------------------------


def test_cp1b_view_without_a_context_offers_what_the_validator_accepts() -> None:
    producer = misc.shifted("USD")
    pack = own._ctx_pack("ctx-match").model_copy(update={"sources": ()})
    body = json.loads(cp1b.view(own._Store(producer, "", pack), own._attempt(producer))[1])
    assert [(p["prior_period_id"], p["current_period_id"]) for p in body["pairs"]] == [
        ("q3-2026", "q4-2026")
    ]
    assert misc._owner_step(producer, pack).output is not None


def test_cp1b_refused_register_has_the_same_text_in_view_and_validator() -> None:
    base = misc.shifted("EUR")
    row = next(f.row_id for f in base.facts if f.table_id == "T4.14")
    twin = [
        f.model_copy(update={"fact_id": f.fact_id + ":dup", "row_id": row + ".dup"})
        for f in base.facts
        if f.table_id == "T4.14" and f.row_id == row
    ]
    producer = base.model_copy(update={"facts": (*base.facts, *twin)})
    pack = _pack("EUR")
    body = json.loads(cp1b.view(own._Store(producer, "", pack), own._attempt(producer))[1])
    assert body["pairs"] == []
    assert misc._owner_step(producer, pack).issues == (body["context_issue"],)


def test_r5b_cp1b_through_the_context_with_the_oracle_pair() -> None:
    want = KEY["runs"]["R5b"]["modules"]["CP-1B"]
    base = misc.shifted("USD")
    q2 = {
        "period_id": "q2-2026",
        "fiscal_quarter": "Q2",
        "start_date": "2026-04-01",
        "end_date": "2026-06-30",
    }
    extra = tuple(
        f.model_copy(
            update={
                "fact_id": f.fact_id.replace("q3-2026", "q2-2026"),
                "row_id": "period.q2-2026",
                "period": "q2-2026",
                "text": q2.get(f.field, f.text),
            }
        )
        for f in base.facts
        if f.row_id == "period.q3-2026"
    )
    producer = base.model_copy(update={"facts": (*base.facts, *extra)})
    pack = _pack("USD", current="q3-2026", prior="q2-2026")
    body = json.loads(cp1b.view(own._Store(producer, "", pack), own._attempt(producer))[1])
    step = StepSubmission(step_id="earnings_delta", inputs=(), payload_sha256="b" * 64)
    payload = own._payload("q2-2026", "q3-2026", "flat_sequential")
    outcome = cp1b._validate_step(
        own._Store(producer, payload, pack), pack, own._attempt(producer, step)
    )
    assert body["pairs"] == [] and outcome.output is None
    assert len(outcome.issues) == 1 and want["issue_contains"] in outcome.issues[0]


# --- the receipt path's context lookup -----------------------------------------------------------------


def test_preflight_follows_the_context_currency() -> None:
    head = misc.shifted("EUR")
    ew._preflight(head, "q3-2026", "q4-2026", _pack("EUR"))
    with pytest.raises(ValueError, match="^incompatible_dimensions$"):
        ew._preflight(head, "q3-2026", "q4-2026", _pack("USD"))
    with pytest.raises(ValueError, match="^incompatible_dimensions$"):
        ew._preflight(head, "q3-2026", "q4-2026", _pack("EUR", issuer="Somebody Else"))


def test_grant_reads_the_context_currency(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_grant` hands the delta core the context's currency. The test head has no T4.10 selection
    rows, so `_grant` stops at `identity_mismatch` after the core; the core's currency is recorded."""
    head = misc.shifted("EUR")
    view = cp1b.cp1_view(head)
    seen: list[str] = []
    core = earnings.build_earnings_delta_in

    def spy(module: Any, prior: str, current: str, currency: str) -> Any:
        seen.append(currency)
        return core(module, prior, current, currency)

    monkeypatch.setattr(ew, "_full_cp1", lambda store, binding: (head, view))
    monkeypatch.setattr(ew, "build_earnings_delta_in", spy)

    class Store:
        def __init__(self, pack: Any) -> None:
            self._pack = pack

        def pack(self, snapshot: Any = None) -> Any:
            return self._pack

    for pack, currency in ((_pack("EUR"), "EUR"),):
        with pytest.raises(ew.OwnerError, match="identity_mismatch"):
            ew._grant(cast(Execution, Store(pack)), cast(Any, None), "q3-2026", "q4-2026")
        assert seen[-1] == currency
    with pytest.raises(ValueError, match="^incompatible_dimensions$"):
        ew._grant(cast(Execution, Store(_pack("USD"))), cast(Any, None), "q3-2026", "q4-2026")


# --- the liquidity chart axis (ruling P8T7-R7) -----------------------------------------------------------


def _recurrency(view: Any, module_id: str, currency: str, *, alternate: bool = False) -> Any:
    """The module with its USD facts stated in `currency` (every other one when `alternate`)."""
    module = next(m for m in view.modules if m.module_id == module_id)
    facts = []
    count = 0
    for f in module.facts:
        if f.currency == "USD":
            count += 1
            if not alternate or count % 2:
                f = f.model_copy(update={"currency": currency})
        facts.append(f)
    return module.model_copy(update={"facts": tuple(facts)})


@pytest.mark.parametrize(("module_id", "build"), [("CP-2D", cp2d_view), ("CP-3C", cp3c_view)])
def test_liquidity_axis_states_the_charted_currency(module_id: str, build: Any) -> None:
    view = build("positive")
    chart = (
        liquidity_series.cp2d_chart_series
        if module_id == "CP-2D"
        else liquidity_series.cp3c_chart_series
    )
    assert {s.axis_label for s in chart(_recurrency(view, module_id, "USD"))} == {"US$ m"}
    assert {s.axis_label for s in chart(_recurrency(view, module_id, "EUR"))} == {"EUR m"}


@pytest.mark.parametrize(("module_id", "build"), [("CP-2D", cp2d_view), ("CP-3C", cp3c_view)])
def test_liquidity_axis_refuses_more_than_one_currency(module_id: str, build: Any) -> None:
    chart = (
        liquidity_series.cp2d_chart_series
        if module_id == "CP-2D"
        else liquidity_series.cp3c_chart_series
    )
    mixed = _recurrency(build("positive"), module_id, "EUR", alternate=True)
    with pytest.raises(ValueError, match="more than one currency"):
        chart(mixed)
