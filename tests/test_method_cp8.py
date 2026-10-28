"""CP-8 Stage 1: validator, Decimal diff and composed result against the frozen oracle.

Every expected value is read from ``cases/cp8-owner/expected.json`` (with the literal submissions,
the manifest's frozen pages and the CP-0 facts the oracle pins); nothing here is derived from the
code under test. The tool-use rules (``RULES``), the G1-level refusals, the blocked and refused
execution cases, store, tamper, rendering and consumption are Stages 2-4.
"""

import copy
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
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


@pytest.mark.parametrize("name", list(EXPECTED["fixtures"]))
def test_fixture_derive(name: str) -> None:
    fx = EXPECTED["fixtures"][name]["inputs"]
    inputs = LedgerInputs(
        expected={k: Decimal(v) for k, v in fx["expected"].items()},
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


# --- fail closed where neither the lease nor the oracle pins wording (reported for LEAD) ---------


def _partial_outcome() -> dict[str, Any]:
    """The positive literal without the realized interest cover (a valid, partial outcome)."""
    lit: dict[str, Any] = copy.deepcopy(SUBMISSIONS["positive"])
    lit["observations"] = [
        o
        for o in lit["observations"]
        if not (o["side"] == "realized" and o["metric"] == "interest_cover")
    ]
    lit["confidence"] = [c for c in lit["confidence"] if c["metric_id"] != "interest_cover"]
    lit["attributions"] = [a for a in lit["attributions"] if a["metric_id"] != "interest_cover"]
    lit["lessons"] = [{**lit["lessons"][0], "metric_ids": ["total_leverage"]}]
    return lit


def _unsound_overall() -> dict[str, Any]:
    """The positive literal with an overall Unflagged Risk Materialized judged unsound."""
    lit: dict[str, Any] = copy.deepcopy(SUBMISSIONS["positive"])
    overall = lit["attributions"][3]
    overall.update(
        label="Unflagged Risk Materialized",
        process_sound="N",
        originating_module="CP-3",
        flag_quote=None,
    )
    return lit


@pytest.mark.parametrize("literal", [_partial_outcome, _unsound_overall])
def test_unpinned_wording_fails_closed(literal: Any) -> None:
    sub = submission(literal())
    assert (
        validate_ledger(submission=sub, upstream=upstream("positive"), pack=pack("positive")) == ()
    )
    with pytest.raises(ValueError, match="no pinned wording"):
        decision_ledger(pack=pack("positive"), submission=sub, upstream=upstream("positive"))


def test_invalid_submission_does_not_compose() -> None:
    entry = ENTRIES["r23"]
    with pytest.raises(ValueError, match="validator issues"):
        decision_ledger(
            pack=pack("positive"),
            submission=submission(entry["literal"]),
            upstream=upstream("positive"),
        )
