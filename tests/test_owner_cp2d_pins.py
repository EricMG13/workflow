"""CP-2D honours the horizon and minimum cash pinned in the context file (Phase 6 Task 4).

Expectations come from `cases/pins-context-owner/{expected,submissions}.json` (the CP-2D entry) and
the frozen base oracle `cases/cp2d-owner/expected.json`, never from the code under test. Each case
runs on a real `Execution` seeded as in `tests/test_connect_cp2d.py`, over the base run's pack with
the `prepare`d context source last. Fast: no store promotion run (`tests/test_owner_cp2d.py`).
"""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2d as connect
import test_method_cp2d as tm

from deploy_vii.contracts import Module
from deploy_vii.execution import MAX_ISSUE_CHARS, Attempt, Execution
from deploy_vii.preparation import PreparedPack, prepare
from deploy_workflow.context import (
    CONTEXT_SOURCE_ID,
    ContextRefused,
    load_context,
    preparation_request,
)
from deploy_workflow.owners import cp2d
from deploy_workflow.owners.pins import pinned_line

ORACLE = Path(__file__).resolve().parents[1] / "cases" / "pins-context-owner"
EXPECTED: dict[str, Any] = json.loads((ORACLE / "expected.json").read_text())["modules"]["CP-2D"]
CASES: dict[str, Any] = json.loads((ORACLE / "submissions.json").read_text())["modules"]["CP-2D"][
    "cases"
]
PINNED = pinned_line("CP-2D")
REFUSED = ("differs", "differs_minimum_cash", "differs_both", "absence")
ALL_CASES = (*REFUSED, "match", "no_pin", "no_context")


def _pack(tmp_path: Path, context: str | None) -> PreparedPack:
    """The base CP-2D run's pack with the prepared context source appended last."""
    base = connect.PACK
    if context is None:
        return base
    raw = (ORACLE / context).read_bytes()
    request = preparation_request(
        load_context(raw), run_id=base.run.run_id, context_path="context.json", sources=()
    )
    (tmp_path / "root").mkdir()
    (tmp_path / "root" / "context.json").write_bytes(raw)
    prepared = prepare(request, tmp_path / "root", tmp_path / "pack")
    found = tuple(s for s in prepared.sources if s.source_id == CONTEXT_SOURCE_ID)
    assert len(found) == 1
    return PreparedPack(run=base.run, sources=(*base.sources, *found))


def _seed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, context: str | None, base_case: str
) -> tuple[Execution, Attempt]:
    pack = _pack(tmp_path, context)
    monkeypatch.setattr(connect, "PACK", pack)
    return connect.make_upstream(tmp_path / "run", base_case)


def _payload(case: str) -> dict[str, Any]:
    bound: dict[str, Any] = tm._bind(CASES[case]["payload"])
    return bound


def _submission(payload: dict[str, Any]) -> cp2d.LiquidityBridgeSubmission:
    return cp2d.LiquidityBridgeSubmission.model_validate_json(json.dumps(payload))


def _upstream(store: Execution, attempt: Attempt) -> cp2d.Upstream:
    return cp2d.cp2d_upstream(store=store, attempt=attempt)


def _journal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> Any:
    store, attempt = _seed(tmp_path, monkeypatch, CASES[case]["context"], CASES[case]["base_case"])
    cp2d.submit(store, attempt.ticket_id, cp2d.STEP_ID, json.dumps(_payload(case)), None)
    return store, attempt, connect._finished(store, attempt.ticket_id)


def _report(
    store: Execution, attempt: Attempt, payload: dict[str, Any]
) -> cp2d.LiquidityBridgeReport:
    return cp2d.liquidity_bridge(
        pack=store.pack(), submission=_submission(payload), upstream=_upstream(store, attempt)
    )


def _module(store: Execution, attempt: Attempt, payload: dict[str, Any]) -> Module:
    report = _report(store, attempt, payload)
    return cp2d.cp2d_module(report=report, inputs=attempt.inputs, attempt=attempt.number)


def _equals_base_oracle(module: Module, base_case: str, *, skip_limitations: bool = False) -> None:
    """The module equals the frozen `cases/cp2d-owner/expected.json` case, table by table."""
    want = tm.CASES[base_case]
    facts = {f.fact_id: f for f in module.facts}
    for table_id, table in want["tables"].items():
        got = next(t for t in module.tables if t.table_id == table_id)
        assert [r.label for r in got.rows] == [r[0] for r in table["rows"]]
        for row, (_, cells) in zip(got.rows, table["rows"], strict=True):
            for fact_id, cell in zip(
                row.fact_ids, cells if isinstance(cells, list) else [cells], strict=True
            ):
                assert fact_id == cell["fact_id"]
                connect._assert_fact(facts[fact_id], cell, base_case)
    assert [c.text for c in module.claims] == [c["template"] for c in want["claims"]]
    if not skip_limitations:
        assert list(module.limitations) == want["own_limitations"]
        ledger = next(t for t in module.tables if t.table_id == "T2E.7")
        assert [(r.label, facts[r.fact_ids[0]].text) for r in ledger.rows] == [
            (label, kind) for label, kind in want["T2E.7_rows"]
        ]


@pytest.mark.parametrize("case", REFUSED)
def test_a_differing_pin_is_a_journaled_refusal_with_the_oracle_lines(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, finished = _journal(tmp_path, monkeypatch, case)
    assert finished.status == "finished"
    assert list(finished.issues) == EXPECTED["cases"][case]["issues"]
    assert finished.steps[0].status == "invalid"


@pytest.mark.parametrize("case", REFUSED)
def test_the_composer_gate_raises_on_the_same_lines(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, attempt = _seed(tmp_path, monkeypatch, CASES[case]["context"], CASES[case]["base_case"])
    with pytest.raises(ValueError) as caught:
        _report(store, attempt, _payload(case))
    assert str(caught.value) == "; ".join(EXPECTED["cases"][case]["issues"])


def test_a_content_issue_comes_before_the_pin_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, attempt = _seed(tmp_path, monkeypatch, CASES["differs"]["context"], "positive")
    payload = _payload("differs")
    payload["minimum_cash"]["amount"] = "-1"
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(), submission=_submission(payload), upstream=_upstream(store, attempt)
    )
    assert issues == (
        cp2d.NEGATIVE_MINIMUM_ISSUE,
        "assumptions.cp2d.horizon_months: pinned 24; submitted 25",
        "assumptions.cp2d.minimum_cash_m: pinned 10; submitted -1",
    )


def test_a_stale_line_comes_before_the_pin_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, attempt = _seed(tmp_path, monkeypatch, CASES["differs"]["context"], "positive")
    stale = replace(_upstream(store, attempt), current="Required upstream is unrun")
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(), submission=_submission(_payload("differs")), upstream=stale
    )
    assert issues == (
        "Stale inputs: Required upstream is unrun",
        *EXPECTED["cases"]["differs"]["issues"],
    )


def test_a_shape_failure_gets_no_pin_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store, attempt = _seed(tmp_path, monkeypatch, CASES["differs"]["context"], "positive")
    payload = _payload("differs")
    payload["horizon_months"] = 24.0  # Contract is strict: a float for an int is a shape refusal
    cp2d.submit(store, attempt.ticket_id, cp2d.STEP_ID, json.dumps(payload), None)
    finished = connect._finished(store, attempt.ticket_id)
    assert finished.issues and not any("pinned" in line for line in finished.issues)


def test_match_composes_with_the_oracle_limitations_and_the_pinned_row_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Minimum cash `10.0` against the pin `10`; the horizon stays the JSON integer 24."""
    store, attempt, finished = _journal(tmp_path, monkeypatch, "match")
    assert finished.status == "finished" and finished.issues == ()
    module = _module(store, attempt, _payload("match"))
    want = EXPECTED["cases"]["match"]
    assert list(module.limitations) == want["own_limitations"]
    assert module.limitations[-1] == PINNED == want["pinned_line"]
    _equals_base_oracle(module, "positive", skip_limitations=True)
    rows = want["limitation_rows"]
    ledger = next(t for t in module.tables if t.table_id == rows["table_id"])
    facts = {f.fact_id: f for f in module.facts}
    assert [(r.label, facts[r.fact_ids[0]].text) for r in ledger.rows] == [
        tuple(x) for x in rows["T2E.7_rows_after"]
    ]
    last = ledger.rows[-1]
    assert (last.row_id, last.label, last.fact_ids[0]) == (
        rows["row_id"],
        rows["label"],
        rows["fact_id"],
    )
    assert facts[rows["fact_id"]].text == rows["kind"]
    assert rows["text"] == PINNED
    head = next(h for h in store.read().heads if h.module_id == cp2d.MODULE_ID)
    assert PINNED in store.head_module(head).limitations
    cp2d.probe(store, store.read(), finished)  # the verifier's replay reproduces the label


@pytest.mark.parametrize("case", ("no_pin", "no_context"))
def test_no_context_or_no_pin_equals_the_base_oracle(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, attempt, finished = _journal(tmp_path, monkeypatch, case)
    assert finished.status == "finished" and finished.issues == ()
    module = _module(store, attempt, _payload(case))
    assert PINNED not in module.limitations
    _equals_base_oracle(module, "positive")


@pytest.mark.parametrize("base_case", tm.PACK_CASES)
def test_the_label_is_last_on_every_path_that_composes_the_limitations(base_case: str) -> None:
    """Every base case (including the no-minimum-cash gap branch) and the pure function."""
    inputs = tm._inputs(base_case)
    want = tm.CASES[base_case]["own_limitations"]
    assert list(cp2d.compute(inputs).own_limitations) == want
    pinned = cp2d.compute(replace(inputs, pinned=True))
    assert list(pinned.own_limitations) == [*want, PINNED]
    assert pinned.gaps_ledger.rows[-1] == ("Pinned assumptions", "Limitation")
    assert len(pinned.gaps_ledger.rows) == len(want) + 1
    bridge = cp2d.bridge_of(inputs)
    got = cp2d.own_limitations(operands=inputs.operands, bridge=bridge, pinned=True)
    assert list(got) == [*want, PINNED]
    assert list(cp2d.own_limitations(operands=inputs.operands, bridge=bridge)) == want


def test_a_pinned_run_labels_the_long_horizon_report_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The label does not depend on the submitted case: a pinned run composed from the
    composer carries it on the real store path."""
    store, attempt, finished = _journal(tmp_path, monkeypatch, "match")
    assert finished.issues == ()
    report = _report(store, attempt, _payload("match"))
    assert report.limitations[-1] == PINNED


def test_a_context_that_differs_from_the_run_is_one_refusal_line_after_the_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P6-P3: only `ContextRefused` is caught; it becomes `Context refused: <message>`, with no
    pin lines, after the content issues."""
    store, attempt = _seed(tmp_path, monkeypatch, "context-credit_snapshot.json", "positive")
    pack, upstream = store.pack(), _upstream(store, attempt)
    positive = _submission(_payload("no_context"))
    issues = cp2d.validate_liquidity_bridge(pack=pack, submission=positive, upstream=upstream)
    assert len(issues) == 1 and issues[0].startswith("Context refused: run.pathway: context has")
    negative = _payload("no_context")
    negative["minimum_cash"]["amount"] = "-1"
    got = cp2d.validate_liquidity_bridge(
        pack=pack, submission=_submission(negative), upstream=upstream
    )
    assert got == (cp2d.NEGATIVE_MINIMUM_ISSUE, issues[0])
    with pytest.raises(ValueError, match="Context refused"):
        cp2d.liquidity_bridge(pack=pack, submission=positive, upstream=upstream)


def test_only_context_refused_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A `ValueError` that is not a `ContextRefused` escapes the validator."""
    store, attempt = _seed(tmp_path, monkeypatch, CASES["match"]["context"], "positive")

    def boom(*_: object, **__: object) -> tuple[str, ...]:
        raise ValueError("not a context refusal")

    monkeypatch.setattr(cp2d, "pin_issues", boom)
    with pytest.raises(ValueError, match="not a context refusal"):
        cp2d.validate_liquidity_bridge(
            pack=store.pack(),
            submission=_submission(_payload("match")),
            upstream=_upstream(store, attempt),
        )


def test_a_long_refusal_with_several_problems_is_one_clipped_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, attempt = _seed(tmp_path, monkeypatch, CASES["match"]["context"], "positive")
    message = "; ".join(f"problem {i}: " + "x" * 120 for i in range(8))
    assert len(message) > MAX_ISSUE_CHARS

    def refuse(*_: object, **__: object) -> tuple[str, ...]:
        raise ContextRefused(message.split("; "))

    monkeypatch.setattr(cp2d, "pin_issues", refuse)
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(),
        submission=_submission(_payload("match")),
        upstream=_upstream(store, attempt),
    )
    assert len(issues) == 1
    assert issues[0].startswith("Context refused: problem 0: ")
    assert len(issues[0]) <= MAX_ISSUE_CHARS and issues[0].endswith("…")


@pytest.mark.parametrize(
    ("amount", "horizon", "lines"),
    [
        ("1E+1", 24, []),  # Decimal('1E+1') equals the pin 10
        ("10.00", 24, []),
        ("0.1E+2", 24, []),
        ("10.01", 24, ["assumptions.cp2d.minimum_cash_m: pinned 10; submitted 10.01"]),
        ("1E+2", 24, ["assumptions.cp2d.minimum_cash_m: pinned 10; submitted 100"]),
        ("10", 25, ["assumptions.cp2d.horizon_months: pinned 24; submitted 25"]),
    ],
)
def test_equal_spellings_are_the_pin_and_unequal_values_are_refused(
    amount: str, horizon: int, lines: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, attempt = _seed(tmp_path, monkeypatch, CASES["match"]["context"], "positive")
    payload = _payload("match")
    payload["minimum_cash"]["amount"] = amount
    payload["horizon_months"] = horizon
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(), submission=_submission(payload), upstream=_upstream(store, attempt)
    )
    assert list(issues) == lines


def test_a_json_float_minimum_cash_is_compared_through_the_amount(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`MinimumCash.amount` is a Decimal: a JSON number is read as its decimal text (:90-91)."""
    store, attempt = _seed(tmp_path, monkeypatch, CASES["match"]["context"], "positive")
    payload = _payload("match")
    payload["minimum_cash"]["amount"] = 10.01
    submission = _submission(payload)
    assert submission.minimum_cash is not None
    assert submission.minimum_cash.amount == Decimal("10.01")
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(), submission=submission, upstream=_upstream(store, attempt)
    )
    assert list(issues) == EXPECTED["cases"]["differs_minimum_cash"]["issues"]
    payload["minimum_cash"]["amount"] = 10.0
    exact = _submission(payload)
    assert (
        cp2d.validate_liquidity_bridge(
            pack=store.pack(), submission=exact, upstream=_upstream(store, attempt)
        )
        == ()
    )
