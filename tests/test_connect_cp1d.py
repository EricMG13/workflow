"""CP-1D Stage 2 connection, fast tests (docs/CP1D-OWNER-LEASE.md Public API, D7, D12).

Everything here runs over hand-built `Module` objects whose facts come from the frozen oracle
(`cases/cp1d-owner`); no store run, no CP-1 promotion. The store runs are in
`tests/test_owner_cp1d.py` (deferred to Stage 5). Fixtures vary the CP-1 amounts, the as-of date,
the CP-1B state and the pack so that a constant equal to the oracle cannot pass.
"""

import copy
import dataclasses
import datetime
import hashlib
import json
import re
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import cp1d_runs as runs
import pytest
import test_method_cp1d as stage1

from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Citation, Fact, Input, Module, ModuleView, Run, View
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    candidate_issues,
    settle,
    text_sha256,
)
from deploy_vii.live.tools import Seen, cited_locators
from deploy_vii.preparation import PreparedPack
from deploy_vii.report_view import _EARNINGS_QUALITY, Block, _spec_of, build, pathways
from deploy_workflow import host, owner_workflow
from deploy_workflow.owners import cp1d
from deploy_workflow.workflow import WorkflowError

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = stage1.EXPECTED
SUBMISSIONS = stage1.SUBMISSIONS
MANIFEST = stage1.MANIFEST
AS_OF = datetime.date(2026, 1, 10)
NAMES = tuple(cp1d._CP1_METRICS)
CASES = stage1.CASES


def _fact_id(name: str) -> str:
    return "interface-fact:" + hashlib.sha256(name.encode()).hexdigest()


def _cp1_module(
    scale: Decimal = Decimal(1),
    as_of: datetime.date = AS_OF,
    t417: int = 0,
    decimals: int | None = 2,
) -> Module:
    """A CP-1 head holding the seven T4.10 LTM Q4 25 facts (amounts times `scale`, leverage
    recomputed as CP-1 does), an FY25 decoy per metric and `t417` T4.17 rows. `decimals=None`
    shapes the facts as `model_interface` builds real CP-1 facts."""
    base = stage1._cp1()
    amounts = {f.figure: (f.amount or Decimal(0)) * scale for f in base.ordered()}
    amounts["total_leverage_adjusted"] = cp1d._quotient(
        amounts["total_debt_ltm"], amounts["adjusted_ebitda_ltm"]
    )
    amounts["net_leverage_adjusted"] = cp1d._quotient(
        amounts["net_debt_ltm"], amounts["adjusted_ebitda_ltm"]
    )
    facts: list[Fact] = []
    for f in base.ordered():
        facts.append(
            Fact(
                fact_id=_fact_id(f.figure),
                label=f.label,
                table_id="T4.10",
                row_id=f.figure,
                field="value",
                amount=amounts[f.figure],
                unit=f.unit,
                currency=f.currency,
                period=f.period,
                value_class=f.value_class,
                calculation_id="calc:" + f.figure,
                scale=Decimal(1000000) if f.unit == "MILLIONS" else Decimal(1),
                decimals=decimals,
            )
        )
        facts.append(  # the FY25 decoy: same label, other period (never selected)
            facts[-1].model_copy(
                update={
                    "fact_id": _fact_id("fy25" + f.figure),
                    "period": "FY25: 2025-01-01 to 2025-12-31",
                    "amount": amounts[f.figure] + 1,
                }
            )
        )
    facts += [
        Fact(
            fact_id=f"t417-{n}",
            label=f"Add-back {n}",
            table_id="T4.17",
            row_id=f"r{n}",
            field="value",
            text="x",
        )
        for n in range(t417)
    ]
    return Module(
        run_id="cp1d-owner-positive",
        issuer_id="northbridge-synthetic",
        as_of=as_of,
        module_id="CP-1",
        status="restricted",
        facts=tuple(facts),
        limitations=("CP-1 note",),
    )


def _cp0_module(as_of: datetime.date = AS_OF) -> Module:
    return Module(
        run_id="cp1d-owner-positive",
        issuer_id="northbridge-synthetic",
        as_of=as_of,
        module_id="CP-0",
        status="restricted",
        limitations=("CP-0 note",),
    )


def _run(case: str) -> Run:
    return Run.model_validate_json(json.dumps(MANIFEST["cases"][case]["run"]))


def _pack(case: str) -> PreparedPack:
    run_case = case if case in MANIFEST["cases"] else "positive"
    return PreparedPack(run=_run(run_case), sources=stage1._pack_sources(case))


def _upstream(
    cp1: Module | None = None, *, cp1b: str | None = None, inherited: tuple[str, ...] = ()
) -> cp1d.Upstream:
    cp1 = _cp1_module() if cp1 is None else cp1
    cp0 = _cp0_module()
    bound = [
        Input(input_id="CP-0", sha256=cp0.content_hash(), status="restricted"),
        Input(input_id="CP-1", sha256=cp1.content_hash(), status="restricted"),
    ]
    head1b: Module | None = None
    if cp1b is not None:
        blocked = cp1b == "blocked"
        head1b = Module(
            run_id="cp1d-owner-positive",
            issuer_id="northbridge-synthetic",
            as_of=AS_OF,
            module_id="CP-1B",
            status="blocked" if blocked else "accepted",
            limitations=("Earnings update source missing",) if blocked else (),
        )
        bound.append(
            Input(
                input_id="CP-1B",
                sha256=head1b.content_hash(),
                status="blocked" if blocked else "accepted",
            )
        )
    inputs = tuple(bound)
    return cp1d.Upstream(
        bound=inputs, current=inputs, cp0=cp0, cp1=cp1, cp1b=head1b, inherited=inherited
    )


def _bind_figures(text: str, cp1: Module) -> str:
    ids = {
        f.row_id: f.fact_id
        for f in cp1.facts
        if f.table_id == "T4.10" and f.period == cp1d._CP1_PERIOD
    }

    def replace(match: re.Match[str]) -> str:
        return "{" + ids[match[1]] + "|" + match[2] + "}"

    return re.sub(r"\{\{FIG:([a-z_]+)\|([^}]+)\}\}", replace, text)


def _submission(case: str, cp1: Module | None = None) -> cp1d.EarningsQualitySubmission:
    text = json.dumps(SUBMISSIONS[case]["earnings_quality"])
    return cp1d.EarningsQualitySubmission.model_validate_json(
        _bind_figures(text, _cp1_module() if cp1 is None else cp1)
    )


def _fp02(case: str) -> dict[str, Block]:
    """FP02 (`report_view.build`, earnings_update, the shipped maps) over the CP-1D module built
    from the case's literal; every other shipped module is unrun."""
    pack, upstream = _pack(case), _upstream()
    report = cp1d.earnings_quality(pack=pack, submission=_submission(case), upstream=upstream)
    module = cp1d.cp1d_module(report, inputs=upstream.bound, attempt=0)
    view = View(
        run=pack.run,
        mode="accepted",
        modules=(
            ModuleView(
                module_id="CP-1D",
                title="Earnings quality",
                aliases=("CP-1E",),
                status=EXPECTED["cases"][case]["module_status"],
                artifact_sha256="a" * 64,
                facts=module.facts,
                tables=module.tables,
                claims=module.claims,
                limitations=module.limitations,
            ),
            *(
                ModuleView(module_id=m.module_id, title=m.module_id, aliases=(), status="unrun")
                for m in SHIPPED_MAPS
                if m.module_id != "CP-1D"
            ),
        ),
    )
    pathway = next(p for p in pathways() if p.id == "earnings_update")
    return {b.block_id: b for b in build(view, pathway, SHIPPED_MAPS).blocks}


# --- registrations equal the lease ---------------------------------------------------------------


def test_registration_rows_equal_the_lease() -> None:
    spec = owner_workflow.OWNER_SPECS["CP-1D"]
    assert (spec.module_id, spec.entry, spec.kind, spec.publish) == (
        "CP-1D",
        "owner_core",
        "analytical",
        None,
    )
    (step,) = spec.steps
    assert (step.step_id, step.schema, step.sources, step.extract, step.upstream_grant) == (
        "earnings_quality",
        cp1d.EarningsQualitySubmission,
        True,
        False,
        None,
    )
    assert (step.inputs, step.rules) == ("module_context", "journaled")
    assert "CP-1D" in owner_workflow.SUPPORTED_ANALYTICAL
    assert owner_workflow._CORES["CP-1D"] is cp1d
    assert owner_workflow._QUALIFICATION["CP-1D"] == cp1d.QUALIFICATION
    assert owner_workflow._PROBES["CP-1D"] is cp1d.probe
    assert owner_workflow._VIEWS["earnings_quality"] is cp1d.view
    assert owner_workflow._ENTRY_VALIDATORS["CP-1D"] is cp1d.ENTRY_VALIDATOR
    assert "CP-1D" not in owner_workflow._PRECHECKS  # the lease names no precheck
    assert (cp1d.MODULE_ID, cp1d.STEP_ID, cp1d.STEP_IDS) == (
        "CP-1D",
        "earnings_quality",
        ("earnings_quality",),
    )
    owner_workflow._check_steps("CP-1D", spec)


def test_sources_flag_matches_the_h1_owner_scope_row() -> None:
    """G1-X guard: `sources` agrees with whether `_OWNER_SCOPES` has the CP-1D row."""
    assert ("CP-1D", "earnings_quality") in host._OWNER_SCOPES
    assert owner_workflow.OWNER_SPECS["CP-1D"].steps[0].sources is True
    for case in CASES:
        pack = _pack(case)
        scoped = host._OWNER_SCOPES[("CP-1D", "earnings_quality")](pack)
        assert scoped == tuple(s.source_id for s in pack.sources if s.source_id in cp1d.SCOPE)
    wrong = dataclasses.replace(owner_workflow.OWNER_SPECS["CP-1D"].steps[0], sources=False)
    bad = dataclasses.replace(owner_workflow.OWNER_SPECS["CP-1D"], steps=(wrong,))
    with pytest.raises(WorkflowError):
        owner_workflow._check_steps("CP-1D", bad)


def test_registrations_are_appended_at_the_end() -> None:
    """Brief section 3 (review L4): every CP-1D row follows the base rows and the CP-L10 row merged
    before it, `OWNER_SPECS` included. Later modules append after CP-1D, so no last key is pinned."""
    for rows, base in (
        (owner_workflow.OWNER_SPECS, ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL"]),
        (owner_workflow._QUALIFICATION, ["CP-1", "CP-1A", "CP-2", "CP-MODEL"]),
        (owner_workflow._PROBES, ["CP-0", "CP-1", "CP-1A", "CP-2"]),
        (owner_workflow._ENTRY_VALIDATORS, ["CP-1A", "CP-2"]),
        (owner_workflow._CORES, []),
    ):
        keys = list(rows)
        assert keys[: len(base)] == base
        assert keys.index("CP-1D") > keys.index("CP-L10")
    views = list(owner_workflow._VIEWS)
    assert views[0] == "credit_synthesis"
    assert views.index("earnings_quality") > views.index("change_screen")
    ids = [m.module_id for m in SHIPPED_MAPS]
    base = ["CP-0", "CP-1", "CP-1B", "CP-MODEL", "CP-1A", "CP-2"]
    assert ids[: len(base)] == base
    assert "CP-1D" in ids[len(base) :]
    assert ids.index("CP-1D") > ids.index("CP-6")


def test_report_view_composition_and_spec_of() -> None:
    """The `_Spec` heads are the oracle's FP02 heads (lease A1: FP02 equal expected)."""
    assert set(_EARNINGS_QUALITY) == {"earnings-quality", "restated-leverage"}
    for case in CASES:
        oracle = EXPECTED["cases"][case]["FP02"]["blocks"]
        assert set(oracle) == set(_EARNINGS_QUALITY)
        for block, want in oracle.items():
            spec = _spec_of(block)
            assert (spec.title, spec.owner, spec.kind, spec.producers, spec.route_label) == (
                want["title"],
                want["owner"],
                want["kind"],
                ("CP-1D",),
                "Full analysis",
            )
    blocks = next(p for p in pathways() if p.id == "earnings_update").blocks
    at = blocks.index("ebitda-adjustments")
    assert blocks[at + 1 : at + 3] == ("earnings-quality", "restated-leverage")


@pytest.mark.parametrize("case", CASES)
def test_fp02_block_titles_and_tab_labels_equal_the_oracle(case: str) -> None:
    """Review M2: the rendered FP02 heads, the binding labels and the rendered tab labels equal
    `expected.json cases.<case>.FP02`. A one-table block renders no tab strip, so its one oracle
    tab label is the binding label of its one table."""
    blocks = _fp02(case)
    entries = next(m for m in SHIPPED_MAPS if m.module_id == "CP-1D").entries
    for block_id, want in EXPECTED["cases"][case]["FP02"]["blocks"].items():
        block = blocks[block_id]
        assert (block.title, block.owner, block.kind, block.state) == (
            want["title"],
            want["owner"],
            want["kind"],
            want["state"],
        )
        tabs = [(t["table_id"], t["label"]) for t in want["tabs"]]
        assert [(e.fact_coord.table_id, e.label) for e in entries if e.block_id == block_id] == tabs
        if len(tabs) == 1:
            assert block.tab_label is None and block.tabs == ()
        else:
            assert [block.tab_label, *(t.label for t in block.tabs)] == [t[1] for t in tabs]


@pytest.mark.parametrize("case", CASES)
def test_schemas_round_trip_and_tail_digest_on_the_oracle_literals(case: str) -> None:
    assert cp1d.SCHEMAS == {"earnings_quality": cp1d.EarningsQualitySubmission}
    text = json.dumps(SUBMISSIONS[case]["earnings_quality"])
    parsed = cp1d.SCHEMAS["earnings_quality"].model_validate_json(text)
    again = cp1d.SCHEMAS["earnings_quality"].model_validate_json(parsed.model_dump_json())
    assert again == parsed and again.content_hash() == parsed.content_hash()
    upstream = _upstream()
    report = cp1d.earnings_quality(
        pack=_pack(case), submission=_submission(case), upstream=upstream
    )
    module = cp1d.cp1d_module(report, inputs=upstream.bound, attempt=0)
    tail = module.inputs[len(upstream.bound) :]
    assert [i.input_id for i in tail] == ["earnings-quality-submission"]
    assert tail[0].sha256 == _submission(case).content_hash()


# --- the store adapter ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("state", [None, "settled", "blocked"])
def test_adapter_returns_the_stage_1_input_object(case: str, state: str | None) -> None:
    """The adapter's object equals the Stage 1 test's, but for the CP-1 fact ids (real ones
    here, `cp1:<figure>` in Stage 1)."""
    upstream = _upstream(cp1b=state)
    mine, facts = cp1d._inputs(_pack(case), _submission(case), upstream)
    theirs = stage1._inputs(case, SUBMISSIONS[case]["earnings_quality"], cp1b=upstream.cp1b_state)
    assert [dataclasses.replace(f, fact_id="") for f in mine.cp1.ordered()] == [
        dataclasses.replace(f, fact_id="") for f in theirs.cp1.ordered()
    ]
    assert mine.sources == theirs.sources
    assert (
        mine.cp1b
        == theirs.cp1b
        == {None: "unbound", "settled": "settled", "blocked": "blocked"}[state]
    )
    assert {n: f.fact_id for n, f in facts.items()} == {n: _fact_id(n) for n in NAMES}
    assert [f.fact_id for f in mine.cp1.ordered()] == [_fact_id(n) for n in NAMES]


def test_adapter_keeps_only_the_scoped_sources() -> None:
    """A pack source outside the fixed H1 scope (here `business`) never reaches the core."""
    pack = _pack("positive")
    extra = pack.sources[0].model_copy(update={"source_id": "business", "name": "Business note"})
    wide = PreparedPack(run=pack.run, sources=(*pack.sources, extra))
    mine, _ = cp1d._inputs(wide, _submission("positive"), _upstream())
    assert [s.source_id for s in mine.sources] == ["identity", "financial", "bridge"]


def test_adapter_reads_the_cp1_head_not_a_constant() -> None:
    cp1 = _cp1_module(Decimal(3))
    mine, _ = cp1d._inputs(_pack("positive"), _submission("positive"), _upstream(cp1))
    assert mine.cp1.ebitda.amount == Decimal(90)
    assert mine.cp1.cfo.amount == Decimal(57)
    assert mine.cp1.total_leverage.amount == cp1d._quotient(Decimal(150), Decimal(90))


def test_adapter_refuses_a_cp1_head_without_exactly_one_selected_fact() -> None:
    cp1 = _cp1_module()
    missing = cp1.model_copy(update={"facts": tuple(f for f in cp1.facts if f.row_id != "cfo_ltm")})
    twin = cp1.facts[0].model_copy(update={"fact_id": "dup-1"})
    double = cp1.model_copy(update={"facts": (*cp1.facts, twin)})
    for head in (missing, double):
        issues = cp1d.validate_earnings_quality(
            pack=_pack("positive"), submission=_submission("positive"), upstream=_upstream(head)
        )
        assert len(issues) == 1 and issues[0].startswith("CP-1 operands unavailable: CP-1 T4.10 ")


# --- RULES, validator and refusals ---------------------------------------------------------------


def test_rules_reproduce_the_tool_refusal_and_only_that() -> None:
    payload = json.dumps(SUBMISSIONS["positive"]["earnings_quality"])
    refusal = next(t for t in EXPECTED["tool_refusals"] if t["id"] == "t01")
    want = tuple(refusal["expected_issues"])
    assert cp1d.RULES(payload, Seen()) == want
    assert cp1d.RULES(payload, Seen(read=frozenset({("bridge", "page:2")}))) == ()
    assert cp1d.RULES(payload, Seen(read=frozenset({("bridge", "page:1")}))) == want
    assert cp1d.RULES("[1,", Seen()) == ()  # never raises on malformed model text


@pytest.mark.parametrize("index", range(19))
def test_validator_reproduces_the_oracle_refusals(index: int) -> None:
    literal = SUBMISSIONS["refusals"][index]
    refusal = EXPECTED["refusals"][index]
    assert literal["id"] == refusal["id"]
    submission = cp1d.EarningsQualitySubmission.model_validate_json(
        _bind_figures(json.dumps(literal["payload"]), _cp1_module())
    )
    issues = cp1d.validate_earnings_quality(
        pack=_pack(literal["pack"]), submission=submission, upstream=_upstream()
    )
    want = refusal["expected_issues"]
    assert len(issues) == len(want)
    for got, expected in zip(issues, want, strict=True):
        assert got == expected or (expected.endswith(" (") and got.startswith(expected))


def test_validator_flags_unreplaced_figures_stale_and_swapped_inputs() -> None:
    raw = cp1d.EarningsQualitySubmission.model_validate_json(
        json.dumps(SUBMISSIONS["positive"]["earnings_quality"])
    )
    pack, good = _pack("positive"), _submission("positive")
    assert cp1d.validate_earnings_quality(pack=pack, submission=raw, upstream=_upstream()) == (
        "overall.rationale: Value error, Malformed run text: unbalanced or empty reference",
    )
    up = _upstream()
    stale = dataclasses.replace(up, current=(up.bound[0],))
    found = cp1d.validate_earnings_quality(pack=pack, submission=good, upstream=stale)
    assert found and all(i.startswith("Stale input") for i in found)
    refused = dataclasses.replace(up, current="CP-0 has not authorized this consumer")
    assert cp1d.validate_earnings_quality(pack=pack, submission=good, upstream=refused) == (
        "Stale inputs: CP-0 has not authorized this consumer",
    )
    swapped = dataclasses.replace(up, cp1=_cp1_module(Decimal(2)))
    assert cp1d.validate_earnings_quality(pack=pack, submission=good, upstream=swapped) == (
        "Upstream CP-1: the supplied module is not the bound input",
    )


def test_overall_reference_to_an_unknown_fact_is_an_issue_not_a_raise() -> None:
    payload = copy.deepcopy(SUBMISSIONS["positive"]["earnings_quality"])
    payload["overall"]["rationale"] = "Leverage is {interface-fact:nope|x} on the statements."
    submission = cp1d.EarningsQualitySubmission.model_validate_json(json.dumps(payload))
    issues = cp1d.validate_earnings_quality(
        pack=_pack("positive"), submission=submission, upstream=_upstream()
    )
    assert issues and all("interface-fact:nope" in i for i in issues)


def test_caller_text_that_the_product_would_refuse_is_an_issue_before_composition() -> None:
    """Model text is checked with the type the step later builds, so nothing raises after the
    binding write (rulings Stage 2 round 3)."""
    payload = copy.deepcopy(SUBMISSIONS["positive"]["earnings_quality"])
    payload["assessments"][1]["rationale"] = "The saving of {broken is not achievable."
    submission = cp1d.EarningsQualitySubmission.model_validate_json(json.dumps(payload))
    issues = cp1d.validate_earnings_quality(
        pack=_pack("positive"), submission=submission, upstream=_upstream()
    )
    assert issues and all("{broken" not in i for i in issues)  # the input is not echoed
    direct = [i for i in cp1d._model_text_issues(submission) if i.startswith("assessments[")]
    assert len(direct) == 1 and direct[0].startswith("assessments[1].rationale: ")
    assert "{broken" not in direct[0]


# --- the composed report and the module ----------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_report_facts_tables_claims_limitations_equal_the_oracle(case: str) -> None:
    want = EXPECTED["cases"][case]
    report = cp1d.earnings_quality(
        pack=_pack(case), submission=_submission(case), upstream=_upstream()
    )
    by_id = {f.fact_id: f for f in report.facts}
    for fact in want["facts"]:
        mine = by_id[fact["fact_id"]]
        raw = fact.get("amount_exact")
        expected_amount = None if raw is None else Decimal(raw)
        assert mine.amount == expected_amount
        assert (mine.status, mine.table_id, mine.row_id, mine.field) == (
            fact["status"],
            fact["table_id"],
            fact["row_id"],
            fact["field"],
        )
    assert {f.fact_id for f in report.facts if f.table_id.startswith("T1D.")} == {
        f["fact_id"] for f in want["facts"]
    }
    assert [t.table_id for t in report.tables] == [t["table_id"] for t in want["tables"]] + [
        "cp1_references"
    ]
    for table in want["tables"]:
        mine_t = next(t for t in report.tables if t.table_id == table["table_id"])
        assert [r.row_id for r in mine_t.rows] == [r["row_id"] for r in table["rows"]]
        assert [r.fact_ids for r in mine_t.rows] == [tuple(r["fact_ids"]) for r in table["rows"]]
    claims = {c.claim_id: c for c in report.claims}
    assert list(claims) == [c["claim_id"] for c in want["claims"]]
    for claim in want["claims"]:
        mine_c = claims[claim["claim_id"]]
        assert mine_c.text == _bind_figures(claim["text"], _cp1_module())
        assert mine_c.limitation == claim["limitation"]
        assert [c.quote for c in mine_c.citations] == [
            e["quote"] for e in claim.get("evidence", [])
        ]
    assert list(report.limitations) == want["own_limitations"]
    refs = [f for f in report.facts if f.table_id == "cp1_references"]
    assert [f.row_id for f in refs] == [r["row_id"] for r in want["cp1_references"]]
    assert [f.amount for f in refs] == [Decimal(r["amount_exact"]) for r in want["cp1_references"]]


@pytest.mark.parametrize("case", CASES)
def test_module_passes_the_product_candidate_checks_and_settles_the_oracle_limitations(
    case: str,
) -> None:
    """A head built by `settle` over the real candidate: candidate_issues (identity, bound
    inputs, citations against the pack, every claim resolving against the module's facts) is
    empty; own limitations are the oracle list then the synthetic line."""
    cp1 = _cp1_module(Decimal("1.5"))
    upstream = _upstream(cp1)
    pack = _pack(case)
    report = cp1d.earnings_quality(pack=pack, submission=_submission(case, cp1), upstream=upstream)
    candidate = cp1d.cp1d_module(report, inputs=upstream.bound, attempt=0)
    payload = candidate.model_dump_json()
    attempt = Attempt(
        ticket_id="t1",
        module_id="CP-1D",
        inputs=upstream.bound,
        number=0,
        payload_sha256=text_sha256(payload),
    )
    snapshot = ExecutionSnapshot(run=pack.run, pack_sha256=pack.content_hash(), attempts=(attempt,))
    assert candidate_issues(snapshot, attempt, candidate, pack=pack) == ()
    finished, head = settle(
        snapshot,
        attempt,
        payload,
        lambda supplied: () if supplied == candidate else ("Candidate differs",),
        pack=pack,
        load=lambda _head: candidate,
    )
    assert finished.issues == ()
    assert head.status == EXPECTED["cases"][case]["module_status"]
    own = EXPECTED["cases"][case]["own_limitations"]
    assert list(head.limitations) == [*own, "Synthetic case; not real issuer qualification"]
    if case == "positive":
        assert list(head.limitations) == EXPECTED["cases"][case]["settled_limitations"]


def test_amounts_follow_the_cp1_head() -> None:
    """Leverage restates on the head's own debt and EBITDA (a constant cannot pass)."""
    for scale in (Decimal(1), Decimal(2), Decimal("1.5")):
        cp1 = _cp1_module(scale)
        report = cp1d.earnings_quality(
            pack=_pack("statements_only"),
            submission=_submission("statements_only", cp1),
            upstream=_upstream(cp1),
        )
        stmt = next(f for f in report.facts if f.fact_id == "T1D.6.statements.total_leverage")
        assert stmt.amount == cp1d._quotient(Decimal(50) * scale, Decimal(30) * scale)
        start = next(f for f in report.facts if f.fact_id == "T1D.3.start.value")
        assert start.amount == Decimal(30) * scale


@pytest.mark.parametrize("state", [None, "settled", "blocked"])
def test_cp1b_own_limitation_follows_the_bound_state(state: str | None) -> None:
    report = cp1d.earnings_quality(
        pack=_pack("positive"), submission=_submission("positive"), upstream=_upstream(cp1b=state)
    )
    wording = EXPECTED["cp1b"]["limitation_wordings"]
    line = wording["unbound"] if state is None else wording["bound_settled"]
    assert line in report.limitations
    assert not ({wording["unbound"], wording["bound_settled"]} - {line}) & set(report.limitations)


def test_derived_fact_citations_are_one_per_page_first_quote() -> None:
    page1 = Citation(source_id="bridge", source_sha256="a" * 64, locator="page:1", quote="first")
    again = page1.model_copy(update={"quote": "second"})
    page2 = page1.model_copy(update={"locator": "page:2", "quote": "other"})
    last = page1.model_copy(update={"quote": "last"})
    assert cp1d._one_per_page([page1, page2, again, last]) == (page1, page2)
    assert cp1d._one_per_page([]) == ()
    cell = cp1d.CellFact(
        "T1D.3.x.value",
        "T1D.3",
        "x",
        "value",
        "Value",
        "known",
        unit="MILLIONS",
        period="LTM Q4 25: 2025-01-01 to 2025-12-31",
        amount=Decimal(1),
        value_class="calculated",
        citations=(page1, again, page2),
    )
    assert cp1d._module_fact(cell).citations == (page1, page2)
    sourced = dataclasses.replace(cell, value_class="source")
    assert cp1d._module_fact(sourced).citations == (page1, again, page2)  # its own field


# --- the view -------------------------------------------------------------------------------------


def _walk_strings(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, Mapping):
        return [s for v in node.values() for s in _walk_strings(v)]
    if isinstance(node, list):
        return [s for v in node for s in _walk_strings(v)]
    return []


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("t417", [0, 3])
def test_view_matches_the_lease_key_tree_and_holds_no_quote(case: str, t417: int) -> None:
    upstream = _upstream(_cp1_module(t417=t417), inherited=("An inherited line",))
    block = cp1d.context_block(pack=_pack(case), upstream=upstream)
    assert set(block) == {
        "upstream",
        "bridge",
        "cp1_facts",
        "cp1_t417_rows",
        "cp1_facts_note",
        "inherited_limitations",
    }
    assert block["upstream"] == [
        {"module_id": "CP-0", "status": "restricted"},
        {"module_id": "CP-1", "status": "restricted"},
    ]
    assert block["cp1_t417_rows"] == t417
    assert block["inherited_limitations"] == ["An inherited line"]
    facts = block["cp1_facts"]
    assert isinstance(facts, list) and len(facts) == 7
    assert all(set(f) == {"ref", "label", "period", "unit", "shown"} for f in facts)
    assert [f["ref"] for f in facts] == [_fact_id(n) for n in NAMES]
    bridge = block["bridge"]
    assert isinstance(bridge, dict)
    assert set(bridge) == {"state", "source_id", "pages", "items", "totals"}
    if case == "statements_only":
        assert bridge["state"] == "absent" and bridge["items"] == [] and bridge["totals"] is None
    else:
        assert bridge["state"] == "present" and bridge["source_id"] == "bridge"
        assert [i["label"] for i in bridge["items"]] == [
            "Procurement programme savings",
            "Head-office reorganisation savings",
            "Legal and advisory fees",
            "Insurance and facilities savings",
        ]
        assert all(
            set(i) == {"row", "label", "type", "status", "claimed_ref", "claimed_shown"}
            for i in bridge["items"]
        )
    # no quote: no string of the view is a long span of any source page
    pages = [s.text for src in _pack(case).sources for s in src.spans]
    for text in _walk_strings(block):
        assert not (len(text) > 40 and any(text in page for page in pages)), text


VIEW_TREE = ROOT / "cases" / "cp1d-owner" / "cp1d-view-tree.json"


def _shape(node: object) -> object:
    """The key tree of a view value: scalars by type name, a list by its first element's shape
    (an empty list stays empty), no value."""
    if isinstance(node, Mapping):
        return {key: _shape(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_shape(node[0])] if node else []
    return "null" if node is None else type(node).__name__


def view_tree_of(case: str) -> dict[str, object]:
    """The committed tree of one case: `context_block` over the fixture heads with 3 T4.17 rows."""
    upstream = _upstream(_cp1_module(t417=3), inherited=("An inherited line",))
    block = cp1d.context_block(pack=_pack(case), upstream=upstream)
    return {"top_level_keys": list(block), "tree": _shape(block)}


@pytest.mark.parametrize("case", CASES)
def test_the_committed_view_tree_is_the_views_key_tree(case: str) -> None:
    """`cases/cp1d-owner/cp1d-view-tree.json` (lease Tool use) holds the shape of the view of
    each case and no value, so a change of key, nesting or type shows here."""
    committed = json.loads(VIEW_TREE.read_text(encoding="utf-8"))
    assert committed[case] == view_tree_of(case)
    assert not any(len(s) > 40 for s in _walk_strings(committed[case]["tree"]))


def test_view_body_is_compact_json_and_the_hash_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    upstream = _upstream()

    class Store:
        def pack(self) -> PreparedPack:
            return _pack("positive")

    monkeypatch.setattr(cp1d, "cp1d_upstream", lambda _store, _attempt: upstream)
    digest, body = cp1d.view(cast(Execution, Store()), cast(Attempt, None))
    assert hashlib.sha256(body.encode()).hexdigest() == digest
    assert body == json.dumps(json.loads(body), ensure_ascii=False, separators=(",", ":"))


def test_view_upstream_lists_each_bound_status_not_a_constant() -> None:
    """The view reports the status each bound head carries (CP-0, CP-1, CP-1B), in bound order."""
    upstream = _upstream(cp1b="blocked")
    bound = tuple(
        item.model_copy(update={"status": status})
        for item, status in zip(upstream.bound, ("accepted", "restricted", "blocked"), strict=True)
    )
    block = cp1d.context_block(
        pack=_pack("positive"), upstream=dataclasses.replace(upstream, bound=bound)
    )
    assert block["upstream"] == [
        {"module_id": "CP-0", "status": "accepted"},
        {"module_id": "CP-1", "status": "restricted"},
        {"module_id": "CP-1B", "status": "blocked"},
    ]


def test_view_lists_only_the_known_cp1_facts() -> None:
    """A CP-1 figure that is not known has no spelling a `{ref|unit}` may name; it is not listed."""
    cp1 = _cp1_module()
    target = next(
        f for f in cp1.facts if f.row_id == "total_debt_ltm" and f.period == cp1d._CP1_PERIOD
    )
    gap = Fact.model_validate(
        {
            **target.model_dump(),
            "status": "missing",
            "amount": None,
            "text": None,
            "limitation": "Total debt not disclosed",
        }
    )
    cp1 = cp1.model_copy(update={"facts": tuple(gap if f is target else f for f in cp1.facts)})
    block = cp1d.context_block(pack=_pack("positive"), upstream=_upstream(cp1))
    facts = block["cp1_facts"]
    assert isinstance(facts, list)
    listed = [f["ref"] for f in facts]
    assert target.fact_id not in listed and len(listed) == 6


def test_upstream_current_is_the_stores_current_input_set_not_the_bound_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, ticket = _settled_store(tmp_path, "positive")
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket)
    moved = (Input(input_id="CP-0", sha256="f" * 64, status="accepted"),)
    asked: list[tuple[str, str]] = []

    def current(snapshot: ExecutionSnapshot, module_id: str) -> tuple[Input, ...]:
        asked.append((snapshot.content_hash(), module_id))
        return moved

    monkeypatch.setattr(cp1d, "current_inputs", current)
    upstream = cp1d.cp1d_upstream(store, attempt)
    assert upstream.current == moved != attempt.inputs
    assert upstream.bound == attempt.inputs
    assert asked == [(store.read().content_hash(), "CP-1D")]


# --- bindings -------------------------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_validate_bindings_over_the_expected_tables_is_empty(case: str) -> None:
    pack = _pack(case)
    upstream = _upstream()
    report = cp1d.earnings_quality(pack=pack, submission=_submission(case), upstream=upstream)
    module = cp1d.cp1d_module(report, inputs=upstream.bound, attempt=0)
    view = View(
        run=pack.run,
        mode="candidate",
        modules=(
            ModuleView(
                module_id="CP-1D",
                title="Earnings quality",
                aliases=("CP-1E",),
                status="restricted",
                artifact_sha256="a" * 64,
                facts=module.facts,
                tables=module.tables,
                claims=module.claims,
                limitations=module.limitations,
            ),
        ),
    )
    assert validate_bindings(view, SHIPPED_MAPS) == ()
    entries = next(m for m in SHIPPED_MAPS if m.module_id == "CP-1D").entries
    assert {e.block_id for e in entries} == {
        "earnings-quality",
        "restated-leverage",
        "evidence",
        "limitations",
    }
    assert {e.fact_coord.table_id for e in entries if e.block_id == "earnings-quality"} == {
        "T1D.2",
        "T1D.3",
        "T1D.5",
    }
    assert {e.fact_coord.table_id for e in entries if e.block_id == "restated-leverage"} == {
        "T1D.6"
    }
    assert len({e.slot for e in entries}) == len(entries)


def test_no_reader_is_named_by_the_lease() -> None:
    """Rulings Q6: a reader goes where the lease's Public API puts it. CP-1D's names none (D3 is
    open until CP-2G reads the head), so none is built here."""
    lease = (ROOT / "docs" / "CP1D-OWNER-LEASE.md").read_text()
    api = lease[lease.index("## Public API") : lease.index("## Submission schema")]
    assert "reader" not in api.lower()
    assert not hasattr(cp1d, "cp1d_reader")


# --- guard-limit notes hold (methods/cp1d.md) ---------------------------------------------------


@pytest.mark.parametrize(
    ("line", "amounts"),
    [("Saving of 95 - 96 in range.", ["95", "-96"]), ("- 1.80 bullet item", ["-1.80"])],
)
def test_rule_w_cost_noted_in_the_method(line: str, amounts: list[str]) -> None:
    inputs = stage1._a01_on_page1(line)
    accepted = inputs.submission.assessments[0].accepted_basis
    assert accepted is not None
    assert cp1d._basis_amounts(accepted, inputs.sources) == amounts
    assert cp1d.validation_issues(inputs)  # refused, never composed


@pytest.mark.parametrize(
    "line",
    [
        "Saving 1,250 total.",
        "Saving 1,5 decimal comma.",
        "Items 1, 2, 3 listed.",
        "Since 2025, 1.80 saving.",
        "Published January 10, 2026 saving 1.80",
        "The FY25 saving.",
        "The 2nd saving.",
        "A saving of ½.",
    ],
)
def test_comma_identifier_ordinal_costs_noted_in_the_method(line: str) -> None:
    assert cp1d._one_whole_run(line) is False


@pytest.mark.parametrize("line", ["A saving of 2.5m.", "A saving of 25bps.", "The 2nds saving."])
def test_letter_after_a_run_is_still_read(line: str) -> None:
    assert cp1d._one_whole_run(line) is True


@pytest.mark.parametrize(
    "line", ["Savings of 1.5-Q are signed.", "Savings of 1.5-\nnd are signed."]
)
def test_round_5_item_12_readings_noted_in_the_method(line: str) -> None:
    """Rulings round 5 item 12: the right side of a run never makes an identifier, and a decimal
    run is never an ordinal, so `1.5-Q` and a wrapped `1.5-` then `nd` read 1.5 and compose."""
    inputs = stage1._a01_on_page1(line)
    accepted = inputs.submission.assessments[0].accepted_basis
    assert accepted is not None
    assert cp1d._one_whole_run(line) is True
    assert cp1d._basis_amounts(accepted, inputs.sources) == ["1.5"]
    assert cp1d.validation_issues(inputs) == ()


def test_method_note_exists_and_names_each_limit() -> None:
    text = (ROOT / "src" / "deploy_vii" / "methods" / "cp1d.md").read_text()
    for needle in (
        "Rule W",
        "Item 8 comma costs",
        "Addendum 5",
        "Round 5 item 12",
        "`1.5-Q`",
        "Source quotes",
        "one `Citation` per (source, page)",
    ):
        assert needle in text


@pytest.mark.parametrize("blank", [" ", "\u200b", "­", "﻿", "\n\t", " ­ "])
@pytest.mark.parametrize("where", ["evidence", "basis", "overall"])
def test_blank_citation_quote_is_refused_never_composed(where: str, blank: str) -> None:
    """Backlog inventory (round 13 addendum 3): no blank quote passes the pack-quote check, so
    the Medium defect is absent here; this pins the refusal."""
    payload = copy.deepcopy(SUBMISSIONS["positive"]["earnings_quality"])
    if where == "evidence":
        payload["assessments"][1]["evidence"][0]["quote"] = blank
    elif where == "basis":
        payload["assessments"][0]["accepted_basis"]["quote"] = blank
    else:
        payload["overall"]["evidence"] = [
            dict(payload["assessments"][1]["evidence"][0], quote=blank)
        ]
    assert cp1d.validation_issues(stage1._inputs("positive", payload))


# --- a real store, built fast (no CP-1 promotion): submit, settle, probe, view ------------------


def _command(module_id: str) -> Fact:
    return Fact(
        fact_id=f"t8-{module_id.lower()}",
        label="Command",
        table_id="T8",
        row_id=module_id,
        field="exact_command",
        text=f"Run {module_id}",
    )


def _settled_store(
    tmp_path: Path, case: str, scale: Decimal = Decimal(1), decimals: int | None = 2
) -> tuple[Execution, str]:
    """CP-0 and CP-1 settled in a real store (hand-built modules through `begin`/`finish`), then
    CP-1D begun. Returns the store and the CP-1D ticket."""
    pack = _pack(case)
    store = Execution.create(tmp_path / "store", pack)
    cp0_ticket = store.begin("CP-0")
    cp0 = _cp0_module().model_copy(
        update={
            "status": "candidate",
            "inputs": cp0_ticket.inputs,
            "run_id": pack.run.run_id,
            "facts": (_command("CP-1"), _command("CP-1D")),
        }
    )
    store.finish(cp0_ticket.ticket_id, cp0.model_dump_json(), lambda _m: ())
    cp1_ticket = store.begin("CP-1")
    cp1 = _cp1_module(scale, decimals=decimals).model_copy(
        update={"status": "candidate", "inputs": cp1_ticket.inputs, "run_id": pack.run.run_id}
    )
    store.finish(cp1_ticket.ticket_id, cp1.model_dump_json(), lambda _m: ())
    return store, store.begin("CP-1D").ticket_id


def _payload(store: Execution, case: str) -> str:
    cp1 = next(h for h in store.read().heads if h.module_id == "CP-1")
    text = json.dumps(SUBMISSIONS[case]["earnings_quality"])
    return _bind_figures(text, store.head_module(cp1))


def _read_all(text: str) -> Seen:
    return Seen(read=frozenset(cited_locators(text)))


@pytest.mark.parametrize("case", CASES)
def test_submit_settles_the_head_and_the_probe_accepts_it(tmp_path: Path, case: str) -> None:
    store, ticket = _settled_store(tmp_path, case, Decimal("1.5"))
    payload = _payload(store, case)
    seen = _read_all(payload)
    submitted = cp1d.submit(
        store, ticket, "earnings_quality", payload, lambda text: cp1d.RULES(text, seen)
    )
    assert submitted.journal.status == "finished" and submitted.journal.issues == ()
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == "CP-1D")
    assert head.status == EXPECTED["cases"][case]["module_status"]
    settled = store.head_module(head)
    tail = settled.inputs[-1]
    assert (tail.input_id, tail.sha256) == (
        "earnings-quality-submission",
        cp1d.EarningsQualitySubmission.model_validate_json(submitted.payload).content_hash(),
    )
    assert list(settled.limitations)[-1] == "Synthetic case; not real issuer qualification"
    assert list(settled.limitations)[:-1] == EXPECTED["cases"][case]["own_limitations"]
    assert settled.inherited_limitations == ("CP-0 note", "CP-1 note")
    cp1d.probe(store, snapshot, submitted.journal)  # rebuilds exactly, writes nothing
    assert store.read() == snapshot


def test_probe_raises_identity_mismatch_when_the_retained_step_differs(tmp_path: Path) -> None:
    store, ticket = _settled_store(tmp_path, "positive")
    payload = _payload(store, "positive")
    seen = _read_all(payload)
    done = cp1d.submit(store, ticket, "earnings_quality", payload, lambda t: cp1d.RULES(t, seen))
    snapshot = store.read()
    step = done.journal.steps[0]
    other = json.loads(payload)
    other["overall"]["rationale"] = other["overall"]["rationale"] + " Reviewed."
    forged_sha = store._store(json.dumps(other))
    forged = done.journal.model_copy(
        update={"steps": (step.model_copy(update={"payload_sha256": forged_sha}),)}
    )
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cp1d.probe(store, snapshot, forged)
    two = done.journal.model_copy(update={"steps": (step, step)})
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cp1d.probe(store, snapshot, two)


def test_invalid_submission_twice_settles_blocked_with_no_tables(tmp_path: Path) -> None:
    """r06 twice: attempt 0 is rejected, the one repair is blocked; a blocked head carries
    limitations only."""
    case = EXPECTED["blocked"]["attempt_0"]
    assert case == "r06"
    literal = next(r for r in SUBMISSIONS["refusals"] if r["id"] == "r06")
    store, ticket = _settled_store(tmp_path, literal["pack"])
    payload = _bind_figures(json.dumps(literal["payload"]), next_cp1(store))
    seen = _read_all(payload)
    first = cp1d.submit(store, ticket, "earnings_quality", payload, lambda t: cp1d.RULES(t, seen))
    assert first.journal.status == "finished" and first.journal.issues
    again = store.begin("CP-1D")
    second = cp1d.submit(
        store, again.ticket_id, "earnings_quality", payload, lambda t: cp1d.RULES(t, seen)
    )
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == "CP-1D")
    assert head.status == "blocked" and second.journal.number == 1
    blocked = store.head_module(head)
    assert blocked.tables == () and blocked.facts == ()
    assert EXPECTED["blocked"]["limitations_contain"] in blocked.limitations


def next_cp1(store: Execution) -> Module:
    return store.head_module(next(h for h in store.read().heads if h.module_id == "CP-1"))


def test_unread_page_is_a_journaled_invalid_step(tmp_path: Path) -> None:
    store, ticket = _settled_store(tmp_path, "positive")
    payload = _payload(store, "positive")
    refusal = next(t for t in EXPECTED["tool_refusals"] if t["id"] == "t01")
    done = cp1d.submit(store, ticket, "earnings_quality", payload, lambda t: cp1d.RULES(t, Seen()))
    assert done.journal.status == "finished"
    assert done.journal.issues == tuple(refusal["expected_issues"])
    assert not any(h.module_id == "CP-1D" and h.status != "blocked" for h in store.read().heads)


def test_view_over_a_real_store_is_the_context_block(tmp_path: Path) -> None:
    store, ticket = _settled_store(tmp_path, "positive")
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket)
    digest, body = cp1d.view(store, attempt)
    block = json.loads(body)
    assert hashlib.sha256(body.encode()).hexdigest() == digest
    assert block == json.loads(
        json.dumps(
            cp1d.context_block(pack=store.pack(), upstream=cp1d.cp1d_upstream(store, attempt))
        )
    )
    assert block["inherited_limitations"] == [
        "CP-0 note",
        "Synthetic case; not real issuer qualification",
        "CP-1 note",
    ]
    assert [u["module_id"] for u in block["upstream"]] == ["CP-0", "CP-1"]


@pytest.mark.parametrize("case", CASES)
def test_run_driver_binds_the_oracle_figures_over_the_view_of_a_real_store(
    tmp_path: Path, case: str
) -> None:
    """Review M1: `cp1d_runs.fig_bindings` (what `drive_cp1d` calls in every closed run and fork)
    over the real view of a fast store whose CP-1 facts are shaped as `model_interface` builds
    them (no `decimals`). The view's `unit` and `shown` stay separate, as the oracle keeps them."""
    store, ticket = _settled_store(tmp_path, case, decimals=None)
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket)
    _, body = cp1d.view(store, attempt)
    figures = runs.oracle()["submissions"]["figures"]
    raw = runs.literal(case, "earnings_quality")
    names = {n: figures[n] for n in dict.fromkeys(m[1] for m in runs.FIG.finditer(raw))}
    assert "adjusted_ebitda_ltm" in names  # every case's literal names it
    cp1 = next_cp1(store)
    ids = {f.label: f.fact_id for f in cp1.facts if f.period == runs.LTM_PERIOD}
    expected = {n: (ids[f["label"]], f["unit_token"]) for n, f in figures.items()}
    assert runs.fig_bindings(store, json.loads(body), names) == {n: expected[n] for n in names}
    assert runs.fig_bindings(store, json.loads(body), figures) == expected  # all seven


def test_validate_step_reads_the_payload_only_through_json_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Protocol section 6: the step validator parses the bounded `json_object` document, never raw
    text; text it refuses is refused with a bounded issue even if Pydantic would parse it."""
    seen: list[str] = []

    def refuse(text: str) -> None:
        seen.append(text)

    monkeypatch.setattr(cp1d, "json_object", refuse)
    store = SimpleNamespace(payload=lambda sha: "{}")
    attempt = SimpleNamespace(steps=[SimpleNamespace(payload_sha256="x")])
    out = cp1d._validate_step(cast(Any, store), cast(Any, None), cast(Any, attempt))
    assert seen == ["{}"] and out.output is None
    assert out.issues and all(len(i) <= 600 for i in out.issues)


def test_cp1_facts_note_says_where_cp1_references_bind() -> None:
    """Low L6: assessment rationales bind module facts only, so a CP-1 `{ref|unit}` there is an
    unresolved reference; the note must admit CP-1 references only where the core binds them."""
    block = cp1d.context_block(pack=_pack("positive"), upstream=_upstream())
    note = str(block["cp1_facts_note"])
    assert "overall rationale" in note and "assessment" in note
