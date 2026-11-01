"""CP-3C honours the repricing basis points pinned in the context file (Phase 6 Task 6).

Expectations come from `cases/pins-context-owner/{expected,submissions}.json` (the CP-3C entry) and
the frozen base oracle `cases/cp3c-owner/expected.json`, never from the code under test. Each case
runs on a real `Execution` seeded as in `tests/test_connect_cp3c.py`, over the base run's pack with
the `prepare`d context source last (CP-2D settles under the same context). Fast: no store promotion
run (`tests/test_owner_cp3c.py`).
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp3c as connect
import test_method_cp3c as tm

from deploy_vii.contracts import Module
from deploy_vii.execution import MAX_ISSUE_CHARS, Attempt, Execution
from deploy_vii.preparation import PreparedPack, prepare
from deploy_workflow.context import (
    CONTEXT_SOURCE_ID,
    ContextRefused,
    load_context,
    preparation_request,
)
from deploy_workflow.owners import cp3c
from deploy_workflow.owners.pins import pinned_line

ORACLE = Path(__file__).resolve().parents[1] / "cases" / "pins-context-owner"
EXPECTED: dict[str, Any] = json.loads((ORACLE / "expected.json").read_text())["modules"]["CP-3C"]
CASES: dict[str, Any] = json.loads((ORACLE / "submissions.json").read_text())["modules"]["CP-3C"][
    "cases"
]
PINNED = pinned_line("CP-3C")
CP2D_PINNED = pinned_line("CP-2D")
REFUSED = ("differs", "absence")
CONTEXT = "context-covenant_refinancing.json"
NO_CP2D = "context-covenant_refinancing-no-cp2d.json"
NO_CP3C = "context-covenant_refinancing-no-cp3c.json"
SYNTHETIC = connect.SYNTHETIC
LABEL = ["Pinned assumptions", "Limitation"]
_BASE_PACK = connect.make_pack  # `_seed` replaces `connect.make_pack` for the run


def _pack(tmp_path: Path, context: str | None) -> PreparedPack:
    """The base CP-3C run's pack with the prepared context source appended last."""
    base = _BASE_PACK()
    if context is None:
        return base
    raw = (ORACLE / context).read_bytes()
    request = preparation_request(
        load_context(raw), run_id=base.run.run_id, context_path="context.json", sources=()
    )
    (tmp_path / "root").mkdir(parents=True)
    (tmp_path / "root" / "context.json").write_bytes(raw)
    prepared = prepare(request, tmp_path / "root", tmp_path / "pack")
    found = tuple(s for s in prepared.sources if s.source_id == CONTEXT_SOURCE_ID)
    assert len(found) == 1
    return PreparedPack(run=base.run, sources=(*base.sources, *found))


def _seed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, context: str | None, base_case: str
) -> tuple[Execution, PreparedPack, Attempt]:
    pack = _pack(tmp_path, context)
    monkeypatch.setattr(connect, "make_pack", lambda **_: pack)
    return connect.seed(tmp_path / "run", base_case)


def _payload(store: Execution, attempt: Attempt, case: str) -> dict[str, Any]:
    bound: dict[str, Any] = connect.bound_payload(
        copy.deepcopy(CASES[case]["payload"]), connect.refs(store, attempt)
    )
    return bound


def _bound(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> dict[str, Any]:
    """The case payload with its facts bound, from a throwaway seed (its own directory)."""
    store, _, attempt = _seed(tmp_path / "bound", monkeypatch, CASES[case]["context"], "positive")
    return _payload(store, attempt, case)


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    *,
    payload: dict[str, Any] | None = None,
    context: str | None = None,
) -> tuple[Execution, PreparedPack, Attempt]:
    """Seed over the case's context (or `context`), submit its (or the given) payload."""
    spec = CASES[case]
    chosen = spec["context"] if context is None else context
    store, pack, attempt = _seed(tmp_path, monkeypatch, chosen, spec["base_case"])
    body = _payload(store, attempt, case) if payload is None else payload
    connect._submit(store, attempt, json.dumps(body))
    return store, pack, attempt


def _issues(store: Execution, attempt: Attempt) -> list[str]:
    return list(connect.finished(store, attempt).issues)


def _submission(store: Execution, attempt: Attempt, case: str) -> cp3c.RefinancingRiskSubmission:
    return cp3c.RefinancingRiskSubmission.model_validate_json(
        json.dumps(_payload(store, attempt, case))
    )


def _settled_module(store: Execution, attempt: Attempt) -> Module:
    done = connect.finished(store, attempt)
    assert done.status == "finished" and done.issues == ()
    return store.head_module(connect.head(store, connect.MODULE))


def _rows(module: Module, table_id: str) -> list[list[str]]:
    facts = {f.fact_id: f for f in module.facts}
    table = next(t for t in module.tables if t.table_id == table_id)
    return [[r.label, *(facts[i].text or "" for i in r.fact_ids)] for r in table.rows]


def _base(case: str = "positive") -> dict[str, Any]:
    base: dict[str, Any] = tm.EXPECTED["cases"][case]
    return base


# --- the refusals ---------------------------------------------------------------------------------
@pytest.mark.parametrize("case", REFUSED)
def test_a_differing_pin_is_a_validator_refusal_with_the_oracle_lines(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = _run(tmp_path, monkeypatch, case)
    assert connect.finished(store, attempt).steps[0].status == "invalid"
    assert _issues(store, attempt) == EXPECTED["cases"][case]["issues"]
    assert not [h for h in store.read().heads if h.module_id == connect.MODULE]


@pytest.mark.parametrize("case", REFUSED)
def test_the_composer_gate_raises_on_the_pin_lines(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = CASES[case]
    store, pack, attempt = _seed(tmp_path, monkeypatch, spec["context"], spec["base_case"])
    upstream = connect.upstream_of(store, attempt)
    with pytest.raises(ValueError) as caught:
        cp3c.refinancing_risk(
            pack=pack, submission=_submission(store, attempt, case), upstream=upstream
        )
    assert str(caught.value) == "; ".join(EXPECTED["cases"][case]["issues"])


@pytest.mark.parametrize("bps", (40, 4000, 399, 401, -400, 0, 1000, 4001))
def test_every_other_value_is_shown_as_typed(
    bps: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mapping that truncates, strips, pads or deduplicates the typed value fails here: 40 and
    4000 are a prefix of the pin and an extension of it."""
    payload = _bound(tmp_path, monkeypatch, "match")
    payload["repricing"]["bps"] = bps
    store, _, attempt = _run(tmp_path, monkeypatch, "match", payload=payload)
    line = f"assumptions.cp3c.repricing_bps: pinned 400; submitted {bps}"
    assert _issues(store, attempt)[-1] == line


def test_a_content_issue_comes_before_the_pin_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _bound(tmp_path, monkeypatch, "differs")
    payload["repricing"]["bps"] = 5000  # beyond the bounds as well as off the pin
    store, _, attempt = _run(tmp_path, monkeypatch, "differs", payload=payload)
    assert _issues(store, attempt) == [
        tm.EXPECTED["refusals"]["step_up_over_limit"],
        "assumptions.cp3c.repricing_bps: pinned 400; submitted 5000",
    ]


def test_a_huge_integer_is_a_bounded_shape_refusal_with_no_pin_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = json.dumps(_bound(tmp_path, monkeypatch, "differs")).replace(
        '"bps": 401', '"bps": ' + "9" * 5000
    )
    store, _, attempt = _seed(tmp_path, monkeypatch, CONTEXT, "positive")
    connect._submit(store, attempt, text)
    issues = _issues(store, attempt)
    assert issues and all(len(x) <= MAX_ISSUE_CHARS for x in issues)
    assert not any("pinned" in line for line in issues)


def test_a_shape_failure_gets_no_pin_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _bound(tmp_path, monkeypatch, "differs")
    payload["repricing"]["bps"] = "401"  # a string for an integer is a shape refusal
    store, _, attempt = _run(tmp_path, monkeypatch, "differs", payload=payload)
    issues = _issues(store, attempt)
    assert issues and not any("pinned" in line for line in issues)


def test_pin_lines_follow_the_stale_only_and_provenance_only_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, attempt = _seed(tmp_path, monkeypatch, CONTEXT, "positive")
    submission = _submission(store, attempt, "differs")
    good = connect.upstream_of(store, attempt)
    pin = tuple(EXPECTED["cases"]["differs"]["issues"])
    refused = "Required upstream is unrun, stale or blocked"
    stale = replace(good, current=refused)
    assert cp3c._lines(pack, submission, stale) == (f"Stale inputs: {refused}", *pin)
    forged = replace(good, cp1=good.cp1.model_copy(update={"limitations": ("another",)}))
    assert cp3c._lines(pack, submission, forged) == (
        "Upstream CP-1: the supplied module is not the bound input",
        *pin,
    )


# --- the catch ------------------------------------------------------------------------------------
def test_a_context_that_differs_from_the_run_is_one_refusal_line_after_the_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P6-P3: only `ContextRefused` is caught; it becomes `Context refused: <message>`, with no
    pin lines, after the content issues. CP-2D refuses such a context too, so the run settles
    under its own context and the validator is handed the other run's pack."""
    store, _, attempt = _run(tmp_path, monkeypatch, "match")
    done = connect.finished(store, attempt)
    other = _pack(tmp_path / "other", "context-credit_snapshot.json")
    refused = list(cp3c.ENTRY_VALIDATOR(store, other, done).issues)
    assert len(refused) == 1 and refused[0].startswith("Context refused: ")
    assert "pinned" not in refused[0]
    upstream = connect.upstream_of(store, attempt)
    with pytest.raises(ValueError, match="Context refused"):
        cp3c.refinancing_risk(
            pack=other, submission=_submission(store, attempt, "match"), upstream=upstream
        )
    payload = _payload(store, attempt, "match")
    payload["repricing"]["bps"] = 5000
    bad = cp3c.RefinancingRiskSubmission.model_validate_json(json.dumps(payload))
    got = cp3c._lines(other, bad, upstream)
    assert got[0] == tm.EXPECTED["refusals"]["step_up_over_limit"]
    assert got[1:] == tuple(refused)


def test_only_context_refused_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Widening the catch to `ValueError` must fail: any other `ValueError` escapes the step
    validator (through `submit`) and the composer."""
    store, pack, attempt = _seed(tmp_path, monkeypatch, CONTEXT, "positive")
    payload = _payload(store, attempt, "match")
    submission = _submission(store, attempt, "match")
    upstream = connect.upstream_of(store, attempt)

    def boom(*_: object, **__: object) -> tuple[str, ...]:
        raise ValueError("not a context refusal")

    monkeypatch.setattr(cp3c, "pin_issues", boom)
    with pytest.raises(ValueError, match="not a context refusal"):
        cp3c.refinancing_risk(pack=pack, submission=submission, upstream=upstream)
    with pytest.raises(ValueError, match="not a context refusal"):
        connect._submit(store, attempt, json.dumps(payload))


def test_a_long_refusal_with_several_problems_is_one_clipped_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = _seed(tmp_path, monkeypatch, CONTEXT, "positive")
    message = "; ".join(f"problem {i}: " + "x" * 120 for i in range(8))
    assert len(message) > MAX_ISSUE_CHARS

    def refuse(*_: object, **__: object) -> tuple[str, ...]:
        raise ContextRefused(message.split("; "))

    monkeypatch.setattr(cp3c, "pin_issues", refuse)
    connect._submit(store, attempt, json.dumps(_payload(store, attempt, "match")))
    issues = _issues(store, attempt)
    assert len(issues) == 1
    assert issues[0].startswith("Context refused: problem 0: ")
    assert len(issues[0]) <= MAX_ISSUE_CHARS and issues[0].endswith("…")


@pytest.mark.parametrize("context", (NO_CP3C, None))
def test_nothing_is_mapped_when_no_context_pins_the_module(
    context: str | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No pin, no context: `pin_issues` is never called, so no submitted figure is formatted."""

    def never(*_: object, **__: object) -> tuple[str, ...]:
        raise AssertionError("pin_issues called without a pin")

    monkeypatch.setattr(cp3c, "pin_issues", never)
    store, _, attempt = _seed(tmp_path, monkeypatch, context, "positive")
    connect._submit(store, attempt, connect.literal(store, attempt))
    assert _settled_module(store, attempt).limitations


# --- the accepted run -----------------------------------------------------------------------------
def test_a_matching_submission_is_labelled_user_supplied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, attempt = _run(tmp_path, monkeypatch, "match")
    module = _settled_module(store, attempt)
    want = EXPECTED["cases"]["match"]
    base = _base()
    assert want["pinned_line"] == want["limitation_rows"]["text"] == PINNED
    assert want["own_limitations"] == [*base["own_limitations"], PINNED]
    assert list(module.limitations) == [*want["own_limitations"], SYNTHETIC]
    assert _rows(module, "T3D.7") == base["T3D.7_rows"]  # `400 bp (analyst assumption)`
    assert _rows(module, "T3D.9") == base["T3D.9_rows"]
    assert _rows(module, "T3D.8") == [*base["T3D.8_rows"], LABEL]
    last = next(t for t in module.tables if t.table_id == "T3D.8").rows[-1]
    assert (last.row_id, last.label, last.fact_ids) == (
        "r14",
        "Pinned assumptions",
        ("T3D.8.r14",),
    )
    assert [c.claim_id for c in module.claims] == [c["claim_id"] for c in base["claims"]]
    again = cp3c.refinancing_risk(
        pack=pack,
        submission=_submission(store, attempt, "match"),
        upstream=connect.upstream_of(store, attempt),
    )
    assert (again.facts, again.tables, again.claims) == (module.facts, module.tables, module.claims)


def test_the_verifier_replay_reproduces_the_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Probe and the entry validator rebuild the settled head from the pack and the payload."""
    store, pack, attempt = _run(tmp_path, monkeypatch, "match")
    done = connect.finished(store, attempt)
    cp3c.probe(store, store.read(), done)
    outcome = cp3c.ENTRY_VALIDATOR(store, pack, done)
    assert outcome.issues == () and outcome.retained_as(done.steps[0])
    assert outcome.output is not None
    assert cp3c.RefinancingRiskReport.model_validate_json(outcome.output).limitations[-1] == PINNED


@pytest.mark.parametrize(("context", "case"), ((NO_CP3C, "no_pin"), (None, "no_context")))
def test_no_context_or_no_pin_equals_the_frozen_base_oracle(
    context: str | None, case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = _seed(tmp_path, monkeypatch, context, "positive")
    connect._submit(store, attempt, connect.literal(store, attempt))
    module = _settled_module(store, attempt)
    connect.assert_module_equals_oracle(module, "positive")
    assert list(module.limitations) == [*_base()["own_limitations"], SYNTHETIC]
    assert PINNED not in module.limitations and LABEL not in _rows(module, "T3D.8")
    assert case in CASES


# --- the label on every path that composes the own limitations ----------------------------------------
_CASES = tm.PACK_CASES  # the fixtures compose operands only, never the own limitations


@pytest.mark.parametrize("case", _CASES)
def test_the_label_is_last_on_every_base_fixture(case: str) -> None:
    inputs = tm._inputs(case)
    base = cp3c.compute(inputs)
    assert list(base.own_limitations) == _base(case)["own_limitations"]
    assert PINNED not in base.own_limitations
    pinned = cp3c.compute(replace(inputs, pinned=True))
    assert pinned.own_limitations == (*base.own_limitations, PINNED)
    assert [list(r) for r in pinned.gaps_ledger.rows] == [*_base(case)["T3D.8_rows"], LABEL]
    assert [list(r) for r in pinned.judgments.rows] == _base(case)["T3D.7_rows"]
    assert [list(r) for r in pinned.trace.rows] == _base(case)["T3D.9_rows"]
    assert pinned.claims == base.claims and pinned.tables == base.tables


def test_the_label_is_last_after_a_path_limitation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive run's two path limitations (Gap rows) come before the pinned row."""
    store, _, attempt = _run(tmp_path, monkeypatch, "match")
    rows = _rows(_settled_module(store, attempt), "T3D.8")
    assert rows[-3:] == [["Asset sale or equity support", "Gap"]] + [
        ["Liability-management exercise", "Gap"],
        LABEL,
    ]


# --- the line CP-3C inherits from CP-2D -------------------------------------------------------------
def _carried(module: Module, line: str) -> int:
    return [*module.limitations, *module.inherited_limitations].count(line)


def test_the_cp2d_pinned_line_is_inherited_once_when_the_context_pins_cp2d(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = _run(tmp_path, monkeypatch, "match", context=CONTEXT)
    module = _settled_module(store, attempt)
    assert CP2D_PINNED in module.inherited_limitations
    assert CP2D_PINNED not in module.limitations
    assert _carried(module, CP2D_PINNED) == 1 and _carried(module, PINNED) == 1


def test_no_cp2d_pinned_line_when_the_context_does_not_pin_cp2d(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = _run(tmp_path, monkeypatch, "match", context=NO_CP2D)
    module = _settled_module(store, attempt)
    assert _carried(module, CP2D_PINNED) == 0 and _carried(module, PINNED) == 1
    assert _rows(module, "T3D.7") == _base()["T3D.7_rows"]


# --- the label with a facility line, the clipped refusal and the dedupe (T6 L1, L2, I1) -------------
def _not_stated(inputs: cp3c.Cp3cInputs, name: str) -> cp3c.Cp3cInputs:
    (terms,) = inputs.cp1.facilities
    terms = replace(terms, **{name: replace(getattr(terms, name), text="NOT_STATED")})
    return replace(inputs, cp1=replace(inputs.cp1, facilities=(terms,)))


FACILITY_VARIANTS = {
    "seniority_missing": lambda i: connect._with_term(i, "cp1", "seniority", "missing"),
    "secured_not_stated": lambda i: _not_stated(i, "secured_status"),
    "amortisation_missing": lambda i: connect._with_term(
        i, "cp1", "annual_amortisation", "missing"
    ),
    "principal_missing": lambda i: connect._with_term(i, "cp2d", "principal", "missing"),
    "maturity_missing": lambda i: connect._with_term(i, "cp2d", "maturity_date", "missing"),
}


@pytest.mark.parametrize("case", tm.PACK_CASES)
@pytest.mark.parametrize("variant", list(FACILITY_VARIANTS))
def test_k13_the_label_is_last_with_facility_lines(case: str, variant: str) -> None:
    inputs = FACILITY_VARIANTS[variant](tm._inputs(case))
    base = cp3c.compute(inputs)
    pinned = cp3c.compute(replace(inputs, pinned=True))
    base_rows = [list(r) for r in base.gaps_ledger.rows]
    assert [r for r in base_rows if r[0].startswith("Facility ")], "a facility line is composed"
    assert PINNED not in base.own_limitations
    assert pinned.own_limitations == (*base.own_limitations, PINNED)
    assert [list(r) for r in pinned.gaps_ledger.rows] == [*base_rows, LABEL]


def test_k13_journal_with_a_facility_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pack = _pack(tmp_path / "ctx", CONTEXT)
    monkeypatch.setattr(connect, "make_pack", lambda **_: pack)
    module = connect.cp1_module(pack.run, terms={"seniority": "NOT_STATED"})
    store, _, attempt = connect.seed(tmp_path / "run", "positive", cp1=module)
    connect._submit(store, attempt, json.dumps(_payload(store, attempt, "match")))
    done = connect.finished(store, attempt)
    settled = _settled_module(store, attempt)
    rows = _rows(settled, "T3D.8")
    assert any(r[0].startswith("Facility ") for r in rows)
    own = [x for x in settled.limitations if x != SYNTHETIC]
    assert own[-1] == PINNED and own.count(PINNED) == 1 and rows[-1] == LABEL
    cp3c.probe(store, store.read(), done)


def test_k39_the_refusal_line_is_clipped_before_the_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_pin_lines` itself returns one line of at most MAX_ISSUE_CHARS for a long refusal."""
    store, pack, attempt = _seed(tmp_path, monkeypatch, CONTEXT, "positive")
    sub = _submission(store, attempt, "match")
    problems = [f"problem {i}: " + "x" * 120 for i in range(8)]

    def refuse(*_: object, **__: object) -> tuple[str, ...]:
        raise ContextRefused(problems)

    monkeypatch.setattr(cp3c, "pin_issues", refuse)
    got = cp3c._pin_lines(pack, sub)
    assert len(got) == 1 and got[0].startswith("Context refused: problem 0: ")
    assert len(got[0]) <= MAX_ISSUE_CHARS


DUP_LINE = "paths[repay_from_resources].basis_refs: names a fact the view does not offer"


@pytest.mark.parametrize("context", (CONTEXT, None))
def test_k47_the_step_issues_are_deduplicated(
    context: str | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two unoffered basis_refs on one path give their line once in the journaled step, then the
    pin line (bps 401 under the context)."""
    store, _, attempt = _seed(tmp_path, monkeypatch, context, "positive")
    body = _payload(store, attempt, "match")
    body["repricing"]["bps"] = 401
    path = next(p for p in body["paths"] if p["kind"] == "repay_from_resources")
    path["basis_refs"] = [*path["basis_refs"], "nope-1", "nope-2"]
    connect._submit(store, attempt, json.dumps(body))
    step = list(connect.finished(store, attempt).steps[0].issues)
    pin = ["assumptions.cp3c.repricing_bps: pinned 400; submitted 401"] if context else []
    assert step == [DUP_LINE, *pin]
