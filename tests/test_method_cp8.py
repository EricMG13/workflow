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
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from deploy_vii import prose
from deploy_vii.contracts import Fact, Source, Span, validate_tables
from deploy_vii.readiness import shape_issues
from deploy_vii.report_view import fact_spelling
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

NOT_CALCULABLE = "Not calculable: needs an expected and a realized value"  # pinned (no_outcome)
NOT_ASSESSED = "Not assessed: the measure is not compared"  # pinned (no_outcome)
POSITIVE_LIMITS = tuple(EXPECTED["cases"]["positive"]["own_limitations"])
LIM_INTERIM = POSITIVE_LIMITS[3]
Q_OFFER_TWO_DATES = (  # prior_case page:2, verbatim: the offer's span reaches the cover line's date
    "Interest cover recorded at Approval on January 10, 2026 was 6.00x.\n"
    "Dealer quotation recorded at Approval, as of January 9, 2026: bid 98.50 and offer 99.25"
)


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


def edited_pack(source_id: str, old: str, new: str, case: str = "positive") -> tuple[Source, ...]:
    """The case's pack with one stated line edit on one source (its hash recomputed)."""
    out = []
    for source in pack(case):
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
    # <name> is the T7.4 row label: the quotation's bid and offer feed the mid's row
    mid = (
        "Not stated: no realized mid level of the term loan quotation is recorded from a "
        "post-decision source"
    )
    assert missing(cells(report, "T7.3", "loan_bid")["realized_value"], mid)
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


def test_8_2_missing_expected_under_outcome_absence_still_fails_closed() -> None:
    # not ruled: the T7.4 evidence cell then cites nothing and no gap wording is pinned for it
    sub = submission(
        without(copy.deepcopy(SUBMISSIONS["no_outcome"]), "expected", "total_leverage")
    )
    up, packed = upstream("no_outcome"), pack("no_outcome")
    assert validate_ledger(submission=sub, upstream=up, pack=packed) == ()
    with pytest.raises(ValueError, match="no pinned wording"):
        decision_ledger(pack=packed, submission=sub, upstream=up)


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


def test_8_7_bid_and_offer_dated_differently() -> None:
    lit = positive()
    offer = lit["observations"][3]
    assert (offer["side"], offer["metric"]) == ("expected", "loan_offer")
    offer.update(
        as_of_text="January 10, 2026", quote={**offer["quote"], "quote": Q_OFFER_TWO_DATES}
    )
    with_judgments = submission(lit)
    found = validate_ledger(
        submission=with_judgments, upstream=upstream("positive"), pack=pack("positive")
    )
    # the quotation is not compared, so its judgments are refused
    assert "confidence[2]: loan_mid is not a compared metric" in found
    report = settle(uncompared(lit, "loan_mid"))
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
    # not ruled: 8-1's T7.8 wording ("No expected value is recorded") would be false here; no row
    assert "not_compared_loan_mid" not in row_ids(report, "T7.8")


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
