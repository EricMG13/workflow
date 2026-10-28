"""CP-4C Stage 2: the connection of the Stage 1 core to the store, the registrations, the
bindings, the readers and the fast consumption proof (`docs/CP4C-OWNER-LEASE.md`,
`docs/G1X-OWNER-CORE-PROTOCOL.md`).

Expectations come from the lease and `cases/cp4c-owner/{expected,submissions}.json` (with the
pinned CP-2A, CP-2G and CP-4 oracles), never from the code under test. The stores here are real
`Execution` stores whose CP-0, CP-1, CP-2A, CP-4 and CP-2G heads are settled through
`begin`/`finish` from the oracles' own records (CP-2G also through the real CP-2G core), so no
CP-1 promotion runs: the genuine runs are `tests/test_owner_cp4c.py` and `tests/cp4c_runs.py`.
The fixtures vary the CP-1 amounts, the as-of date, the case kind (heads settle accepted or
restricted), the T4.18 period and the CP-2G head, so a constant equal to the oracle cannot pass.
"""

import json
from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest
import test_method_cp4c as stage1

from deploy_vii import prose
from deploy_vii.contracts import Fact
from deploy_workflow.owners import cp4c

MODULE = "CP-4C"
STEP = "restructuring_fulcrum"
MAX_LINE = 600
LTM = cp4c.LTM_PERIOD
Q3 = "Q3 25: 2025-07-01 to 2025-09-30"
DIFFER = "CP-4C: CP-2A T2B.1 facts differ in period"
NO_PERIOD = "CP-4C: CP-2A T2B.1 facts state no period"
NO_ROW = "CP-4C: CP-2G T2H.3.d01 and T2H.3.d02 sources name no single CP-2A T2B.1 row"


def _payload(case: str = "positive") -> dict[str, Any]:
    bound: dict[str, Any] = stage1._bind_all(stage1._payload(case), case)
    return bound


def _with(context: cp4c.Cp4cContext, payload: dict[str, Any]) -> cp4c.Cp4cInputs:
    sub = cp4c.RestructuringSubmission.model_validate_json(json.dumps(payload))
    return cp4c.Cp4cInputs(context=context, submission=sub)


def _cells(result: cp4c.RestructuringResult) -> dict[str, Fact]:
    return {c.fact.fact_id: c.fact for c in result.cells}


# --- backlog (stage2-backlog.md CP-4C rows; rulings stage2 round 5 item 16; protocol section 6) ---


def _shock(row: str, field: str, period: str | None) -> Fact:
    known = period is not None
    return Fact(
        fact_id=f"T2B.1.{row}.{field}",
        label=field,
        table_id="T2B.1",
        row_id=row,
        field=field,
        amount=Decimal("0.2") if known else None,
        status="known" if known else "missing",
        unit="PERCENT",
        period=period,
        limitation=None if known else "Not stated in CP-2A",
    )


def _cp2a(periods: dict[str, tuple[str | None, str | None]]) -> cp4c.Cp2aHead:
    facts: list[Fact] = []
    for row, (decline, increase) in periods.items():
        facts += [
            _shock(row, "ebitda_decline", decline),
            _shock(row, "interest_increase", increase),
        ]
    return cp4c.Cp2aHead(status="restricted", facts=tuple(facts))


def test_base_period_is_the_one_stated_period_of_the_row() -> None:
    """Round 13 R1 L2: the period the row's two shocks share, per row (never a constant)."""
    head = _cp2a({"s01": (Q3, Q3), "s03": (LTM, LTM)})
    assert (head.base_period("s01"), head.base_period("s03")) == (Q3, LTM)


def test_shocks_of_one_row_that_differ_in_period_raise_the_invariant() -> None:
    with pytest.raises(ValueError) as caught:
        _cp2a({"s03": (LTM, Q3)}).base_period("s03")
    assert str(caught.value) == DIFFER


@pytest.mark.parametrize("periods", [(None, LTM), (LTM, None)])
def test_a_shock_without_a_period_is_not_a_period_conflict(
    periods: tuple[str | None, str | None],
) -> None:
    """Stage 2 round 5 item 16: R1 L2 "if they differ" compares stated periods only."""
    assert _cp2a({"s03": periods}).base_period("s03") == LTM


def test_a_row_whose_shocks_state_no_period_raises() -> None:
    """No stated period at all leaves no base period: it raises, never returns None (backlog
    mutant "base_period returning None for a shared None period")."""
    with pytest.raises(ValueError) as caught:
        _cp2a({"s03": (None, None)}).base_period("s03")
    assert str(caught.value) == NO_PERIOD


def _with_cp2a(ctx: cp4c.Cp4cContext, change: Any) -> cp4c.Cp4cContext:
    return replace(ctx, cp2a=replace(ctx.cp2a, facts=tuple(change(f) for f in ctx.cp2a.facts)))


def test_an_unsettled_decline_without_a_period_takes_its_copy_path() -> None:
    """Round 5 item 16 (with round 8 A-4): a missing `ebitda_decline` that states no period
    composes; the copy is a gap with CP-2A's own status and limitation, and the base period is
    the interest increase's."""
    decline = "T2B.1.s03.ebitda_decline"
    ctx = _with_cp2a(
        stage1._context("positive"),
        lambda f: (
            stage1._refact(
                f, amount=None, status="missing", period=None, limitation="Not stated in CP-2A"
            )
            if f.fact_id == decline
            else f
        ),
    )
    cells = _cells(cp4c.compute(_with(ctx, _payload())))
    for case in ("v02", "v03"):
        copy = cells[f"T4E.3.{case}.ebitda_decline"]
        assert (copy.status, copy.limitation) == ("missing", "Not stated in CP-2A")
    assert cells["T4E.1.u_cp2a.basis"].text == f"Base period {LTM}"


def _source(fact: Fact, text: str) -> Fact:
    return fact.model_copy(update={"text": text})


def _named(ctx: cp4c.Cp4cContext, d01: str, d02: str) -> cp4c.Cp4cContext:
    g = ctx.cp2g
    return replace(
        ctx,
        cp2g=replace(
            g,
            down_ebitda_source=_source(g.down_ebitda_source, d01),
            down_interest_source=_source(g.down_interest_source, d02),
        ),
    )


def test_the_upstream_register_states_the_base_period_of_the_applied_row() -> None:
    """Backlog mutant `base_period("s03")` (cp4c.py `_t4e1`): CP-2G names s01, whose shocks are
    stated for Q3 while s03's are LTM; T4E.1 states s01's period."""
    ctx = _with_cp2a(
        stage1._context("positive"),
        lambda f: (
            stage1._refact(f, period=Q3)
            if f.row_id == "s01" and f.field in ("ebitda_decline", "interest_increase")
            else f
        ),
    )
    ctx = _named(ctx, "CP-2A T2B.1.s01.ebitda_decline", "CP-2A T2B.1.s01.interest_increase")
    cells = _cells(cp4c.compute(_with(ctx, _payload())))
    assert cells["T4E.1.u_cp2a.basis"].text == f"Base period {Q3}"
    assert cells["T4E.3.v02.cp2a_scenario"].text == ctx.cp2a.fact("T2B.1.s01.name").text


ARABIC = "٠٣"  # ARABIC-INDIC DIGIT ZERO, THREE: `\d` matches them, `[0-9]` does not


@pytest.mark.parametrize(
    "d01,d02",
    [
        (f"CP-2A T2B.1.s{ARABIC}.ebitda_decline", f"CP-2A T2B.1.s{ARABIC}.interest_increase"),
        ("CP-2A T2BX1.s03.ebitda_decline", "CP-2A T2B.1.s03.interest_increase"),
        ("CP-2A T2B.1Xs03.ebitda_decline", "CP-2A T2B.1.s03.interest_increase"),
        ("CP-2A T2B.1.s03Xebitda_decline", "CP-2A T2B.1.s03.interest_increase"),
        ("CP-2A T2B.1.s03.interest_increase", "CP-2A T2B.1.s03.interest_increase"),
        ("CP-2A T2B.1.s01.ebitda_decline", "CP-2A T2B.1.s03.interest_increase"),
    ],
)
def test_source_texts_that_name_no_single_ascii_row_raise_the_invariant(d01: str, d02: str) -> None:
    """Backlog mutants `\\d` for `[0-9]` (both source patterns) and the unescaped `.` of the d01
    pattern: each text must fullmatch the lease pattern exactly, ASCII digits only."""
    ctx = _named(stage1._context("positive"), d01, d02)
    with pytest.raises(ValueError) as caught:
        cp4c.compute(_with(ctx, _payload()))
    assert str(caught.value) == NO_ROW


def test_prose_and_quoting_issue_lines_are_clipped() -> None:
    """Protocol section 6 and the backlog f-string sites: every content issue line that quotes
    the analyst's text (prose issues, bare figures, the column, a class name, a source id or
    locator, a treatment class id) is cut at 600 characters before the journal sees it."""
    payload = _payload()
    long = "x" * 5000
    payload["assessment"]["rationale"] = "A figure of " + "7" * 5000 + " appears."
    payload["valuation"][0]["label"] = "Base " + "9" * 5000
    payload["claims"][1]["period_column"] = long
    payload["claims"][0]["support"][0]["source_id"] = long
    payload["claims"][0]["support"].append(
        {"source_id": "financial", "locator": "page:" + long, "quote": "Trade payables"}
    )
    payload["claims"][2]["amount_quote"]["locator"] = long
    issues = cp4c.content_issues(_with(stage1._context("positive"), payload))
    assert len(issues) == 6
    assert all(len(i) <= MAX_LINE for i in issues), [len(i) for i in issues]


def test_a_treatment_class_id_quoted_in_its_issue_is_clipped() -> None:
    payload = _payload()
    payload["plan"][0]["treatments"][0]["class_id"] = "x" * 5000
    issues = cp4c.content_issues(_with(stage1._context("positive"), payload))
    assert [i for i in issues if i.startswith("plan[0].treatments[0].class_id: not a claim class")]
    assert all(len(i) <= MAX_LINE for i in issues), [len(i) for i in issues]


def test_a_class_name_quoted_in_the_zero_claim_issue_is_clipped() -> None:
    payload = stage1._zero_rank_payload()
    payload["claims"][3]["name"] = "Unsecured debt " + "y" * 5000
    issues = cp4c.content_issues(_with(stage1._context("positive"), payload))
    assert [i for i in issues if i.startswith("claims[3]: a claim class needs a claim above zero")]
    assert all(len(i) <= MAX_LINE for i in issues), [len(i) for i in issues]


def test_the_join_of_a_raised_composition_is_bounded() -> None:
    """`compute` raises on any issue; its message is the bounded list (20 lines and a count)."""
    payload = _payload()
    blank = {"gap": " ", "why_it_matters": " ", "affected_analysis": " ", "action": " "}
    payload["gaps"] = [dict(payload["gaps"][0], **blank) for _ in range(8)]
    inputs = _with(stage1._context("positive"), payload)
    assert len(cp4c.content_issues(inputs)) == 32
    with pytest.raises(ValueError) as caught:
        cp4c.compute(inputs)
    assert str(caught.value).endswith("; 12 further issues not listed")  # 20 shown of 32


def test_stale_text_is_clipped() -> None:
    (issue,) = cp4c.stale_issues(bound=(), current="Required upstream " + "x" * 5000)
    assert issue.startswith("Stale inputs: Required upstream") and len(issue) <= MAX_LINE


def test_claim_text_is_checked_with_the_type_the_claim_builds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 2 round 3 item 2: a rationale becomes `Claim.text` (`RunText`); if `prose.issues`
    ever passed text `RunText` refuses, the validator still journals the type's own message
    (`include_input=False`) instead of the composition raising after the binding write."""
    monkeypatch.setattr(prose, "issues", lambda text, bound, names=(): [])
    payload = _payload()
    payload["fulcrum"][1]["rationale"] = "{low"
    issues = cp4c.content_issues(_with(stage1._context("positive"), payload))
    assert issues == (
        "fulcrum[1].rationale: Value error, Malformed run text: unbalanced or empty reference",
    )


def test_payload_text_is_parsed_through_json_object(monkeypatch: pytest.MonkeyPatch) -> None:
    """Protocol section 6 (the cp4c `payload_issues` rewire): the schema validates the bounded
    `json_object` document, never raw text; the frozen shape refusals keep their issues."""
    seen: list[str] = []
    real = cp4c.RestructuringSubmission.model_validate_json

    def spy(text: str | bytes, **kwargs: Any) -> cp4c.RestructuringSubmission:
        seen.append(str(text))
        return real(text, **kwargs)

    monkeypatch.setattr(cp4c.RestructuringSubmission, "model_validate_json", spy)
    spaced = json.dumps(_payload(), indent=2)
    assert cp4c.payload_issues(spaced, stage1._context("positive")) == ()
    assert seen and spaced not in seen
    for rid in [r for r in stage1.REFUSALS if r.startswith("r")]:
        got = cp4c.payload_issues(stage1._refusal_text(rid), stage1._context("positive"))
        assert list(got) == stage1._expected_issues(rid), rid
    for hostile in ('{"a": "\\ud800"}', "[" * 5000 + "]" * 5000, '{"x": NaN}'):
        issues = cp4c.payload_issues(hostile, stage1._context("positive"))
        assert issues and all(len(i) <= MAX_LINE for i in issues)
