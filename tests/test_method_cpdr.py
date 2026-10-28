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
    assert validate_research(submission=sub, upstream=gaps, pack=sources()) == ()

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
    got = validate_research(submission=submission(item["payload"]), upstream=gaps, pack=sources())
    assert got == content


def test_blocked_attempts_validator_issues() -> None:
    for attempt in ("attempt_0", "attempt_1"):
        got = validate_research(
            submission=submission(SUBMISSIONS["cpdr"]["blocked"][attempt]),
            upstream=agenda(empty=False),
            pack=sources(),
        )
        assert got == tuple(EXPECTED["blocked"][attempt]["issues"]), attempt


# --- lease-literal cases (fix round 1; strings and rules verbatim from docs/CPDR-OWNER-LEASE.md) --
# Payloads reuse the oracle's literal questions (submissions.json#cpdr.partial / .unresolved) with
# one stated edit each; the expected strings are the lease's own wording, never expected.json.

PARTIAL_GAP = SUBMISSIONS["cpdr"]["partial"]["gaps"][0]
TRANSACTIONS, DISTRIBUTIONS, OWNER = PARTIAL_GAP["questions"]
POLICY = SUBMISSIONS["cpdr"]["unresolved"]["gaps"][0]["questions"][1]
GAP_ID = PARTIAL_GAP["gap_id"]


def one_gap(*questions: dict[str, Any]) -> ResearchSubmission:
    return submission({"gaps": [{"gap_id": GAP_ID, "questions": list(questions)}]})


def edited(question: dict[str, Any], **changes: Any) -> dict[str, Any]:
    return {**question, **changes}


def check(sub: ResearchSubmission, pack: tuple[Source, ...] | None = None) -> tuple[str, ...]:
    return validate_research(
        submission=sub, upstream=agenda(empty=False), pack=sources() if pack is None else pack
    )


@pytest.mark.parametrize(
    "questions",
    [
        pytest.param([TRANSACTIONS], id="one-question"),
        pytest.param([TRANSACTIONS, DISTRIBUTIONS, OWNER, POLICY], id="four-questions"),
    ],
)
def test_a_gap_accepts_one_to_four_questions(questions: list[dict[str, Any]]) -> None:
    # lease-literal: :112 "not 1 to 4 questions" is the only count refusal; 1 and 4 are accepted
    assert check(one_gap(*questions)) == ()


def test_answered_without_category() -> None:
    # lease-literal: :114 answered: missing answer, category or citation
    sub = one_gap(edited(TRANSACTIONS, category=None), DISTRIBUTIONS, OWNER)
    issue = "an answered question needs an answer, a category and at least one citation: "
    assert check(sub) == (issue + "transactions",)


def test_not_found_with_a_citation_only() -> None:
    # lease-literal: :114 not_found: has an answer, category or citation (the citation is a
    # verbatim, in-pack literal, so rule 6 adds nothing)
    sub = one_gap(TRANSACTIONS, DISTRIBUTIONS, edited(OWNER, citations=TRANSACTIONS["citations"]))
    assert check(sub) == (
        "a not_found question carries no answer, category or citation: owner-identity",
    )


def test_several_content_issues_on_one_question_in_rule_order() -> None:
    # lease-literal: :114 then :117 (rule 4, then rule 7: digit rule, then prohibited words)
    sub = one_gap(
        edited(TRANSACTIONS, limitation="We recommend asking about 2025."), DISTRIBUTIONS, OWNER
    )
    assert check(sub) == (
        "an answered question carries no limitation: transactions",
        "text must not contain a figure: transactions",
        "text carries a prohibited conclusion: transactions",
    )


def test_digit_in_question_text() -> None:
    # lease-literal: :117 the digit rule covers the question `text`
    sub = one_gap(TRANSACTIONS, DISTRIBUTIONS, edited(OWNER, text="Who owned the issuer in 2025?"))
    assert check(sub) == ("text must not contain a figure: owner-identity",)


def test_prohibited_word_in_question_text() -> None:
    # lease-literal: :117 prohibited words in the same fields (question `text` included)
    sub = one_gap(TRANSACTIONS, DISTRIBUTIONS, edited(OWNER, text="Who holds the recovery claim?"))
    assert check(sub) == ("text carries a prohibited conclusion: owner-identity",)


@pytest.mark.parametrize("word", ["Recommend", "REFINANCING", "covenant", "Recovery"])
def test_each_prohibited_word_case_insensitive(word: str) -> None:
    # lease-literal: :117 case-insensitive substrings "recommend", "refinanc", "covenant", "recovery"
    limitation = f"No prepared source names the {word} terms."
    sub = one_gap(TRANSACTIONS, DISTRIBUTIONS, edited(OWNER, limitation=limitation))
    assert check(sub) == ("text carries a prohibited conclusion: owner-identity",)


def test_a_pack_source_that_is_not_ready() -> None:
    # lease-literal: :115 a source that is not a ready pack source
    missing = Source(
        source_id="registry",
        name="Shareholder register",
        status="missing",
        limitation="The shareholder register was not supplied.",
    )
    searched = [*OWNER["searched_sources"], "registry"]
    sub = one_gap(TRANSACTIONS, DISTRIBUTIONS, edited(OWNER, searched_sources=searched))
    assert check(sub, (*sources(), missing)) == (
        "searched source is not a ready prepared source: owner-identity registry",
    )


def _t5(text: str) -> Fact:
    return Fact(
        fact_id=f"T5.{GAP_ID}.gap",
        label="gap",
        table_id="T5",
        row_id=GAP_ID,
        field="gap",
        text=text,
    )


def test_gap_description_containing_a_semicolon() -> None:
    # lease-literal: :46 kind/severity before the first ": "; consumers between the last
    # "; affects " and the next "; "; remediation the rest (T5 text form: readiness.py:500)
    (gap,) = parse_agenda(
        (
            _t5(
                "scope/material: Ownership content is absent; transaction content is absent; "
                "affects CP-DR, CP-5; Supply the ownership and transaction documents"
            ),
        )
    )
    assert gap.kind_severity == "scope/material"
    assert gap.description == "Ownership content is absent; transaction content is absent"
    assert gap.named_consumers == ("CP-DR", "CP-5")
    assert gap.remediation == "Supply the ownership and transaction documents"


def test_gap_with_no_named_consumer() -> None:
    # readiness.py:500 joins affected_modules with ", ": an empty list leaves "affects ; "
    (gap,) = parse_agenda((_t5("scope/material: Ownership is absent; affects ; Supply it"),))
    assert gap.named_consumers == ()
    assert gap.remediation == "Supply it"


def test_share_rounds_half_up_at_four_places() -> None:
    # lease-literal: :47 share = a / n quantised to 4 places ROUND_HALF_UP; 1 / 32 = 0.03125
    # is a tie at the fifth place (bookkeeping counts any submission; 8 gaps x 4 questions)
    def renamed(question: dict[str, Any], suffix: str) -> dict[str, Any]:
        return edited(question, question_id=f"{question['question_id']}-{suffix}")

    gaps = [
        {
            "gap_id": f"gap-{g}",
            "questions": [
                renamed(TRANSACTIONS if (g, i) == (0, 0) else OWNER, f"{g}-{i}") for i in range(4)
            ],
        }
        for g in range(8)
    ]
    bk = bookkeeping(submission=submission({"gaps": gaps}))
    assert (bk.questions_total, bk.answered_total) == (32, 1)
    assert bk.answered_share == Decimal("0.0313")
    assert str(bk.answered_share) == "0.0313"


# --- compose fails closed (fix round 1, item 5) ---------------------------------------------------


def test_compose_refuses_an_agenda_gap_missing_from_the_submission() -> None:
    inputs = CpdrInputs(
        agenda=agenda(empty=False), submission=submission({"gaps": []}), as_of=AS_OF
    )
    with pytest.raises(ValueError, match="missing from the submission"):
        compose(inputs)


def test_compose_refuses_a_submission_against_the_empty_agenda() -> None:
    # the empty-agenda limitation is decided by the agenda: a non-empty submission never gets it
    sub = submission(SUBMISSIONS["cpdr"]["partial"])
    with pytest.raises(ValueError, match="not in the CP-0 agenda"):
        compose(CpdrInputs(agenda=agenda(empty=True), submission=sub, as_of=AS_OF))


def test_compose_refuses_a_repeated_gap() -> None:
    sub = submission(SUBMISSIONS["refusal_inputs"]["gap_repeated"]["payload"])
    with pytest.raises(ValueError, match="appears twice"):
        compose(CpdrInputs(agenda=agenda(empty=False), submission=sub, as_of=AS_OF))
