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

import hashlib
import importlib
import json
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import pytest
import test_method_cp2g as cp2g_stage1
import test_method_cp4c as stage1
from defect_classes import (
    MODEL_TEXT_HOSTILE,
    assert_hostile_refused,
    free_text_paths,
    path_matches,
    with_text,
)

from deploy_vii import prose
from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import (
    Fact,
    Input,
    Module,
    ModuleView,
    ReportTable,
    Run,
    TableColumn,
    TableRow,
    View,
)
from deploy_vii.execution import Attempt, Execution, Head, Qualification
from deploy_vii.live.tools import UNREAD_PAGE, Seen, cited_locators
from deploy_vii.preparation import PreparedPack
from deploy_vii.report_view import _DISTRESSED, _PRESETS, _spec_of, fact_spelling
from deploy_workflow import host
from deploy_workflow.financial_workflow import _FrozenExecution
from deploy_workflow.owners import cp2g, cp4c
from deploy_workflow.workflow import WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")

MODULE = "CP-4C"
STEP = "restructuring_fulcrum"
MAX_LINE = 600
LTM = cp4c.LTM_PERIOD
Q3 = "Q3 25: 2025-07-01 to 2025-09-30"
DIFFER = "CP-4C: CP-2A T2B.1 facts differ in period"
NO_PERIOD = "CP-4C: CP-2A T2B.1 facts state no period"
NO_ROW = "CP-4C: CP-2G T2H.3.d01 and T2H.3.d02 sources name no single CP-2A T2B.1 row"
SYNTHETIC = "Synthetic case; not real issuer qualification"
EXPECTED = stage1.EXPECTED
MANIFEST = stage1.MANIFEST
CaseKind = Literal["public", "private", "synthetic"]


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


# --- the plug-in parts that need no store (protocol section 2) ---------------------------------


def test_core_attributes_match_the_lease() -> None:
    assert (cp4c.MODULE_ID, cp4c.STEP_ID, cp4c.SCHEMA_VERSION) == (
        MODULE,
        STEP,
        "restructuring-fulcrum/1",
    )
    assert cp4c.QUALIFICATION == Qualification(implementation="implemented")
    assert cp4c.STEP_IDS == (STEP,)
    assert dict(cp4c.SCHEMAS) == {STEP: cp4c.RestructuringSubmission}
    assert cp4c.SUBMISSION_INPUT == "restructuring-fulcrum-submission"
    for name in ("probe", "view", "submit", "ENTRY_VALIDATOR", "RULES", "cp4c_reader"):
        assert callable(getattr(cp4c, name)), name
    for name in ("cp2a_reader", "cp4_reader", "cp4c_upstream", "context_block", "cp4c_module"):
        assert callable(getattr(cp4c, name)), name
    for name in ("validate_restructuring", "restructuring", "waterfall"):
        assert callable(getattr(cp4c, name)), name
    assert not hasattr(cp4c, "precheck")  # lease Files: no precheck gate


@pytest.mark.parametrize("case", stage1.RUNS)
def test_schemas_round_trip_and_give_the_tail_digest(case: str) -> None:
    parsed = cp4c.SCHEMAS[STEP].model_validate_json(json.dumps(_payload(case)))
    assert cp4c.SCHEMAS[STEP].model_validate_json(parsed.model_dump_json()) == parsed
    assert parsed.content_hash() == hashlib.sha256(parsed.model_dump_json().encode()).hexdigest()


def _seen(*pages: tuple[str, str]) -> Seen:
    return Seen(read=frozenset(pages))


CITED = (("financial", "page:4"), ("legal-covenants", "page:1"))
CITED_SOURCES = ("financial", "legal-covenants")


@pytest.mark.parametrize("case", stage1.RUNS)
def test_rules_refuse_every_cited_page_not_read(case: str) -> None:
    """Lease Tool use: every cited `page:N` read first (UNREAD_PAGE, sorted); the oracle's
    `read_pages` calls (financial page:4, legal-covenants page:1) satisfy it."""
    text = json.dumps(_payload(case))
    assert cp4c.RULES(text, _seen(*CITED)) == ()
    assert cp4c.RULES(text, _seen()) == tuple(f"{UNREAD_PAGE}: {s} {p}" for s, p in CITED)
    assert cp4c.RULES(text, _seen(CITED[1])) == (f"{UNREAD_PAGE}: financial page:4",)


def test_shared_hostile_text_set_over_the_schemas() -> None:
    """Rulings stage2 Q5: the schema refuses the hostile set only with `ValueError`."""
    for schema in cp4c.SCHEMAS.values():
        assert_hostile_refused(schema)


# Stage 2 round 5 item 10: the free-text paths of the positive payload whose value is stored as
# plain text and never built as `RunText`. Sinks: each class, valuation, fulcrum, plan and
# assessment `limitation` is `Claim.limitation` of its analyst claim (`restructuring` claims);
# each gap text is a T4E.10 `Fact.text` (and `gap` also an own limitation, `Text`). Every other
# free-text path (names, labels, rationales, quotes, ids, the column) must be refused.
CP4C_VERBATIM: frozenset[tuple[str | int, ...]] = frozenset(
    {
        ("claims", "*", "limitation"),
        ("valuation", "*", "limitation"),
        ("fulcrum", "*", "limitation"),
        ("plan", "*", "limitation"),
        ("assessment", "limitation"),
        ("gaps", "*", "gap"),
        ("gaps", "*", "why_it_matters"),
        ("gaps", "*", "affected_analysis"),
        ("gaps", "*", "action"),
    }
)


def test_model_text_is_refused_or_stored_verbatim() -> None:
    """Round 3 item 2 and round 5 item 10 at the validator (the run-level form, with the wedge
    check, is `test_owner_cp4c.py`): every hostile value on every free-text path is an issue,
    except on the `CP4C_VERBATIM` paths, where it composes and is stored as plain text."""
    payload = _payload()
    paths = free_text_paths(payload, cp4c.RestructuringSubmission)
    assert all(any(path_matches(p, path) for path in paths) for p in CP4C_VERBATIM)
    context = stage1._context("positive")
    for path in paths:
        for value in MODEL_TEXT_HOSTILE:
            text = json.dumps(with_text(payload, path, value))
            issues = cp4c.payload_issues(text, context)
            if any(path_matches(p, path) for p in CP4C_VERBATIM):
                assert issues == (), (path, value)
                result = cp4c.compute(_with(context, json.loads(text)))
                stored = [c.limitation for c in result.claims]
                stored += [c.fact.text for c in result.cells if c.fact.table_id == "T4E.10"]
                assert value in stored, (path, value)
            else:
                assert issues, (path, value)


# --- a real store, heads settled from the oracles' own records ----------------------------------


def _run(case: str, *, as_of: str | None, case_kind: CaseKind) -> Run:
    document = dict(MANIFEST["cases"][case]["run"])
    document["case_kind"] = case_kind
    if as_of is not None:
        document["as_of"] = as_of
    return Run.model_validate_json(json.dumps(document))


def _pack(
    case: str = "positive", *, as_of: str | None = None, case_kind: CaseKind = "synthetic"
) -> PreparedPack:
    base = stage1._pack(case)
    return PreparedPack(run=_run(case, as_of=as_of, case_kind=case_kind), sources=base.sources)


def _command(module_id: str) -> Fact:
    return Fact(
        fact_id=f"t8-{module_id.lower()}",
        label="Command",
        table_id="T8",
        row_id=module_id,
        field="exact_command",
        text=f"Run {module_id}",
    )


def _finish(
    store: Execution,
    module_id: str,
    facts: tuple[Fact, ...],
    note: str | None,
    tables: tuple[ReportTable, ...] = (),
) -> None:
    ticket = store.begin(module_id)
    run = store.read().run
    module = Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=module_id,
        inputs=ticket.inputs,
        facts=facts,
        tables=tables,
        limitations=() if note is None else (note,),
    )
    store.finish(ticket.ticket_id, module.model_dump_json(), lambda _m: ())


def _blocked(store: Execution, module_id: str) -> None:
    """Two refused settlements: attempt 0 rejected, the repair blocked."""
    for _ in range(2):
        ticket = store.begin(module_id)
        store.finish(ticket.ticket_id, "{}", lambda _m: ("refused",))


def _text(table: str, row: str, field: str, text: str, period: str | None) -> Fact:
    return Fact(
        fact_id=f"cp1-{table}-{row}-{field}",
        label=field,
        table_id=table,
        row_id=row,
        field=field,
        text=text,
        period=period,
    )


PERIODS = (("q3-2025", "QUARTER", "2025-09-30"), ("q4-2025", "QUARTER", "2025-12-31"))
# Another CP-1 total debt under which every oracle judgment still fits (v03, EV 37.08, breaks at
# c01; v02, EV 55.62, at c02 and c03), so a constant equal to the oracle's 50 cannot pass.
DEBT = "45"
FY_ALIAS = ("fy-2025", "FY", "2025-12-31")


def _t414(periods: tuple[tuple[str, str, str], ...]) -> tuple[Fact, ...]:
    return tuple(
        _text("T4.14", f"period-{pid}", name, value, pid)
        for pid, kind, end in periods
        for name, value in (("period_id", pid), ("period_type", kind), ("end_date", end))
    )


def _t418_row(row: str, period: str, secured: str, seniority: str) -> tuple[Fact, ...]:
    return (
        _text("T4.18", row, "facility_id", stage1.FACILITY, period),
        _text("T4.18", row, "period_id", period, period),
        _text("T4.18", row, "secured_status", secured, period),
        _text("T4.18", row, "seniority", seniority, period),
    )


def cp1_facts(
    case: str = "positive",
    *,
    total_debt: str | None = None,
    alias: tuple[str, str] | None = ("SECURED", "SENIOR"),
    current_row: bool = True,
) -> tuple[Fact, ...]:
    """A CP-1 head: CP-2G's T4.10 facts (its total debt and EBITDA are exactly CP-4C's Stage 1
    ones), the Stage 1 T4.18 terms of the term loan at q4-2025 in one row with its facility and
    period ids, an earlier q3-2025 row (UNSECURED, never chosen), the FY alias row and T4.14.
    Without `current_row` the q4-2025 term-loan row is left out (T4.14 still states q4-2025)."""
    t410 = cp2g_stage1._cp1_facts("gap")
    if total_debt is not None:
        t410 = tuple(
            f.model_copy(update={"amount": Decimal(total_debt)}) if f.row_id == "total_debt" else f
            for f in t410
        )
    terms = tuple(stage1._cp1_t418(case, f) for f in ("secured_status", "seniority"))
    current = (
        _text("T4.18", "term-loan", "facility_id", stage1.FACILITY, "q4-2025"),
        _text("T4.18", "term-loan", "period_id", "q4-2025", "q4-2025"),
        *terms,
    )
    earlier = _t418_row("term-loan-q3", "q3-2025", "UNSECURED", "SUBORDINATED")
    fy = () if alias is None else _t418_row("term-loan-fy", "fy-2025", *alias)
    current_terms = current if current_row else ()
    return (*t410, *earlier, *current_terms, *fy, *_t414((*PERIODS, FY_ALIAS)))


def oracle_facts(source: dict[str, Any], case: str) -> tuple[Fact, ...]:
    return tuple(stage1._fact(rec) for rec in source["cases"][case]["facts"])


def _t2h7(case: str = "gap") -> ReportTable:
    """The CP-2G T2H.7 table of the oracle case (the reader reads its rows)."""
    table = next(t for t in stage1.CP2G_EXP["cases"][case]["tables"] if t["table_id"] == "T2H.7")
    facts = {f.fact_id: f for f in oracle_facts(stage1.CP2G_EXP, case)}
    first = [facts[fid] for fid in table["rows"][0]["fact_ids"]]
    return ReportTable(
        table_id="T2H.7",
        title=table["title"],
        columns=tuple(TableColumn(field=f.field, label=f.label) for f in first),
        rows=tuple(
            TableRow(row_id=r["row_id"], label=r["label"], fact_ids=tuple(r["fact_ids"]))
            for r in table["rows"]
        ),
    )


def _cp2g_genuine(store: Execution) -> None:
    """The real CP-2G core over the seeded heads: the frozen CP-2G gap literal (the CP-4C
    oracle's `upstream_step_literals.CP-2G` pointer), figures bound by the CP-2G rule."""
    ticket = store.begin("CP-2G")
    payload = cp2g_stage1._bind_all(cp2g_stage1._payload("gap"))
    done = cp2g.submit(store, ticket.ticket_id, "forward_credit_model", json.dumps(payload), None)
    assert done.journal.status == "finished" and done.journal.issues == ()


def seed(
    root: Path,
    case: str = "positive",
    *,
    cp1: tuple[Fact, ...] | None = None,
    genuine_cp2g: bool = False,
    cp2g_blocked: bool = False,
    as_of: str | None = None,
    case_kind: CaseKind = "synthetic",
    notes: bool = True,
) -> tuple[Execution, PreparedPack, Attempt]:
    """A real store with CP-0, CP-1, CP-2A, CP-4 and CP-2G settled (plan order), CP-4C begun."""
    pack = _pack(case, as_of=as_of, case_kind=case_kind)
    store = Execution.create(root / "store", pack)

    def note(module_id: str) -> str | None:
        return f"{module_id} note" if notes else None

    commands = tuple(_command(m) for m in ("CP-1", "CP-2A", "CP-4", "CP-2G", "CP-4C"))
    _finish(store, "CP-0", commands, note("CP-0"))
    _finish(store, "CP-1", cp1_facts(case) if cp1 is None else cp1, note("CP-1"))
    _finish(store, "CP-2A", oracle_facts(stage1.CP2A_EXP, "positive"), note("CP-2A"))
    _finish(store, "CP-4", stage1._cp4(case).facts, note("CP-4"))
    if cp2g_blocked:
        _blocked(store, "CP-2G")
        return store, pack, store.read().attempts[-1]
    if genuine_cp2g:
        _cp2g_genuine(store)
    else:
        _finish(store, "CP-2G", oracle_facts(stage1.CP2G_EXP, "gap"), note("CP-2G"), (_t2h7(),))
    return store, pack, store.begin(MODULE)


def _head(store: Execution, module_id: str) -> Head:
    return next(h for h in store.read().heads if h.module_id == module_id)


def _finished(store: Execution, attempt: Attempt) -> Attempt:
    return next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)


def _upstream(store: Execution, attempt: Attempt) -> "cp4c.Upstream":
    return cp4c.cp4c_upstream(store=store, attempt=attempt)


def _submission(case: str = "positive") -> cp4c.RestructuringSubmission:
    return cp4c.RestructuringSubmission.model_validate_json(json.dumps(_payload(case)))


def _cp4_read(head: cp4c.Cp4Head) -> cp4c.Cp4Head:
    """The lease's `cp4_reader` selection (T4C.11, T4.10.r02, T4.13) of a Stage 1 CP-4 head."""
    keep = ("T4C.11.", "T4.10.r02.", "T4.13.")
    return replace(head, facts=tuple(f for f in head.facts if f.fact_id.startswith(keep)))


# --- the store adapter (one adapter for submit, probe and view) ----------------------------------


@pytest.mark.parametrize("case", stage1.RUNS)
def test_adapter_returns_the_stage_1_input_object(case: str, tmp_path: Path) -> None:
    """Over heads settled from the oracles' own records, the adapter returns the Stage 1 test's
    `Cp4cInputs` (pack, CP-1 head, CP-2A head, CP-2G head, statuses), except that the CP-4 head
    holds what the lease's `cp4_reader` reads; the core composes exactly the Stage 1 result, so
    the CP-4 facts left out are never read."""
    store, pack, attempt = seed(tmp_path, case)
    got = cp4c._inputs(pack, _submission(case), _upstream(store, attempt))
    want = stage1._inputs(case)
    narrowed = replace(want.context, cp4=_cp4_read(want.context.cp4))
    assert got == replace(want, context=narrowed)
    assert {f.fact_id for f in got.context.cp4.facts} >= set(cp4c.CP4_FACTS)
    assert cp4c.compute(got) == stage1._result(case)


def test_adapter_follows_the_cp1_head(tmp_path: Path) -> None:
    store, pack, attempt = seed(tmp_path, cp1=cp1_facts(total_debt=DEBT), as_of="2026-02-03")
    got = cp4c._inputs(pack, _submission(), _upstream(store, attempt))
    cells = {c.fact.fact_id: c.fact for c in cp4c.compute(got).cells}
    assert cells["T4E.2.c01.claim"].amount == Decimal(45)
    assert cells["T4E.9.v01.total_claims"].amount == Decimal(75)
    assert pack.run.as_of.isoformat() == "2026-02-03"


@pytest.mark.parametrize("case_kind", ["synthetic", "private"])
def test_adapter_statuses_are_the_bound_input_statuses(case_kind: CaseKind, tmp_path: Path) -> None:
    """A private run with no notes settles its heads accepted, a synthetic run restricted; the
    adapter passes the bound statuses through, never a constant."""
    synthetic = case_kind == "synthetic"
    store, pack, attempt = seed(tmp_path, case_kind=case_kind, notes=synthetic)
    want = "restricted" if synthetic else "accepted"
    ctx = cp4c._inputs(pack, _submission(), _upstream(store, attempt)).context
    assert (ctx.cp1.status, ctx.cp2a.status, ctx.cp2g.status, ctx.cp4.status) == (want,) * 4
    assert [i.status for i in attempt.inputs if i.input_id.startswith("CP-")] == [want] * 5


def test_adapter_reads_each_status_from_its_own_bound_input(tmp_path: Path) -> None:
    """A bound optional CP-3C (never read) shows its own status in T4E.1; unbound it is absent."""
    store, pack, attempt = seed(tmp_path)
    upstream = _upstream(store, attempt)
    cp3c = Input(input_id="CP-3C", sha256="c" * 64, status="blocked")
    ctx = cp4c._inputs(pack, _submission(), replace(upstream, bound=(*upstream.bound, cp3c)))
    assert ctx.context.cp3c_status == "blocked"
    assert cp4c._inputs(pack, _submission(), upstream).context.cp3c_status is None


def test_the_quarter_row_wins_over_its_fy_alias_and_an_earlier_quarter(tmp_path: Path) -> None:
    """Manifest cp1_t418: the QUARTER period at the latest T4.14 end (q4-2025) wins; the q3-2025
    row (UNSECURED) is not read, the FY alias must agree."""
    store, _, attempt = seed(tmp_path)
    cp1 = _upstream(store, attempt).cp1
    assert (cp1.secured_status.period, cp1.secured_status.text) == ("q4-2025", "SECURED")
    assert (cp1.seniority.period, cp1.seniority.text) == ("q4-2025", "SENIOR")
    assert cp1.facility_id == "term-loan"


@pytest.mark.parametrize(
    "facts,message",
    [
        (cp1_facts(alias=("SECURED", "SUBORDINATED")), "seniority differs between its q4-2025"),
        (cp1_facts(alias=("UNSECURED", "SENIOR")), "secured_status differs between its q4-2025"),
        (cp1_facts(current_row=False), "states no term-loan terms for q4-2025"),
        (tuple(f for f in cp1_facts() if f.table_id != "T4.14"), "states no T4.14 period"),
    ],
)
def test_t418_terms_that_cannot_be_read_fail_closed(
    facts: tuple[Fact, ...], message: str, tmp_path: Path
) -> None:
    store, _, attempt = seed(tmp_path, cp1=facts)
    with pytest.raises(ValueError, match=message):
        _upstream(store, attempt)


def test_without_an_alias_row_the_quarter_row_is_read(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path, cp1=cp1_facts(alias=None))
    assert _upstream(store, attempt).cp1.secured_status.text == "SECURED"


def test_upstream_binds_the_attempt_and_reports_the_inputs_now(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    upstream = _upstream(store, attempt)
    assert [i.input_id for i in attempt.inputs] == EXPECTED["execution"]["inputs"]
    assert upstream.bound == attempt.inputs and upstream.current == attempt.inputs
    assert upstream.inherited == (
        "CP-0 note",
        SYNTHETIC,
        "CP-1 note",
        "CP-2A note",
        "CP-4 note",
        "CP-2G note",
    )
    snapshot = store.read()
    heads = tuple(h for h in snapshot.heads if h.module_id != "CP-2G")
    stale = _FrozenExecution(store, snapshot.model_copy(update={"heads": heads}))
    assert _upstream(stale, attempt).current == "Required upstream is unrun, stale or blocked"


@pytest.mark.parametrize("rid", sorted(stage1.STALE))
def test_a_stale_bound_upstream_is_the_oracle_issue_alone(rid: str, tmp_path: Path) -> None:
    """v24-v27: the store-bound tuple against a current tuple in which only that one upstream
    Input differs gives exactly the oracle line, and no content check runs."""
    upstream_id = stage1.STALE[rid]
    store, pack, attempt = seed(tmp_path)
    upstream = _upstream(store, attempt)
    literal = stage1.REFUSALS[rid]["upstream_literal"]["current"][0]
    other = Input(input_id=literal["input_id"], sha256=literal["sha256"], status=literal["status"])
    current = tuple(other if i.input_id == upstream_id else i for i in attempt.inputs)
    bound = next(i for i in attempt.inputs if i.input_id == upstream_id)
    (issue,) = stage1._expected_issues(rid)
    want = re.sub(r"<12 hex of [^>]*>", bound.sha256[:12], issue)
    stale = replace(upstream, current=current)
    sub = _submission()
    assert cp4c.validate_restructuring(pack=pack, submission=sub, upstream=stale) == (want,)
    high = _payload()
    high["assessment"]["confidence"] = "High"
    bad = cp4c.RestructuringSubmission.model_validate_json(json.dumps(high))
    assert cp4c.validate_restructuring(pack=pack, submission=bad, upstream=stale) == (want,)
    assert cp4c.validate_restructuring(pack=pack, submission=bad, upstream=upstream) == (
        cp4c.HIGH_ISSUE,
    )


def test_a_refused_current_inputs_text_is_one_clipped_stale_issue(tmp_path: Path) -> None:
    store, pack, attempt = seed(tmp_path)
    upstream = replace(_upstream(store, attempt), current="Required upstream " + "x" * 5000)
    (issue,) = cp4c.validate_restructuring(pack=pack, submission=_submission(), upstream=upstream)
    assert issue.startswith("Stale inputs: Required upstream") and len(issue) <= MAX_LINE


def test_a_bound_input_of_another_module_is_refused(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    cp1 = next(i for i in attempt.inputs if i.input_id == "CP-1")
    forged = attempt.model_copy(
        update={
            "inputs": tuple(
                i.model_copy(update={"sha256": cp1.sha256}) if i.input_id == "CP-2G" else i
                for i in attempt.inputs
            )
        }
    )
    with pytest.raises(ValueError, match="CP-2G input is a CP-1 module"):
        _upstream(store, forged)


# --- the journal: submit, the entry validator, probe ---------------------------------------------


def _every_cited_read(text: str) -> tuple[str, ...]:
    """The journaled rules of a step that read every page it cites (isolates the validator)."""
    return cp4c.RULES(text, Seen(read=frozenset(cited_locators(text))))


def _all_read(text: str) -> tuple[str, ...]:
    """The journaled rules of a step whose oracle `read_pages` calls all ran."""
    return cp4c.RULES(text, _seen(*CITED))


def _submit(store: Execution, attempt: Attempt, payload: str, rules: Any = _all_read) -> Any:
    return cp4c.submit(store, attempt.ticket_id, STEP, payload, rules)


def settled(
    root: Path, case: str = "positive", **kwargs: Any
) -> tuple[Execution, PreparedPack, Attempt, Any]:
    store, pack, attempt = seed(root, case, **kwargs)
    return store, pack, attempt, _submit(store, attempt, json.dumps(_payload(case)))


@pytest.mark.parametrize("case", stage1.RUNS)
def test_submit_settles_the_head_with_the_tail_input(case: str, tmp_path: Path) -> None:
    store, pack, attempt, submitted = settled(tmp_path, case)
    assert (submitted.nulls_resolved, submitted.prefilled, submitted.prefilled_kinds) == (
        (),
        (),
        (),
    )
    finished = _finished(store, attempt)
    assert finished.status == "finished" and finished.issues == ()
    head = _head(store, MODULE)
    assert head.status == EXPECTED["cases"][case]["module_status"] == "restricted"
    assert head.qualification == cp4c.QUALIFICATION
    module = store.head_module(head)
    parsed = cp4c.RestructuringSubmission.model_validate_json(submitted.payload)
    tail = Input(input_id="restructuring-fulcrum-submission", sha256=parsed.content_hash())
    assert module.inputs == (*attempt.inputs, tail)
    upstream = _upstream(store, attempt)
    report = cp4c.restructuring(pack=pack, submission=parsed, upstream=upstream)
    assert (module.facts, module.tables, module.claims) == (
        report.facts,
        report.tables,
        report.claims,
    )
    assert list(module.limitations) == [*EXPECTED["cases"][case]["own_limitations"], SYNTHETIC]
    assert module.inherited_limitations == tuple(
        n for n in upstream.inherited if n not in module.limitations
    )


def test_an_unread_cited_page_journals_an_invalid_step(tmp_path: Path) -> None:
    """Lease Tool use: an unread citation is refused (the journaled rule after the validator)."""
    store, _, attempt = seed(tmp_path)

    def legal_page_only(text: str) -> tuple[str, ...]:
        return cp4c.RULES(text, _seen(CITED[1]))

    _submit(store, attempt, json.dumps(_payload()), legal_page_only)
    finished = _finished(store, attempt)
    assert finished.status == "finished" and finished.steps[0].status == "invalid"
    assert list(finished.issues) == [f"{UNREAD_PAGE}: financial page:4"]
    assert not [h for h in store.read().heads if h.module_id == MODULE]


def test_probe_rebuilds_the_settled_head_and_writes_nothing(tmp_path: Path) -> None:
    store, _, attempt, _ = settled(tmp_path)
    snapshot = store.read()
    cp4c.probe(store, snapshot, _finished(store, attempt))
    assert store.read() == snapshot


def test_probe_refuses_a_journal_that_does_not_rebuild(tmp_path: Path) -> None:
    store, _, attempt, _ = settled(tmp_path)
    snapshot, finished = store.read(), _finished(store, attempt)
    step = finished.steps[0]
    other = _payload()
    other["assessment"]["rationale"] = "A different, figure-free rationale for the assessment."
    forged_steps = {
        "another step output": (step.model_copy(update={"output_sha256": "0" * 64}),),
        "a step that is not valid": (step.model_copy(update={"status": "invalid"}),),
        "two steps": (step, step),
        "another payload": (
            step.model_copy(update={"payload_sha256": store._store(json.dumps(other))}),
        ),
    }
    for name, steps in forged_steps.items():
        with pytest.raises(WorkflowError) as caught:
            cp4c.probe(store, snapshot, finished.model_copy(update={"steps": steps}))
        assert caught.value.code == "identity_mismatch", name


def test_probe_refuses_the_forged_value_break_in_the_result_module(tmp_path: Path) -> None:
    """A4's target (expected.tamper): the T4E.7.v03.value_break text lives only in the result
    Module, so a head whose Module says otherwise does not rebuild."""
    store, _, attempt, _ = settled(tmp_path)
    snapshot = store.read()
    module = store.head_module(_head(store, MODULE))
    tamper = EXPECTED["tamper"]
    target = tamper["target_fact"]
    assert next(f for f in module.facts if f.fact_id == target).text == tamper["from"]
    forged = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"text": tamper["to"]}) if f.fact_id == target else f
                for f in module.facts
            )
        }
    )
    digest = store._store(forged.model_dump_json())
    finished = _finished(store, attempt).model_copy(update={"result_sha256": digest})
    heads = tuple(
        h.model_copy(update={"result_sha256": digest}) if h.module_id == MODULE else h
        for h in snapshot.heads
    )
    with pytest.raises(WorkflowError) as caught:
        cp4c.probe(store, snapshot.model_copy(update={"heads": heads}), finished)
    assert caught.value.code == "identity_mismatch"


def test_entry_validator_is_the_one_submit_journals_with(tmp_path: Path) -> None:
    store, pack, attempt, _ = settled(tmp_path)
    finished = _finished(store, attempt)
    outcome = cp4c.ENTRY_VALIDATOR(store, pack, finished)
    assert outcome.issues == () and outcome.retained_as(finished.steps[0])


RUN_LEVEL = [rid for rid in stage1.REFUSALS if rid not in stage1.STALE]


@pytest.mark.parametrize("rid", RUN_LEVEL)
def test_each_refusal_is_a_journaled_invalid_step_with_the_oracle_issues(
    rid: str, tmp_path: Path
) -> None:
    store, _, attempt = seed(tmp_path)
    _submit(store, attempt, stage1._refusal_text(rid), _every_cited_read)
    finished = _finished(store, attempt)
    want = stage1._expected_issues(rid)
    assert finished.status == "finished" and list(finished.issues) == want
    assert finished.steps[0].status == "invalid"
    assert all(len(i) <= MAX_LINE for i in finished.issues)
    rejected = store.result(finished.result_sha256 or "")
    assert rejected.status == "rejected" and list(rejected.limitations) == want
    assert not [h for h in store.read().heads if h.module_id == MODULE]


def test_v08_also_journals_the_out_of_scope_page_it_could_not_read(tmp_path: Path) -> None:
    """v08 cites identity page:1, outside the step's H1 scope, so `read_pages` never returns it:
    under the oracle's reads the journal holds the validator issue, then the unread page."""
    store, _, attempt = seed(tmp_path)
    _submit(store, attempt, stage1._refusal_text("v08"))
    assert list(_finished(store, attempt).issues) == [
        *stage1._expected_issues("v08"),
        f"{UNREAD_PAGE}: identity page:1",
    ]


def test_two_refusals_block_the_module(tmp_path: Path) -> None:
    """expected.json cases.blocked: r01 on attempt 0 (rejected), v13 on attempt 1 (blocked); the
    reader of the blocked head gives its status and hash only."""
    expected = EXPECTED["cases"]["blocked"]
    store, _, first = seed(tmp_path)
    _submit(store, first, stage1._refusal_text("r01"))
    assert list(_finished(store, first).issues) == expected["attempt_0"]["limitations"]
    second = store.begin(MODULE)
    assert second.number == 1 and second.repair_of == first.ticket_id
    assert list(second.repair_issues) == expected["attempt_1"]["repair_issues"]
    _submit(store, second, stage1._refusal_text("v13"))
    head = _head(store, MODULE)
    module = store.head_module(head)
    assert head.status == expected["head"]["status"] == "blocked"
    assert (len(module.tables), len(module.facts)) == (
        expected["head"]["tables"],
        expected["head"]["facts"],
    )
    assert list(module.limitations) == expected["attempt_1"]["limitations"]
    read = cp4c.cp4c_reader(store, head)
    assert (read.status, read.head_sha256, read.facts, read.limitations) == (
        "blocked",
        head.result_sha256,
        (),
        (),
    )


def test_a_blocked_cp2g_head_refuses_the_cp4c_begin(tmp_path: Path) -> None:
    """expected.json cases.cp2g_blocked: CP-2G is a required edge, so a blocked CP-2G head is
    never bound; `begin` raises the oracle message and no CP-4C attempt exists."""
    store, _, _ = seed(tmp_path, cp2g_blocked=True)
    want = EXPECTED["cases"]["cp2g_blocked"]["cp4c_begin"]
    with pytest.raises(ValueError) as caught:
        store.begin(MODULE)
    assert (type(caught.value).__name__, str(caught.value)) == (want["error"], want["message"])
    assert not [a for a in store.read().attempts if a.module_id == MODULE]


def test_submit_refuses_a_foreign_step(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    with pytest.raises(ValueError, match="one step"):
        cp4c.submit(store, attempt.ticket_id, "other_step", json.dumps(_payload()), None)


# --- the settled head equals the oracle (A1, A2; fast form) --------------------------------------


@pytest.mark.parametrize("case", stage1.RUNS)
def test_settled_facts_claims_and_limitations_equal_the_oracle(case: str, tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, case)
    module = store.head_module(_head(store, MODULE))
    want = EXPECTED["cases"][case]
    own = [f for f in module.facts if f.table_id.startswith("T4E.")]
    assert len(own) == len(want["facts"]) == {"positive": 256, "gap": 301}[case]
    assert [f.fact_id for f in own] == [e["fact_id"] for e in want["facts"]]
    citations = stage1._oracle_citations(case)  # the oracle's lineage rule over its own records
    for fact, e in zip(own, want["facts"], strict=True):
        # A settled Fact stores no lineage and no spelling: both are the oracle's own here, so
        # the record compares every stored field (lineage is the D3 test's, spelling FP05's).
        cell = cp4c.Cell(fact, tuple(e.get("derives_from", ())), (), e["shown"])
        record = stage1._record(cell)
        expected = {k: v for k, v in e.items() if k != "citations"}
        assert record == expected, fact.fact_id
        assert stage1._cites(fact.citations) == citations[fact.fact_id], fact.fact_id
    assert [(c.claim_id, c.text, c.citations, c.limitation) for c in module.claims] == [
        (c["claim_id"], stage1._bind(c["text"], case), (), c["limitation"]) for c in want["claims"]
    ]
    assert list(module.limitations) == [*want["own_limitations"], SYNTHETIC]
    tables = [t.table_id for t in module.tables]
    refs = ["cp1_references", "cp2g_references", "cp2a_references", "cp4_references"]
    assert tables == [*cp4c.TABLES, *refs]
    for table, e in zip(module.tables, want["tables"], strict=False):
        assert (table.table_id, table.title) == (e["table_id"], e["title"])
        assert [(r.row_id, r.label, list(r.fact_ids)) for r in table.rows] == [
            (r["row_id"], r["label"], r["fact_ids"]) for r in e["rows"]
        ]


@pytest.mark.parametrize("case", stage1.RUNS)
def test_reference_tables_carry_the_upstream_facts_verbatim(case: str, tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, case)
    module = store.head_module(_head(store, MODULE))
    facts = {f.fact_id: f for f in module.facts}
    upstream = {
        f.fact_id: f
        for h in store.read().heads
        if h.module_id in ("CP-1", "CP-2A", "CP-4", "CP-2G")
        for f in store.head_module(h).facts
    }
    coordinates = {"table_id", "row_id", "field"}
    for name in ("cp1_references", "cp2g_references", "cp2a_references", "cp4_references"):
        table = next(t for t in module.tables if t.table_id == name)
        want = EXPECTED["cases"][case][name]
        assert (table.title, table.row_header) == (want["title"], want["row_header"])
        assert [(c.field, c.label) for c in table.columns] == [("value", "Value")]
        assert [(r.row_id, r.label) for r in table.rows] == [
            (r["row_id"], r["label"]) for r in want["rows"]
        ]
        for row, e in zip(table.rows, want["rows"], strict=True):
            (fid,) = row.fact_ids
            copy = facts[fid]
            assert (copy.table_id, copy.row_id, copy.field) == (name, row.row_id, "value")
            assert copy.model_dump(exclude=coordinates) == upstream[fid].model_dump(
                exclude=coordinates
            )
            assert (copy.status, stage1._norm(copy.amount)) == (e["status"], e["amount_exact"])


# --- the exact `read_inputs` view -----------------------------------------------------------------

FORBIDDEN_KEYS = {"quote", "citations", "record_json"}
TREE_KEYS = list(MANIFEST["tool_use"]["view_tree_draft"]["keys"])


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def _quotes(store: Execution) -> set[str]:
    return {
        c.quote for h in store.read().heads for f in store.head_module(h).facts for c in f.citations
    }


@pytest.mark.parametrize("case", stage1.RUNS)
def test_view_is_the_lease_key_tree_without_quotes(case: str, tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path, case)
    digest, body = cp4c.view(_FrozenExecution(store, store.read()), attempt)
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    tree = json.loads(body)
    assert body == json.dumps(tree, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    assert list(tree) == TREE_KEYS and not _keys(tree) & FORBIDDEN_KEYS
    assert _quotes(store) and not [q for q in _quotes(store) if q in body]
    e = EXPECTED["cases"][case]
    assert [u["module_id"] for u in tree["upstream"]] == EXPECTED["execution"]["inputs"][1:]
    debt = e["figures"]["total_debt_ltm"]
    secured = tree["claims_offered"]["secured"]
    assert (secured["ref"], secured["shown"]) == (stage1._fig_id("total_debt_ltm"), debt["spelled"])
    assert (secured["secured_status"], secured["seniority"]) == ("SECURED", "SENIOR")
    assert (secured["facility_id"], secured["facility"]) == ("term-loan", "Northbridge Term Loan")
    rows = {r["label"]: r["columns"] for r in tree["claims_offered"]["statement_rows"]}
    for claim in _payload(case)["claims"]:
        if claim["amount_source"] == "source_row":
            label = claim["amount_quote"]["quote"].split("  ")[0]
            assert claim["period_column"] in rows[label]
    offered = {(x["case"], x["year"]): x for x in tree["ebitda_offered"]}
    assert len(offered) == 6
    for name in ("ebitda_base_fy26", "ebitda_down_fy26"):
        figure = e["figures"][name]
        hit = next(x for x in offered.values() if x["ref"] == figure["fact_id"])
        assert (hit["shown"], hit["status"]) == (figure["spelled"], "known")
    assert tree["cp2a"]["scenario_row"] == e["cp2a_head"]["scenario"]
    assert tree["cp2a"]["name"] == e["cp2a_head"]["scenario_name"]
    assert tree["cp2a"]["ebitda_decline"] == {"shown": "40.0%", "status": "known"}
    cp4_rows = {r["fact_id"]: r["text"] for r in e["cp4_references"]["rows"]}
    assert tree["cp4"] == {
        "facility": cp4_rows["T4C.11.r01.facility"],
        "lender_protection": cp4_rows["T4.13.rating.rating"],
        "additional_debt_conditions": cp4_rows["T4.10.r02.conditions"],
    }
    assert tree["bounds"]["multiple"] == {"max": "99.99", "places": 2, "may_be_not_assessed": True}
    assert tree["bounds"]["treatments"] == [
        "Paid in full",
        "Receives reorganised equity",
        "Equity retained",
        "No recovery",
        "Not determined",
    ]
    assert [f["ref"] for f in tree["cp1_facts"]] == [
        stage1._fig_id("total_debt_ltm"),
        stage1._fig_id("ebitda_ltm"),
    ]
    assert {f["ref"] for f in tree["cp2g_facts"]} >= {"T2H.4.b26.ebitda", "T2H.4.d26.ebitda"}
    assert tree["inherited_limitations"] == list(_upstream(store, attempt).inherited)


def test_view_is_the_registered_view_of_the_step(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    frozen = _FrozenExecution(store, store.read())
    assert owner._VIEWS[STEP](frozen, attempt) == cp4c.view(frozen, attempt)


def test_the_view_follows_the_heads(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path, cp1=cp1_facts(total_debt=DEBT))
    tree = json.loads(cp4c.view(store, attempt)[1])
    assert tree["claims_offered"]["secured"]["shown"] == "45 US$ m"


# --- registrations (lease Files; append-only rows) -----------------------------------------------


def test_registrations_equal_the_lease() -> None:
    expected = owner.OwnerSpec(
        module_id=MODULE,
        steps=(
            owner.StepSpec(
                step_id=STEP,
                schema=cp4c.RestructuringSubmission,
                sources=True,
                extract=False,
                upstream_grant=None,
                inputs="module_context",
                rules="journaled",
            ),
        ),
        entry="owner_core",
        kind="analytical",
        publish=None,
    )
    assert owner.OWNER_SPECS[MODULE] == expected
    assert MODULE in owner.SUPPORTED_ANALYTICAL
    assert owner._CORES[MODULE] is cp4c
    assert owner._QUALIFICATION[MODULE] is cp4c.QUALIFICATION
    assert owner._PROBES[MODULE] is cp4c.probe
    assert owner._VIEWS[STEP] is cp4c.view
    assert owner._ENTRY_VALIDATORS[MODULE] is cp4c.ENTRY_VALIDATOR
    assert MODULE not in owner._PRECHECKS
    pack = _pack()
    held = tuple(s.source_id for s in pack.sources if s.source_id in CITED_SOURCES)
    assert host._OWNER_SCOPES[(MODULE, STEP)](pack) == held == CITED_SOURCES
    owner._check_steps(MODULE, owner.OWNER_SPECS[MODULE])


def test_registrations_are_appended_after_their_dependencies() -> None:
    """Append-only: the shipped prefix stands, and each CP-4C row comes after the rows of the
    owners it consumes (CP-2A, CP-4, CP-2G). Later appends are not this test's."""
    assert tuple(owner.OWNER_SPECS)[:5] == ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL")
    assert tuple(owner._QUALIFICATION)[:4] == ("CP-1", "CP-1A", "CP-2", "CP-MODEL")
    assert tuple(owner._PROBES)[:4] == ("CP-0", "CP-1", "CP-1A", "CP-2")
    assert tuple(owner._VIEWS)[:1] == ("credit_synthesis",)
    assert tuple(owner._ENTRY_VALIDATORS)[:2] == ("CP-1A", "CP-2")
    assert tuple(owner._CORES)[:2] == ("CP-DR", "CP-3D")
    producers = ("CP-2A", "CP-4", "CP-2G")
    for table, key, after in (
        (owner.OWNER_SPECS, MODULE, producers),
        (owner._QUALIFICATION, MODULE, producers),
        (owner._PROBES, MODULE, producers),
        (owner._ENTRY_VALIDATORS, MODULE, producers),
        (owner._CORES, MODULE, ("CP-2A", "CP-2G")),
        (owner._VIEWS, STEP, ("downside_pathway", "legal_covenants", "forward_credit_model")),
    ):
        order = list(table)
        assert all(order.index(key) > order.index(a) for a in after), (key, after)


def test_a_plan_with_cp4c_passes_check_specs(tmp_path: Path) -> None:
    for case in stage1.RUNS:
        planned = owner._check_specs(_pack(case), owner.OWNER_SPECS, None, tmp_path / case)
        assert list(planned) == EXPECTED["execution"]["plan_order"]


# --- bindings and the _Spec rows (lease D7) -------------------------------------------------------

BLOCKS = ("recovery-by-class", "value-allocation-claims")


def test_both_blocks_are_already_in_the_distressed_preset_once() -> None:
    blocks = next(b for pid, _, _, b in _PRESETS if pid == "distressed_restructuring")
    assert all(blocks.count(b) == 1 for b in BLOCKS)
    others = [b for pid, _, _, bs in _PRESETS if pid != "distressed_restructuring" for b in bs]
    assert not set(BLOCKS) & set(others)


def test_spec_rows_are_in_the_cp2a_composition() -> None:
    fp05 = EXPECTED["cases"]["positive"]["FP05"]["blocks"]
    for block in BLOCKS:
        spec = _spec_of(block)
        assert _DISTRESSED[block] is spec
        assert (spec.title, spec.owner, spec.kind, spec.producers, spec.route_label) == (
            fp05[block]["title"],
            fp05[block]["owner"],
            fp05[block]["kind"],
            (MODULE,),
            "Full analysis",
        )
    assert list(_DISTRESSED)[:2] == ["downside-stress", "break-points"]


def test_shipped_maps_hold_cp4c_once_after_its_producers() -> None:
    ids = [m.module_id for m in SHIPPED_MAPS]
    assert ids.count(MODULE) == 1
    assert ids.index(MODULE) > max(ids.index(m) for m in ("CP-2A", "CP-4", "CP-2G"))


def _view(pack: PreparedPack, module: Module) -> View:
    return View(
        run=pack.run,
        mode="accepted",
        modules=(
            ModuleView(
                module_id=MODULE,
                title="Restructuring fulcrum",
                aliases=(),
                status=module.status,
                artifact_sha256=module.content_hash(),
                facts=module.facts,
                tables=module.tables,
                claims=module.claims,
                limitations=module.limitations,
            ),
        ),
    )


@pytest.mark.parametrize("case", stage1.RUNS)
def test_bindings_place_every_expected_table_exactly_once(case: str, tmp_path: Path) -> None:
    store, pack, _, _ = settled(tmp_path, case)
    module = store.head_module(_head(store, MODULE))
    cp4c_map = next(m for m in SHIPPED_MAPS if m.module_id == MODULE)
    assert validate_bindings(_view(pack, module), (cp4c_map,)) == ()
    by_table = {e.fact_coord.table_id: e for e in cp4c_map.entries}
    assert len(by_table) == len(cp4c_map.entries)
    fp05 = EXPECTED["cases"][case]["FP05"]
    for block_id, block in fp05["blocks"].items():
        for tab in block["tabs"]:
            entry = by_table[tab["table_id"]]
            assert (entry.block_id, entry.label) == (block_id, tab["label"])
    evidence = [e.fact_coord.table_id for e in cp4c_map.entries if e.block_id == "evidence"]
    assert evidence == fp05["evidence_rail_tables"]
    for table in fp05["limitations_rail_tables"]:
        assert by_table[table].block_id == "limitations"
    placed = {t["table_id"] for b in fp05["blocks"].values() for t in b["tabs"]}
    rails = {*fp05["evidence_rail_tables"], *fp05["limitations_rail_tables"]}
    assert set(by_table) == placed | rails == {t.table_id for t in module.tables}
    assert all(e.cell_slot.startswith("cp4c-") for e in cp4c_map.entries)


@pytest.mark.parametrize("case", stage1.RUNS)
def test_fp05_cells_are_the_settled_spellings(case: str, tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, case)
    module = store.head_module(_head(store, MODULE))
    facts = {f.fact_id: f for f in module.facts}
    tables = {t.table_id: t for t in module.tables}
    for block in EXPECTED["cases"][case]["FP05"]["blocks"].values():
        for tab in block["tabs"]:
            table = tables[tab["table_id"]]
            assert [r.row_id for r in table.rows] == [r["row_id"] for r in tab["rows"]]
            for row, want in zip(table.rows, tab["rows"], strict=True):
                assert row.label == want["label"]
                assert list(row.fact_ids) == [c["fact_id"] for c in want["cells"]]
                for fid, cell in zip(row.fact_ids, want["cells"], strict=True):
                    _uc, state, text = fact_spelling(facts[fid], "G1")
                    assert (state, text.replace("G1", "G#")) == (cell["state"], cell["shown"])


# --- the readers (lease Public API) ----------------------------------------------------------------


@pytest.mark.parametrize("case", stage1.RUNS)
def test_cp4c_reader_exposes_ev_recoveries_and_the_fulcrum(case: str, tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, case)
    head = _head(store, MODULE)
    module = store.head_module(head)
    facts = {f.fact_id: f for f in module.facts}
    read = cp4c.cp4c_reader(store, head)
    assert (read.status, read.head_sha256) == ("restricted", head.result_sha256)
    assert read.limitations == module.limitations and read.limitations[-1] == SYNTHETIC
    assert list(read.limitations[:-1]) == EXPECTED["cases"][case]["own_limitations"]
    rows = {
        t["table_id"]: [r["row_id"] for r in t["rows"]] for t in EXPECTED["cases"][case]["tables"]
    }
    want = [
        *(f"T4E.3.{r}.ev" for r in rows["T4E.3"]),
        *(f"T4E.5.{r}.recovery" for r in rows["T4E.5"]),
        *(f"T4E.7.{r}.value_break" for r in rows["T4E.7"]),
    ]
    assert [f.fact_id for f in read.facts] == want
    assert all(f == facts[f.fact_id] for f in read.facts)
    waterfall = EXPECTED["cases"][case]["waterfall"]
    for v, w in waterfall.items():
        ev = read.fact(f"T4E.3.{v}.ev")
        assert stage1._norm(ev.amount) == w["ev"]
    with pytest.raises(ValueError, match="not exposed"):
        read.fact("T4E.1.u_cp1.module")


def test_cp4c_reader_follows_the_head_and_refuses_others(tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, cp1=cp1_facts(total_debt=DEBT))
    read = cp4c.cp4c_reader(store, _head(store, MODULE))
    assert read.fact("T4E.5.v02c02.recovery").amount == Decimal("10.62") / 30
    assert read.fact("T4E.3.v01.ev").amount == Decimal("123.6")
    with pytest.raises(ValueError, match="not a CP-4C head"):
        cp4c.cp4c_reader(store, _head(store, "CP-2G"))
    stale = _head(store, MODULE).model_copy(update={"status": "stale"})
    with pytest.raises(ValueError, match="CP-4C head is stale"):
        cp4c.cp4c_reader(store, stale)


def test_consumer_readers_read_the_cp2a_and_cp4_heads(tmp_path: Path) -> None:
    store, _, _ = seed(tmp_path)
    assert cp4c.cp2a_reader(store, _head(store, "CP-2A")) == stage1._cp2a("positive")
    assert cp4c.cp4_reader(store, _head(store, "CP-4")) == _cp4_read(stage1._cp4("positive"))
    with pytest.raises(ValueError, match="not a CP-2A head"):
        cp4c.cp2a_reader(store, _head(store, "CP-4"))
    with pytest.raises(ValueError, match="not a CP-4 head"):
        cp4c.cp4_reader(store, _head(store, "CP-2A"))


def test_cp2g_is_read_through_its_own_reader_and_selected_into_the_core_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rulings stage2 Q6: the adapter calls `owners.cp2g.cp2g_reader` and selects into
    `cp4c.Cp2gHead`; a blocked CP-2G read is refused."""
    store, _, attempt = seed(tmp_path)
    calls: list[str] = []
    real = cp2g.cp2g_reader

    def spy(executed: Execution, head: Head) -> cp2g.Cp2gHead:
        calls.append(head.result_sha256)
        return real(executed, head)

    monkeypatch.setattr(cp2g, "cp2g_reader", spy)
    got = _upstream(store, attempt).cp2g
    assert calls == [_head(store, "CP-2G").result_sha256]
    assert got == stage1._cp2g("positive")
    with pytest.raises(ValueError, match="CP-2G head is blocked"):
        cp4c.cp2g_of(cp2g.Cp2gHead(status="blocked", head_sha256="0" * 64))


# --- consumption (D3): CP-4C reads the settled CP-2G, CP-4 and CP-2A heads ----------------------


def test_d3_cp4c_consumes_the_genuine_cp2g_head_and_the_cp4_and_cp2a_heads(tmp_path: Path) -> None:
    """A6 (lease Consumption proof) over a store whose CP-2G head the real CP-2G core settled:
    (a) the attempt binds the final heads hash for hash in the oracle's input order; (b) each
    head's hash is the bound Input; (c) the copied cells equal the heads' own facts, the
    reference tables carry them verbatim, and the composer's lineage lists the CP-2G (two
    distinct T2H.4 EBITDA facts, the T2H.7.b01 first years), CP-2A (the row the CP-2G T2H.3
    source texts name) and CP-4 (facility, rating, conditions) facts it read."""
    store, pack, attempt = seed(tmp_path, genuine_cp2g=True)
    _submit(store, attempt, json.dumps(_payload()))
    heads = {h.module_id: h for h in store.read().heads}
    assert [i.input_id for i in attempt.inputs] == EXPECTED["execution"]["inputs"]
    for item in attempt.inputs[1:]:
        head = heads[item.input_id]
        assert (item.sha256, item.status) == (head.result_sha256, head.status)
    module = store.head_module(heads[MODULE])
    mine = {f.fact_id: f for f in module.facts}
    theirs = {
        m: {f.fact_id: f for f in store.head_module(heads[m]).facts}
        for m in ("CP-2G", "CP-2A", "CP-4")
    }
    read = cp2g.cp2g_reader(store, heads["CP-2G"])
    s = EXPECTED["cases"]["positive"]["cp2a_head"]["scenario"]
    assert read.fact("T2H.3.d01.source").text == f"CP-2A T2B.1.{s}.ebitda_decline"
    for v in _payload()["valuation"]:
        row = f"{'b' if v['ebitda_case'] == 'base' else 'd'}{v['ebitda_year'][-2:]}"
        fid = f"T2H.4.{row}.ebitda"
        assert mine[f"T4E.3.{v['case_id']}.ebitda"].amount == theirs["CP-2G"][fid].amount
    assert mine["T4E.3.v02.cp2a_scenario"].text == theirs["CP-2A"][f"T2B.1.{s}.name"].text
    decline = theirs["CP-2A"][f"T2B.1.{s}.ebitda_decline"]
    assert mine["T4E.3.v02.ebitda_decline"].amount == decline.amount
    for field, fid in (
        ("facility", "T4C.11.r01.facility"),
        ("lender_protection", "T4.13.rating.rating"),
        ("additional_debt", "T4.10.r02.conditions"),
    ):
        assert mine[f"T4E.2.c01.{field}"].text == theirs["CP-4"][fid].text
    coordinates = {"table_id", "row_id", "field"}
    for name, source in (
        ("cp2g_references", "CP-2G"),
        ("cp2a_references", "CP-2A"),
        ("cp4_references", "CP-4"),
    ):
        table = next(t for t in module.tables if t.table_id == name)
        assert table.rows
        for ref in table.rows:
            (fid,) = ref.fact_ids
            assert mine[fid].model_dump(exclude=coordinates) == theirs[source][fid].model_dump(
                exclude=coordinates
            )
    cells = cp4c.compute(cp4c._inputs(pack, _submission(), _upstream(store, attempt))).cells
    lineage = {c.fact.fact_id: c.derives_from for c in cells}
    ebitda = {d for v in ("v01", "v02", "v03") for d in lineage[f"T4E.3.{v}.ebitda"]}
    assert ebitda == {"cp2g:T2H.4.b26.ebitda", "cp2g:T2H.4.d26.ebitda"}
    assert lineage["T4E.3.v01.first_break"] == ("cp2g:T2H.7.b01.base_first",)
    assert lineage["T4E.3.v02.first_break"] == ("cp2g:T2H.7.b01.down_first",)
    assert lineage["T4E.3.v02.cp2a_scenario"] == (f"cp2a:T2B.1.{s}.name",)
    assert lineage["T4E.3.v02.ebitda_decline"] == (f"cp2a:T2B.1.{s}.ebitda_decline",)
    assert lineage["T4E.2.c01.facility"] == ("cp4:T4C.11.r01.facility",)
    assert lineage["T4E.2.c01.lender_protection"] == ("cp4:T4.13.rating.rating",)
    assert lineage["T4E.2.c01.additional_debt"] == ("cp4:T4.10.r02.conditions",)
