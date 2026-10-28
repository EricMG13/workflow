"""CP-L10 Stage 1: the change-screen calculation against the frozen oracle.

Inputs are built from the oracle's own source facts (``cases.*.view_topics``, ``cases.*.topics``)
and the manifest's fact selection rule, never from the module. Items that LEAD amendment 1
(F1-F5) changes are left out until the oracle is re-frozen: TL10.2 ``total``, TL10.3 ``overall``,
TL10.1 ``source_ref`` / ``scope_status``, the summary and overall claims, gap limitation lines,
overall and gaps validation, and claim citations.
"""

import hashlib
import json
from datetime import date
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from deploy_vii import prose
from deploy_vii.contracts import Fact
from deploy_workflow.owners import cpl10

CASE = Path(__file__).resolve().parents[1] / "cases" / "cpl10-owner"
EXPECTED: dict[str, Any] = json.loads((CASE / "expected.json").read_text())
SUBMISSIONS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text())
MANIFEST: dict[str, Any] = json.loads((CASE / "manifest.json").read_text())
CP1_MARKER = "{{CP1_CALCULATION_ID}}"
GAP = "G1"  # the report-wide G# is bound at run time; any valid gap id spells the same pattern

# Pending LEAD amendment 1 (not asserted until the re-freeze).
PENDING_ROWS = {("TL10.2", "total"), ("TL10.3", "overall")}
PENDING_FIELDS = {("TL10.1", "source_ref"), ("TL10.1", "scope_status")}
PENDING_CLAIMS = {"TL10.2.summary", "TL10.3.overall"}


def _calculation_id(label: str) -> str:
    return "canonical-kpi:" + hashlib.sha256(label.encode()).hexdigest()


def _cp1_facts() -> list[Fact]:
    """The 28 CP-1 T4.10 operands, from the oracle's view values and observed value classes."""
    rule = MANIFEST["fact_selection_rule"]
    column = {c["period"]: c["label"] for c in rule["columns"].values()}
    value_class: dict[str, Any] = {}
    for case in ("positive", "limited"):
        for topic in EXPECTED["cases"][case]["topics"]:
            for end in ("from", "to"):
                value_class[topic[end]["label"]] = topic[end]["value_class"]
    facts = []
    for topic in EXPECTED["cases"]["positive"]["view_topics"]:
        money = topic["unit"] == "US$ m"
        for value in topic["values"]:
            label = f"{column[value['period']]} · {topic['cp1_metric']}"
            known = value["status"] == "known"
            facts.append(
                Fact(
                    fact_id="interface-fact:" + hashlib.sha256(label.encode()).hexdigest(),
                    label=label,
                    table_id="T4.10",
                    row_id=topic["cp1_metric"],
                    field="value",
                    status=value["status"],
                    amount=Decimal(value["amount_exact"]) if known else None,
                    unit="MILLIONS" if money else "MULTIPLE",
                    currency="USD" if money else None,
                    scale=Decimal(1000000) if money else Decimal(1),
                    period=value["period"],
                    calculation_id=_calculation_id(label),
                    value_class=value_class[label],
                    limitation=value["limitation"],
                )
            )
    assert len(facts) == 28 and len(value_class) == 28
    return facts


def _upstream() -> cpl10.Upstream:
    run = MANIFEST["run"]
    return cpl10.Upstream(
        issuer_name=run["issuer_name"],
        as_of=date.fromisoformat(run["as_of"]),
        cp0_status_word="With limitations",
        cp0_result_sha256="0" * 64,
        cp1_status_word="With limitations",
        cp1_result_sha256="1" * 64,
        cp1_facts=cpl10.bind_operands(_cp1_facts()),
    )


UPSTREAM = _upstream()


def _payload(name: str) -> str:
    return json.dumps(SUBMISSIONS[name])


# --- composer fixtures and rank -----------------------------------------------------------


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


def _pending(fact_id: str) -> bool:
    table, row, field = fact_id.split(".")[0] + "." + fact_id.split(".")[1], *fact_id.split(".")[2:]
    return (table, row) in PENDING_ROWS or (table, field) in PENDING_FIELDS


def _assert_cell(cell: cpl10.Cell, want: dict[str, Any]) -> None:
    fact = cell.fact
    calculation_id = want.get("calculation_id")
    if calculation_id == CP1_MARKER:
        calculation_id = UPSTREAM.cp1_facts[want["copied_from_cp1"]].calculation_id
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
        "shown": cpl10.shown_text(fact, GAP),
    }
    expected = {
        "coordinates": (want["table_id"], want["row_id"], want["field"]),
        "label": want["label"],
        "status": want["status"],
        "unit": want.get("unit"),
        "period": want.get("period"),
        "amount": None if want.get("amount_exact") is None else Decimal(want["amount_exact"]),
        "text": want.get("text"),
        "decimals": want.get("decimals"),
        "value_class": want.get("value_class"),
        "calculation_id": calculation_id,
        "formula": want.get("formula"),
        "limitation": want.get("limitation"),
        "currency": want.get("currency"),
        "scale": Decimal(want.get("scale", "1")),
        "derives_from": tuple(want.get("derives_from", ())),
        "copied_from_cp1": want.get("copied_from_cp1"),
        "shown": want["shown"].replace("G#", GAP),
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

    def dec(value: str | None) -> Decimal | None:
        return None if value is None else Decimal(value)

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
    want = {f["fact_id"]: f for f in expected["facts"] if not _pending(f["fact_id"])}
    produced = {i for i in cells if not _pending(i)}
    assert produced == set(want)
    for fact_id, fact in want.items():
        _assert_cell(cells[fact_id], fact)


def test_tables_equal_oracle(composed: tuple[dict[str, Any], cpl10.ScreenResult]) -> None:
    expected, result = composed
    got = [
        {
            "table_id": t.table_id,
            "title": t.title,
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)}
                for r in t.rows
                if (t.table_id, r.row_id) not in PENDING_ROWS
            ],
        }
        for t in result.tables
    ]
    want = [
        {
            **t,
            "rows": [r for r in t["rows"] if (t["table_id"], r["row_id"]) not in PENDING_ROWS],
        }
        for t in expected["tables"]
    ]
    assert got == want


def test_claims_equal_oracle(composed: tuple[dict[str, Any], cpl10.ScreenResult]) -> None:
    expected, result = composed
    got = [
        {
            "claim_id": c.claim_id,
            "limitation": c.limitation,
            "refs": list(c.refs),
            "text": c.text,
        }
        for c in result.claims
        if c.claim_id not in PENDING_CLAIMS
    ]
    want = [
        {k: c[k] for k in ("claim_id", "limitation", "refs", "text")}
        for c in expected["claims"]
        if c["claim_id"] not in PENDING_CLAIMS
    ]
    assert got == want
    bound = prose.bind(c.fact for c in result.cells)
    names = (UPSTREAM.issuer_name,)
    for claim in result.claims:
        if claim.claim_id not in PENDING_CLAIMS:
            assert prose.issues(claim.text, bound, names=names) == (), claim.claim_id


def test_own_limitations(composed: tuple[dict[str, Any], cpl10.ScreenResult]) -> None:
    expected, result = composed

    def kept(items: Any) -> list[str]:
        return [i for i in items if not i.startswith("Gap (")]

    assert kept(result.limitations) == kept(expected["own_limitations"])


# --- refusals (calculation-level validator issues) ----------------------------------------


@pytest.mark.parametrize("refusal", SUBMISSIONS["refusals"], ids=lambda r: r["id"])
def test_refusal(refusal: dict[str, Any]) -> None:
    expected = {r["id"]: r for r in EXPECTED["refusals"]}[refusal["id"]]
    issues = cpl10.validate_screen(submission=json.dumps(refusal["payload"]), upstream=UPSTREAM)
    assert list(issues) == expected["expected_issues"]
    with pytest.raises(ValueError):
        cpl10.change_screen(submission=json.dumps(refusal["payload"]), upstream=UPSTREAM)
