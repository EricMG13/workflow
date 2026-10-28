"""CP-8 Stage 1: validator, Decimal diff and composed result against the frozen oracle.

Every expected value is read from ``cases/cp8-owner/expected.json`` (with the literal submissions,
the manifest's frozen pages and the CP-0 facts the oracle pins); nothing here is derived from the
code under test. The tool-use rules (``RULES``), the G1-level refusals, the blocked and refused
execution cases, store, tamper, rendering and consumption are Stages 2-4.
"""

import copy
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, Inexact, getcontext
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from deploy_vii import prose
from deploy_vii.contracts import Fact, Source, Span, validate_tables
from deploy_vii.display import format_date
from deploy_vii.readiness import shape_issues
from deploy_vii.report_view import fact_spelling
from deploy_workflow.owners import cp8 as cp8_module
from deploy_workflow.owners.cp8 import (
    METRICS,
    DecisionLedgerSubmission,
    Derived,
    LedgerInputs,
    RecordedSize,
    Upstream,
    breached,
    current_decision,
    decision_ledger,
    derive,
    source_authority,
    validate_ledger,
)

ROOT = Path(__file__).parents[1]
CASE = ROOT / "cases/cp8-owner"
EXPECTED = json.loads((CASE / "expected.json").read_text())
SUBMISSIONS = json.loads((CASE / "submissions.json").read_text())
MANIFEST = json.loads((CASE / "manifest.json").read_text())
FINANCIAL = json.loads((ROOT / "cases/financial/manifest.json").read_text())
GAP_REF = "G1"  # any report-wide gap number; the oracle spells it G# (bound at run time)
CASES = ("positive", "no_outcome")
ENTRIES = {e["id"]: e for e in SUBMISSIONS["refusal_mutations"]["entries"]}
PINNED = {r["id"]: r for r in EXPECTED["refusals"]}


# --- inputs from the oracle ----------------------------------------------------------------------


def cp0_facts(case: str) -> tuple[Fact, ...]:
    """The CP-0 head facts the oracle pins for the case (``expected.json#cp0``)."""
    out = []
    for item in EXPECTED["cp0"][case]["facts"]:
        table, rest = item["fact_id"].split(".", 1)
        row, field = rest.rsplit(".", 1)
        out.append(
            Fact(
                fact_id=item["fact_id"],
                label=field,
                table_id=table,
                row_id=row,
                field=field,
                text=item["text"],
            )
        )
    return tuple(out)


def upstream(case: str, cp6: tuple[str, str] | None = None) -> Upstream:
    return Upstream(
        as_of=date.fromisoformat(EXPECTED["cases"][case]["run"]["as_of"]),
        authority=source_authority(cp0_facts(case)),
        cp6=cp6,
    )


def pack(case: str) -> tuple[Source, ...]:
    """The ready pack of the case: the manifest's new sources and the frozen identity note."""
    identity = next(s for s in FINANCIAL["sources"] if s["source_id"] == "identity")
    out = []
    for item in EXPECTED["cases"][case]["pack_sources"]:
        sid = item["source_id"]
        raw = identity if sid == "identity" else MANIFEST["new_sources"][sid]
        pages = raw["pages"]
        digest = hashlib.sha256("\f".join(p["text"] for p in pages).encode()).hexdigest()
        assert digest == item["sha256"] == raw["sha256"], sid
        out.append(
            Source(
                source_id=sid,
                name=item["name"],
                status="ready",
                sha256=item["sha256"],
                spans=tuple(Span(locator=p["locator"], text=p["text"]) for p in pages),
                extraction_status="complete",
            )
        )
    return tuple(out)


def submission(payload: dict[str, Any]) -> DecisionLedgerSubmission:
    return DecisionLedgerSubmission.model_validate_json(json.dumps(payload))


def report_of(case: str, cp6: tuple[str, str] | None = None) -> Any:
    return decision_ledger(
        pack=pack(case), submission=submission(SUBMISSIONS[case]), upstream=upstream(case, cp6)
    )


# --- oracle shapes -------------------------------------------------------------------------------


def dstr(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def stored(d: Derived) -> dict[str, Any]:
    """The derived values in the oracle's ``stored`` form (exact decimal strings)."""
    out: dict[str, Any] = {}
    for metric in METRICS:
        m = d.measures[metric]
        out[metric] = {
            "expected": dstr(m.expected),
            "realized": dstr(m.realized),
            "variance": dstr(m.variance),
            "direction": m.direction,
            "magnitude": dstr(m.magnitude),
        }
        if metric == "loan_mid":
            out[metric]["magnitude_bp"] = dstr(d.loan_mid_magnitude_bp)
        out[metric]["downside_breach"] = m.downside_breach
    out["window_days"] = d.window_days
    out["window_end"] = None if d.window_end is None else d.window_end.isoformat()
    out["compared"] = list(d.compared)
    out["by_direction"] = None if d.by_direction is None else dict(d.by_direction)
    out["labelled"] = d.labelled
    out["confirmed"] = d.confirmed
    out["distribution"] = None if d.distribution is None else dict(d.distribution)
    out["decisions_recorded"] = d.decisions_recorded
    out["decisions_required"] = d.decisions_required
    out["hit_rate"] = dstr(d.hit_rate)
    return out


def cell(fact: Fact) -> dict[str, Any]:
    """One fact in the oracle's cell form (page-level cites, the product's spelling)."""
    return {
        "fact_id": fact.fact_id,
        "column": fact.label,
        "period": fact.period,
        "amount": dstr(fact.amount),
        "unit": fact.unit,
        "decimals": fact.decimals,
        "text": fact.text,
        "shown": fact_spelling(fact, GAP_REF)[2],
        "status": fact.status,
        "cites": [list(p) for p in dict.fromkeys((c.source_id, c.locator) for c in fact.citations)],
        "value_class": fact.value_class,
        "calculation_id": fact.calculation_id,
        "formula": fact.formula,
        "limitation": fact.limitation,
    }


def oracle_cell(item: dict[str, Any]) -> dict[str, Any]:
    """The oracle cell with its gap number bound (a known text keeps its literal text)."""
    out = dict(item)
    if item["status"] != "known":
        out["shown"] = item["shown"].replace("G#", GAP_REF)
    return out


def refs(text: str) -> list[str]:
    return [
        f"{run.text}|{run.unit}" if run.figure else run.text
        for run in prose.tokenize(text)
        if run.kind != "text"
    ]


def spell(text: str, facts: dict[str, Fact]) -> str:
    return "".join(
        run.text if run.kind == "text" else fact_spelling(facts[run.text], GAP_REF)[2]
        for run in prose.tokenize(text)
    )


# --- the two settled cases (acceptance 1, 2) ------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_case_literal_is_valid(case: str) -> None:
    got = validate_ledger(
        submission=submission(SUBMISSIONS[case]), upstream=upstream(case), pack=pack(case)
    )
    assert got == ()


@pytest.mark.parametrize("case", CASES)
def test_case_derived_values(case: str) -> None:
    assert stored(report_of(case).derived) == EXPECTED["cases"][case]["derived"]


@pytest.mark.parametrize("case", CASES)
def test_case_tables_cell_for_cell(case: str) -> None:
    want = EXPECTED["cases"][case]
    report = report_of(case)
    validate_tables(report.tables, report.facts)
    facts = {f.fact_id: f for f in report.facts}
    assert (
        len(facts)
        == len(report.facts)
        == sum(len(r["facts"]) for t in want["tables"] for r in t["rows"])
    )
    assert [t.table_id for t in report.tables] == [t["table_id"] for t in want["tables"]]
    for table, exp in zip(report.tables, want["tables"], strict=True):
        assert table.title == exp["title"], table.table_id
        assert table.row_header == exp["row_header"], table.table_id
        assert [(c.field, c.label) for c in table.columns] == [
            (c["field"], c["label"]) for c in exp["columns"]
        ]
        assert [(r.row_id, r.label) for r in table.rows] == [
            (r["row_id"], r["label"]) for r in exp["rows"]
        ]
        for row, erow in zip(table.rows, exp["rows"], strict=True):
            assert list(row.fact_ids) == [f["fact_id"] for f in erow["facts"]]
            for fact_id, efact in zip(row.fact_ids, erow["facts"], strict=True):
                assert cell(facts[fact_id]) == oracle_cell(efact), fact_id


@pytest.mark.parametrize("case", CASES)
def test_case_missing_is_never_zero(case: str) -> None:
    report = report_of(case)
    missing = [f.fact_id for f in report.facts if f.status != "known"]
    assert missing == EXPECTED["cases"][case]["missing_not_zero"]
    assert all(f.amount is None and f.text is None for f in report.facts if f.status != "known")


@pytest.mark.parametrize("case", CASES)
def test_case_claims(case: str) -> None:
    want = EXPECTED["cases"][case]["claims"]
    report = report_of(case)
    facts = {f.fact_id: f for f in report.facts}
    bound = prose.bind(report.facts)
    assert [c.claim_id for c in report.claims] == [c["claim_id"] for c in want]
    for claim, exp in zip(report.claims, want, strict=True):
        assert claim.text == exp["text"], claim.claim_id
        assert claim.limitation == exp["limitation"], claim.claim_id
        assert refs(claim.text) == exp["refs"], claim.claim_id
        assert spell(claim.text, facts) == exp["resolved"].replace("G#", GAP_REF)
        assert prose.issues(claim.text, bound) == (), claim.claim_id  # acceptance 9


@pytest.mark.parametrize("case", CASES)
def test_case_own_limitations(case: str) -> None:
    assert report_of(case).limitations == tuple(EXPECTED["cases"][case]["own_limitations"])


# --- the decision line and the fixtures (acceptance 4) -------------------------------------------


@pytest.mark.parametrize("name", list(EXPECTED["decision_fixtures"]))
def test_decision_fixture(name: str) -> None:
    fx = EXPECTED["decision_fixtures"][name]
    current = None if fx["current_cp6"] is None else tuple(fx["current_cp6"])
    prior = tuple(fx["prior"])
    assert current_decision(prior=prior, cp6=current) == (fx["kind"], fx["text"])


@pytest.mark.parametrize(
    "name", ["fixture_cp6_same", "fixture_cp6_changed", "fixture_cp6_insufficient"]
)
def test_decision_line_reads_the_cp6_call(name: str) -> None:
    fx = EXPECTED["decision_fixtures"][name]
    assert tuple(fx["prior"]) == ("Neutral", "Medium")  # the positive Prior Case record's decision
    report = report_of("positive", cp6=(fx["current_cp6"][0], fx["current_cp6"][1]))
    line = next(f for f in report.facts if f.fact_id == "cp8.what_changed.decision.value")
    if fx["kind"] == "known":
        assert (line.status, line.text, line.limitation) == ("known", fx["text"], None)
    else:
        assert (line.status, line.text, line.limitation) == ("missing", None, fx["text"])
    # a comparable CP-6 call leaves no current_decision gap row (8-20 adds it for Insufficient)
    assert ("current_decision" in row_ids(report, "T7.8")) == (fx["kind"] != "known")


POSITIVE_PACK_IDS = tuple(s["source_id"] for s in EXPECTED["cases"]["positive"]["pack_sources"])
POSITIVE_EXPECTED_AS_OF = {
    o["metric"]: datetime.strptime(o["as_of_text"], "%B %d, %Y").date()
    for o in SUBMISSIONS["positive"]["observations"]
    if o["side"] == "expected"
}


@pytest.mark.parametrize("name", list(EXPECTED["fixtures"]))
def test_fixture_derive(name: str) -> None:
    fx = EXPECTED["fixtures"][name]["inputs"]
    inputs = LedgerInputs(
        expected={k: Decimal(v) for k, v in fx["expected"].items()},
        # the fixtures restate the positive record's expectations, so they carry its quote dates
        expected_as_of={k: POSITIVE_EXPECTED_AS_OF[k] for k in fx["expected"]},
        realized={k: Decimal(v) for k, v in fx["realized"].items()},
        realized_as_of={k: date.fromisoformat(v) for k, v in fx["realized_as_of"].items()},
        decision_date=date.fromisoformat(fx["decision_date"]),
        downside_sizes={
            k: RecordedSize(comparator=v["comparator"], level=Decimal(v["level"]))
            for k, v in fx["downside_sizes"].items()
        },
        overall_label=fx["overall_label"],
        metric_labels=tuple(fx["metric_labels"]),
        # composer-only fixtures over the positive pack (one Prior Case record)
        pack_source_ids=POSITIVE_PACK_IDS,
    )
    assert stored(derive(inputs=inputs)) == EXPECTED["fixtures"][name]["stored"]


@pytest.mark.parametrize("comparator", ["above", "below"])
def test_a_figure_equal_to_its_size_is_not_breached(comparator: str) -> None:
    # lease-literal: expected.json#arithmetic.downside_breach "equal is not breached" (the
    # fixtures pin it for below only: fixture_not_breached interest cover 5.75 against 5.75)
    level = Decimal("1.75")
    assert breached(RecordedSize(comparator=comparator, level=level), level) is False


# --- calculation-level refusals (acceptance 5, validator part) -----------------------------------


def test_refusal_ids_cover_the_oracle() -> None:
    assert set(PINNED) == set(ENTRIES) | {"r00"}


@pytest.mark.parametrize("rid", sorted(ENTRIES))
def test_refusal_validator_issues(rid: str) -> None:
    entry, pinned = ENTRIES[rid], PINNED[rid]
    # the journaled tuple is the validator part then the RULES part (Stage 2 appends RULES)
    assert pinned["issues"] == entry["validator_issues"] + entry["rules_issues"]
    assert pinned["rules_issues"] == entry["rules_issues"]
    base = entry["base"]
    got = validate_ledger(
        submission=submission(entry["literal"]), upstream=upstream(base), pack=pack(base)
    )
    assert got == tuple(entry["validator_issues"])


def test_shape_refusal() -> None:
    literal = SUBMISSIONS["shape_refusal"]
    with pytest.raises(ValidationError) as caught:
        submission(literal["literal"])
    assert shape_issues(caught.value) == tuple(literal["issues"]) == tuple(PINNED["r00"]["issues"])


def test_an_unready_pack_source_is_unavailable_before_the_scope_rule() -> None:
    # lease-literal: quotes are checked "source in the pack, source inside the host scope, ...";
    # a pack source that is not ready is unavailable in readiness.citation_issues' own terms.
    # Literal r30 (identity cited) over the positive pack with identity made unreadable.
    ready = pack("positive")
    identity = next(s for s in ready if s.source_id == "identity")
    unreadable = identity.model_copy(
        update={"status": "unreadable", "extraction_status": "degraded", "limitation": "Unreadable"}
    )
    got = validate_ledger(
        submission=submission(ENTRIES["r30"]["literal"]),
        upstream=upstream("positive"),
        pack=tuple(unreadable if s is identity else s for s in ready),
    )
    assert got == ("Unavailable or changed source: identity",)


# --- LEAD rulings round 5 (docs/rulings/2026-10-28-stage1.md, "CP-8") ---------------------------
# Expected strings are the rulings' own wording; inputs are the oracle's literals with stated edits.

# Code points, not literals (as in deploy_vii.quotes): the characters are easy to misread.
SOFT_HYPHEN, NO_BREAK_SPACE, EN_DASH = chr(0x00AD), chr(0x00A0), chr(0x2013)
SUPERSCRIPT_TWO, ONE_HALF = chr(0x00B2), chr(0x00BD)
NOT_CALCULABLE = "Not calculable: needs an expected and a realized value"  # pinned (no_outcome)
NOT_ASSESSED = "Not assessed: the measure is not compared"  # pinned (no_outcome)
POSITIVE_LIMITS = tuple(EXPECTED["cases"]["positive"]["own_limitations"])
LIM_INTERIM = POSITIVE_LIMITS[3]
Q_OFFER_TWO_DATES = (  # prior_case page:2, verbatim: the offer's span reaches the cover line's date
    "Interest cover recorded at Approval on January 10, 2026 was 6.00x.\n"
    "Dealer quotation recorded at Approval, as of January 9, 2026: bid 98.50 and offer 99.25"
)  # round 9 item 2 refuses it (two dates); kept as that refusal's input


def positive() -> dict[str, Any]:
    lit: dict[str, Any] = copy.deepcopy(SUBMISSIONS["positive"])
    return lit


def without(lit: dict[str, Any], side: str, *metrics: str) -> dict[str, Any]:
    """Drop the side's observations of ``metrics``; an uncompared measure loses its judgments."""
    lit["observations"] = [
        o for o in lit["observations"] if not (o["side"] == side and o["metric"] in metrics)
    ]
    return lit


def uncompared(lit: dict[str, Any], *metrics: str) -> dict[str, Any]:
    lit["confidence"] = [c for c in lit["confidence"] if c["metric_id"] not in metrics]
    lit["attributions"] = [a for a in lit["attributions"] if a["metric_id"] not in metrics]
    for lesson in lit["lessons"]:
        lesson["metric_ids"] = [m for m in lesson["metric_ids"] if m not in metrics]
    return lit


def settle(
    lit: dict[str, Any],
    *,
    packed: tuple[Source, ...] | None = None,
    up: Upstream | None = None,
    case: str = "positive",
) -> Any:
    """Validate (no issue), compose, and check the composed tables and claims."""
    packed = pack(case) if packed is None else packed
    up = upstream(case) if up is None else up
    sub = submission(lit)
    assert validate_ledger(submission=sub, upstream=up, pack=packed) == ()
    report = decision_ledger(pack=packed, submission=sub, upstream=up)
    validate_tables(report.tables, report.facts)
    bound = prose.bind(report.facts)
    assert all(prose.issues(c.text, bound) == () for c in report.claims)
    return report


def cells(report: Any, table: str, row_id: str) -> dict[str, Fact]:
    return {f.field: f for f in report.facts if (f.table_id, f.row_id) == (table, row_id)}


def row_ids(report: Any, table: str) -> list[str]:
    return [r.row_id for r in next(t for t in report.tables if t.table_id == table).rows]


def texts(report: Any, table: str, row_id: str) -> dict[str, str | None]:
    return {field: f.text for field, f in cells(report, table, row_id).items()}


def missing(fact: Fact, reason: str) -> bool:
    return (fact.status, fact.text, fact.amount, fact.limitation) == ("missing", None, None, reason)


def edited_pack(
    source_id: str,
    old: str,
    new: str,
    case: str = "positive",
    base: tuple[Source, ...] | None = None,
) -> tuple[Source, ...]:
    """The case's pack (or ``base``) with one stated line edit on one source (hash recomputed)."""
    out = []
    for source in pack(case) if base is None else base:
        if source.source_id == source_id:
            spans = tuple(
                Span(locator=s.locator, text=s.text.replace(old, new)) for s in source.spans
            )
            assert spans != source.spans
            digest = hashlib.sha256("\f".join(s.text for s in spans).encode()).hexdigest()
            source = source.model_copy(update={"spans": spans, "sha256": digest})
        out.append(source)
    return tuple(out)


def test_8_1_partial_outcome_settles() -> None:
    report = settle(uncompared(without(positive(), "realized", "interest_cover"), "interest_cover"))
    reason = "Not stated: no realized interest cover is recorded from a post-decision source"
    t73 = cells(report, "T7.3", "interest_cover")
    for field in ("realized_value", "as_of", "source", "evidence_id"):
        assert missing(t73[field], reason), field
    assert (t73["interim_final"].status, t73["interim_final"].text) == ("known", "Interim")
    t74 = cells(report, "T7.4", "interest_cover")
    assert missing(t74["realized"], reason)
    assert missing(t74["direction"], NOT_CALCULABLE) and missing(t74["magnitude"], NOT_CALCULABLE)
    assert missing(t74["confidence"], NOT_ASSESSED)
    assert row_ids(report, "T7.8") == [
        *("posture", "size", "expected_spread_return", "expected_rating_path", "expected_hold"),
        *("not_compared_interest_cover", "current_decision", "calibration_gate"),
        *("extra_01", "extra_02"),
    ]
    assert texts(report, "T7.8", "not_compared_interest_cover") == {
        "gap": "Interest cover not compared",
        "missing_item": "Realized interest cover",
        "why_it_matters": (
            "No realized value is recorded for interest cover, so its variance cannot be measured"
        ),
        "impact_on_output": "Variance and attribution are shown only for the compared measures",
        "follow_up": "Supply a dated post-decision source that states interest cover",
    }
    at = POSITIVE_LIMITS.index(LIM_INTERIM) + 1
    assert report.limitations == (
        *POSITIVE_LIMITS[:at],
        "Measures not compared: interest cover; their variance and attribution are not shown.",
        *POSITIVE_LIMITS[at:],
    )
    assert report.derived.compared == ("total_leverage", "loan_mid")
    assert row_ids(report, "T7.5") == ["total_leverage", "loan_mid", "overall"]
    assert [c.claim_id for c in report.claims] == [
        *("CP-8-VAR-01", "CP-8-VAR-03", "CP-8-WIN-01", "CP-8-ATT-01", "CP-8-CAL-01"),
        "CP-8-VIEW-01",
    ]


def test_8_1_two_measures_not_compared() -> None:
    lit = without(positive(), "realized", "interest_cover", "loan_bid", "loan_offer")
    report = settle(uncompared(lit, "interest_cover", "loan_mid"))
    assert (
        "Measures not compared: interest cover and mid level of the term loan quotation; their "
        "variance and attribution are not shown."
    ) in report.limitations
    assert [r for r in row_ids(report, "T7.8") if r.startswith("not_compared_")] == [
        "not_compared_interest_cover",
        "not_compared_loan_mid",
    ]
    # round 6c (a): a T7.3 row names itself; the mid's name stays where it is compared (T7.4)
    for metric, name in (("loan_bid", "dealer bid"), ("loan_offer", "dealer offer")):
        reason = f"Not stated: no realized {name} is recorded from a post-decision source"
        t73 = cells(report, "T7.3", metric)
        assert all(missing(t73[f], reason) for f in ("realized_value", "as_of", "source")), metric
        assert missing(t73["evidence_id"], reason), metric
    mid = (
        "Not stated: no realized mid level of the term loan quotation is recorded from a "
        "post-decision source"
    )
    assert missing(cells(report, "T7.4", "loan_mid")["realized"], mid)


def test_8_2_missing_expected_settles() -> None:
    lit = uncompared(without(positive(), "expected", "total_leverage"), "total_leverage")
    report = settle(lit)
    t74 = cells(report, "T7.4", "total_leverage")
    assert missing(
        t74["expected"],
        "Not stated: no expected total leverage is recorded from the Prior Case record",
    )
    assert t74["realized"].status == "known" and missing(t74["direction"], NOT_CALCULABLE)
    assert t74["evidence_id"].text == "Quarterly update note, page:1"
    assert texts(report, "T7.8", "not_compared_total_leverage") == {
        "gap": "Total leverage not compared",
        "missing_item": "Expected total leverage",
        "why_it_matters": (
            "No expected value is recorded for total leverage, so its variance cannot be measured"
        ),
        "impact_on_output": "Variance and attribution are shown only for the compared measures",
        "follow_up": "Cite the expected total leverage from the Prior Case record",
    }
    assert (
        "Measures not compared: total leverage; their variance and attribution are not shown."
        in report.limitations
    )


def no_evidence(fact: Fact, name: str) -> bool:
    """8-24: an evidence cell with no cited quote: missing, no refs, no class, no calc id."""
    return missing(fact, f"Not stated: no quote is cited for {name}") and (
        fact.citations,
        fact.value_class,
        fact.calculation_id,
    ) == ((), None, None)


def test_8_24_missing_expected_under_outcome_absence() -> None:
    lit = without(copy.deepcopy(SUBMISSIONS["no_outcome"]), "expected", "total_leverage")
    report = settle(lit, case="no_outcome")
    t74 = cells(report, "T7.4", "total_leverage")
    assert no_evidence(t74["evidence_id"], "total leverage")
    assert missing(
        t74["expected"],
        "Not stated: no expected total leverage is recorded from the Prior Case record",
    )
    rows = row_ids(report, "T7.8")
    # (d): only the expected side adds a row; the frozen outcome row covers the realized side
    assert rows.index("not_compared_total_leverage") + 1 == rows.index("outcome")
    assert [r for r in rows if r.startswith("not_compared_")] == ["not_compared_total_leverage"]
    assert texts(report, "T7.8", "not_compared_total_leverage")["missing_item"] == (
        "Expected total leverage"
    )
    assert report.limitations == tuple(EXPECTED["cases"]["no_outcome"]["own_limitations"])


def test_8_24_neither_value_without_outcome_absence() -> None:
    lit = without(without(positive(), "expected", "interest_cover"), "realized", "interest_cover")
    report = settle(uncompared(lit, "interest_cover"))
    assert no_evidence(cells(report, "T7.4", "interest_cover")["evidence_id"], "interest cover")
    assert texts(report, "T7.8", "not_compared_interest_cover") == {
        "gap": "Interest cover not compared",
        "missing_item": "Expected and realized interest cover",
        "why_it_matters": (
            "No expected or realized value is recorded for interest cover, so its variance "
            "cannot be measured"
        ),
        "impact_on_output": "Variance and attribution are shown only for the compared measures",
        "follow_up": (
            "Cite the expected interest cover from the Prior Case record and supply a dated "
            "post-decision source that states it"
        ),
    }
    assert (
        "Measures not compared: interest cover; their variance and attribution are not shown."
        in report.limitations
    )


def test_8_3_unchanged_measure_claim() -> None:
    old = "Total leverage for the twelve months to March 31, 2026 is reported as 1.80x."
    new = "Total leverage for the twelve months to March 31, 2026 is reported as 1.67x."
    lit = positive()
    realized = lit["observations"][4]
    assert realized["quote"]["quote"] == old
    realized.update(value_text="1.67", quote={**realized["quote"], "quote": new})
    # 1.67x breaches no size, so leverage is no longer a flagged risk
    lit["attributions"][0].update(label="Thesis Confirmed", flag_quote=None)
    report = settle(lit, packed=edited_pack("update", old, new))
    claim = next(c for c in report.claims if c.claim_id == "CP-8-VAR-01")
    assert claim.text == (
        "Total leverage was recorded at {T7.4.total_leverage.expected|x} and is now "
        "{T7.4.total_leverage.realized|x}, unchanged."
    )
    line = cells(report, "cp8.what_changed", "total_leverage")["value"]
    assert line.text == "Total leverage was recorded at 1.67x and is now 1.67x, unchanged."


def test_8_4_overall_process_judged_unsound() -> None:
    lit = positive()
    lit["attributions"][3].update(
        label="Unflagged Risk Materialized",
        process_sound="N",
        originating_module="CP-3",
        flag_quote=None,
    )
    report = settle(lit)
    said = "The attribution is Unflagged Risk Materialized; the process is judged unsound."
    assert next(c.text for c in report.claims if c.claim_id == "CP-8-ATT-01") == said
    assert cells(report, "cp8.what_changed", "attribution")["value"].text == said


def test_8_5_compared_measure_without_a_recorded_size() -> None:
    lit = positive()
    lit["thesis"]["downside_sizes"] = [lit["thesis"]["downside_sizes"][1]]  # cover only
    lit["attributions"][0].update(label="Thesis Confirmed", flag_quote=None)
    report = settle(lit)
    breach = cells(report, "T7.5", "total_leverage")["breach"]
    assert missing(
        breach,
        "Not calculable: the Prior Case record has no recorded downside size for total leverage",
    )


Q_NOREC1 = "Portfolio posture and position size were not recorded."
Q_NOREC2 = (
    "Expected spread or return, expected rating path and expected holding period were not recorded."
)


@pytest.mark.parametrize(
    ("recorded", "line"),
    [
        (
            ("posture",),
            (
                "Position size, expected spread or return, rating path and holding period are "
                "not recorded in the Prior Case record"
            ),
        ),
        (
            ("posture", "size", "expected_spread_return", "expected_rating_path"),
            "Holding period is not recorded in the Prior Case record",
        ),
        (
            ("posture", "size", "expected_spread_return", "expected_rating_path", "expected_hold"),
            None,
        ),
    ],
)
def test_8_6_partly_unrecorded_fields(recorded: tuple[str, ...], line: str | None) -> None:
    lit = positive()
    texts_of = {"posture": "Portfolio posture", "size": "position size"}
    for field in recorded:
        if field in texts_of:  # a decision field states its text inside its quote (r02)
            quote = {"source_id": "prior_case", "locator": "page:1", "quote": Q_NOREC1}
            lit["decision"][field] = {"text": texts_of[field], "quote": quote}
        else:
            quote = {"source_id": "prior_case", "locator": "page:2", "quote": Q_NOREC2}
            lit["thesis"][field] = {"quote": quote}
    limits = settle(lit).limitations
    assert POSITIVE_LIMITS[1] not in limits
    assert limits[1] == (POSITIVE_LIMITS[2] if line is None else line)


# 8-7 under round 9 item 2: an as-of date is the only date its quote states, so a split
# quotation cites its bid and its offer from separate single-date lines. No frozen page has
# such lines, so the side's quotation line is edited into two (a stated edit, hash recomputed).
SPLIT_LINES = {  # side -> (source, frozen line, edited lines, bid quote, offer quote, offer as-of)
    "expected": (
        "prior_case",
        (
            "Dealer quotation recorded at Approval, as of January 9, 2026: bid 98.50 and offer "
            "99.25, expressed as a percentage of par."
        ),
        (
            "Dealer quotation recorded at Approval, as of January 9, 2026: bid 98.50.\n"
            "Dealer offer recorded at Approval, as of January 10, 2026: offer 99.25, expressed as a "
            "percentage of par."
        ),
        "Dealer quotation recorded at Approval, as of January 9, 2026: bid 98.50.",
        "Dealer offer recorded at Approval, as of January 10, 2026: offer 99.25",
        "January 10, 2026",
    ),
    "realized": (
        "market_update",
        (
            "Dealer quotation on April 29, 2026: bid 98.00 and offer 98.75, expressed as a "
            "percentage of par."
        ),
        (
            "Dealer quotation on April 29, 2026: bid 98.00.\n"
            "Dealer offer on April 30, 2026: offer 98.75, expressed as a percentage of par."
        ),
        "Dealer quotation on April 29, 2026: bid 98.00.",
        "Dealer offer on April 30, 2026: offer 98.75",
        "April 30, 2026",
    ),
}


def split(lit: dict[str, Any], side: str) -> dict[str, Any]:
    """The side's bid and offer cited from the edited lines of ``split_pack``; the offer's
    date differs from the bid's (8-7)."""
    _, line, _, bid_quote, offer_quote, offer_as_of = SPLIT_LINES[side]
    for metric, quote in (("loan_bid", bid_quote), ("loan_offer", offer_quote)):
        obs = next(o for o in lit["observations"] if (o["side"], o["metric"]) == (side, metric))
        assert obs["quote"]["quote"] == line
        obs["quote"] = {**obs["quote"], "quote": quote}
        if metric == "loan_offer":
            obs["as_of_text"] = offer_as_of
    return lit


def split_pack(*sides: str) -> tuple[Source, ...]:
    packed = pack("positive")
    for side in sides:
        source_id, line, lines, *_ = SPLIT_LINES[side]
        packed = edited_pack(source_id, line, lines, base=packed)
    return packed


def split_row(sides: str) -> dict[str, str]:
    return {  # round 6c (b)
        "gap": "Mid level of the term loan quotation not compared",
        "missing_item": f"Same-day {sides} bid and offer",
        "why_it_matters": (
            f"The {sides} bid and offer are quoted on different dates, so no mid level is "
            "calculated and its variance cannot be measured"
        ),
        "impact_on_output": "Variance and attribution are shown only for the compared measures",
        "follow_up": "Cite a bid and an offer quoted on the same day",
    }


def test_8_7_both_sides_split_take_one_row() -> None:
    report = settle(
        uncompared(split(split(positive(), "expected"), "realized"), "loan_mid"),
        packed=split_pack("expected", "realized"),
    )
    t74 = cells(report, "T7.4", "loan_mid")
    assert missing(
        t74["realized"],
        "Not calculable: the realized bid and offer are quoted on different dates "
        "(2026-04-29 and 2026-04-30)",
    )
    assert texts(report, "T7.8", "not_compared_loan_mid") == split_row("expected and realized")
    assert report.derived.window_end == date(2026, 4, 30)  # the latest realized as-of date


MID_SPLIT = "Not calculable: the {} bid and offer are quoted on different dates ({})"
MID_ABSENT = {
    "realized": (
        "Not stated: no realized mid level of the term loan quotation is recorded from a "
        "post-decision source"
    ),
    "expected": (
        "Not stated: no expected mid level of the term loan quotation is recorded from the "
        "Prior Case record"
    ),
}
FOLLOW_UP_6H = {  # round 6h: the follow-up's second clause names the missing side's source
    "realized": "supply a dated post-decision source that states the quotation",
    "expected": "cite the expected quotation from the Prior Case record",
}


@pytest.mark.parametrize(
    ("split_side", "missing_side", "dates"),
    [
        ("expected", "realized", "2026-01-09 and 2026-01-10"),
        ("realized", "expected", "2026-04-29 and 2026-04-30"),
    ],
)
def test_6h_one_side_split_and_the_other_missing(
    split_side: str, missing_side: str, dates: str
) -> None:
    lit = without(split(positive(), split_side), missing_side, "loan_bid", "loan_offer")
    report = settle(uncompared(lit, "loan_mid"), packed=split_pack(split_side))
    assert texts(report, "T7.8", "not_compared_loan_mid") == {
        "gap": "Mid level of the term loan quotation not compared",
        "missing_item": f"Same-day {split_side} bid and offer, and a {missing_side} quotation",
        "why_it_matters": (
            f"The {split_side} bid and offer are quoted on different dates and no {missing_side} "
            "quotation is recorded, so no mid level is calculated and its variance cannot be "
            "measured"
        ),
        "impact_on_output": "Variance and attribution are shown only for the compared measures",
        "follow_up": "Cite a bid and an offer quoted on the same day; "
        + FOLLOW_UP_6H[missing_side],
    }
    t74 = cells(report, "T7.4", "loan_mid")  # 8-7 and 8-1/8-2, each side as before
    assert missing(t74[split_side], MID_SPLIT.format(split_side, dates))
    assert missing(t74[missing_side], MID_ABSENT[missing_side])
    assert missing(t74["direction"], NOT_CALCULABLE)
    assert (
        "Measures not compared: mid level of the term loan quotation; their variance and "
        "attribution are not shown."
    ) in report.limitations
    bid = cells(report, "T7.3", "loan_bid")["realized_value"]  # 6c (a): the row names itself
    if missing_side == "realized":
        reason = "Not stated: no realized dealer bid is recorded from a post-decision source"
        assert missing(bid, reason)
    else:
        assert bid.status == "known"


def test_8_7_bid_and_offer_dated_differently() -> None:
    lit, packed = split(positive(), "expected"), split_pack("expected")
    found = validate_ledger(submission=submission(lit), upstream=upstream("positive"), pack=packed)
    # the quotation is not compared, so its judgments are refused
    assert "confidence[2]: loan_mid is not a compared metric" in found
    report = settle(uncompared(lit, "loan_mid"), packed=packed)
    t74 = cells(report, "T7.4", "loan_mid")
    assert missing(
        t74["expected"],
        "Not calculable: the expected bid and offer are quoted on different dates "
        "(2026-01-09 and 2026-01-10)",
    )
    assert t74["realized"].status == "known" and missing(t74["direction"], NOT_CALCULABLE)
    assert report.derived.compared == ("total_leverage", "interest_cover")
    assert report.derived.window_days == EXPECTED["cases"]["positive"]["derived"]["window_days"]
    assert "CP-8-VAR-03" not in [c.claim_id for c in report.claims]
    assert (
        "Measures not compared: mid level of the term loan quotation; their variance and "
        "attribution are not shown."
    ) in report.limitations
    assert texts(report, "T7.8", "not_compared_loan_mid") == split_row("expected")  # 6c (b)


def test_8_9_prior_case_authority_from_cp0() -> None:
    up = upstream("positive")
    up = Upstream(as_of=up.as_of, authority={**up.authority, "prior_case": "issuer"}, cp6=None)
    report = settle(positive(), up=up)
    assert report.limitations[0] == (
        "The Prior Case record is a supplied file classified issuer by CP-0; its authenticity is "
        "its hash only."
    )


def validator_issues(lit: dict[str, Any], case: str = "positive") -> tuple[str, ...]:
    return validate_ledger(submission=submission(lit), upstream=upstream(case), pack=pack(case))


def test_8_10_text_without_its_quote() -> None:
    lit = positive()
    lit["decision"]["instrument"] = {"text": "Northbridge Term Loan"}
    assert validator_issues(lit) == ("decision.instrument: text and quote are given together",)


def test_8_10_quote_beside_an_absence() -> None:
    lit = positive()
    lit["decision"]["posture"]["quote"] = lit["decision"]["posture"]["absence"]["quote"]
    assert validator_issues(lit) == (
        "decision.posture: exactly one of quote and absence is required",
    )


def test_8_11_repeated_confidence() -> None:
    lit = positive()
    lit["confidence"].append(copy.deepcopy(lit["confidence"][0]))
    issue = "confidence: total_leverage appears more than once"
    assert validator_issues(lit) == (issue, issue)  # once per occurrence (r42)


def test_8_12_no_cp0_authority_is_an_invariant() -> None:
    up = upstream("positive")
    up = Upstream(
        as_of=up.as_of, authority={k: v for k, v in up.authority.items() if k != "update"}
    )
    with pytest.raises(ValueError, match="invariant"):
        validate_ledger(submission=submission(positive()), upstream=up, pack=pack("positive"))


def test_8_13_neither_form_given() -> None:
    lit = positive()
    lit["decision"]["posture"] = {}
    lit["thesis"]["exit_trigger"] = {}
    assert validator_issues(lit) == (
        "decision.posture: exactly one of text and absence is required",
        "thesis.exit_trigger: exactly one of quote and absence is required",
    )


def test_8_14_a_repeat_counts_whatever_the_first_entry() -> None:
    lit = copy.deepcopy(ENTRIES["r37"]["literal"])  # observations[4] as_of not in its quote
    lit["observations"].append(copy.deepcopy(SUBMISSIONS["positive"]["observations"][4]))
    assert validator_issues(lit) == (
        "observations[4]: as_of_text March 30, 2026 does not occur in the quote",
        "observations: (realized, total_leverage) appears more than once",
    )


def test_8_14_pairing_counts_an_invalid_bid() -> None:
    lit = positive()
    lit["observations"][6]["value_text"] = "97.00"  # realized bid not in its quote
    assert validator_issues(lit) == (
        "observations[6]: value_text 97.00 does not occur in the quote",
    )


@pytest.mark.parametrize(
    ("text", "issues"),
    [
        ("No default has occurred", ()),  # word start: "default" does not trip "fault"
        ("The buyer held the loan", ("synthesis.text: prohibited conclusion: buy",)),  # the limit
    ],
)
def test_8_16_prohibited_phrases_match_at_word_start(text: str, issues: tuple[str, ...]) -> None:
    lit = positive()
    lit["synthesis"]["text"] = text
    assert validator_issues(lit) == issues


def test_8_17_exit_trigger_absent() -> None:
    lit = positive()
    lit["thesis"]["exit_trigger"] = {
        "absence": {
            "quote": None,
            "reason": "The Prior Case record names no exit trigger",
            "follow_up": "Record an exit trigger at the next Approval",
        }
    }
    limits = settle(lit).limitations
    assert limits[2] == "No exit trigger is recorded, so exit discipline cannot be measured"
    assert POSITIVE_LIMITS[2] not in limits


def test_8_17_exit_trigger_stating_a_figure() -> None:
    lit = positive()
    lit["thesis"]["exit_trigger"] = {"quote": copy.deepcopy(lit["observations"][0]["quote"])}
    limits = settle(lit).limitations
    assert POSITIVE_LIMITS[2] not in limits
    assert not any("exit" in limit for limit in limits)


def test_8_17_a_footnote_mark_is_not_a_figure() -> None:
    # round 6c (f): only an ASCII digit states a threshold; a superscript mark keeps LIM_EXIT
    old = "Exit trigger recorded: a sharp move in the quotation. No threshold was recorded."
    new = old.replace("quotation.", "quotation." + SUPERSCRIPT_TWO)
    lit = positive()
    assert lit["thesis"]["exit_trigger"]["quote"]["quote"] == old
    lit["thesis"]["exit_trigger"]["quote"]["quote"] = new
    limits = settle(lit, packed=edited_pack("prior_case", old, new)).limitations
    assert limits[2] == POSITIVE_LIMITS[2]


def test_8_20_cp6_states_insufficient_information() -> None:
    fx = EXPECTED["decision_fixtures"]["fixture_cp6_insufficient"]
    cp6 = (fx["current_cp6"][0], fx["current_cp6"][1])
    report = settle(positive(), up=upstream("positive", cp6=cp6))
    assert texts(report, "T7.8", "current_decision") == {
        "gap": "No current decision to compare",
        "missing_item": "Current committee decision",
        "why_it_matters": "CP-6 states Insufficient Information",
        "impact_on_output": "The decision line of the what-changed block is missing",
        "follow_up": "Complete the CP-6 committee decision",
    }
    assert report.limitations[-1] == (
        "CP-6 states Insufficient Information, so the decision itself is not compared"
    )
    assert POSITIVE_LIMITS[-1] not in report.limitations


# --- property test: derive's exact arithmetic and comparison scope (8-7 extends it) ---------------

FIGURES = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("999.99"), places=2)
LATER = st.dates(min_value=date(2026, 1, 11), max_value=date(2027, 12, 31))
EARLIER = st.dates(min_value=date(2025, 1, 1), max_value=date(2026, 1, 10))
DECIDED = date(2026, 1, 10)


@settings(max_examples=300, deadline=None)
@given(
    values=st.tuples(FIGURES, FIGURES, FIGURES, FIGURES, FIGURES, FIGURES),
    expected_dates=st.tuples(EARLIER, EARLIER),
    realized_dates=st.tuples(LATER, LATER, LATER),
)
def test_derive_property(
    values: tuple[Decimal, ...],
    expected_dates: tuple[date, date],
    realized_dates: tuple[date, date, date],
) -> None:
    e_lev, r_lev, e_bid, e_offer, r_bid, r_offer = values
    e_bid_day, e_offer_day = expected_dates
    r_lev_day, r_bid_day, r_offer_day = realized_dates
    d = derive(
        inputs=LedgerInputs(
            expected={"total_leverage": e_lev, "loan_bid": e_bid, "loan_offer": e_offer},
            expected_as_of={
                "total_leverage": DECIDED,
                "loan_bid": e_bid_day,
                "loan_offer": e_offer_day,
            },
            realized={"total_leverage": r_lev, "loan_bid": r_bid, "loan_offer": r_offer},
            realized_as_of={
                "total_leverage": r_lev_day,
                "loan_bid": r_bid_day,
                "loan_offer": r_offer_day,
            },
            decision_date=DECIDED,
            downside_sizes={},
            overall_label="Thesis Confirmed",
            metric_labels=("Thesis Confirmed",),
            pack_source_ids=("identity", "prior_case"),
        )
    )
    lev, mid = d.measures["total_leverage"], d.measures["loan_mid"]
    assert lev.variance == r_lev - e_lev and lev.magnitude == abs(r_lev - e_lev)
    assert lev.direction == (
        "Higher" if r_lev > e_lev else "Lower" if r_lev < e_lev else "Unchanged"
    )
    same_dates = e_bid_day == e_offer_day and r_bid_day == r_offer_day
    assert ("loan_mid" in d.compared) == same_dates
    if same_dates:
        assert mid.expected == (e_bid + e_offer) / 2 / 100
        assert mid.realized == (r_bid + r_offer) / 2 / 100
        assert mid.variance is not None and mid.magnitude == abs(mid.variance)
        assert d.loan_mid_magnitude_bp == mid.magnitude * 10000
    else:
        assert (mid.variance, mid.direction, mid.magnitude, d.loan_mid_magnitude_bp) == (
            *(None, None, None),
            None,
        )
    assert "interest_cover" not in d.compared
    assert d.window_end == max(realized_dates)  # the latest realized as-of, compared or not
    assert d.window_days == (max(realized_dates) - DECIDED).days
    assert d.decisions_recorded == 1 and d.hit_rate == 1


def test_invalid_submission_does_not_compose() -> None:
    entry = ENTRIES["r23"]
    with pytest.raises(ValueError, match="validator issues"):
        decision_ledger(
            pack=pack("positive"),
            submission=submission(entry["literal"]),
            upstream=upstream("positive"),
        )


# --- fix round 1 (work/build/stage1/cp8/fix1-brief.md; review-adversary.md M1, L1) --------------
# readiness.citation_issues matches a quote through deploy_vii.quotes' normalisation, so every
# figure, date, label and text cp8 reads from a quote is read from that same normalised text.


def issues_over(lit: dict[str, Any], packed: tuple[Source, ...]) -> tuple[str, ...]:
    return validate_ledger(submission=submission(lit), upstream=upstream("positive"), pack=packed)


def requote(lit: dict[str, Any], at: int, old: str, new: str) -> dict[str, Any]:
    quote = lit["observations"][at]["quote"]
    assert quote["quote"] == old
    quote["quote"] = new
    return lit


Q_REALIZED_LEVERAGE = "Total leverage for the twelve months to March 31, 2026 is reported as 1.80x."


def test_m1_soft_hyphen_inside_a_quoted_figure() -> None:
    # p01: the matcher deletes U+00AD, so "bid 9-8.00" (soft hyphen) is the page's 98.00
    lit = positive()
    bid = lit["observations"][6]
    bid["quote"]["quote"] = bid["quote"]["quote"].replace("bid 98.00", f"bid 9{SOFT_HYPHEN}8.00")
    bid["value_text"] = "8.00"
    assert validator_issues(lit) == (
        "observations[6]: value_text 8.00 does not occur in the quote",
    )


def test_m1_whitespace_inside_a_quoted_date() -> None:
    # a no-break space the matcher collapses: the as-of date is read where the page states it
    new = Q_REALIZED_LEVERAGE.replace("March 31, 2026", f"March 31,{NO_BREAK_SPACE}2026")
    report = settle(requote(positive(), 4, Q_REALIZED_LEVERAGE, new))
    assert stored(report.derived) == EXPECTED["cases"]["positive"]["derived"]


def test_m1_mapped_dash_inside_a_quoted_designation() -> None:
    # an en dash the matcher maps to "-": the decision text is read from the normalised quote
    old = "on the Northbridge Term Loan."
    packed = edited_pack("prior_case", old, "on the Northbridge Term Loan B-2.")
    lit = positive()
    for field in ("action_bias", "confidence", "instrument"):
        quote = lit["decision"][field]["quote"]
        quote["quote"] = quote["quote"].replace(old, f"on the Northbridge Term Loan B{EN_DASH}2.")
    lit["decision"]["instrument"]["text"] = "Northbridge Term Loan B-2"
    report = settle(lit, packed=packed)
    assert cells(report, "T7.1", "d01")["instrument"].text == "Northbridge Term Loan B-2"


def test_m1_soft_hyphen_inside_a_quoted_size_level() -> None:
    # the level is read from the normalised quote, as the statement and span checks already were
    lit = positive()
    size = lit["thesis"]["downside_sizes"][0]["quote"]
    size["quote"] = size["quote"].replace("1.75x", f"1.7{SOFT_HYPHEN}5x")
    settle(lit)


def test_m1_whitespace_inside_a_quoted_default_date() -> None:
    lit = positive()
    statement = lit["default_restructuring"]["quote"]
    statement["quote"] = statement["quote"].replace(
        "April 30, 2026", f"April{NO_BREAK_SPACE}30, 2026"
    )
    settle(lit)


def test_8_15_the_first_figure_after_the_label() -> None:
    # p09: two frozen spans reach the rule; a later figure after the label is not the value
    page = next(s for s in pack("positive") if s.source_id == "update").spans[0].text
    span = page[page.index("Total leverage for the twelve months to February 28") :]
    span = span[: span.index(Q_REALIZED_LEVERAGE) + len(Q_REALIZED_LEVERAGE)]
    offer_as_bid = positive()
    offer_as_bid["observations"][6]["value_text"] = "98.75"
    assert validator_issues(offer_as_bid) == (
        "observations[6]: loan_bid value_text 98.75 is not labelled loan_bid in the quote",
    )
    assert validator_issues(requote(positive(), 4, Q_REALIZED_LEVERAGE, span)) == (
        (
            "observations[4]: total_leverage value_text 1.80 is not labelled total_leverage in "
            "the quote"
        ),
    )


def test_8_15_a_figure_is_quoted_as_n_nn() -> None:
    new = Q_REALIZED_LEVERAGE.replace("1.80x", "1.8x")
    lit = requote(positive(), 4, Q_REALIZED_LEVERAGE, new)
    lit["observations"][4]["value_text"] = "1.8"
    assert issues_over(lit, edited_pack("update", Q_REALIZED_LEVERAGE, new)) == (
        "observations[4]: value_text 1.8 does not occur in the quote",
    )


def test_a_value_quoted_twice_is_refused() -> None:
    new = Q_REALIZED_LEVERAGE.replace("1.80x.", "1.80x, as it was a quarter earlier at 1.80x.")
    lit = requote(positive(), 4, Q_REALIZED_LEVERAGE, new)
    assert issues_over(lit, edited_pack("update", Q_REALIZED_LEVERAGE, new)) == (
        "observations[4]: value_text 1.80 does not occur in the quote",
    )


def test_a_realized_figure_dated_on_the_decision_day_is_refused() -> None:
    new = Q_REALIZED_LEVERAGE.replace("March 31, 2026", "January 10, 2026")
    lit = requote(positive(), 4, Q_REALIZED_LEVERAGE, new)
    lit["observations"][4]["as_of_text"] = "January 10, 2026"
    assert issues_over(lit, edited_pack("update", Q_REALIZED_LEVERAGE, new)) == (
        "observations[4]: realized as_of January 10, 2026 is not after the decision date",
    )


def test_a_default_statement_dated_on_the_decision_day_is_refused() -> None:
    old = "No default or restructuring has occurred as of April 30, 2026."
    new = old.replace("April 30, 2026", "January 10, 2026")
    lit = positive()
    assert lit["default_restructuring"]["quote"]["quote"] == old
    lit["default_restructuring"]["quote"]["quote"] = new
    lit["default_restructuring"]["as_of_text"] = "January 10, 2026"
    assert issues_over(lit, edited_pack("update", old, new)) == (
        "default_restructuring: as_of January 10, 2026 is not after the decision date",
    )


def test_a_blank_flag_quote_is_refused() -> None:
    lit = positive()
    lit["attributions"][0]["flag_quote"] = "   "
    assert validator_issues(lit) == ("attributions[0]: Flagged Risk Materialized needs flag_quote",)


def test_a_numeric_character_counts_as_a_digit_in_analyst_text() -> None:
    lit = positive()
    lit["synthesis"]["text"] = f"About {ONE_HALF} of the measures moved"  # numeric, not isdigit
    assert validator_issues(lit) == ("synthesis.text: digits are not allowed",)


def test_derive_runs_under_the_exact_context() -> None:
    fx = EXPECTED["fixtures"]["fixture_partial"]["inputs"]
    inputs = LedgerInputs(
        expected={"total_leverage": Decimal("1.0000000000000000000000000001")},
        expected_as_of={"total_leverage": DECIDED},
        realized={"total_leverage": Decimal(10)},  # 10 - that needs 29 digits
        realized_as_of={"total_leverage": date(2026, 3, 31)},
        decision_date=DECIDED,
        downside_sizes={},
        overall_label=fx["overall_label"],
        metric_labels=tuple(fx["metric_labels"]),
        pack_source_ids=POSITIVE_PACK_IDS,
    )
    with pytest.raises(Inexact):
        derive(inputs=inputs)


def test_composition_runs_under_the_exact_context(monkeypatch: pytest.MonkeyPatch) -> None:
    traps: list[bool] = []

    def spy(day: date) -> str:  # cp8 calls format_date only inside composition
        traps.append(bool(getcontext().traps[Inexact]))
        return format_date(day)

    monkeypatch.setattr(cp8_module, "format_date", spy)
    report_of("positive")
    assert traps and all(traps)


# --- LEAD round 9, CP-8 items 1-5 (docs/rulings/2026-10-28-stage1.md, "# Round 9") ---------------

UPDATE_PAGE = next(s for s in pack("positive") if s.source_id == "update").spans[0].text


def update_span(first: str, last: str) -> str:
    """A verbatim span of the frozen update page from ``first`` through ``last``."""
    start = UPDATE_PAGE.index(first)
    return UPDATE_PAGE[start : UPDATE_PAGE.index(last, start) + len(last)]


@pytest.mark.parametrize(
    ("field", "text"),
    [
        ("action_bias", ""),
        ("confidence", " "),
        ("instrument", ""),
        ("decision_date", " "),
        ("decision_maker_role", " "),
        ("posture", " "),
    ],
)
def test_r9_1_blank_decision_text_is_empty(field: str, text: str) -> None:
    lit = positive()
    item = lit["decision"][field]
    quote = item["absence"]["quote"] if "absence" in item else item["quote"]
    lit["decision"][field] = {"text": text, "quote": quote}
    assert validator_issues(lit) == (f"decision.{field}: text is empty",)


def test_r9_2_an_as_of_is_the_only_date_its_quote_states() -> None:
    # p03: realized leverage carrying the default line's date from a longer verbatim span
    lev = positive()
    lev["observations"][4]["quote"]["quote"] = update_span(Q_REALIZED_LEVERAGE, "April 30, 2026.")
    lev["observations"][4]["as_of_text"] = "April 30, 2026"
    assert validator_issues(lev) == (
        "observations[4]: as_of_text April 30, 2026 is not the only date in the quote",
    )
    # the expected side too: the offer's span reaches the cover line's date (the old 8-7 setup)
    offer = positive()
    offer["observations"][3].update(as_of_text="January 10, 2026")
    offer["observations"][3]["quote"]["quote"] = Q_OFFER_TWO_DATES
    assert validator_issues(offer) == (
        "observations[3]: as_of_text January 10, 2026 is not the only date in the quote",
    )
    # the default statement
    default = positive()
    span = update_span(Q_REALIZED_LEVERAGE, "April 30, 2026.")
    default["default_restructuring"]["quote"]["quote"] = span
    assert validator_issues(default) == (
        "default_restructuring: as_of_text April 30, 2026 is not the only date in the quote",
    )
    # a repeat of the same date is fine
    same = positive()
    two = update_span(Q_REALIZED_LEVERAGE, "is reported as 5.50x.")
    same["observations"][4]["quote"]["quote"] = two
    assert two.count("March 31, 2026") == 2
    assert validator_issues(same) == ()


@pytest.mark.parametrize("authority", ["unknown", "issuer"])
def test_r9_3_a_default_statement_cannot_cite_prior_case(authority: str) -> None:
    # p10: a Prior Case page carrying an incidence line, whatever CP-0 classifies it
    line = "No default or restructuring had occurred as of February 2, 2026."
    packed = edited_pack("prior_case", "Exit trigger recorded:", line + "\nExit trigger recorded:")
    base = upstream("positive")
    up = Upstream(as_of=base.as_of, authority={**base.authority, "prior_case": authority})
    lit = positive()
    lit["default_restructuring"] = {
        "as_of_text": "February 2, 2026",
        "quote": {"source_id": "prior_case", "locator": "page:2", "quote": line},
    }
    found = validate_ledger(submission=submission(lit), upstream=up, pack=packed)
    assert found == (
        "default_restructuring.quote: a default or restructuring statement cannot cite prior_case",
    )


def test_r9_4_the_source_rule_comes_before_locator_and_quote() -> None:
    # p11: two defects each; lease :60 reports the field's own source rule first
    on_prior_case = positive()
    on_prior_case["observations"][4]["quote"] = {
        "source_id": "prior_case",
        "locator": "page:9",
        "quote": "Total leverage 1.80x",
    }
    assert validator_issues(on_prior_case) == (
        "observations[4].quote: a realized observation cannot cite prior_case",
    )
    third_party = positive()
    third_party["observations"][4]["quote"] = {
        "source_id": "market_update",
        "locator": "page:1",
        "quote": "Total leverage 1.80x as of March 31, 2026",
    }
    assert validator_issues(third_party) == (
        (
            "observations[4]: total_leverage needs an issuer source, market_update is third_party "
            "(CP-0 T3)"
        ),
    )
    default = positive()
    default["default_restructuring"]["quote"] = {
        "source_id": "market_update",
        "locator": "page:1",
        "quote": "No default as of April 30, 2026.",
    }
    assert validator_issues(default) == (
        "default_restructuring: needs an issuer source, market_update is third_party (CP-0 T3)",
    )


def test_r9_5_an_exit_trigger_absence_has_its_gap_row() -> None:
    lit = positive()
    reason, follow_up = (
        "The Prior Case record names no exit trigger",
        "Record an exit trigger at the next Approval",
    )
    lit["thesis"]["exit_trigger"] = {
        "absence": {"quote": None, "reason": reason, "follow_up": follow_up}
    }
    report = settle(lit)
    rows = row_ids(report, "T7.8")
    assert rows[rows.index("expected_hold") + 1] == "exit_trigger"  # T7.2 order: exit last
    assert texts(report, "T7.8", "exit_trigger") == {
        "gap": "Exit trigger not recorded",
        "missing_item": "Exit trigger",
        "why_it_matters": reason,
        "impact_on_output": "Exit discipline cannot be measured",
        "follow_up": follow_up,
    }
    assert (
        report.limitations[2]
        == "No exit trigger is recorded, so exit discipline cannot be measured"
    )
