"""O7d D1a: the CP-DR peer pack, TDR.4-6 (contracts, checks, composition).

Answer key: ``cases/cpdr-peers-owner/expected.json#tables/TDR.4..6``, ``#facts``,
``#refusals/peers``, ``#no_ownership_leak`` and ``submissions.json#research_peers`` /
``#refusal_inputs``. Read at test time, never edited. The key declares the shapes; nothing here
restates a value the key holds.
"""

import copy
from decimal import Decimal
from typing import Any

import pytest
from cpdr_peers_support import KEY_FIELDS, Case, peers_case
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from deploy_vii.contracts import Fact, validate_tables
from deploy_workflow.owners import cp1c
from deploy_workflow.research import contracts as c
from deploy_workflow.research import peers as p
from deploy_workflow.research import review
from deploy_workflow.research import tables as t


@pytest.fixture(scope="module")
def case() -> Case:
    return peers_case()


@pytest.fixture(scope="module")
def key(case: Case) -> dict[str, Any]:
    return case.key


def cell_value(fact: Fact) -> str | None:
    """The key's table-cell form: the text, the amount as stated, or ``missing: <limitation>``."""
    if fact.status == "missing":
        return f"missing: {fact.limitation}"
    return fact.text if fact.amount is None else str(fact.amount)


def test_the_key_submission_has_no_peer_issue(case: Case) -> None:
    assert case.issues() == ()


def assert_tables_are_the_key(composed: t.Composed, key: dict[str, Any]) -> None:
    by_id = {f.fact_id: f for f in composed.facts}
    for table in composed.tables:
        want = key["tables"][table.table_id]
        assert (table.title, table.row_header) == (want["title"], want["row_header"])
        assert [col.field for col in table.columns] == want["columns"]
        got_rows = [
            [
                row.row_id,
                {
                    col.field: cell_value(by_id[f])
                    for col, f in zip(table.columns, row.fact_ids, strict=True)
                },
            ]
            for row in table.rows
        ]
        assert got_rows == want["rows"], table.table_id


def assert_fact_is_the_key(fact: Fact, want: dict[str, Any]) -> None:
    assert {n: fact.model_dump(mode="json")[n] for n in KEY_FIELDS} == {
        n: want.get(n) for n in KEY_FIELDS
    }, fact.fact_id
    canonical = None if fact.amount is None else format(fact.amount.normalize(), "f")
    assert canonical == want.get("amount"), fact.fact_id
    assert fact.scale == Decimal(want.get("scale", "1")), fact.fact_id
    assert fact.decimals == want.get("decimals"), fact.fact_id
    assert [x.model_dump() for x in fact.citations] == want.get("citations", []), fact.fact_id


def test_tdr6_figures_are_located(case: Case, key: dict[str, Any]) -> None:
    """The key submission composes ``#tables/TDR.4..6`` and ``#facts`` exactly."""
    composed = case.composed()
    validate_tables(composed.tables, composed.facts)
    assert_tables_are_the_key(composed, key)
    wanted = [w for k, ws in key["facts"].items() if k != "_source" for w in ws]
    assert sorted(f.fact_id for f in composed.facts) == sorted(w["fact_id"] for w in wanted)
    by_id = {f.fact_id: f for f in composed.facts}
    for want in wanted:
        assert_fact_is_the_key(by_id[want["fact_id"]], want)


def test_a_quote_the_rule_cannot_read_is_the_missing_cell(case: Case, key: dict[str, Any]) -> None:
    ref = key["refusals"]["peers"]["inputs"]["unlocated_figure"].split(" ")[0]
    fact = {f.fact_id: f for f in case.composed().facts}[ref]
    assert (fact.status, f"missing: {fact.limitation}") == (
        "missing",
        key["refusals"]["peers"]["unlocated_figure"],
    )
    assert case.issues() == ()  # a gap is composed, not a review issue


def test_a_period_after_the_cutoff_is_the_missing_cell(case: Case, key: dict[str, Any]) -> None:
    ref = key["refusals"]["peers"]["inputs"]["after_cutoff"].split(" ")[0]
    fact = {f.fact_id: f for f in case.composed().facts}[ref]
    assert (fact.status, f"missing: {fact.limitation}") == (
        "missing",
        key["refusals"]["peers"]["after_cutoff"],
    )


@pytest.mark.parametrize("name", ["operand_unknown", "not_in_tdr4"])
def test_a_refusal_input_is_the_keyed_issue(case: Case, key: dict[str, Any], name: str) -> None:
    got = case.issues(case.replaced("figures", name))
    assert [str(issue) for issue in got] == [key["refusals"]["peers"][name]]


def test_an_amount_typed_by_the_model_is_a_shape_refusal(case: Case) -> None:
    with pytest.raises(ValidationError, match="amount"):
        case.submission(case.replaced("figures", "typed_amount"))


def test_no_cp1c_ownership_leak(case: Case, key: dict[str, Any]) -> None:
    """No TDR.4-6 column is a forbidden field; a submission carrying one is a shape refusal."""
    leak = key["no_ownership_leak"]
    columns = {col.field for table in case.composed().tables for col in table.columns}
    assert columns.isdisjoint(leak["forbidden_fields"])
    assert {
        tbl.table_id: [col.field for col in tbl.columns] for tbl in case.composed().tables
    } == leak["columns"]
    with pytest.raises(ValidationError, match="included"):
        case.submission(case.replaced("observations", "leak_field", 1))
    for field in leak["forbidden_fields"]:
        body = copy.deepcopy(case.body)
        body["peers"]["candidates"][0][field] = "x"
        with pytest.raises(ValidationError, match=field):
            case.submission(body)


def test_the_pack_is_refused_when_not_requested(case: Case, key: dict[str, Any]) -> None:
    want = key["refusals"]["peers"]["pack_not_requested"]
    assert [i.text for i in case.issues(brief=case.plain)] == [want]
    with pytest.raises(t.TablesInvalid, match=want):
        t.compose(case.plain, case.submission(), case.evidence, *_inputs(case, case.plain))


def test_a_requested_pack_must_come(case: Case, key: dict[str, Any]) -> None:
    want = key["refusals"]["peers"]["pack_missing"]
    body = {k: v for k, v in case.body.items() if k != "peers"}
    assert [i.text for i in case.issues(body)] == [want]
    with pytest.raises(t.TablesInvalid, match=want):
        t.compose(
            case.brief, case.submission(body), case.evidence, *_inputs(case, case.brief, body)
        )


def test_no_pack_and_none_requested_has_no_issue(case: Case) -> None:
    body = {k: v for k, v in case.body.items() if k != "peers"}
    assert case.issues(body, case.plain) == ()


def _inputs(
    case: Case, brief: c.ResearchBrief, body: dict[str, Any] | None = None
) -> tuple[Any, ...]:
    sub = case.submission(body)
    return review.answer_counts(sub), review.claim_states(sub, brief), brief.as_of.isoformat()


def test_compose_appends_tdr4_to_tdr6_when_requested(case: Case) -> None:
    sub = case.submission()
    composed = t.compose(case.brief, sub, case.evidence, *_inputs(case, case.brief))
    validate_tables(composed.tables, composed.facts)
    assert [tbl.table_id for tbl in composed.tables] == [f"TDR.{n}" for n in range(1, 7)]


def test_compose_without_a_pack_keeps_tdr1_to_tdr3(case: Case) -> None:
    body = {k: v for k, v in case.body.items() if k != "peers"}
    composed = t.compose(
        case.plain, case.submission(body), case.evidence, *_inputs(case, case.plain, body)
    )
    validate_tables(composed.tables, composed.facts)
    assert [tbl.table_id for tbl in composed.tables] == ["TDR.1", "TDR.2", "TDR.3"]


def test_research_issues_carry_the_peer_issues(case: Case, key: dict[str, Any]) -> None:
    got = review.research_issues(
        submission=case.submission(case.replaced("figures", "not_in_tdr4")),
        brief=case.brief,
        evidence=case.evidence,
        sources=case.sources,
    )
    assert [str(i) for i in got] == [key["refusals"]["peers"]["not_in_tdr4"]]


def test_a_dotted_or_repeated_peer_id_is_an_issue(case: Case) -> None:
    body = copy.deepcopy(case.body)
    body["peers"]["candidates"][1]["peer_id"] = "p01"
    body["peers"]["candidates"][2]["peer_id"] = "p.3"
    texts = [i.text for i in case.issues(body)]
    assert "peer_id appears twice in TDR.4" in texts
    assert any(text.startswith("peer_id has no dot") for text in texts)


def test_a_non_date_period_end_is_an_issue_and_cannot_compose(case: Case) -> None:
    body = copy.deepcopy(case.body)
    body["peers"]["figures"][0]["period_end"] = "2025-02-30"
    assert [i.text for i in case.issues(body)] == [p.NOT_A_DATE]
    with pytest.raises(t.TablesInvalid, match="calendar date"):
        case.composed(body)


def test_a_citation_that_is_not_accepted_evidence_is_an_issue(case: Case) -> None:
    body = copy.deepcopy(case.body)
    body["peers"]["figures"][0]["citation"]["source_id"] = "financial"
    assert [i.text for i in case.issues(body)] == [p.NOT_EVIDENCE]


def test_a_quote_not_in_its_span_is_an_issue(case: Case) -> None:
    body = copy.deepcopy(case.body)
    body["peers"]["figures"][0]["citation"]["quote"] = "999.0"
    got = case.issues(body)
    assert len(got) == 1 and got[0].text.startswith("Quote/locator mismatch")


def test_analyst_text_holds_no_figure(case: Case) -> None:
    body = copy.deepcopy(case.body)
    body["peers"]["observations"][0]["observation"] = "Ends in month 9."
    assert [i.text for i in case.issues(body)] == [review.FIGURE_ISSUE]


def test_an_unaccepted_item_cannot_compose(case: Case) -> None:
    items = {i.item_id: i for i in case.evidence if i.item_id != "ev-3"}
    with pytest.raises(t.TablesInvalid, match="ev-3"):
        p.compose_peer_tables(case.pack(), items, case.brief.cutoff)


@given(
    st.one_of(
        st.text(alphabet="0123456789.-+ aE", max_size=8),
        st.from_regex(r"-?[0-9]{1,6}(\.[0-9]{1,3})?", fullmatch=True),
        st.sampled_from([cp1c.NOT_STATED, "", "1,000.0", "٣.٠", "1.", ".5", "00.5"]),
    )
)
def test_amount_from_quote_accepts_exactly_what_the_table_rule_accepts(token: str) -> None:
    try:
        rule = cp1c._amount(token)
    except cp1c.PeerTableError:
        rule = None
    assert p.amount_from_quote(token) == rule


def renamed(case: Case, old: str, new: str) -> dict[str, Any]:
    body = copy.deepcopy(case.body)
    for section in ("candidates", "observations", "figures"):
        for row in body["peers"][section]:
            if row["peer_id"] == old:
                row["peer_id"] = new
    return body


def test_a_maximal_peer_id_composes_every_table_without_a_validation_error(case: Case) -> None:
    """The longest fact id (a TDR.5 ``<id>.definition.observation``) stays within the bound."""
    body = renamed(case, "p05", "x" * p.PEER_ID_MAX)
    assert case.issues(body) == ()
    composed = case.composed(body)
    assert max(len(f.fact_id) for f in composed.facts) <= 160
    assert [i.text for i in case.issues(renamed(case, "p05", "x" * (p.PEER_ID_MAX + 1)))] == [
        f"peer_id has no dot and is at most {p.PEER_ID_MAX} long"
    ]


def test_the_longest_operand_in_the_bound_is_the_longest_cp1c_operand() -> None:
    assert max(len(key) for key, _ in cp1c.OPERANDS) == len(p.LONGEST_OPERAND)


def test_a_tdr5_peer_id_absent_from_tdr4_is_the_issue(case: Case) -> None:
    body = copy.deepcopy(case.body)
    row = body["peers"]["observations"][0]
    row["peer_id"] = "p99"
    assert [str(i) for i in case.issues(body)] == [f"p99.{row['dimension']}: {p.NOT_A_CANDIDATE}"]
