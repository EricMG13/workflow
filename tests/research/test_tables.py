"""O7b-1c S2a, Behaviour 10: TDR.1-3 composition and the dossier input.

Answer key: ``cases/cpdr-research-owner/expected.json#cases/{positive,v2}/{tables,facts,counts,
claim_state_list,dossier}`` and ``#cases/v2/differs_from_positive``. Read at test time, never edited.
"""

import copy
import hashlib
from datetime import date
from typing import Any

import pytest
from cpdr_o7b1b_support import brief, evidence
from cpdr_peers_support import peers_case

from deploy_vii import prose
from deploy_vii.contracts import validate_tables
from deploy_workflow.research import contracts as c
from deploy_workflow.research import dossier as d
from deploy_workflow.research import review
from deploy_workflow.research import tables as t
from deploy_workflow.research.intake import RefusedItem

BRIEF_MARKER = "{{BRIEF_SHA256}}"
FACT_FIELDS = (
    "fact_id",
    "table_id",
    "row_id",
    "field",
    "label",
    "text",
    "amount",
    "status",
    "unit",
    "period",
)
SUBMISSION = {"positive": "research_v1", "v2": "research_v2"}


def rejected(expected: dict[str, Any]) -> tuple[RefusedItem, ...]:
    return tuple(
        RefusedItem(
            locator=e["locator"],
            family=e["family"],
            published=date.fromisoformat(e["published"]) if e["published"] else None,
            reason=e["reason"],
        )
        for e in expected["intake"]["rejected_json"]["entries"]
    )


class Run:
    """Everything one case feeds to ``compose`` and ``dossier_input``."""

    def __init__(
        self, expected: dict[str, Any], submissions: dict[str, Any], case: str, body: Any = None
    ) -> None:
        self.key = expected["cases"][case]
        self.expected = expected
        self.brief = brief(expected, case)
        self.submission = review.ResearchSubmission.parse(body or submissions[SUBMISSION[case]])
        self.evidence = evidence(expected)
        self.counts = review.answer_counts(self.submission)
        self.states = review.claim_states(self.submission, self.brief)
        self.period = self.brief.as_of.isoformat()

    def compose(self) -> t.Composed:
        return t.compose(
            self.brief, self.submission, self.evidence, self.counts, self.states, self.period
        )

    def dossier(self, head_sha256: str = "0" * 64) -> d.DossierInput:
        return t.dossier_input(
            self.compose(),
            self.brief,
            self.states,
            self.evidence,
            rejected(self.expected),
            head_sha256,
            self.brief.brief_sha256,
        )


def shown_cells(tables: Any) -> dict[str, Any]:
    """Per table: its rows as ``[row_id, {column: (fact, shown, state)}]``."""
    return {
        table_id: [
            [
                row_id,
                {col: (cell["fact"], cell["shown"], cell["state"]) for col, cell in cells.items()},
            ]
            for row_id, cells in table["rows"]
        ]
        for table_id, table in tables.items()
    }


CASES = ["positive", "v2"]


@pytest.mark.parametrize("case", CASES)
def test_validate_tables_passes(
    case: str, expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    composed = Run(expected, submissions, case).compose()
    validate_tables(composed.tables, composed.facts)
    assert [tbl.table_id for tbl in composed.tables] == ["TDR.1", "TDR.2", "TDR.3"]


@pytest.mark.parametrize("case", CASES)
def test_inputs_equal_the_key_counts_and_states(
    case: str, expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    given = Run(expected, submissions, case)
    key = expected["cases"][case]
    assert {k: str(v) for k, v in vars(given.counts).items()} == key["counts"]
    assert list(given.states) == key["claim_state_list"]


@pytest.mark.parametrize("case", CASES)
def test_facts_equal_the_key_on_the_contract_fields(
    case: str, expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    facts = Run(expected, submissions, case).compose().facts
    key_facts = expected["cases"][case]["facts"]
    # The key lists a TDR.1 row's focus_module fact first (builder order); fact order carries no
    # meaning, so the facts are compared by id.
    assert sorted(f.fact_id for f in facts) == sorted(f["fact_id"] for f in key_facts)
    by_id = {f.fact_id: f for f in facts}
    for want in key_facts:
        fact = by_id[want["fact_id"]]
        got = {n: None if (v := getattr(fact, n)) is None else str(v) for n in FACT_FIELDS}
        assert got == {n: want.get(n) for n in FACT_FIELDS}, fact.fact_id
        assert fact.limitation == want.get("limitation"), fact.fact_id
        assert fact.value_class == want.get("value_class"), fact.fact_id
        assert fact.calculation_id == want.get("calculation_id"), fact.fact_id
        assert fact.formula == want.get("formula"), fact.fact_id
        assert [x.model_dump() for x in fact.citations] == want.get("citations", []), fact.fact_id


@pytest.mark.parametrize("case", CASES)
def test_shown_cells_equal_the_key(
    case: str, expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    tables = Run(expected, submissions, case).dossier().tables
    key_tables = expected["cases"][case]["tables"]
    assert list(tables) == list(key_tables)
    for table_id, want in key_tables.items():
        for name in ("title", "row_header", "columns"):
            assert tables[table_id][name] == want[name], (table_id, name)
    assert shown_cells(tables) == shown_cells(key_tables)


def test_only_the_named_rows_differ_between_v1_and_v2(
    expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    first = {
        k: dict(v)
        for k, v in shown_cells(Run(expected, submissions, "positive").dossier().tables).items()
    }
    second = {
        k: dict(v)
        for k, v in shown_cells(Run(expected, submissions, "v2").dossier().tables).items()
    }
    named = expected["cases"]["v2"]["differs_from_positive"]["tdr_rows_differing"]
    by_id = {
        (table_id, row_id)
        for table_id in first
        for row_id in first[table_id].keys() | second[table_id].keys()
        if first[table_id].get(row_id) != second[table_id].get(row_id)
    }
    assert by_id == {tuple(pair) for pair in named}


def test_not_found_is_missing_with_the_limitation_never_zero(
    expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    given = Run(expected, submissions, "positive")
    composed = given.compose()
    want = next(a for a in given.submission.answers if a.question_id == "valuation-context")
    by_id = {f.fact_id: f for f in composed.facts}
    for field in ("answer", "contrary", "uncertainty"):
        fact = by_id[f"TDR.3.valuation-context.{field}"]
        assert (fact.status, fact.amount, fact.text) == ("missing", None, None)
        assert fact.limitation == want.limitation
    assert f"valuation-context: {want.limitation}" in composed.limitations
    zero = by_id["TDR.3.valuation-context.answered"]
    assert (zero.status, str(zero.amount), zero.unit) == ("known", "0", "questions")
    cells = given.dossier().tables["TDR.3"]["rows"]
    row = dict(cells)["valuation-context"]
    assert [row[f]["shown"] for f in ("answer", "contrary", "uncertainty")] == [t.GAP_SHOWN] * 3


@pytest.mark.parametrize("case", CASES)
def test_claims_quote_the_total_row_and_the_limitations_carry_local(
    case: str, expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    composed = Run(expected, submissions, case).compose()
    bound = prose.bind(composed.facts)
    assert composed.claims
    for claim in composed.claims:
        assert prose.issues(claim.text, bound) == ()
        assert "TDR.3.total." in claim.text
    assert composed.limitations[0] == t.LOCAL_LIMITATION


@pytest.mark.parametrize("case", CASES)
def test_dossier_input_renders_the_key_bytes(
    case: str, expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    given = Run(expected, submissions, case)
    template = expected["cases"][case]["dossier"]
    assert (
        hashlib.sha256(template["template_text"].encode()).hexdigest()
        == template["template_sha256"]
    )
    text = template["template_text"].replace(BRIEF_MARKER, given.brief.brief_sha256)
    head = hashlib.sha256(text.encode()).hexdigest()
    assert d.dossier_markdown(given.dossier(head)) == text
    assert given.dossier(head).head_sha256 == head
    assert given.dossier(head).head_brief_sha256 == given.brief.brief_sha256


def test_two_not_found_questions_are_counted_and_named(
    expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    body = copy.deepcopy(submissions["research_v1"])
    first = body["answers"][0]
    first.update(
        answer_state="not_found",
        claims=[],
        contrary=[],
        uncertainty=None,
        searched=["ev-1"],
        limitation="Nothing located.",
    )
    given = Run(expected, submissions, "positive", body)
    total = {f.fact_id: f for f in given.compose().facts}
    assert total["TDR.3.total.uncertainty"].text == (
        "2 questions have no located answer: ctx-1, valuation-context"
    )
    assert str(total["TDR.3.total.not_found"].amount) == "2"
    assert given.states[0] == "missing"


def test_a_mixed_citation_keeps_each_items_date_and_family(
    expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    body = copy.deepcopy(submissions["research_v1"])
    claim = body["answers"][0]["claims"][0]
    cite = {"source_id": "financial", "source_sha256": "a" * 64, "locator": "page:1", "quote": "q"}
    claim["citations"].append(cite)
    given = Run(expected, submissions, "positive", body)
    composed = given.compose()
    validate_tables(composed.tables, composed.facts)
    key = expected["cases"]["positive"]
    na = dict(key["tables"]["TDR.1"]["rows"])["competition"]["focus_module"]["shown"]
    row = dict(given.dossier().tables["TDR.2"]["rows"])[claim["claim_id"]]
    want = dict(key["tables"]["TDR.2"]["rows"])[claim["claim_id"]]
    assert row["locator"]["shown"] == want["locator"]["shown"] + "; page:1"
    assert row["evidence_id"]["shown"] == want["evidence_id"]["shown"] + "; financial"
    ours = {f.fact_id: f for f in composed.facts}
    for f in ("published", "family"):
        assert row[f]["shown"] == f"{want[f]['shown']}; {na}"
        assert ours[row[f]["fact"]].status == "known"
    qid = claim["claim_id"].split(".")[0]
    touched = (f"TDR.2.{claim['claim_id']}.", f"TDR.3.{qid}.answer")
    assert set(ours) == {f["fact_id"] for f in key["facts"]}
    for want_fact in key["facts"]:
        if not want_fact["fact_id"].startswith(touched):
            got = {
                n: None if (v := getattr(ours[want_fact["fact_id"]], n)) is None else str(v)
                for n in FACT_FIELDS
            }
            assert got == {n: want_fact.get(n) for n in FACT_FIELDS}, want_fact["fact_id"]
    mine = shown_cells(given.dossier().tables)["TDR.2"]
    theirs = shown_cells(key["tables"])["TDR.2"]
    assert [r for r in mine if r[0] != claim["claim_id"]] == [
        r for r in theirs if r[0] != claim["claim_id"]
    ]


def test_a_pack_only_claim_has_not_applicable_date_and_family(
    expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    body = copy.deepcopy(submissions["research_v1"])
    claim = body["answers"][0]["claims"][0]
    cite = {"source_id": "financial", "source_sha256": "a" * 64, "locator": "page:1", "quote": "q"}
    claim["citations"] = [cite]
    given = Run(expected, submissions, "positive", body)
    composed = given.compose()
    validate_tables(composed.tables, composed.facts)
    key = expected["cases"]["positive"]
    na = dict(key["tables"]["TDR.1"]["rows"])["competition"]["focus_module"]["shown"]
    row = dict(given.dossier().tables["TDR.2"]["rows"])[claim["claim_id"]]
    ours = {f.fact_id: f for f in composed.facts}
    for f in ("published", "family"):
        assert (row[f]["shown"], row[f]["state"]) == (na, "not_applicable")
        assert ours[row[f]["fact"]].status == "not_applicable"
    assert row["locator"]["shown"] == "page:1"


def test_an_uppercase_evidence_id_is_refused_as_not_accepted(
    expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    body = copy.deepcopy(submissions["research_v1"])
    body["answers"][0]["claims"][0]["citations"][0]["source_id"] = "EV-9"
    with pytest.raises(t.TablesInvalid, match="not accepted evidence"):
        Run(expected, submissions, "positive", body).compose()


def test_a_claim_with_no_uncertainty_is_refused(
    expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    body = copy.deepcopy(submissions["research_v1"])
    body["answers"][0]["uncertainty"] = None
    given = Run(expected, submissions, "positive", body)
    with pytest.raises(t.TablesInvalid, match="no uncertainty"):
        given.compose()


@pytest.mark.parametrize(
    "damage",
    ["blocked", "short_states", "dropped_answer", "wrong_counts", "unknown_citation", "no_limit"],
)
def test_refuses_what_it_cannot_compose(
    damage: str, expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    body = copy.deepcopy(submissions["research_v1"])
    if damage == "dropped_answer":
        body["answers"].pop(0)
    if damage == "unknown_citation":
        body["answers"][0]["claims"][0]["citations"][0]["source_id"] = "ev-9"
    if damage == "no_limit":
        body["answers"][4]["limitation"] = None
    given = Run(expected, submissions, "positive", body)
    states = list(given.states)
    counts = given.counts
    if damage == "blocked":
        states[0] = "blocked"
    if damage == "short_states":
        states = states[:-1]
    if damage == "wrong_counts":
        counts = review.Counts(**{**vars(counts), "answered": counts.answered + 1})
    with pytest.raises(t.TablesInvalid):
        t.compose(given.brief, given.submission, given.evidence, counts, states, given.period)


def test_a_question_named_total_is_refused(
    expected: dict[str, Any], submissions: dict[str, Any]
) -> None:
    given = Run(expected, submissions, "positive")
    questions = tuple(
        c.ResearchQuestion.model_validate({**q.model_dump(), "question_id": "total"})
        if q.question_id == "regulation"
        else q
        for q in given.brief.questions
    )
    renamed = c.ResearchBrief.build(
        **{**given.brief.model_dump(exclude={"brief_sha256"}), "questions": questions}
    )
    body = copy.deepcopy(given.submission.model_dump(mode="json"))
    body["answers"][-1]["question_id"] = "total"
    submission = review.ResearchSubmission.parse(body)
    with pytest.raises(t.TablesInvalid):
        t.compose(
            renamed,
            submission,
            given.evidence,
            review.answer_counts(submission),
            review.claim_states(submission, renamed),
            given.period,
        )


def test_validate_tables_passes_over_tdr1_to_tdr6() -> None:
    """O7d D1a: the pack's three tables join TDR.1-3 with uniform columns, one fact per cell."""
    case = peers_case()
    submission = case.submission()
    composed = t.compose(
        case.brief,
        submission,
        case.evidence,
        review.answer_counts(submission),
        review.claim_states(submission, case.brief),
        case.brief.as_of.isoformat(),
    )
    validate_tables(composed.tables, composed.facts)
    key = case.key["tables"]
    assert [tbl.table_id for tbl in composed.tables] == ["TDR.1", "TDR.2", "TDR.3", *list(key)[:3]]
    assert {tbl.table_id: len(tbl.rows) for tbl in composed.tables if tbl.table_id in key} == {
        name: len(key[name]["rows"]) for name in list(key)[:3]
    }
