"""CP-DR Stage 1: the agenda and the composed result against the frozen oracle.

Every expected value comes from ``cases/cpdr-owner/expected.json`` (with the CP-0 upstream facts it
pins and the manifest's frozen pages); nothing here is derived from the code under test. The
tool-use rules (``RULES``), store, execution, rendering and tamper sections are Stages 2-4.
"""

import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from defect_classes import BLANK_CASES, EMPTY_TEXT, Adapter, BlankCase, blank_failure

from deploy_vii import prose
from deploy_vii.contracts import Citation, Fact, Source, Span, validate_tables
from deploy_vii.report_view import fact_spelling
from deploy_workflow.owners.cpdr import (
    AgendaGap,
    CpdrInputs,
    GapResearch,
    ResearchQuestion,
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


# docs/CPDR-OWNER-LEASE.md header: submissions from the LEAD freeze, expected from the 0d render
# re-pin, builder and manifest from the serialised methodology re-pin line.
PINNED = {
    "manifest.json": "44862ca3166a29f7d8ff44e7c1073bbdfa2229201c46d83586a262f5de192066",
    "submissions.json": "4ffb322a4d640bc6208250cfd0697cef389b8d0843f6071340247e31b478b1af",
    "expected.json": "36572c50b663ab4a1f6eaa300d7ee2e668f511cb206dcacfa820105e60b65263",
    "builder/build.py": "591da654cfe1eb0e932bffa3b48b7dc362d9d1f3180821bd838e3bdd0f99aae5",
}


def test_oracle_files_are_the_pinned_revision() -> None:
    for name, digest in PINNED.items():
        assert hashlib.sha256((CASE / name).read_bytes()).hexdigest() == digest, name


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
    # lease-literal: :117 case-insensitive "recommend", "refinanc", "covenant", "recovery"
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
    # lease-literal: :46, as amended by ruling R4 (round 5): kind/severity before the first ": ";
    # the one "; affects " whose segment is a list of methodology ids splits the rest
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


# --- rulings round (docs/rulings/2026-10-28-stage1.md section CP-DR) -----------------------------


def test_issue_order_with_many_defects() -> None:
    # ruling R2: rule 1 per submitted gap; rule 2 per agenda gap; then per question in submission
    # order: 3, 4, 5 per searched source in listed order, 6 per citation in order, 7. The strings
    # are lease-literal (:111-:117) or pinned in expected.json#refusals for the same citation.
    web = SUBMISSIONS["refusal_inputs"]["citation_outside_pack"]["payload"]["gaps"][0]
    web_citation = web["questions"][0]["citations"][0]
    forged = SUBMISSIONS["refusal_inputs"]["quote_not_verbatim"]["payload"]["gaps"][0]
    forged_citation = forged["questions"][0]["citations"][0]
    defective = edited(
        TRANSACTIONS,
        limitation="Asked about 2025.",
        searched_sources=["web", "registry"],
        citations=[web_citation, forged_citation],
    )
    payload = {
        "gaps": [
            {"gap_id": "invented-gap", "questions": [edited(OWNER, limitation=None)]},
            {
                "gap_id": GAP_ID,
                "questions": [
                    TRANSACTIONS,
                    DISTRIBUTIONS,
                    defective,
                    POLICY,
                    edited(OWNER, question_id="owner-two", searched_sources=[]),
                ],
            },
        ]
    }
    quote_issue = EXPECTED["refusals"]["quote_not_verbatim"]["step_issues"][0]
    assert check(submission(payload)) == (
        "gap_id is not in the CP-0 agenda: invented-gap",
        "a gap takes 1 to 4 research questions: missing-ownership-transaction",
        "a not_found question states its limitation: owner-identity",
        "question_id appears twice: transactions",
        "an answered question carries no limitation: transactions",
        "searched source is not a ready prepared source: transactions web",
        "searched source is not a ready prepared source: transactions registry",
        "Unavailable or changed source: web",
        quote_issue,
        "text must not contain a figure: transactions",
        "searched_sources must name at least one prepared source: owner-two",
    )


def test_tdr3_layout() -> None:
    # ruling R3: labels field.replace("_", " "), row header "Total", row label "All gaps", row kind
    sub = submission(SUBMISSIONS["cpdr"]["partial"])
    result = compose(CpdrInputs(agenda=agenda(empty=False), submission=sub, as_of=AS_OF))
    (tdr3,) = (t for t in result.tables if t.table_id == "TDR.3")
    assert [(c.field, c.label) for c in tdr3.columns] == [
        (field, field.replace("_", " ")) for field in [*TOTAL_KEYS, "answered_share"]
    ]
    assert tdr3.row_header == "Total"
    (row,) = tdr3.rows
    assert (row.row_id, row.label, row.row_kind) == ("total", "All gaps", "row")


# --- rulings round 5 (docs/rulings/2026-10-28-stage1.md "# Round 5" section CP-DR) --------------
AMBIGUOUS = "Not stated: the CP-0 gap text names its consumers ambiguously"  # ruling-literal: R4


def test_r4_a_later_affects_that_names_no_module_is_not_a_split() -> None:
    # ruling-literal: R4 a candidate split is a "; affects " whose segment up to the next "; "
    # is a ", "-list of methodology ids; exactly one candidate is used
    (gap,) = parse_agenda((_t5("scope/material: Desc; affects CP-DR; Ask; affects nothing"),))
    assert (gap.kind_severity, gap.description) == ("scope/material", "Desc")
    assert gap.named_consumers == ("CP-DR",)
    assert gap.remediation == "Ask; affects nothing"


def test_r4_an_earlier_affects_that_names_no_module_is_not_a_split() -> None:
    # ruling-literal: R4 (the "valuation" segment is not a methodology id)
    (gap,) = parse_agenda((_t5("scope/material: Note; affects valuation; affects CP-DR; Ask"),))
    assert gap.description == "Note; affects valuation"
    assert gap.named_consumers == ("CP-DR",)
    assert gap.remediation == "Ask"


AMBIGUOUS_TEXT = (
    "scope/material: Content that affects CP-DR; affects CP-DR; Supply; affects CP-DR; documents"
)


def test_r4_two_candidate_splits_parse_as_not_stated() -> None:
    # ruling-literal: R4 more than one candidate: description, consumers and remediation are
    # not stated; kind and severity still come before the first ": "
    (gap,) = parse_agenda((_t5(AMBIGUOUS_TEXT),))
    assert gap.kind_severity == "scope/material"
    assert (gap.description, gap.named_consumers, gap.remediation) == (None, None, None)
    assert gap.text == AMBIGUOUS_TEXT


def test_r4_two_candidate_splits_settle_with_missing_cells_and_the_own_line() -> None:
    # ruling-literal: R4 nothing is refused; the cells are missing with the pinned reason and the
    # own line names the gap
    gaps = parse_agenda((_t5(AMBIGUOUS_TEXT),))
    sub = submission(SUBMISSIONS["cpdr"]["partial"])
    assert validate_research(submission=sub, upstream=gaps, pack=sources()) == ()
    result = compose(CpdrInputs(agenda=gaps, submission=sub, as_of=AS_OF))
    facts = {f.fact_id: f for f in result.facts}
    for field in ("description", "named_consumers"):
        fact = facts[f"TDR.1.{GAP_ID}.{field}"]
        assert (fact.status, fact.text, fact.limitation) == ("missing", None, AMBIGUOUS)
        assert fact.value_class is None
        assert fact_spelling(fact, GAP_REF)[1:] == ("gap", f"∅ {GAP_REF}")
    assert facts[f"TDR.1.{GAP_ID}.kind_severity"].text == "scope/material"
    own_line = (
        f"CP-0 gap {GAP_ID} cannot be split into description, consumers and remediation; "
        "its full text is the gap."
    )
    partial = EXPECTED["cases"]["partial"]["own_limitations"]
    assert result.limitations == (partial[0], own_line, *partial[1:])
    validate_tables(result.tables, result.facts)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("unknown/material: Desc; affects CP-DR; Ask", id="kind-outside-vocabulary"),
        pytest.param("scope/severe: Desc; affects CP-DR; Ask", id="severity-outside-vocabulary"),
        pytest.param("scope/material: Desc; affects nobody; Ask", id="no-candidate-split"),
    ],
)
def test_r4_text_outside_the_readiness_form_fails_closed(text: str) -> None:
    # R4 rules one and several candidates; none, or a head outside readiness.GapKind /
    # GapSeverity, is not CP-0's T5 form and stays an invariant raise (listed for LEAD)
    with pytest.raises(ValueError, match="not in the readiness form"):
        parse_agenda((_t5(text),))


def test_r5_row_labels() -> None:
    # ruling-literal: R5 the row id with "-" and "_" as spaces and the first letter upper-cased
    sub = submission(SUBMISSIONS["cpdr"]["partial"])
    result = compose(CpdrInputs(agenda=agenda(empty=False), submission=sub, as_of=AS_OF))
    labels = {t.table_id: [(r.row_id, r.label) for r in t.rows] for t in result.tables}
    assert labels["TDR.1"] == [(GAP_ID, "Missing ownership transaction")]
    assert labels["TDR.2"] == [
        ("transactions", "Transactions"),
        ("distributions", "Distributions"),
        ("owner-identity", "Owner identity"),
    ]
    assert labels["TDR.3"] == [("total", "All gaps")]


def test_a_gap_naming_no_consumer_settles() -> None:
    # ruling-literal: round 6e CP-DR, a gap that names no consumer settles: named_consumers is
    # missing with the pinned reason, description is parsed as usual, and no own line is added
    gaps = parse_agenda((_t5("scope/material: Ownership is absent; affects ; Supply it"),))
    sub = submission(SUBMISSIONS["cpdr"]["partial"])
    result = compose(CpdrInputs(agenda=gaps, submission=sub, as_of=AS_OF))
    validate_tables(result.tables, result.facts)
    facts = {f.fact_id: f for f in result.facts}
    consumers = facts[f"TDR.1.{GAP_ID}.named_consumers"]
    reason = "Not stated: the CP-0 gap names no consumer"
    assert (consumers.status, consumers.text, consumers.limitation) == ("missing", None, reason)
    assert consumers.value_class is None
    assert fact_spelling(consumers, GAP_REF)[1:] == ("gap", f"∅ {GAP_REF}")
    description = facts[f"TDR.1.{GAP_ID}.description"]
    assert (description.status, description.text) == ("known", "Ownership is absent")
    assert result.limitations == tuple(EXPECTED["cases"]["partial"]["own_limitations"])


def test_r4_description_containing_a_colon() -> None:
    # ruling-literal: R4 kind and severity come before the FIRST ": " (reviewer L2, round 6e)
    (gap,) = parse_agenda((_t5("scope/material: Note: register absent; affects CP-DR; Ask"),))
    assert (gap.kind_severity, gap.description) == ("scope/material", "Note: register absent")
    assert (gap.named_consumers, gap.remediation) == (("CP-DR",), "Ask")


def test_r5_row_label_with_underscores_and_capitals() -> None:
    # ruling-literal: R5 "_" is a space too, and only the first letter changes case
    sub = one_gap(edited(TRANSACTIONS, question_id="share_register-UK"), DISTRIBUTIONS, OWNER)
    result = compose(CpdrInputs(agenda=agenda(empty=False), submission=sub, as_of=AS_OF))
    (tdr2,) = (t for t in result.tables if t.table_id == "TDR.2")
    assert tdr2.rows[0].label == "Share register UK"


# --- ruling C4 (round 6b): TDR.1 and TDR.2 row order -------------------------------------------


def test_c4_rows_follow_the_agenda_order() -> None:
    # ruling-literal: C4 TDR.1 rows follow agenda order (CP-0's T5 order); TDR.2 rows are grouped
    # by gap in agenda order and keep submission order within each gap
    def t5(gap_id: str) -> Fact:
        text = "scope/material: Something is absent; affects CP-DR; Supply it"
        return Fact(
            fact_id=f"T5.{gap_id}.gap",
            label="gap",
            table_id="T5",
            row_id=gap_id,
            field="gap",
            text=text,
        )

    gaps = parse_agenda((t5("gap-a"), t5("gap-b")))
    sub = submission(
        {
            "gaps": [
                {"gap_id": "gap-b", "questions": [OWNER]},
                {"gap_id": "gap-a", "questions": [DISTRIBUTIONS, TRANSACTIONS]},
            ]
        }
    )
    assert validate_research(submission=sub, upstream=gaps, pack=sources()) == ()
    result = compose(CpdrInputs(agenda=gaps, submission=sub, as_of=AS_OF))
    rows = {t.table_id: [r.row_id for r in t.rows] for t in result.tables}
    assert rows["TDR.1"] == ["gap-a", "gap-b"]
    assert rows["TDR.2"] == ["distributions", "transactions", "owner-identity"]
    validate_tables(result.tables, result.facts)


def test_c4_every_per_gap_sequence_follows_the_agenda() -> None:
    # ruling-literal: round 6e C4 extended: TDR.1, TDR.2, the answered-question claims, the
    # "Unresolved:" lines and the consumption facts follow agenda order, submission order inside
    # a gap ("Unresolved: <question> <limitation>" is lease Method 8, :53)
    def t5(gap_id: str) -> Fact:
        text = "scope/material: Something is absent; affects CP-DR; Supply it"
        return Fact(
            fact_id=f"T5.{gap_id}.gap",
            label="gap",
            table_id="T5",
            row_id=gap_id,
            field="gap",
            text=text,
        )

    gaps = parse_agenda((t5("gap-a"), t5("gap-b")))
    sub = submission(
        {
            "gaps": [
                {"gap_id": "gap-b", "questions": [TRANSACTIONS, POLICY]},
                {"gap_id": "gap-a", "questions": [DISTRIBUTIONS, OWNER]},
            ]
        }
    )
    assert validate_research(submission=sub, upstream=gaps, pack=sources()) == ()
    result = compose(CpdrInputs(agenda=gaps, submission=sub, as_of=AS_OF))
    rows = {t.table_id: [r.row_id for r in t.rows] for t in result.tables}
    assert rows["TDR.1"] == ["gap-a", "gap-b"]
    assert rows["TDR.2"] == [
        "distributions",
        "owner-identity",
        "transactions",
        "distribution-policy",
    ]
    assert [c.claim_id for c in result.claims] == [
        "CPDR-SUM-01",
        "CPDR-ANS-distributions",
        "CPDR-ANS-transactions",
    ]
    assert result.limitations[1:] == (
        f"Unresolved: {OWNER['text']} {OWNER['limitation']}",
        f"Unresolved: {POLICY['text']} {POLICY['limitation']}",
    )
    per_gap = ("questions", "answered", "unresolved", "answered_share", "status")
    assert result.consumption_facts == (
        *(f"TDR.1.{g}.{f}" for g in ("gap-a", "gap-b") for f in per_gap),
        *(f"TDR.3.total.{f}" for f in (*TOTAL_KEYS, "answered_share")),
        "TDR.2.owner-identity.answer",
        "TDR.2.distribution-policy.answer",
    )
    validate_tables(result.tables, result.facts)


# Round 11 "Blank text is one defect class" (shared library `tests/defect_classes.py`): every
# analyst text field refuses whitespace-only text. CP-DR pins no empty-text frame, so the fallback
# `<path>: empty text` applies. `text` and `answer` are `Text` (`min_length=1`), so the schema's
# refusal of `""` stands; a not_found `limitation` of `""` keeps its completeness issue. The
# fields run on the frozen `partial` submission: questions[0] is answered (text, answer) and
# questions[2] is not_found (limitation; an answered question carries none by design).
BLANK_FIELDS: tuple[tuple[str, int, str], ...] = (
    ("gaps[0].questions[0].text", 0, "text"),
    ("gaps[0].questions[0].answer", 0, "answer"),
    ("gaps[0].questions[2].limitation", 2, "limitation"),
)
# Ids and closed vocabularies; citations go to the shared `citation_issues` check. CP-DR reads no
# figure, name or label from a quote, so the quote-reader cases (B1, B3) do not apply.
NOT_TEXT_FIELDS = frozenset({"question_id", "outcome", "category", "citations", "searched_sources"})


def _blank_adapter(index: int, key: str) -> Adapter:
    """Places the value in one analyst text field of the frozen partial submission. Page and quote
    are unused: CP-DR reads no value from an analyst quote."""

    def adapter(page: str, quote: str, value: str) -> tuple[str, ...]:
        raw = json.loads(json.dumps(SUBMISSIONS["cpdr"]["partial"]))
        raw["gaps"][0]["questions"][index][key] = value
        return check(submission(raw))

    return adapter


def test_blank_fields_cover_every_analyst_text_field() -> None:
    """Every submission field is a blank-class text field or a named non-text field."""
    assert set(ResearchSubmission.model_fields) == {"gaps"}
    assert set(GapResearch.model_fields) == {"gap_id", "questions"}
    texts = {key for _, _, key in BLANK_FIELDS}
    assert set(ResearchQuestion.model_fields) == texts | NOT_TEXT_FIELDS


@pytest.mark.parametrize("field", BLANK_FIELDS, ids=lambda f: f[0])
@pytest.mark.parametrize("blank", BLANK_CASES, ids=lambda c: c.case_id)
def test_blank_text_is_refused(blank: BlankCase, field: tuple[str, int, str]) -> None:
    path, index, key = field
    failure = blank_failure(blank, _blank_adapter(index, key), EMPTY_TEXT.format(path=path))
    assert failure is None, failure


@pytest.mark.parametrize("field", BLANK_FIELDS, ids=lambda f: f[0])
def test_blank_text_twin_is_accepted(field: tuple[str, int, str]) -> None:
    """The twin: the same field holding text is accepted outright."""
    _, index, key = field
    assert _blank_adapter(index, key)("", "", "Which prepared source names the owners?") == ()


def test_blank_text_path_names_the_gap_and_question() -> None:
    """The path carries the submitted gap and question positions (0-based), not index 0 only."""
    owner = edited(OWNER, limitation="  ")
    sub = submission(
        {
            "gaps": [
                {"gap_id": GAP_ID, "questions": [TRANSACTIONS, DISTRIBUTIONS, owner]},
                {"gap_id": "gap-b", "questions": [edited(POLICY, text="\t")]},
            ]
        }
    )
    second = Fact(
        fact_id="T5.gap-b.gap",
        label="gap",
        table_id="T5",
        row_id="gap-b",
        field="gap",
        text="scope/material: Something is absent; affects CP-DR; Supply it",
    )
    gaps = (*agenda(empty=False), *parse_agenda((second,)))
    issues = validate_research(submission=sub, upstream=gaps, pack=sources())
    assert issues == (
        "gaps[0].questions[2].limitation: empty text",
        "gaps[1].questions[0].text: empty text",
    )
