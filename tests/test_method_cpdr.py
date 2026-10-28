"""CP-DR Stage 1: the agenda and the composed result against the frozen oracle.

Every expected value comes from ``cases/cpdr-owner/expected.json`` (with the CP-0 upstream facts it
pins and the manifest's frozen pages); nothing here is derived from the code under test. The
tool-use rules (``RULES``), store, execution, rendering and tamper sections are Stages 2-4.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_vii import prose
from deploy_vii.contracts import Citation, Fact, Source, Span, validate_tables
from deploy_vii.report_view import fact_spelling
from deploy_workflow.owners.cpdr import (
    AgendaGap,
    CpdrInputs,
    ResearchSubmission,
    bookkeeping,
    compose,
    parse_agenda,
    validate_research,
)

ROOT = Path(__file__).parents[1]
CASE = ROOT / "cases/cpdr-owner"
EXPECTED = json.loads((CASE / "expected.json").read_text())
SUBMISSIONS = json.loads((CASE / "submissions.json").read_text())
MANIFEST = json.loads((CASE / "manifest.json").read_text())
FINANCIAL = json.loads((ROOT / "cases/financial/manifest.json").read_text())
SNAPSHOT = json.loads((ROOT / "cases/snapshot/manifest.json").read_text())
AS_OF = date.fromisoformat(MANIFEST["run"]["as_of"])
GAP_REF = "G1"  # any report-wide gap number; the oracle spells it G# (bound at run time)
# The two RULES (tool-use) issue families; G1-X appends them after the validator issues (Stage 2).
RULES_PREFIXES = (
    "Absence claim without a recorded search:",
    "Cited page not read through read_pages:",
)


def cp0_facts(*, empty: bool) -> tuple[Fact, ...]:
    """The CP-0 T5 fact the oracle pins (readiness.build_readiness field() coordinates)."""
    if empty:
        up = EXPECTED["cp0_upstream_empty_agenda"]
        fact_id, text = up["review_gaps_fact_id"], up["review_gaps_fact_text"]
    else:
        up = EXPECTED["cp0_upstream"]
        fact_id, text = up["gap_fact_id"], up["gap_fact_text"]
    table, rest = fact_id.split(".", 1)
    row, field = rest.rsplit(".", 1)
    return (
        Fact(fact_id=fact_id, label=field, table_id=table, row_id=row, field=field, text=text),
        # A non-T5 CP-0 fact the agenda parser must ignore.
        Fact(
            fact_id="T7.run.method",
            label="method",
            table_id="T7",
            row_id="run",
            field="method",
            text="deploy-v-r14",
        ),
    )


def agenda(*, empty: bool) -> tuple[AgendaGap, ...]:
    return parse_agenda(cp0_facts(empty=empty))


def sources() -> tuple[Source, ...]:
    """The ready pack: identity and financial from the financial case, the business gap note."""
    business = SNAPSHOT["business_source"]
    items = [
        *(s for s in FINANCIAL["sources"] if s["source_id"] in {"identity", "financial"}),
        {**business["common"], **business["gap"]},
    ]
    pinned = {s["source_id"]: s["sha256"] for s in MANIFEST["sources"]}
    return tuple(
        Source(
            source_id=item["source_id"],
            name=item["name"],
            status="ready",
            sha256=pinned[item["source_id"]],
            spans=tuple(Span(locator=p["locator"], text=p["text"]) for p in item["pages"]),
            extraction_status="complete",
        )
        for item in items
    )


def submission(payload: dict[str, Any]) -> ResearchSubmission:
    return ResearchSubmission.model_validate_json(json.dumps(payload))


def oracle_fact(item: dict[str, Any]) -> Fact:
    data = dict(item)
    if "amount" in data:
        data["amount"] = Decimal(data["amount"])
    data["citations"] = tuple(Citation(**c) for c in data.get("citations", ()))
    return Fact(**data)


def spell(text: str, facts: dict[str, Fact]) -> str:
    """A claim's text spelled with the product's own fact spelling (the oracle's ``spelled``)."""
    return "".join(
        run.text if run.kind == "text" else fact_spelling(facts[run.text], None)[2]
        for run in prose.tokenize(text)
    )


def counts(gaps: Any) -> list[dict[str, Any]]:
    return [
        {
            "gap_id": g.gap_id,
            "questions": g.questions,
            "answered": g.answered,
            "unresolved": g.unresolved,
            "answered_share": str(g.answered_share),
            "status": g.status,
        }
        for g in gaps
    ]


TOTAL_KEYS = (
    "gaps_total",
    "gaps_resolved",
    "gaps_partial",
    "gaps_unresolved",
    "questions_total",
    "answered_total",
    "unresolved_total",
)


# --- agenda (Method 1) ----------------------------------------------------------------------------


def test_agenda_parses_the_cp0_gap_fact() -> None:
    row = EXPECTED["cases"]["partial"]["tables"]["TDR.1"]["rows"][0]
    gap_view = MANIFEST["view_tree_draft"]["keys"]["gaps"][0]
    (gap,) = agenda(empty=False)
    assert gap.gap_id == row[0] == gap_view["gap_id"]
    assert gap.kind_severity == row[1]["kind_severity"]["text"]
    assert gap.kind_severity == f"{gap_view['kind']}/{gap_view['severity']}"
    assert gap.description == row[1]["description"]["text"] == gap_view["description"]
    assert gap.named_consumers == tuple(gap_view["named_consumers"])
    assert ", ".join(gap.named_consumers) == row[1]["named_consumers"]["text"]
    assert gap.remediation == gap_view["remediation"]


def test_empty_agenda_from_the_review_gaps_fact() -> None:
    assert agenda(empty=True) == ()


def test_agenda_without_a_t5_fact_fails_closed() -> None:
    with pytest.raises(ValueError, match="no T5"):
        parse_agenda(cp0_facts(empty=False)[1:])


# --- composed result per case (Method 2-8) --------------------------------------------------------


@pytest.mark.parametrize("case_id", ["partial", "unresolved", "empty_agenda"])
def test_case_matches_the_oracle(case_id: str) -> None:
    want = EXPECTED["cases"][case_id]
    sub = submission(SUBMISSIONS["cpdr"][case_id])
    gaps = agenda(empty=case_id == "empty_agenda")
    assert validate_research(submission=sub, agenda=gaps, sources=sources()) == ()

    result = compose(CpdrInputs(agenda=gaps, submission=sub, as_of=AS_OF))

    bk = result.bookkeeping
    for key in TOTAL_KEYS:
        assert getattr(bk, key) == want["bookkeeping"][key], key
    share = None if bk.answered_share is None else str(bk.answered_share)
    assert share == want["bookkeeping"]["answered_share"]
    assert counts(bk.gaps) == want["bookkeeping"]["gaps"]

    # every fact behind every cell, in order
    assert result.facts == tuple(oracle_fact(f) for f in want["facts"])
    validate_tables(result.tables, result.facts)
    facts = {f.fact_id: f for f in result.facts}

    # tables cell for cell
    assert [t.table_id for t in result.tables] == list(want["tables"])
    for table in result.tables:
        exp = want["tables"][table.table_id]
        assert table.title == exp["title"]
        assert table.row_header == exp["row_header"]
        assert [r.row_id for r in table.rows] == [r[0] for r in exp["rows"]]
        for row, (_, cells) in zip(table.rows, exp["rows"], strict=True):
            assert [c.field for c in table.columns] == list(cells)
            for fact_id, (field, cell) in zip(row.fact_ids, cells.items(), strict=True):
                fact = facts[fact_id]
                assert fact_id == cell["fact"], field
                _, state, shown = fact_spelling(fact, GAP_REF)
                assert state == cell["state"], fact_id
                assert shown == cell["shown"].replace("G#", GAP_REF), fact_id
                if state == "known":
                    assert fact.value_class == cell["value_class"], fact_id
                    assert fact.unit == cell["unit"], fact_id
                    if "amount" in cell:
                        assert str(fact.amount) == cell["amount"], fact_id
                    else:
                        assert fact.text == cell["text"], fact_id

    # claims
    assert [c.claim_id for c in result.claims] == [c["claim_id"] for c in want["claims"]]
    for claim, exp in zip(result.claims, want["claims"], strict=True):
        assert claim.text == exp["text"]
        assert claim.citations == tuple(Citation(**c) for c in exp["citations"])
        assert spell(claim.text, facts) == exp["spelled"]
        assert prose.issues(claim.text, prose.bind(result.facts)) == ()

    # own limitations (execution adds the synthetic line and the inherited set: Stage 2)
    assert result.limitations == tuple(want["own_limitations"])
    assert result.consumption_facts == (
        *want["consumption_facts"]["per_gap"],
        *want["consumption_facts"]["totals"],
        *want["consumption_facts"]["missing_for_unresolved"],
    )


# --- fixtures (acceptance 4) ----------------------------------------------------------------------


def _fixture_payload(name: str) -> dict[str, Any]:
    """build.py:741-742: Q1, Q2, Q3 are the partial submission's three literal questions."""
    (gap,) = SUBMISSIONS["cpdr"]["partial"]["gaps"]
    q1, q2, q3 = gap["questions"]
    first = {"gap_id": gap["gap_id"], "questions": [q1, q2]}
    if name == "fixture_resolved":
        return {"gaps": [first]}
    return {"gaps": [first, {"gap_id": "second-gap", "questions": [q3]}]}


@pytest.mark.parametrize("name", ["fixture_resolved", "fixture_two_gaps"])
def test_fixture_bookkeeping(name: str) -> None:
    want = EXPECTED["fixtures"][name]["derived"]
    bk = bookkeeping(submission=submission(_fixture_payload(name)))
    for key in TOTAL_KEYS:
        assert getattr(bk, key) == want[key], key
    assert str(bk.answered_share) == want["answered_share"]
    assert counts(bk.gaps) == [{k: v for k, v in g.items() if k != "shown"} for g in want["gaps"]]


# --- content refusals (validator rules 1-7; the RULES part is Stage 2) ----------------------------


@pytest.mark.parametrize("name", list(EXPECTED["refusals"]))
def test_refusal_validator_issues(name: str) -> None:
    item = SUBMISSIONS["refusal_inputs"][name]
    pinned = tuple(EXPECTED["refusals"][name]["step_issues"])
    content = tuple(i for i in pinned if not i.startswith(RULES_PREFIXES))
    gaps = agenda(empty=item["cp0"] == "cp0_readiness_review_empty_agenda")
    got = validate_research(submission=submission(item["payload"]), agenda=gaps, sources=sources())
    assert got == content


def test_blocked_attempts_validator_issues() -> None:
    for attempt in ("attempt_0", "attempt_1"):
        got = validate_research(
            submission=submission(SUBMISSIONS["cpdr"]["blocked"][attempt]),
            agenda=agenda(empty=False),
            sources=sources(),
        )
        assert got == tuple(EXPECTED["blocked"][attempt]["issues"]), attempt
