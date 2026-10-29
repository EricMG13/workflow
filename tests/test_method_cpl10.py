"""CP-L10 Stage 1: the change-screen calculation against the frozen oracle (amendment 1).

Inputs are built from the oracle's own source facts (``cases.*.view_topics``, ``cases.*.topics``)
and the manifest's fact selection rule, never from the module. The run-bound markers of the
oracle (head result sha256, status word, CP-1 calculation ids and citations) are bound here to
this test's upstream values; Stage 2 binds them from the store.
"""

import hashlib
import json
from copy import deepcopy
from datetime import date
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from defect_classes import BLANK_CASES, Adapter, BlankCase, blank_failure

from deploy_vii import prose
from deploy_vii.contracts import (
    Citation,
    Contract,
    Fact,
    ReportTable,
    TableColumn,
    TableRow,
    validate_tables,
)
from deploy_workflow.owners import cpl10

CASE = Path(__file__).resolve().parents[1] / "cases" / "cpl10-owner"
EXPECTED: dict[str, Any] = json.loads((CASE / "expected.json").read_text())
SUBMISSIONS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text())
MANIFEST: dict[str, Any] = json.loads((CASE / "manifest.json").read_text())
CP1_MARKER = "{{CP1_CALCULATION_ID}}"
CITATIONS_MARKER = "{{CP1_CITATIONS:"
GAP = "G1"  # the report-wide G# is bound at run time; any valid gap id spells the same pattern
FINANCIAL_SHA = "82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _cp1_facts() -> list[Fact]:
    """The 28 CP-1 T4.10 operands, from the oracle's view values and observed value classes.

    Each carries what a real T4.10 fact carries and the copy must handle: a citation, a
    calculation id, a formula and CP-1's own 0 dp ``decimals``.
    """
    rule = MANIFEST["fact_selection_rule"]
    column = {c["period"]: c["label"] for c in rule["columns"].values()}
    value_class: dict[str, Any] = {}
    for case in ("positive", "limited"):
        for topic in EXPECTED["cases"][case]["topics"]:
            for end in ("from", "to"):
                value_class[topic[end]["label"]] = topic[end]["value_class"]
    facts = []
    for page, topic in enumerate(EXPECTED["cases"]["positive"]["view_topics"], 2):
        money = topic["unit"] == "US$ m"
        for value in topic["values"]:
            label = f"{column[value['period']]} · {topic['cp1_metric']}"
            known = value["status"] == "known"
            facts.append(
                Fact(
                    fact_id="interface-fact:" + _digest(label),
                    label=label,
                    table_id="T4.10",
                    row_id=topic["cp1_metric"],
                    field="value",
                    status=value["status"],
                    amount=Decimal(value["amount_exact"]) if known else None,
                    unit="MILLIONS" if money else "MULTIPLE",
                    currency="USD" if money else None,
                    scale=Decimal(1000000) if money else Decimal(1),
                    decimals=0,
                    period=value["period"],
                    citations=(
                        Citation(
                            source_id="financial",
                            source_sha256=FINANCIAL_SHA,
                            locator=f"page:{page}",
                            quote=label,
                        ),
                    ),
                    calculation_id="canonical-kpi:" + _digest(label),
                    value_class=value_class[label],
                    formula=f"canonical KPI {topic['cp1_metric']}",
                    limitation=value["limitation"],
                )
            )
    assert len(facts) == 28 and len(value_class) == 28
    return facts


def _upstream(facts: list[Fact] | None = None) -> cpl10.Upstream:
    run = MANIFEST["run"]
    return cpl10.Upstream(
        issuer_name=run["issuer_name"],
        as_of=date.fromisoformat(run["as_of"]),
        cp0_status_word="Validated",  # distinct from CP-1's, so a swapped binding is caught
        cp0_result_sha256=_digest("cp0 head"),
        cp1_status_word="With limitations",
        cp1_result_sha256=_digest("cp1 head"),
        cp1_facts=cpl10.bind_operands(_cp1_facts() if facts is None else facts),
    )


UPSTREAM = _upstream()
RUN_MARKERS = {
    "{{CP0_RESULT_SHA256}}": UPSTREAM.cp0_result_sha256,
    "{{CP1_RESULT_SHA256}}": UPSTREAM.cp1_result_sha256,
    "{{CP0_STATUS_WORD}}": UPSTREAM.cp0_status_word,
    "{{CP1_STATUS_WORD}}": UPSTREAM.cp1_status_word,
}


def _bind_run(text: str) -> str:
    for marker, value in RUN_MARKERS.items():
        text = text.replace(marker, value)
    return text


def _payload(name: str) -> str:
    return json.dumps(SUBMISSIONS[name])


def _issues(sub: dict[str, Any], upstream: cpl10.Upstream = UPSTREAM) -> list[str]:
    return list(cpl10.validate_screen(submission=json.dumps(sub), upstream=upstream))


# --- arithmetic: composer fixtures, rank, rounding ------------------------------------------


@pytest.mark.parametrize("name", sorted(EXPECTED["fixtures"]["composer"]))
def test_screen_topic_fixture(name: str) -> None:
    case = EXPECTED["fixtures"]["composer"][name]
    start = None if case["from"] is None else Decimal(case["from"])
    close = None if case["to"] is None else Decimal(case["to"])
    screen = cpl10.screen_topic(start=start, close=close)
    assert screen.materiality == case["materiality"]
    assert screen.evidence == case["evidence"]
    assert screen.disposition == case["disposition"]
    assert screen.pct_status == case["pct_status"]
    assert screen.change == (None if case["change"] is None else Decimal(case["change"]))
    assert screen.pct == (None if case["pct"] is None else Decimal(case["pct"]))
    assert screen.pct_fraction == (
        None if case["pct_fraction"] is None else Fraction(case["pct_fraction"])
    )
    if case["pct_shown"] is not None:
        assert screen.pct is not None
        pct = Fact(fact_id="x", label="x", amount=screen.pct, unit="PERCENT", period="p")
        assert cpl10.shown_text(pct, GAP) == case["pct_shown"]


def test_rank_fixture() -> None:
    rows = EXPECTED["fixtures"]["rank"]["rows"]
    keys = []
    for index, (name, materiality, pct) in enumerate(rows):
        zero_base = pct == "zero base"
        fraction = None if pct in ("zero base", "none") else Fraction(pct)
        keys.append((cpl10.rank_key(materiality, zero_base, fraction, index), name))
    assert [name for _, name in sorted(keys)] == EXPECTED["fixtures"]["rank"]["expected_order"]


def test_quantisation_is_half_even_at_38_digits() -> None:
    # 0.111...1125 (39 significant digits) is a tie at the 38th: half-even keeps the even 2.
    tie = Fraction(int("1" * 37 + "25"), 10**39)
    assert cpl10._q38(tie) == Decimal("0." + "1" * 37 + "2")
    odd = Fraction(int("1" * 37 + "35"), 10**39)  # ...13|5 rounds up to the even 4
    assert cpl10._q38(odd) == Decimal("0." + "1" * 37 + "4")


def test_change_is_stored_exactly_not_rounded_to_38_digits() -> None:
    """R2 L1: CP-1 ratios carry 38 digits; their difference needs 39 and is stored whole."""
    start = Decimal("1.6666666666666666666666666666666666667")  # 5/3 at 38 digits
    close = Decimal("14.285714285714285714285714285714285714")  # 100/7 at 38 digits
    screen = cpl10.screen_topic(start=start, close=close)
    assert screen.change == Decimal("12.6190476190476190476190476190476190473")
    assert str(screen.change) == "12.6190476190476190476190476190476190473"
    assert screen.pct == cpl10._q38((Fraction(close) - Fraction(start)) / abs(Fraction(start)))


def test_change_is_exact_at_the_bound_magnitudes_and_after_a_zero_base() -> None:
    """The exact context does not trap on large amounts, and a zero base stores it exactly too."""
    low, high = Decimal("-999999999999999999.9999999999"), Decimal("999999999999999999.9999999999")
    assert cpl10.screen_topic(start=low, close=high).change == Decimal(
        "1999999999999999999.9999999998"
    )
    big = Decimal("1" + "0" * 37 + "." + "0" * 37 + "1")  # 76 digits; exact, not E+38 form
    assert cpl10.screen_topic(start=Decimal(0), close=big).change == big
    kept = cpl10.screen_topic(start=Decimal(1), close=big).change
    assert kept == Decimal("9" * 37 + "." + "0" * 37 + "1")


# --- operands --------------------------------------------------------------------------------


def test_operand_binding_refuses_missing_and_duplicate_labels() -> None:
    facts = _cp1_facts()
    with pytest.raises(ValueError, match="unbound CP-1 operand"):
        cpl10.bind_operands(facts[1:])
    with pytest.raises(ValueError, match="unbound CP-1 operand"):
        cpl10.bind_operands([*facts, facts[0].model_copy(update={"fact_id": "dup"})])
    operands = dict(UPSTREAM.cp1_facts)
    operands.pop(facts[0].label)
    with pytest.raises(ValueError, match="unbound CP-1 operand"):
        cpl10.Upstream(**{**UPSTREAM.__dict__, "cp1_facts": operands})


def test_operand_unit_and_scale_must_match_the_topic() -> None:
    facts = _cp1_facts()
    close = cpl10.QUARTERS[3].column + " · cash_closing"
    thousands = [
        f.model_copy(update={"unit": "THOUSANDS", "scale": Decimal(1000)})
        if f.label == close
        else f
        for f in facts
    ]
    with pytest.raises(ValueError, match="unit THOUSANDS is not MILLIONS"):
        _upstream(thousands)
    rescaled = [
        f.model_copy(update={"scale": Decimal(1000)}) if f.label == close else f for f in facts
    ]
    with pytest.raises(ValueError, match="cash differ in scale"):
        _upstream(rescaled)


def _limited_with(changes: dict[str, dict[str, Any]], drop_cash: bool = False) -> dict[str, Fact]:
    facts = [f.model_copy(update=changes.get(f.label, {})) for f in _cp1_facts()]
    sub = deepcopy(SUBMISSIONS["limited"])
    if drop_cash:  # cash becomes Not assessed, so its assessment is no longer admitted
        sub["assessments"] = [a for a in sub["assessments"] if a["topic_id"] != "cash"]
    result = cpl10.change_screen(submission=json.dumps(sub), upstream=_upstream(facts))
    return {c.fact.fact_id: c.fact for c in result.cells}


def test_unsettled_copied_cell_takes_the_topics_unit() -> None:
    # Round 5 (f): a copied cell whose value is not known takes the topic's unit, currency and
    # scale, never its own or its twin's; the limited case has both leverage ends missing.
    q2, q3 = cpl10.QUARTERS[1].column, cpl10.QUARTERS[2].column
    unitless = {"unit": None, "currency": None, "scale": Decimal(1)}
    odd = {"unit": "THOUSANDS", "currency": "EUR", "scale": Decimal(1000)}
    cells = _limited_with(
        {
            f"{q2} · total_leverage_reported": unitless,
            f"{q3} · total_leverage_reported": unitless,
            f"{q2} · interest_coverage_reported": odd,
        }
    )
    for fact_id in (
        "TL10.2.total_leverage.from_value",
        "TL10.2.total_leverage.to_value",
        "TL10.2.interest_coverage.from_value",
    ):
        fact = cells[fact_id]
        assert (fact.status, fact.unit, fact.currency, fact.scale) == (
            "missing",
            "MULTIPLE",
            None,
            Decimal(1),
        ), fact_id
    # a MILLIONS topic: its own USD and 1,000,000 even when the twin is known in another currency
    cash = {"status": "missing", "amount": None, "limitation": "close gap", **odd}
    cells = _limited_with(
        {f"{q3} · cash_closing": cash, f"{q2} · cash_closing": {"currency": "EUR"}},
        drop_cash=True,
    )
    fact = cells["TL10.2.cash.to_value"]
    assert (fact.unit, fact.currency, fact.scale) == ("MILLIONS", "USD", Decimal(1000000))
    known = cells["TL10.2.cash.from_value"]  # a known copied cell stays verbatim
    assert (known.unit, known.currency, known.scale) == ("MILLIONS", "EUR", Decimal(1000000))


def test_unsettled_operand_without_unit_is_accepted() -> None:
    # Ruling (f): units are checked on known operands only; a missing fact with unit None is
    # accepted (round 5: its copied cell takes the topic's unit, here equal to its twin's).
    q1, q4 = cpl10.QUARTERS[0], cpl10.QUARTERS[3]
    start = f"{q1.column} · total_leverage_reported"
    cash_close = f"{q4.column} · cash_closing"
    facts = []
    for f in _cp1_facts():
        if f.label == start:
            assert f.status == "missing"
            f = f.model_copy(update={"unit": None})
        elif f.label == cash_close:
            update = {"status": "missing", "amount": None, "limitation": "close gap"}
            f = f.model_copy(update={**update, "unit": None, "currency": None, "scale": Decimal(1)})
        facts.append(f)
    upstream = _upstream(facts)
    sub = deepcopy(SUBMISSIONS["positive"])
    sub["assessments"] = [sub["assessments"][1]]  # cash is now Not assessed
    result = cpl10.change_screen(submission=json.dumps(sub), upstream=upstream)
    cells = {c.fact.fact_id: c.fact for c in result.cells}
    lev = cells["TL10.2.total_leverage.from_value"]
    assert (lev.status, lev.unit, lev.currency, lev.scale) == (
        "missing",
        "MULTIPLE",
        None,
        Decimal(1),
    )
    cash = cells["TL10.2.cash.to_value"]
    assert (cash.status, cash.unit, cash.currency, cash.scale) == (
        "missing",
        "MILLIONS",
        "USD",
        Decimal(1000000),
    )
    # a known operand without the topic's unit is still refused
    known = [
        f.model_copy(update={"unit": None}) if f.label == cash_close else f for f in _cp1_facts()
    ]
    with pytest.raises(ValueError, match="unit None is not MILLIONS"):
        _upstream(known)


@pytest.mark.parametrize(
    ("missing_end", "ends", "cited"),
    [
        ("close", "the closing quarter", "close gap"),
        ("start", "the starting quarter", "start gap"),
        ("both", "either quarter", "start gap"),
    ],
)
def test_missing_end_limitation_is_taken_first(missing_end: str, ends: str, cited: str) -> None:
    """The missing end's CP-1 limitation is cited even when the known end carries a note; with
    both ends missing, the starting end's."""
    q1, q4 = cpl10.QUARTERS[0], cpl10.QUARTERS[3]
    start, close = f"{q1.column} · cash_closing", f"{q4.column} · cash_closing"
    facts = []
    for f in _cp1_facts():
        end = "start" if f.label == start else "close" if f.label == close else None
        if end is not None and missing_end in (end, "both"):
            gap = {"status": "missing", "amount": None, "limitation": f"{end} gap"}
            f = f.model_copy(update=gap)
        elif end is not None:
            f = f.model_copy(update={"limitation": "known end note"})
        facts.append(f)
    upstream = _upstream(facts)
    sub = deepcopy(SUBMISSIONS["positive"])
    sub["assessments"] = [sub["assessments"][1]]  # cash is now Not assessed
    result = cpl10.change_screen(submission=json.dumps(sub), upstream=upstream)
    cells = {c.fact.fact_id: c.fact for c in result.cells}
    want = f"Not calculable: CP-1 carries no known value for {ends} ({cited})"
    assert cells["TL10.2.cash.change"].limitation == want
    assert cells["TL10.4.cash.required_source"].text == (
        f"A CP-1 known value for each quarter compared (CP-1: {cited})"
    )


def test_prohibited_conclusions_ignore_case() -> None:
    # L10-b: substring match in v1, so an operating "Recovery" is refused (a recorded limit).
    sub = _with(("overall", "rationale"), "An earnings Recovery is visible in the screen.")
    assert _issues(sub) == ["overall.rationale: prohibited conclusion: recovery"]


# --- read_inputs view content -------------------------------------------------------------


def test_view_topics_and_pair_screens() -> None:
    expected = EXPECTED["cases"]["positive"]
    assert EXPECTED["cases"]["limited"]["view_topics"] == expected["view_topics"]
    got = [
        {
            "topic_id": t.topic_id,
            "label": t.label,
            "cp1_metric": t.cp1_metric,
            "unit": t.unit,
            "values": [
                {
                    "period": v.period,
                    "status": v.status,
                    "amount": v.amount,
                    "shown": v.shown,
                    "limitation": v.limitation,
                }
                for v in t.values
            ],
        }
        for t in cpl10.view_topics(UPSTREAM, gap_ref=GAP)
    ]
    want = [
        {
            **{k: t[k] for k in ("topic_id", "label", "cp1_metric", "unit")},
            "values": [
                {
                    "period": v["period"],
                    "status": v["status"],
                    "amount": None if v["amount_exact"] is None else Decimal(v["amount_exact"]),
                    "shown": v["shown"].replace("G#", GAP),
                    "limitation": v["limitation"],
                }
                for v in t["values"]
            ],
        }
        for t in expected["view_topics"]
    ]
    assert got == want
    screens = [
        {
            "from_period": s.from_period,
            "to_period": s.to_period,
            "topics": [{"topic_id": t, "materiality": m} for t, m in s.topics],
        }
        for s in cpl10.pair_screens(UPSTREAM)
    ]
    assert screens == expected["view_pair_screens"]


# --- composed cases ---------------------------------------------------------------------------


def _citations(labels: Any) -> tuple[Citation, ...]:
    return tuple(dict.fromkeys(c for label in labels for c in UPSTREAM.cp1_facts[label].citations))


def _assert_cell(cell: cpl10.Cell, want: dict[str, Any]) -> None:
    fact = cell.fact
    calculation_id = want.get("calculation_id")
    copied: str | None = want.get("copied_from_cp1")
    if calculation_id == CP1_MARKER:
        assert copied is not None
        calculation_id = UPSTREAM.cp1_facts[copied].calculation_id
    got = {
        "coordinates": (fact.table_id, fact.row_id, fact.field),
        "label": fact.label,
        "status": fact.status,
        "unit": fact.unit,
        "period": fact.period,
        "amount": fact.amount,
        "text": fact.text,
        "decimals": fact.decimals,
        "value_class": fact.value_class,
        "calculation_id": fact.calculation_id,
        "formula": fact.formula,
        "limitation": fact.limitation,
        "currency": fact.currency,
        "scale": fact.scale,
        "derives_from": cell.derives_from,
        "copied_from_cp1": cell.copied_from_cp1,
        "citations": fact.citations,
        "shown": cpl10.shown_text(fact, GAP),
    }
    expected = {
        "coordinates": (want["table_id"], want["row_id"], want["field"]),
        "label": want["label"],
        "status": want["status"],
        "unit": want.get("unit"),
        "period": want.get("period"),
        "amount": None if want.get("amount_exact") is None else Decimal(want["amount_exact"]),
        "text": None if want.get("text") is None else _bind_run(want["text"]),
        "decimals": want.get("decimals"),
        "value_class": want.get("value_class"),
        "calculation_id": calculation_id,
        "formula": want.get("formula"),  # a copied cell omits CP-1's formula (L10-c)
        "limitation": want.get("limitation"),
        "currency": want.get("currency"),
        "scale": Decimal(want.get("scale", "1")),
        "derives_from": tuple(want.get("derives_from") or ()),
        "copied_from_cp1": copied,
        # F5: a copied cell carries its CP-1 fact's citations; a calculated one its derives_from's.
        "citations": _citations([copied] if copied else want.get("derives_from") or ()),
        "shown": _bind_run(want["shown"]).replace("G#", GAP),
    }
    assert got == expected, fact.fact_id


@pytest.fixture(scope="module", params=["positive", "limited"])
def composed(request: pytest.FixtureRequest) -> tuple[dict[str, Any], cpl10.ScreenResult]:
    name: str = request.param
    assert cpl10.validate_screen(submission=_payload(name), upstream=UPSTREAM) == ()
    return EXPECTED["cases"][name], cpl10.change_screen(
        submission=_payload(name), upstream=UPSTREAM
    )


def test_topic_screens(composed: tuple[dict[str, Any], cpl10.ScreenResult]) -> None:
    expected, result = composed
    assert (result.from_period, result.to_period) == (
        expected["pair"]["from_period"],
        expected["pair"]["to_period"],
    )

    def dec(value: str | None) -> Decimal | None:
        return None if value is None else Decimal(value)

    got = [
        {
            "topic_id": t.topic.topic_id,
            "label": t.topic.label,
            "materiality": t.screen.materiality,
            "evidence": t.screen.evidence,
            "disposition": t.screen.disposition,
            "rank": t.rank,
            "change": t.screen.change,
            "pct": t.screen.pct,
            "pct_fraction": t.screen.pct_fraction,
            "from": (t.start.label, t.start.status, t.start.amount, t.start.value_class),
            "to": (t.close.label, t.close.status, t.close.amount, t.close.value_class),
        }
        for t in result.topics
    ]
    want = [
        {
            "topic_id": t["topic_id"],
            "label": t["label"],
            "materiality": t["materiality"],
            "evidence": t["evidence"],
            "disposition": t["disposition"],
            "rank": t["rank"],
            "change": dec(t["change_exact"]),
            "pct": dec(t["change_pct_exact"]),
            "pct_fraction": (
                None if t["change_pct_fraction"] is None else Fraction(t["change_pct_fraction"])
            ),
            **{
                end: (
                    t[end]["label"],
                    t[end]["status"],
                    dec(t[end]["amount_exact"]),
                    t[end]["value_class"],
                )
                for end in ("from", "to")
            },
        }
        for t in expected["topics"]
    ]
    assert got == want
    assert list(result.required_assessments) == expected["required_assessments"]
    assert dict(result.counts) == expected["counts"]
    assert result.status == expected["module_status"]


def test_cells_equal_oracle(composed: tuple[dict[str, Any], cpl10.ScreenResult]) -> None:
    expected, result = composed
    cells = {c.fact.fact_id: c for c in result.cells}
    assert len(cells) == len(result.cells)
    want = {f["fact_id"]: f for f in expected["facts"]}
    assert set(cells) == set(want)
    for fact_id, fact in want.items():
        _assert_cell(cells[fact_id], fact)


def test_missing_change_cells_derive_from_both_cp1_labels(
    composed: tuple[dict[str, Any], cpl10.ScreenResult],
) -> None:
    """Stage 2 close (CP-L10 missing-change lineage): a missing `change` or `change_pct` cell lists
    the two CP-1 labels its known siblings list, so the claim that names it carries their lineage."""
    _, result = composed
    cells = {c.fact.fact_id: c for c in result.cells}
    missing = [t for t in result.topics if t.screen.change is None]
    assert missing
    for topic in missing:
        for field in ("change", "change_pct"):
            cell = cells[f"TL10.2.{topic.topic.topic_id}.{field}"]
            assert cell.fact.status == "missing"
            assert cell.derives_from == (topic.start.label, topic.close.label)
            assert cell.fact.citations == tuple(
                dict.fromkeys((*topic.start.citations, *topic.close.citations))
            )


def test_copied_cells_keep_cp1_lineage_but_not_its_formula(
    composed: tuple[dict[str, Any], cpl10.ScreenResult],
) -> None:
    _, result = composed
    copied = [c for c in result.cells if c.copied_from_cp1 is not None]
    assert len(copied) == 14
    for cell in copied:
        source = UPSTREAM.cp1_facts[cell.copied_from_cp1 or ""]
        assert source.formula and source.citations and source.decimals == 0
        fact = cell.fact
        assert (fact.citations, fact.limitation, fact.calculation_id, fact.value_class) == (
            source.citations,
            source.limitation,
            source.calculation_id,
            source.value_class,
        )
        assert (fact.status, fact.amount, fact.period) == (
            source.status,
            source.amount,
            source.period,
        )
        assert fact.formula is None
        assert fact.decimals == (2 if fact.unit == "MILLIONS" and fact.status == "known" else None)


def test_tables_equal_oracle(composed: tuple[dict[str, Any], cpl10.ScreenResult]) -> None:
    expected, result = composed
    got = [
        {
            "table_id": t.table_id,
            "title": t.title,
            "columns": list(t.columns),
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)} for r in t.rows
            ],
        }
        for t in result.tables
    ]
    assert got == expected["tables"]
    # F1: the records form valid product tables (column labels are the product's, L3).
    tables = tuple(
        ReportTable(
            table_id=t.table_id,
            title=t.title,
            columns=tuple(TableColumn(field=f, label=f) for f in t.columns),
            rows=tuple(
                TableRow(row_id=r.row_id, label=r.label, fact_ids=r.fact_ids) for r in t.rows
            ),
        )
        for t in result.tables
    )
    validate_tables(tables, tuple(c.fact for c in result.cells))


def test_claims_equal_oracle(composed: tuple[dict[str, Any], cpl10.ScreenResult]) -> None:
    expected, result = composed
    got = [
        {
            "claim_id": c.claim_id,
            "limitation": c.limitation,
            "refs": list(c.refs),
            "text": c.text,
            "citations": c.citations,
        }
        for c in result.claims
    ]
    want = []
    for claim in expected["claims"]:
        labels = []
        for marker in claim["citations"]:
            assert marker.startswith(CITATIONS_MARKER) and marker.endswith("}}")
            labels.append(marker[len(CITATIONS_MARKER) : -2])
        want.append(
            {**{k: claim[k] for k in ("claim_id", "limitation", "refs", "text")}}
            | {"citations": _citations(labels)}
        )
    assert got == want
    bound = prose.bind(c.fact for c in result.cells)
    for claim in result.claims:
        assert prose.issues(claim.text, bound, names=(UPSTREAM.issuer_name,)) == (), claim.claim_id


def test_own_limitations(composed: tuple[dict[str, Any], cpl10.ScreenResult]) -> None:
    expected, result = composed
    assert list(result.limitations) == expected["own_limitations"]


# --- refusals (calculation-level validator issues) ----------------------------------------


@pytest.mark.parametrize("refusal", SUBMISSIONS["refusals"], ids=lambda r: r["id"])
def test_refusal(refusal: dict[str, Any]) -> None:
    expected = {r["id"]: r for r in EXPECTED["refusals"]}[refusal["id"]]
    assert _issues(refusal["payload"]) == expected["expected_issues"]
    with pytest.raises(ValueError):
        cpl10.change_screen(submission=json.dumps(refusal["payload"]), upstream=UPSTREAM)


def test_refusals_cover_r01_to_r19() -> None:
    ids = [r["id"] for r in SUBMISSIONS["refusals"]]
    assert ids == [f"r{i:02d}" for i in range(1, 20)] == [r["id"] for r in EXPECTED["refusals"]]


def _with(path: tuple[Any, ...], value: Any) -> dict[str, Any]:
    sub: dict[str, Any] = deepcopy(SUBMISSIONS["positive"])
    target: Any = sub
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return sub


def test_text_check_binds_every_python_built_fact() -> None:
    # L10-a: the settlement prose path against every Python-built fact of the module.
    for ref in (
        "[TL10.4.cash.blocking_for_full_decision]",
        "[TL10.1.cp1.topics_supported]",
        "{TL10.5.total.material|topics}",
        "{TL10.2.cash.change|US$ m}",
    ):
        assert _issues(_with(("overall", "rationale"), f"See {ref} for the screen.")) == [], ref
    # an analyst cell is not a Python-built fact
    sub = _with(("overall", "rationale"), "See [TL10.3.cash.assessment] for the screen.")
    assert _issues(sub) == ["overall.rationale: Unresolved reference: TL10.3.cash.assessment"]


@pytest.mark.parametrize(
    "ref",
    [
        "TL10.3.cash.assessment",
        "TL10.3.cash.credit_transmission",
        "TL10.3.cash.confidence",
        "TL10.3.overall.assessment",
        "TL10.4.cash.decision_impact",
    ],
)
@pytest.mark.parametrize(
    "path",
    [("assessments", 0, "assessment"), ("assessments", 1, "credit_transmission")],
)
def test_reference_to_an_analyst_cell_is_refused(ref: str, path: tuple[Any, ...]) -> None:
    # Round 5 P2: analyst cells stay unbound; citing one is refused with the product issue.
    sub = _with(path, f"See [{ref}] for the screen.")
    prefix = f"{path[0]}[{path[1]}].{path[2]}"
    assert _issues(sub) == [f"{prefix}: Unresolved reference: {ref}"]


@pytest.mark.parametrize(
    ("text", "issue"),
    [
        (
            "Cash moved by {TL10.2.cash.change|%} over the span.",
            "Unit % differs from the fact's unit US$ m: TL10.2.cash.change",
        ),
        (
            "Leverage moved by {TL10.2.total_leverage.change|x} over the span.",
            "Figure reference names a gap: TL10.2.total_leverage.change",
        ),
        (
            "See [TL10.2.cash.change] for the move.",
            "A numeric fact needs a figure reference {TL10.2.cash.change|unit}",
        ),
    ],
)
def test_reference_kind_refusals_use_the_product_text(text: str, issue: str) -> None:
    assert _issues(_with(("assessments", 0, "assessment"), text)) == [
        f"assessments[0].assessment: {issue}"
    ]


def test_assessment_order_not_assessable_before_repeated() -> None:
    sub = deepcopy(SUBMISSIONS["positive"])
    ebitda = {**sub["assessments"][0], "topic_id": "ebitda"}
    sub["assessments"] += [ebitda, deepcopy(ebitda)]
    assert _issues(sub) == [
        "assessments[2].topic_id: not assessable: ebitda is rated Stable",
        "assessments[3].topic_id: not assessable: ebitda is rated Stable",
    ]


_PAIRING = "must be Insufficient Information exactly when the category is"


@pytest.mark.parametrize(
    ("category", "confidence", "issues"),
    [
        ("Analyst Interpretation", "Insufficient Information", [f"confidence: {_PAIRING}"]),
        ("Insufficient Information", "Medium", [f"confidence: {_PAIRING}"]),
        ("Insufficient Information", "Low", [f"confidence: {_PAIRING}"]),  # round 5 (e): both ways
        ("Insufficient Information", "Insufficient Information", []),
        (
            "Insufficient Information",
            "High",
            ["confidence: High is not allowed in a screen", f"confidence: {_PAIRING}"],
        ),
    ],
)
def test_assessment_confidence_pairing(category: str, confidence: str, issues: list[str]) -> None:
    # Ruling (e): checked after the High check (L2 order); assessments carry no limitation.
    sub = _with(("assessments", 0, "category"), category)
    sub["assessments"][0]["confidence"] = confidence
    assert _issues(sub) == [f"assessments[0].{issue}" for issue in issues]


def test_repeated_gap_keys_on_target_and_text() -> None:
    sub = deepcopy(SUBMISSIONS["positive"])
    sub["gaps"].append({**sub["gaps"][0], "affected_analysis": "cash"})
    assert _issues(sub) == []  # the same gap text on another target is not a repeat


def test_scope_status_binds_each_heads_own_word() -> None:
    result = cpl10.change_screen(submission=_payload("positive"), upstream=UPSTREAM)
    words = {c.fact.fact_id: c.fact.text for c in result.cells if c.fact.field == "scope_status"}
    assert words == {
        "TL10.1.cp0.scope_status": "Validated",
        "TL10.1.cp1.scope_status": "With limitations",
    }


def test_overall_issue_order() -> None:
    # L2: High, then pairing, then limitation required (keyed on the category, L1).
    sub = _with(("overall", "category"), "Insufficient Information")
    sub["overall"]["confidence"] = "High"
    assert _issues(sub) == [
        "overall.confidence: High is not allowed in a screen",
        "overall.confidence: must be Insufficient Information exactly when the category is",
        "overall.limitation: an Insufficient Information overall states its limitation",
    ]
    sub = _with(("overall", "confidence"), "Insufficient Information")
    sub["overall"]["limitation"] = "Two quarters only."
    assert _issues(sub) == [
        "overall.confidence: must be Insufficient Information exactly when the category is",
        "overall.limitation: only an Insufficient Information overall carries a limitation",
    ]


# --- round 11 class round: blank text (docs/rulings/2026-10-28-stage1.md "# Round 11", LEAD
# rulings "Blank text is one defect class"; tests/defect_classes.py). CP-L10 reads no figure,
# name or label from an analyst quote, so only the blank cases apply. Whitespace-only text is
# refused with the module's pinned frame `<path>: empty` (r11 overall.rationale, r17 gaps[i].gap,
# lease step (4) for the assessments; controller: one spelling per module). `""` keeps its
# `Text` shape issue (controller decision, library fix 1). Ids and closed lists (topic_id,
# affected_analysis, periods, category, confidence, severity) are not analyst text.
_INSUFFICIENT = {
    "category": cpl10.INSUFFICIENT,
    "confidence": cpl10.INSUFFICIENT,
    "limitation": "Two quarters only.",
}
EMPTY = "{path}: empty"  # the module's pinned empty-text frame
BLANK_FIELDS: tuple[tuple[str, tuple[str | int, ...]], ...] = (
    ("assessments[0].assessment", ("assessments", 0, "assessment")),
    ("assessments[0].credit_transmission", ("assessments", 0, "credit_transmission")),
    ("assessments[1].assessment", ("assessments", 1, "assessment")),
    ("overall.rationale", ("overall", "rationale")),
    ("overall.limitation", ("overall", "limitation")),
    ("gaps[0].gap", ("gaps", 0, "gap")),
    ("gaps[0].why_it_matters", ("gaps", 0, "why_it_matters")),
    ("gaps[0].action", ("gaps", 0, "action")),
)


def _blank_adapter(keys: tuple[str | int, ...]) -> Adapter:
    """Places the value in one analyst text field of the frozen positive payload; a limitation is
    set on an Insufficient Information overall, the only overall that carries one (r14, r15).
    Page and quote are unused: CP-L10 reads no value from an analyst quote."""

    def adapter(page: str, quote: str, value: str) -> list[str]:
        sub: dict[str, Any] = deepcopy(SUBMISSIONS["positive"])
        if keys == ("overall", "limitation"):
            sub["overall"].update(_INSUFFICIENT)
        target: Any = sub
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
        return _issues(sub)

    return adapter


def test_blank_fields_cover_every_analyst_text_field() -> None:
    models: dict[str, type[Contract]] = {
        "assessments[0]": cpl10.Assessment,
        "overall": cpl10.Overall,
        "gaps[0]": cpl10.Gap,
    }
    not_text = {"assessments[0].topic_id", "gaps[0].affected_analysis"}
    text = {
        f"{prefix}.{name}"
        for prefix, model in models.items()
        for name, info in model.model_fields.items()
        if info.annotation in (str, str | None) or "[str," in str(info.annotation)
    }
    assert text - not_text == {path for path, _ in BLANK_FIELDS if "[1]" not in path}


@pytest.mark.parametrize("field", BLANK_FIELDS, ids=lambda f: f[0])
@pytest.mark.parametrize("blank", BLANK_CASES, ids=lambda c: c.case_id)
def test_blank_text_is_refused(blank: BlankCase, field: tuple[str, tuple[str | int, ...]]) -> None:
    path, keys = field
    failure = blank_failure(blank, _blank_adapter(keys), EMPTY.format(path=path))
    assert failure is None, failure


@pytest.mark.parametrize("field", BLANK_FIELDS, ids=lambda f: f[0])
def test_blank_text_twin_is_accepted(field: tuple[str, tuple[str | int, ...]]) -> None:
    """The twin: the same field holding text is accepted outright."""
    _, keys = field
    assert _blank_adapter(keys)("", "", "Only two quarters are compared.") == []


def test_blank_limitation_ends_after_the_overall_rules() -> None:
    # Step (5): the empty-text refusal follows r14 / r15, so a blank limitation on another
    # overall carries both, r15 first.
    sub = _with(("overall", "limitation"), "  ")
    assert _issues(sub) == [
        "overall.limitation: only an Insufficient Information overall carries a limitation",
        "overall.limitation: empty",
    ]


def test_blank_gap_fields_follow_the_gap_empty_check() -> None:
    # Step (6): gap, why_it_matters, action empty checks in field order, before the digit check.
    sub = deepcopy(SUBMISSIONS["positive"])
    sub["gaps"][0].update(gap=" ", why_it_matters="\t", action="\n")
    sub["gaps"].append({**SUBMISSIONS["positive"]["gaps"][0], "action": "Ask for 2024."})
    assert _issues(sub) == [
        "gaps[0].gap: empty",
        "gaps[0].why_it_matters: empty",
        "gaps[0].action: empty",
        "gaps[1].action: must not contain a digit",
    ]
