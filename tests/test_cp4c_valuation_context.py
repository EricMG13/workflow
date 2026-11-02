"""Phase 7 Task 4: CP-4C binds its valuation multiples to the CP-1C selected multiple.

Every expectation is read at run time from the frozen oracle `cases/valuation-context-owner/`
(`expected.json`: the CP-4C block of each case, the refusal ids and the rules) or from
`cases/cp4c-owner/` (the no-context heads and the committed view trees). Nothing is computed here:
a figure, a text or an issue comes from the key.

The tests drive `validate_restructuring`, `_lines`, `restructuring`, `compute`, `stale_issues` and
`context_block` over hand-built `Upstream` values, so no node runs a store (each node is well under
the 300 s bound). The CP-1C head is the real one: `peer_benchmark` over the case's context, settled
into a `Module`, read through `cp1c.reader_facts`.
"""

import hashlib
import json
import re
from dataclasses import replace
from decimal import Decimal
from functools import cache
from types import SimpleNamespace
from typing import Any, cast

import pytest
import test_cp1c_valuation_context as t3
import test_method_cp4c as stage1
import view_tree
from test_connect_cp1c import _submission, _upstream

from deploy_vii.contracts import Input, Module
from deploy_vii.execution import Attempt, Execution, Head
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owners import cp1c, cp2g, cp4c
from deploy_workflow.owners.period_basis import DEFAULT_BASIS

EXPECTED = t3.expected()
CASES = EXPECTED["cases"]
CLOSED = [name for name, case in CASES.items() if case["pack"] == "closed-chain"]
BOUND = [name for name in CLOSED if CASES[name]["cp4c"].get("selected_multiple")]
UNBOUND = [name for name in CLOSED if CASES[name]["cp4c"].get("multiple_rule")]
ROLE = "CP-1C"


@cache
def head_of(name: str) -> cp1c.Cp1cHead:
    """The CP-1C head of one oracle case as a consumer reads it."""
    pack, up = t3.pack_of(name), _upstream(t3.full_cp1())
    report = cp1c.peer_benchmark(pack=pack, submission=_submission("no_peers"), upstream=up)
    module = cp1c.cp1c_module(report, inputs=up.bound, attempt=0)
    return cp1c.Cp1cHead(
        status="accepted",
        head_sha256=module.content_hash(),
        facts=cp1c.reader_facts(module),
        limitations=module.limitations,
    )


def pack_of(name: str) -> PreparedPack:
    """The CP-4C positive pack with the case's run and its context file (manifest `base`)."""
    base = stage1._pack("positive")
    return PreparedPack(run=t3.run_of(name), sources=(*base.sources, t3.context_source(name)))


def bound_inputs(head: cp1c.Cp1cHead | None) -> tuple[Input, ...]:
    items = [
        stage1._input(i, "accepted" if i == "prepared-pack" else "restricted")
        for i in ("prepared-pack", "CP-0", "CP-1", "CP-2A", "CP-4", "CP-2G")
    ]
    if head is not None:
        items.insert(3, Input(input_id=ROLE, sha256=head.head_sha256, status=head.status))
    return tuple(items)


def upstream_of(
    head: cp1c.Cp1cHead | None, current: tuple[Input, ...] | str | None = None
) -> cp4c.Upstream:
    ctx = stage1._context("positive")
    bound = bound_inputs(head)
    return cp4c.Upstream(
        bound=bound,
        current=bound if current is None else current,
        cp1=ctx.cp1,
        cp2a=ctx.cp2a,
        cp2g=ctx.cp2g,
        cp4=ctx.cp4,
        cp1c=head,
    )


def judgment(payload: dict[str, Any], i: int, m: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """The fulcrum and plan judgments that fit the waterfall at valuation i and multiple m. These
    are submission inputs, taken from the frozen positive payload (a judgment is analyst input):
    every creditor is paid at 7x and above (the v01 judgment), 3x and 4x on the downside EBITDA
    break at c02 and c03 (the v02 judgment), 2x at c01 (the v03 judgment), and a multiple not
    assessed leaves the break undetermined (the gap case's shape)."""
    if m == "not assessed":
        classes = [c["class_id"] for c in payload["claims"]] + ["equity"]
        fulcrum = {**payload["fulcrum"][0], "class_ids": []}
        treatments = [{"class_id": c, "treatment": "Not determined"} for c in classes]
        return fulcrum, {**payload["plan"][0], "treatments": treatments}
    source = 0 if i == 0 or Decimal(m) >= 5 else {"4.00": 1, "3.00": 1, "2.00": 2}[m]
    return payload["fulcrum"][source], payload["plan"][source]


def submission_of(*multiples: str) -> cp4c.RestructuringSubmission:
    payload = stage1._bind_all(stage1._payload("positive"))
    assert len(multiples) == len(payload["valuation"])
    judged = [judgment(payload, i, m) for i, m in enumerate(multiples)]
    for i, (valuation, multiple) in enumerate(zip(payload["valuation"], multiples, strict=True)):
        valuation["multiple"] = multiple
        fulcrum, plan = judged[i]
        payload["fulcrum"][i] = {**fulcrum, "case_id": f"v0{i + 1}"}
        payload["plan"][i] = {**plan, "case_id": f"v0{i + 1}"}
    return stage1._submission(payload)


def lines(name: str, *multiples: str, head: cp1c.Cp1cHead | None | str = "case") -> Any:
    chosen = head_of(name) if head == "case" else head
    assert not isinstance(chosen, str)
    return cp4c._lines(pack_of(name), submission_of(*multiples), upstream_of(chosen))


def report_of(name: str, *multiples: str, head: cp1c.Cp1cHead | None | str = "case") -> Any:
    chosen = head_of(name) if head == "case" else head
    assert not isinstance(chosen, str)
    return cp4c.restructuring(
        pack=pack_of(name), submission=submission_of(*multiples), upstream=upstream_of(chosen)
    )


def facts_of(report: Any) -> dict[str, Any]:
    return {f.fact_id: f for f in report.facts}


def oracle(name: str) -> dict[str, Any]:
    block: dict[str, Any] = CASES[name]["cp4c"]
    return block


def as_typed(multiples: list[str]) -> tuple[str, ...]:
    return tuple(multiples)


# --- the bound multiple is accepted, with the oracle's EV, formula and limitation ----------------------


@pytest.mark.parametrize("pick", [0, 1])
def test_bound_multiple_accepted(pick: int) -> None:
    """auto-public: `7.00` and `7` both equal M; EV, implied multiple, formula and limitation."""
    block = oracle("auto-public")
    multiples = as_typed(block["accepted_submissions"][pick]["multiples"])
    assert lines("auto-public", *multiples) == ()
    facts = facts_of(report_of("auto-public", *multiples))
    v01 = block["valuations"][0]
    assert facts["T4E.3.v01.ev"].amount == Decimal(v01["ev_exact"])
    assert facts["T4E.3.v01.implied_ltm_multiple"].amount == Decimal(
        v01["implied_ltm_multiple_exact"]
    )
    assert facts["T4E.3.v01.multiple"].formula == v01["multiple_formula"]
    limitations = report_of("auto-public", *multiples).limitations
    assert limitations.count(block["added_limitation"]) == 1


def test_differing_multiple_refused() -> None:
    block = oracle("auto-public")
    refused = block["refused_submissions"]["ev-multiple-differs"]
    assert list(lines("auto-public", *refused["multiples"])) == refused["issues"]
    assert refused["issues"] == [EXPECTED["refusal_ids"]["ev-multiple-differs"]["text"]]
    third = block["refused_submissions"]["ev-multiple-differs-v03"]
    assert list(lines("auto-public", *third["multiples"])) == third["issues"]


def test_not_assessed_refused_when_known() -> None:
    refused = oracle("auto-public")["refused_submissions"]["ev-not-assessed-when-selected"]
    assert list(lines("auto-public", *refused["multiples"])) == refused["issues"]
    assert refused["issues"] == [EXPECTED["refusal_ids"]["ev-not-assessed-when-selected"]["text"]]


def test_every_valuation_is_checked_in_case_order() -> None:
    """One issue per valuation, in case order, whatever the submitted text."""
    got = lines("auto-public", "4.00", "not assessed", "5")
    texts = [i.split(": multiple ")[1].split(" differs")[0] for i in got]
    assert [i.split(":")[0] for i in got] == ["valuation v01", "valuation v02", "valuation v03"]
    assert texts == ["4.00", "not assessed", "5"]


def test_all_three_cases_bound() -> None:
    """v02 and v03 carry the same M: the downside and stress EV are the oracle's."""
    block = oracle("auto-public")
    multiples = as_typed(block["accepted_submissions"][0]["multiples"])
    facts = facts_of(report_of("auto-public", *multiples))
    for row in block["valuations"]:
        r = row["case_id"]
        assert facts[f"T4E.3.{r}.ev"].amount == Decimal(row["ev_exact"])
        assert facts[f"T4E.3.{r}.multiple"].formula == row["multiple_formula"]
        assert facts[f"T4E.3.{r}.implied_ltm_multiple"].amount == Decimal(
            row["implied_ltm_multiple_exact"]
        )
    assert {block["valuations"][1]["ev_exact"], block["valuations"][2]["ev_exact"]} == {"129.78"}


@pytest.mark.parametrize("name", BOUND)
def test_every_oracle_case_with_a_selection_binds(name: str) -> None:
    """Each case that selects a multiple accepts its own M and refuses another."""
    m = oracle(name)["selected_multiple"]
    if oracle(name)["pinned_multiple"] is None:
        assert lines(name, m, m, m) == ()
        other = str(Decimal(m) + 1)
        assert len(lines(name, other, m, m)) == 1


# --- an unknown selection changes nothing --------------------------------------------------------------


@pytest.mark.parametrize("name", UNBOUND)
def test_unknown_selection_changes_nothing(name: str) -> None:
    block = oracle(name)
    for sub in block.get("accepted_submissions", ()):
        assert lines(name, *sub["multiples"]) == ()
    numeric = ("4.00", "3.00", "2.00")
    assert lines(name, *numeric) == ()
    assert lines(name, *(("not assessed",) * 3)) == ()
    report = report_of(name, *numeric)
    bare = report_of(name, *numeric, head=None)
    assert report.limitations == bare.limitations  # no extra limitation
    assert [f.formula for f in report.facts] == [f.formula for f in bare.facts]
    assert facts_of(report)["T4E.3.v01.multiple"].formula == "analyst input"


def test_auto_thin_oracle_states_no_rule() -> None:
    block = oracle("auto-thin")
    assert block["formula_suffix"] is None and block["added_limitation"] is None
    assert [s["multiples"] for s in block["accepted_submissions"]] == [
        ["4.00", "3.00", "2.00"],
        ["not assessed"] * 3,
    ]


def test_a_frozen_head_without_t1c11_applies_no_rule() -> None:
    """A CP-1C head from before Phase 7 has no EV facts; the reader set is the frozen one."""
    frozen = cp1c.Cp1cHead(
        status="accepted", head_sha256=hashlib.sha256(b"frozen").hexdigest(), facts=()
    )
    assert lines("auto-public", "4.00", "3.00", "2.00", head=frozen) == ()


def test_a_blocked_head_applies_no_rule() -> None:
    blocked = cp1c.Cp1cHead(status="blocked", head_sha256=hashlib.sha256(b"blocked").hexdigest())
    assert lines("auto-public", "4.00", "3.00", "2.00", head=blocked) == ()


# --- nothing requested, nothing changed ------------------------------------------------------------------


def test_cp1c_unrequested_unchanged() -> None:
    """CP-4C alone over a context pack: no selection key, no refusal, no formula suffix."""
    assert lines("auto-public", "4.00", "3.00", "2.00", head=None) == ()
    upstream = upstream_of(None)
    body = cp4c.context_block(pack=pack_of("auto-public"), upstream=upstream)
    assert "selected_multiple" not in body
    report = report_of("auto-public", "4.00", "3.00", "2.00", head=None)
    assert facts_of(report)["T4E.3.v01.multiple"].formula == "analyst input"
    assert not any("CP-1C selected" in x for x in report.limitations)


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_no_context_unchanged(case: str) -> None:
    """The frozen heads: facts and own limitations equal the CP-4C oracle's, and the `read_inputs`
    view has the committed key tree, with the new fields at their defaults."""
    ctx = stage1._context(case)
    assert ctx.cp1c is None and ctx.context is None
    result = stage1._result(case)
    assert list(result.own_limitations) == stage1.EXPECTED["cases"][case]["own_limitations"]
    assert stage1._records(result) == stage1._oracle_records(case)
    upstream = cp4c.Upstream(
        bound=tuple(
            stage1._input(i, "accepted" if i == "prepared-pack" else "restricted")
            for i in stage1.EXPECTED["execution"]["inputs"]
        ),
        current=(),
        cp1=ctx.cp1,
        cp2a=ctx.cp2a,
        cp2g=ctx.cp2g,
        cp4=ctx.cp4,
        inherited=("An inherited limitation, as a settled store gives",),  # the tree holds one
    )
    assert upstream.cp1c is None
    body = json.dumps(cp4c.context_block(pack=ctx.pack, upstream=upstream), ensure_ascii=False)
    assert view_tree.entry(body) == view_tree.load("cp4c")[case]


# --- staleness ----------------------------------------------------------------------------------------


def test_stale_cp1c_head_refused() -> None:
    """CP-1C re-settled after CP-4C bound it: the existing staleness text, alone."""
    head = replace(head_of("auto-public"), status="restricted")
    bound = bound_inputs(head)
    newer = Input(
        input_id=ROLE, sha256=hashlib.sha256(b"re-settled").hexdigest(), status="restricted"
    )
    current = tuple(newer if i.input_id == ROLE else i for i in bound)
    template = stage1.EXPECTED_REFUSALS["v24"]["expected_issues"][0]
    want = re.sub(r"<12 hex of [^>]*>", head.head_sha256[:12], template)
    want = want.replace("CP-2A", ROLE).replace("5a0542c59b92", newer.sha256[:12])
    upstream = upstream_of(head, current)
    got = cp4c.validate_restructuring(
        pack=pack_of("auto-public"),
        submission=submission_of("4.00", "7.00", "7.00"),  # would also differ from M
        upstream=upstream,
    )
    assert got == (want,)
    assert cp4c.stale_issues(bound=bound, current=bound) == ()


# --- the pin wins over the selection ---------------------------------------------------------------------


def test_pin_wins_over_selection() -> None:
    block = oracle("pin-vs-selection")
    assert block["selected_multiple"] == "7.00" and block["pinned_multiple"] == "8.5"
    for sub in block["accepted_submissions"]:
        assert lines("pin-vs-selection", *sub["multiples"]) == ()
    refused = block["refused_submissions"]["selection-equal-under-pin"]
    assert list(lines("pin-vs-selection", *refused["multiples"])) == refused["issues"]
    assert not any("differs from the CP-1C" in i for i in refused["issues"])
    row = block["valuations"][0]
    report = report_of("pin-vs-selection", *block["accepted_submissions"][0]["multiples"])
    facts = facts_of(report)
    assert facts["T4E.3.v01.ev"].amount == Decimal(row["ev_exact"])
    assert facts["T4E.3.v01.multiple"].formula == row["multiple_formula"] == "analyst input"
    limitations = report.limitations
    assert limitations.count(block["added_limitation"]) == 1
    assert limitations[-1] == block["phase6_pinned_line"]  # the pinned line stays last


# --- the read_inputs view offers the selection only when bound --------------------------------------------


def test_context_block_shows_the_selection_only_when_bound() -> None:
    block = oracle("auto-public")
    head = head_of("auto-public")
    body = cp4c.context_block(pack=pack_of("auto-public"), upstream=upstream_of(head))
    got = cast(dict[str, Any], body["selected_multiple"])
    assert got["shown"] == f"{block['selected_multiple']}x"
    assert got["basis"] == CASES["auto-public"]["cp1c"]["selection"]["selected_basis"]
    assert got["ebitda_basis"] == CASES["auto-public"]["cp1c"]["selection"]["ebitda_basis"]
    assert got["head_sha256"] == head.head_sha256
    thin = cp4c.context_block(pack=pack_of("auto-thin"), upstream=upstream_of(head_of("auto-thin")))
    assert "selected_multiple" not in thin


# --- the upstream reader --------------------------------------------------------------------------------------


def test_the_reader_tests_presence_never_catches_the_missing_fact() -> None:
    """Reader use (Task 3 review, check 5): a head with and a head without the EV facts both read."""
    assert cp4c.selected_multiple(head_of("auto-public")) is not None
    assert cp4c.selected_multiple(head_of("auto-thin")) is None
    assert cp4c.selected_multiple(None) is None


def test_a_bound_head_over_a_pack_without_a_context_applies_no_rule() -> None:
    """Design 11 applies when the pack has a context: the frozen positive pack has none."""
    head = head_of("auto-public")
    got = cp4c._lines(
        stage1._pack("positive"), submission_of("4.00", "3.00", "2.00"), upstream_of(head)
    )
    assert got == ()


class _Store:
    """The two store calls `cp4c_upstream` makes for a bound CP-1C head: its module by hash."""

    def __init__(self, module: Module) -> None:
        self.module = module

    def result(self, sha256: str) -> Module:
        assert sha256 == self.module.content_hash()
        return self.module

    def head_module(self, head: Head) -> Module:
        return self.module


def test_the_upstream_reads_a_bound_cp1c_head_through_the_reader_and_only_then() -> None:
    pack, up = t3.pack_of("auto-public"), _upstream(t3.full_cp1())
    report = cp1c.peer_benchmark(pack=pack, submission=_submission("no_peers"), upstream=up)
    module = cp1c.cp1c_module(report, inputs=up.bound, attempt=0)
    store = cast(Execution, _Store(module))
    item = Input(input_id=ROLE, sha256=module.content_hash(), status="restricted")
    with_cp1c = cast(Attempt, SimpleNamespace(inputs=(*bound_inputs(None), item)))
    got = cp4c._bound_cp1c(store, with_cp1c)
    assert got is not None and got.head_sha256 == module.content_hash()
    assert [f.fact_id for f in got.facts] == [*cp1c.READER_FACTS, *cp1c.EV_READER_FACTS]
    assert cp4c.selected_multiple(got) == cp4c.selected_multiple(head_of("auto-public"))
    assert (
        cp4c._bound_cp1c(store, cast(Attempt, SimpleNamespace(inputs=bound_inputs(None)))) is None
    )


def test_cp1c_and_cp4c_select_the_same_ebitda_fact() -> None:
    """Task 3 review I3: CP-1C's issuer EBITDA (`cp2g.select_cp1`) and CP-4C's implied-multiple
    denominator (`cp4c.select_cp1`) are one fact on every pack both accept. They differ only in
    refusing: CP-4C also requires the LTM period, so a CP-1 EBITDA of another period is read by
    CP-1C and refused by CP-4C (CP-4C stays the stricter; nothing here changes what it refuses).
    CP-1C's selector also wants every CP-2G metric, CP-4C's only the two it reads."""
    assert cp4c.LTM_COLUMN == DEFAULT_BASIS.ltm_column
    assert set(cp4c.CP1_METRICS) <= set(cp2g.CP1_METRICS)  # CP-1C's selector wants more metrics
    facts = t3.cp1_t410_facts()
    assert cp2g.select_cp1(facts)["ebitda"] is cp4c.select_cp1(facts)["ebitda"]
    other = tuple(
        f.model_copy(update={"period": "FY25: 2025"}) if f.label.endswith("ebitda") else f
        for f in facts
    )
    assert cp2g.select_cp1(other)["ebitda"].period == "FY25: 2025"
    with pytest.raises(ValueError, match="is not for"):
        cp4c.select_cp1(other)
