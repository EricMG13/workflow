"""CP-4C honours the EV multiple pinned in the context file (Phase 6 Task 8).

Expectations come from `cases/pins-context-owner/{expected,submissions}.json` (the CP-4C entry) and
the frozen base oracle `cases/cp4c-owner/expected.json`, never from the code under test. Each case
runs on a real `Execution` seeded as in `tests/test_connect_cp4c.py`, over the base run's pack with
the `prepare`d context source last. Fast: no store promotion run (`tests/test_owner_cp4c.py`).

Precedence (Phase 7 Q4): when the pin is set it wins over any CP-1C-selected multiple. Nothing
offers a multiple before Phase 7, so the RED with an offered multiple belongs there.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp4c as connect
import test_method_cp4c as tm

from deploy_vii.contracts import Module
from deploy_vii.execution import MAX_ISSUE_CHARS, Attempt, Execution
from deploy_vii.preparation import PreparedPack, prepare
from deploy_workflow.context import (
    CONTEXT_SOURCE_ID,
    ContextRefused,
    load_context,
    preparation_request,
)
from deploy_workflow.owners import cp3d, cp4c, pins
from deploy_workflow.owners.pins import pinned_line

ORACLE = Path(__file__).resolve().parents[1] / "cases" / "pins-context-owner"
EXPECTED: dict[str, Any] = json.loads((ORACLE / "expected.json").read_text())["modules"]["CP-4C"]
CASES: dict[str, Any] = json.loads((ORACLE / "submissions.json").read_text())["modules"]["CP-4C"][
    "cases"
]
PINNED = pinned_line("CP-4C")
CP2A_PINNED = pinned_line("CP-2A")
REFUSED = ("differs", "base_positive", "not_assessed", "multi_case")
CONTEXT = "context-distressed_restructuring.json"
NO_CP2A = "context-distressed_restructuring-no-cp2a.json"
NO_CP4C = "context-distressed_restructuring-no-cp4c.json"
SYNTHETIC = connect.SYNTHETIC
KEY = "valuation[*].multiple"
_BASE_PACK = connect._pack  # `_seed` replaces `connect._pack` for the run
_FINISH = connect._finish


def _pack(tmp_path: Path, context: str | None, base_case: str) -> PreparedPack:
    """The base run's pack with the prepared context source appended last."""
    base = _BASE_PACK(base_case)
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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    context: str | None,
    base_case: str,
    *,
    cp2a_limitation: str | None = None,
) -> tuple[Execution, PreparedPack, Attempt]:
    """`cp2a_limitation` replaces the one limitation the CP-2A head settles with (the head, not
    CP-4C, is where CP-2A's pinned line lives)."""
    pack = _pack(tmp_path, context, base_case)
    monkeypatch.setattr(connect, "_pack", lambda *_, **__: pack)
    if cp2a_limitation is not None:

        def finish(store: Execution, module_id: str, facts: Any, note: Any, *rest: Any) -> None:
            _FINISH(
                store, module_id, facts, cp2a_limitation if module_id == "CP-2A" else note, *rest
            )

        monkeypatch.setattr(connect, "_finish", finish)
    return connect.seed(tmp_path / "run", base_case)


def _payload(case: str) -> dict[str, Any]:
    spec = CASES[case]
    bound: dict[str, Any] = tm._bind_all(copy.deepcopy(spec["payload"]), spec["base_case"])
    return bound


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    *,
    payload: dict[str, Any] | None = None,
    context: str | None = None,
    cp2a_limitation: str | None = None,
) -> tuple[Execution, PreparedPack, Attempt]:
    spec = CASES[case]
    chosen = spec["context"] if context is None else context
    store, pack, attempt = _seed(
        tmp_path, monkeypatch, chosen, spec["base_case"], cp2a_limitation=cp2a_limitation
    )
    body = _payload(case) if payload is None else payload
    connect._submit(store, attempt, json.dumps(body))
    return store, pack, attempt


def _issues(store: Execution, attempt: Attempt) -> list[str]:
    return list(connect._finished(store, attempt).issues)


def _submission(payload: dict[str, Any]) -> cp4c.RestructuringSubmission:
    return cp4c.RestructuringSubmission.model_validate_json(json.dumps(payload))


def _settled_module(store: Execution, attempt: Attempt) -> Module:
    done = connect._finished(store, attempt)
    assert done.status == "finished" and done.issues == ()
    return store.head_module(connect._head(store, connect.MODULE))


def _base(case: str = "positive") -> dict[str, Any]:
    base: dict[str, Any] = connect.EXPECTED["cases"][case]
    return base


def _pin_tail(case: str) -> list[str]:
    tail: list[str] = EXPECTED["cases"][case]["issues"]
    return tail


# --- the refusals ---------------------------------------------------------------------------------
@pytest.mark.parametrize("case", REFUSED)
def test_a_differing_pin_is_a_validator_refusal_with_the_oracle_lines(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = _run(tmp_path, monkeypatch, case)
    assert connect._finished(store, attempt).steps[0].status == "invalid"
    assert _issues(store, attempt) == _pin_tail(case)
    assert not [h for h in store.read().heads if h.module_id == connect.MODULE]


@pytest.mark.parametrize("case", REFUSED)
def test_the_composer_gate_raises_on_the_pin_lines_joined_exactly(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = CASES[case]
    store, pack, attempt = _seed(tmp_path, monkeypatch, spec["context"], spec["base_case"])
    upstream = connect._upstream(store, attempt)
    with pytest.raises(ValueError) as caught:
        cp4c.restructuring(pack=pack, submission=_submission(_payload(case)), upstream=upstream)
    assert str(caught.value) == "; ".join(_pin_tail(case))
    assert len(_pin_tail("base_positive")) == 2  # several multiples each give a pin line


def test_the_index_follows_the_path_and_the_multiple_is_shown_as_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """3.0 stays 3.0 (not 3), and lines 0 and 2 carry their own index: a mapping that drops the
    index or the position, or dedupes equal strings, fails here."""
    payload = _payload("match")
    for case, text in zip(payload["valuation"], ("3.50", "4.0", "3.50"), strict=True):
        case["multiple"] = text
    store, _, attempt = _run(tmp_path, monkeypatch, "match", payload=payload)
    pin = [x for x in _issues(store, attempt) if x.startswith("assumptions.cp4c.")]
    assert pin == [
        "assumptions.cp4c.ev_multiple (valuation[0].multiple): pinned 4; submitted 3.50",
        "assumptions.cp4c.ev_multiple (valuation[2].multiple): pinned 4; submitted 3.50",
    ]
    assert _issues(store, attempt)[-2:] == pin  # the pin lines come last


@pytest.mark.parametrize("text", ("0.4", "40", "4.10", "3.99", "4.01", "04.5", "99.99", "0"))
def test_every_other_multiple_is_shown_as_typed(
    text: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mapping that truncates, strips, pads or reformats the typed value fails here: 0.4 and 40
    are a shift and an extension of the pin."""
    payload = _payload("match")
    payload["valuation"][1]["multiple"] = text
    store, _, attempt = _run(tmp_path, monkeypatch, "match", payload=payload)
    line = f"assumptions.cp4c.ev_multiple (valuation[1].multiple): pinned 4; submitted {text}"
    assert _issues(store, attempt)[-1] == line


def test_the_mapped_submission_is_the_typed_multiples_in_case_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutants that truncate, strip, dedupe or reorder the list, or rename the key, fail here."""
    seen: list[Any] = []
    real = pins.pin_issues

    def spy(module_id: str, pack: PreparedPack, submitted: Any) -> tuple[str, ...]:
        seen.append((module_id, dict(submitted)))
        return real(module_id, pack, submitted)

    monkeypatch.setattr(cp4c, "pin_issues", spy)
    payload = _payload("match")
    for case, text in zip(payload["valuation"], ("4.50", "4.0", "4.50"), strict=True):
        case["multiple"] = text
    store, pack, attempt = _seed(tmp_path, monkeypatch, CONTEXT, "positive")
    got = cp4c._pin_lines(pack, _submission(payload))
    assert seen == [("CP-4C", {KEY: ["4.50", "4.0", "4.50"]})]
    assert len(got) == 2 and "valuation[0]" in got[0] and "valuation[2]" in got[1]
    del store, attempt


def test_a_content_issue_comes_before_the_pin_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _payload("base_positive")
    payload["assessment"]["confidence"] = "High"  # not allowed, as well as off the pin
    store, _, attempt = _run(tmp_path, monkeypatch, "base_positive", payload=payload)
    issues = _issues(store, attempt)
    assert issues[0].startswith("assessment.confidence: High is not allowed")
    assert issues[1:] == _pin_tail("base_positive")


def test_a_non_numeric_multiple_is_a_shape_refusal_with_no_pin_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = _run(tmp_path, monkeypatch, "non_numeric")
    assert _issues(store, attempt) == _pin_tail("non_numeric")
    assert not any("pinned" in line for line in _issues(store, attempt))


def test_pin_lines_follow_the_stale_only_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, attempt = _seed(tmp_path, monkeypatch, CONTEXT, "positive")
    submission = _submission(_payload("base_positive"))
    good = connect._upstream(store, attempt)
    refused = "Required upstream is unrun, stale or blocked"
    stale = replace(good, current=refused)
    got = cp4c._lines(pack, submission, stale)
    assert got[-2:] == tuple(_pin_tail("base_positive")) and got[:-2]
    assert got[:-2] == cp4c.validate_restructuring(pack=pack, submission=submission, upstream=stale)


# --- the catch ------------------------------------------------------------------------------------
def test_a_context_that_differs_from_the_run_is_one_refusal_line_after_the_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P6-P3: only `ContextRefused` is caught; it becomes `Context refused: <message>`, with no
    pin lines, after the content issues. The validator is handed another run's pack."""
    store, _, attempt = _run(tmp_path, monkeypatch, "match")
    done = connect._finished(store, attempt)
    other = _pack(tmp_path / "other", "context-credit_snapshot.json", "positive")
    refused = list(cp4c.ENTRY_VALIDATOR(store, other, done).issues)
    assert len(refused) == 1 and refused[0].startswith("Context refused: ")
    assert "pinned" not in refused[0]
    upstream = connect._upstream(store, attempt)
    with pytest.raises(ValueError, match="Context refused"):
        cp4c.restructuring(pack=other, submission=_submission(_payload("match")), upstream=upstream)
    bad = _payload("match")
    bad["assessment"]["confidence"] = "High"
    got = cp4c._lines(other, _submission(bad), upstream)
    assert got[0].startswith("assessment.confidence: High is not allowed")
    assert got[1:] == tuple(refused)


def test_only_context_refused_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Widening the catch to `ValueError` must fail: any other `ValueError` escapes the step
    validator (through `submit`) and the composer."""
    store, pack, attempt = _seed(tmp_path, monkeypatch, CONTEXT, "positive")
    payload = _payload("match")
    upstream = connect._upstream(store, attempt)

    def boom(*_: object, **__: object) -> tuple[str, ...]:
        raise ValueError("not a context refusal")

    monkeypatch.setattr(cp4c, "pin_issues", boom)
    with pytest.raises(ValueError) as caught:
        cp4c.restructuring(pack=pack, submission=_submission(payload), upstream=upstream)
    assert str(caught.value) == "not a context refusal"
    with pytest.raises(ValueError) as again:
        cp4c._pin_lines(pack, _submission(payload))
    assert str(again.value) == "not a context refusal"
    with pytest.raises(ValueError, match="not a context refusal"):
        connect._submit(store, attempt, json.dumps(payload))


def test_a_long_refusal_with_several_problems_is_one_clipped_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, attempt = _seed(tmp_path, monkeypatch, CONTEXT, "positive")
    message = "; ".join(f"problem {i}: " + "x" * 120 for i in range(8))
    assert len(message) > MAX_ISSUE_CHARS

    def refuse(*_: object, **__: object) -> tuple[str, ...]:
        raise ContextRefused(message.split("; "))

    monkeypatch.setattr(cp4c, "pin_issues", refuse)
    direct = cp4c._pin_lines(pack, _submission(_payload("match")))  # the clip, unit-asserted
    assert len(direct) == 1
    assert direct[0].startswith("Context refused: problem 0: ")
    assert len(direct[0]) <= MAX_ISSUE_CHARS and direct[0].endswith("…")
    connect._submit(store, attempt, json.dumps(_payload("match")))
    assert _issues(store, attempt) == list(direct)


@pytest.mark.parametrize("context", (NO_CP4C, None))
def test_nothing_is_mapped_when_no_context_pins_the_module(
    context: str | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No pin, no context: `pin_issues` is never called, so no submitted figure is mapped."""

    def never(*_: object, **__: object) -> tuple[str, ...]:
        raise AssertionError("pin_issues called without a pin")

    monkeypatch.setattr(cp4c, "pin_issues", never)
    store, pack, attempt = _seed(tmp_path, monkeypatch, context, "positive")
    assert cp4c._pin_lines(pack, _submission(_payload("no_pin"))) == ()
    connect._submit(store, attempt, json.dumps(_payload("no_pin")))
    assert _settled_module(store, attempt).limitations


# --- the accepted run -----------------------------------------------------------------------------
@pytest.mark.parametrize("case", ("match", "one_multiple"))
def test_a_matching_submission_is_labelled_user_supplied(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, attempt = _run(tmp_path, monkeypatch, case)
    module = _settled_module(store, attempt)
    want = EXPECTED["cases"]["match"]["recomputed_case"]
    assert want["pinned_line"] == want["own_limitations"][-1] == PINNED
    assert list(module.limitations) == [*want["own_limitations"], SYNTHETIC]
    assert module.limitations[-2] == PINNED  # last of the own limitations
    assert list(module.limitations).count(PINNED) == 1
    own = [f for f in module.facts if f.table_id.startswith("T4E.")]
    assert [f.fact_id for f in own] == [e["fact_id"] for e in want["facts"]]
    assert [(f.text, f.status) for f in own] == [
        (e.get("text"), e["status"]) for e in want["facts"]
    ]
    assert [(c.claim_id, c.limitation) for c in module.claims] == [
        (c["claim_id"], c["limitation"]) for c in want["claims"]
    ]
    again = cp4c.restructuring(
        pack=pack,
        submission=_submission(_payload(case)),
        upstream=connect._upstream(store, attempt),
    )
    assert (again.facts, again.tables, again.claims) == (module.facts, module.tables, module.claims)
    assert again.limitations == tuple(want["own_limitations"])


def test_the_verifier_replay_reproduces_the_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Probe and the entry validator rebuild the settled head from the pack and the payload."""
    store, pack, attempt = _run(tmp_path, monkeypatch, "match")
    done = connect._finished(store, attempt)
    cp4c.probe(store, store.read(), done)
    outcome = cp4c.ENTRY_VALIDATOR(store, pack, done)
    assert outcome.issues == () and outcome.retained_as(done.steps[0])
    assert outcome.output is not None
    assert cp4c.RestructuringReport.model_validate_json(outcome.output).limitations[-1] == PINNED


@pytest.mark.parametrize(("context", "case"), ((NO_CP4C, "no_pin"), (None, "no_context")))
def test_no_context_or_no_pin_equals_the_frozen_base_oracle(
    context: str | None, case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = _seed(tmp_path, monkeypatch, context, "positive")
    connect._submit(store, attempt, json.dumps(_payload(case)))
    module = _settled_module(store, attempt)
    want = _base()
    own = [f for f in module.facts if f.table_id.startswith("T4E.")]
    assert [f.fact_id for f in own] == [e["fact_id"] for e in want["facts"]]
    assert [(f.text, f.status) for f in own] == [
        (e.get("text"), e["status"]) for e in want["facts"]
    ]
    assert [(c.claim_id, c.text, c.limitation) for c in module.claims] == [
        (c["claim_id"], tm._bind(c["text"], "positive"), c["limitation"]) for c in want["claims"]
    ]
    assert list(module.limitations) == [*want["own_limitations"], SYNTHETIC]
    assert PINNED not in module.limitations


# --- the label on every path that composes the own limitations ----------------------------------------
@pytest.mark.parametrize("case", tm.CASES)
def test_the_label_is_last_on_every_base_fixture(case: str) -> None:
    inputs = tm._inputs(case)
    base = cp4c.compute(inputs)
    assert list(base.own_limitations) == _base(case)["own_limitations"]
    assert PINNED not in base.own_limitations
    pinned = cp4c.compute(replace(inputs, pinned=True))
    assert pinned.own_limitations == (*base.own_limitations, PINNED)
    assert [c.fact for c in pinned.cells] == [c.fact for c in base.cells]
    assert pinned.claims == base.claims and pinned.tables == base.tables


def test_the_label_is_last_after_the_gaps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store, _, attempt = _run(tmp_path, monkeypatch, "match")
    limitations = list(_settled_module(store, attempt).limitations)
    assert limitations[-3].startswith("Gap (")
    assert limitations[-2:] == [PINNED, SYNTHETIC]


# --- the line CP-4C inherits from the settled CP-2A head ----------------------------------------------
def _carried(module: Module, line: str) -> int:
    return [*module.limitations, *module.inherited_limitations].count(line)


def test_the_cp2a_pinned_line_is_inherited_once_from_the_settled_cp2a_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = _run(tmp_path, monkeypatch, "match", cp2a_limitation=CP2A_PINNED)
    module = _settled_module(store, attempt)
    assert CP2A_PINNED in module.inherited_limitations
    assert CP2A_PINNED not in module.limitations
    assert _carried(module, CP2A_PINNED) == 1 and _carried(module, PINNED) == 1


def test_cp4c_never_composes_cp2a_pinned_line_itself(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The context pins CP-2A, but the settled CP-2A head carries no such line: CP-4C does not
    supply it (the line comes from the head, never from a recomposed CP-2A)."""
    store, _, attempt = _run(tmp_path, monkeypatch, "match")
    module = _settled_module(store, attempt)
    assert _carried(module, CP2A_PINNED) == 0 and _carried(module, PINNED) == 1


def test_no_cp2a_pinned_line_when_the_context_does_not_pin_cp2a(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = _run(tmp_path, monkeypatch, "match", context=NO_CP2A)
    module = _settled_module(store, attempt)
    assert _carried(module, CP2A_PINNED) == 0 and _carried(module, PINNED) == 1
    assert pins.pins_of("CP-2A", store.pack()) is None


# --- review kills (Task 8 fix 1) --------------------------------------------------------------------
def test_the_index_is_the_submitted_position(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rotated cases: the line names the submitted position, not the case-id order."""
    store, pack, attempt = _seed(tmp_path, monkeypatch, CONTEXT, "positive")
    payload = _payload("match")
    cases = payload["valuation"]
    for case, text in zip(cases, ("4.0", "3.5", "4.00"), strict=True):
        case["multiple"] = text
    payload["valuation"] = [cases[1], cases[2], cases[0]]
    line = "assumptions.cp4c.ev_multiple (valuation[0].multiple): pinned 4; submitted 3.5"
    assert cp4c._pin_lines(pack, _submission(payload)) == (line,)
    connect._submit(store, attempt, json.dumps(payload))
    issues = _issues(store, attempt)
    assert issues[-1] == line
    assert sum(i.startswith("assumptions.cp4c") for i in issues) == 1


def _junk(pack: PreparedPack) -> PreparedPack:
    """The pack whose context source has every pinned figure junk: a real, long refusal."""
    src = next(s for s in pack.sources if s.source_id == CONTEXT_SOURCE_ID)
    doc = json.loads("\n".join(s.text for s in src.spans))
    a = doc["assumptions"]
    for sc in a["cp2a"]["scenarios"]:
        sc["ebitda_decline_pct"] = sc["interest_increase_pct"] = "x"
    a["cp2d"]["horizon_months"] = a["cp2d"]["minimum_cash_m"] = "x"
    a["cp3c"]["repricing_bps"] = a["cp3d"]["recovery_pct"] = a["cp4c"]["ev_multiple"] = "x"
    span = src.spans[0].model_copy(update={"text": json.dumps(doc, indent=2)})
    rest = tuple(s for s in pack.sources if s.source_id != CONTEXT_SOURCE_ID)
    return PreparedPack(run=pack.run, sources=(*rest, src.model_copy(update={"spans": (span,)})))


def test_a_long_real_refusal_is_clipped_at_the_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, pack, attempt = _run(tmp_path, monkeypatch, "match")
    done = connect._finished(store, attempt)
    bad = _junk(pack)
    out = cp4c.ENTRY_VALIDATOR(store, bad, done)
    (line,) = out.issues
    assert out.output is None and line.startswith("Context refused: assumptions.cp2a.")
    assert len(line) == MAX_ISSUE_CHARS and line.endswith("…")
    assert cp4c._pin_lines(bad, _submission(_payload("match"))) == (line,)


# --- a model-written copy of the pinned label (Phase 6 phase review M1) ---------------------------
@pytest.mark.parametrize("variant", ["exact", "shouted", "spaced"])
def test_a_gap_cannot_carry_the_pinned_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    line = pinned_line("CP-4C")
    text = {"exact": line, "shouted": line.upper(), "spaced": line.replace(" ", "  ")}[variant]
    payload = _payload("no_context")
    gap = copy.deepcopy(payload["gaps"][0]) if payload.get("gaps") else {"severity": "high"}
    gap["gap"] = text
    payload["gaps"] = [*payload.get("gaps", []), gap]
    store, _, attempt = _run(tmp_path, monkeypatch, "no_context", payload=payload)
    assert f"gaps[{len(payload['gaps']) - 1}].gap: {cp3d.PIN_LABEL_FORGED}" in _issues(
        store, attempt
    )


@pytest.mark.parametrize("field", ["claim_name", "valuation_label"])
def test_a_claim_name_or_valuation_label_cannot_carry_the_pinned_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Both are interpolated into Python limitation sentences (round 2 M1-b)."""
    store, _, attempt = _seed(tmp_path, monkeypatch, None, "gap")
    payload = tm._bind_all(copy.deepcopy(tm._payload("gap")), "gap")
    line = pinned_line("CP-4C")
    if field == "claim_name":
        index = next(
            i for i, c in enumerate(payload["claims"]) if c["amount_source"] == "not_stated"
        )
        payload["claims"][index]["name"] = line
        path = f"claims[{index}].name"
    else:
        payload["valuation"][0]["label"] = line
        path = "valuation[0].label"
    connect._submit(store, attempt, json.dumps(payload))
    assert f"{path}: {cp3d.PIN_LABEL_FORGED}" in _issues(store, attempt)
