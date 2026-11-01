"""CP-2E honours the shocks and hedge ratio pinned in the context file (Phase 6 Task 5).

Expectations come from `cases/pins-context-owner/{expected,submissions}.json` (the CP-2E entry) and
the frozen base oracle `cases/cp2e-owner/expected.json`, never from the code under test. Each case
runs `cp2e.ENTRY_VALIDATOR` over the base run's pack with the `prepare`d context source last, on
the duck-typed store of `tests/test_connect_cp2e.py`. Fast: no store run (`tests/test_owner_cp2e.py`).
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
import test_method_cp2e as tm
from cp2e_runs import make_pack

from deploy_vii.execution import MAX_ISSUE_CHARS, Execution, StepValidation
from deploy_vii.preparation import PreparedPack, prepare
from deploy_workflow.context import (
    CONTEXT_SOURCE_ID,
    ContextRefused,
    load_context,
    preparation_request,
)
from deploy_workflow.owners import cp2e
from deploy_workflow.owners.pins import pinned_line

ORACLE = Path(__file__).resolve().parents[1] / "cases" / "pins-context-owner"
EXPECTED: dict[str, Any] = json.loads((ORACLE / "expected.json").read_text())["modules"]["CP-2E"]
CASES: dict[str, Any] = json.loads((ORACLE / "submissions.json").read_text())["modules"]["CP-2E"][
    "cases"
]
BASE: dict[str, Any] = tm.EXPECTED["cases"]["positive"]
SHOCKS = pinned_line("CP-2E")
SHOCKS_AND_HEDGE = pinned_line("CP-2E", hedge_pinned=True)
REFUSED = (
    "differs",
    "differs_fx",
    "differs_hedge",
    "absence_hedge",
    "count_order_swapped",
    "count_order_one_shock",
    "count_order_fx_two",
    "non_numeric",
)
HEDGE60 = "context-credit_snapshot-hedge60.json"


def _pack(tmp_path: Path, context: str | bytes | None, base_case: str = "positive") -> PreparedPack:
    """The base CP-2E run's pack with the prepared context source appended last."""
    base = make_pack(base_case)
    if context is None:
        return base
    raw = (ORACLE / context).read_bytes() if isinstance(context, str) else context
    request = preparation_request(
        load_context(raw), run_id=base.run.run_id, context_path="context.json", sources=()
    )
    (tmp_path / "root").mkdir()
    (tmp_path / "root" / "context.json").write_bytes(raw)
    prepared = prepare(request, tmp_path / "root", tmp_path / "pack")
    found = tuple(s for s in prepared.sources if s.source_id == CONTEXT_SOURCE_ID)
    assert len(found) == 1
    return PreparedPack(run=base.run, sources=(*base.sources, *found))


def _store(payload: dict[str, Any] | str) -> Any:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    digest = hashlib.sha256(text.encode()).hexdigest()
    return SimpleNamespace(payload=lambda sha: text, digest=digest)


def _attempt(store: Any) -> Any:
    return SimpleNamespace(steps=(SimpleNamespace(payload_sha256=store.digest),), number=0)


def _validate(pack: PreparedPack, payload: dict[str, Any] | str) -> StepValidation:
    store = _store(payload)
    return cp2e.ENTRY_VALIDATOR(cast(Execution, store), pack, _attempt(store))


def _payload(case: str) -> dict[str, Any]:
    return copy.deepcopy(CASES[case]["payload"])


def _submission(payload: dict[str, Any]) -> cp2e.MacroFxSubmission:
    return cp2e.MacroFxSubmission.model_validate_json(json.dumps(payload))


def _report(outcome: StepValidation) -> cp2e.MacroFxReport:
    assert outcome.issues == () and outcome.output is not None
    return cp2e.MacroFxReport.model_validate_json(outcome.output)


def _tables(report: cp2e.MacroFxReport) -> list[dict[str, Any]]:
    return [
        t.model_dump(mode="json", exclude={"rows": {"__all__": {"row_kind"}}}, exclude_none=True)
        for t in report.tables
    ]


def _equals_base_oracle(report: cp2e.MacroFxReport, *, pinned_row: str | None) -> None:
    """The report equals the frozen `cases/cp2e-owner/expected.json` positive case; with
    `pinned_row` the only difference is the appended T2F.9 row r08 and its fact."""
    want_tables = copy.deepcopy(BASE["module_tables"])
    want_facts = [f["fact_id"] for t in BASE["tables"] for r in t["rows"] for f in r["facts"]]
    want_limitations = list(BASE["own_limitations"])
    if pinned_row is not None:
        last = want_tables[-1]
        assert last["table_id"] == "T2F.9"
        last["rows"].append(
            {"row_id": "r08", "label": "Limitation 8", "fact_ids": ["T2F.9.r08.text"]}
        )
        want_facts.append("T2F.9.r08.text")
        want_limitations.append(pinned_row)
    assert _tables(report) == want_tables
    assert [f.fact_id for f in report.facts] == want_facts
    assert [c.text for c in report.claims] == [c["text"] for c in BASE["claims"]]
    assert list(report.limitations) == want_limitations
    if pinned_row is not None:
        assert next(f for f in report.facts if f.fact_id == "T2F.9.r08.text").text == pinned_row


@pytest.mark.parametrize("case", REFUSED)
def test_a_differing_pin_is_a_validator_refusal_with_the_oracle_lines(
    case: str, tmp_path: Path
) -> None:
    outcome = _validate(_pack(tmp_path, CASES[case]["context"]), _payload(case))
    assert outcome.output is None
    assert list(outcome.issues) == EXPECTED["cases"][case]["issues"]


@pytest.mark.parametrize("case", REFUSED)
def test_the_composer_gate_raises_on_the_pin_lines(case: str, tmp_path: Path) -> None:
    """P6-P4: `macro_fx` raises on the pin lines only; it does not re-run the content checks."""
    pack = _pack(tmp_path, CASES[case]["context"])
    with pytest.raises(ValueError) as caught:
        cp2e.macro_fx(pack=pack, submission=_submission(_payload(case)))
    pin_lines = [x for x in EXPECTED["cases"][case]["issues"] if x.startswith("assumptions.cp2e.")]
    assert str(caught.value) == "; ".join(pin_lines)


def test_a_content_issue_comes_before_the_pin_line(tmp_path: Path) -> None:
    payload = _payload("differs")
    payload["rate_shocks_bp"] = ["abc", "200"]
    issues = _validate(_pack(tmp_path, CASES["differs"]["context"]), payload).issues
    assert issues == (
        "rate_shocks_bp[0]: shock must be a whole number of basis points from 1 to 1000",
        "assumptions.cp2e.rate_shocks_bps: pinned 100, 200; submitted abc, 200",
    )


def test_junk_is_shown_as_typed_with_no_exception(tmp_path: Path) -> None:
    payload = _payload("non_numeric")
    payload["rate_shocks_bp"] = ["abc"]
    payload["fx_shocks_percent"] = ["x", "1E+999999999"]
    issues = _validate(_pack(tmp_path, CASES["non_numeric"]["context"]), payload).issues
    assert issues[-2:] == (
        "assumptions.cp2e.rate_shocks_bps: pinned 100, 200; submitted abc",
        "assumptions.cp2e.fx_shocks_pct: pinned 10; submitted x, 1E+999999999",
    )


def test_a_huge_spelling_is_compared_as_typed_and_clipped(tmp_path: Path) -> None:
    payload = _payload("differs")
    payload["rate_shocks_bp"] = ["9" * 5000, "200"]
    issues = _validate(_pack(tmp_path, CASES["differs"]["context"]), payload).issues
    assert issues and all(len(x) <= MAX_ISSUE_CHARS for x in issues)
    assert issues[-1].startswith("assumptions.cp2e.rate_shocks_bps: pinned 100, 200; submitted 99")


def test_a_shape_failure_gets_no_pin_line(tmp_path: Path) -> None:
    payload = _payload("differs")
    payload["rate_shocks_bp"] = "101"  # a string for a list of strings is a shape refusal
    outcome = _validate(_pack(tmp_path, CASES["differs"]["context"]), payload)
    assert outcome.issues and not any("pinned" in line for line in outcome.issues)


@pytest.mark.parametrize(
    ("case", "row"),
    [("match", SHOCKS), ("hedge60", SHOCKS_AND_HEDGE)],
)
def test_a_matching_submission_is_labelled_user_supplied(
    case: str, row: str, tmp_path: Path
) -> None:
    report = _report(_validate(_pack(tmp_path, CASES[case]["context"]), _payload(case)))
    want = EXPECTED["cases"][case]
    if case == "match":
        assert list(report.limitations) == want["own_limitations"]
        assert want["limitation_rows"]["text"] == row == want["pinned_line"]
        _equals_base_oracle(report, pinned_row=row)
    else:
        recomputed = want["recomputed_case"]
        assert list(report.limitations) == recomputed["own_limitations"]
        assert report.limitations[-1] == row == recomputed["pinned_line"]
        assert _tables(report) == recomputed["module_tables"]
        assert [c.claim_id for c in report.claims] == [c["claim_id"] for c in recomputed["claims"]]
    last = next(t for t in report.tables if t.table_id == "T2F.9").rows[-1]
    assert (last.row_id, last.label, last.fact_ids) == ("r08", "Limitation 8", ("T2F.9.r08.text",))


def test_the_verifier_replay_reproduces_the_label(tmp_path: Path) -> None:
    """The step output is the composer's output rebuilt from the pack and submission alone."""
    pack = _pack(tmp_path, CASES["hedge60"]["context"])
    outcome = _validate(pack, _payload("hedge60"))
    again = cp2e.macro_fx(pack=pack, submission=_submission(_payload("hedge60")))
    assert outcome.output == again.model_dump_json()
    assert again.limitations[-1] == SHOCKS_AND_HEDGE


@pytest.mark.parametrize("which", ("value", "absence"))
def test_a_blank_hedge_pin_leaves_the_hedge_free_and_names_shocks_only(
    which: str, tmp_path: Path
) -> None:
    want = EXPECTED["cases"]["blank_hedge"]
    case = want["payloads"][which]
    report = _report(_validate(_pack(tmp_path, CASES[case]["context"]), _payload(case)))
    assert report.limitations[-1] == SHOCKS
    if which == "value":
        recomputed = want["value_case"]
        assert list(report.limitations) == recomputed["own_limitations"]
        assert _tables(report) == recomputed["module_tables"]
    else:
        _equals_base_oracle(report, pinned_row=SHOCKS)


@pytest.mark.parametrize("case", ("no_pin", "no_context"))
def test_no_context_or_no_pin_equals_the_frozen_base_oracle(case: str, tmp_path: Path) -> None:
    report = _report(_validate(_pack(tmp_path, CASES[case]["context"]), _payload(case)))
    assert SHOCKS not in report.limitations and SHOCKS_AND_HEDGE not in report.limitations
    _equals_base_oracle(report, pinned_row=None)


def test_a_pin_changes_nothing_but_the_last_limitation_row(tmp_path: Path) -> None:
    """The unpinned report from the same pack, compared with the frozen base oracle above, plus
    the pinned one: every table other than T2F.9 and every claim is the base oracle's."""
    pinned = _report(_validate(_pack(tmp_path, CASES["match"]["context"]), _payload("match")))
    want = [t for t in BASE["module_tables"] if t["table_id"] != "T2F.9"]
    assert [t for t in _tables(pinned) if t["table_id"] != "T2F.9"] == want


# --- the label on every path that composes the own limitations ----------------------------------
def _variants() -> dict[str, cp2e.MacroFxInputs]:
    positive = tm._inputs("positive")
    gap = tm._inputs("gap_no_facility_schedule")
    facility = positive.facility
    assert facility is not None
    absence = positive.hedge_absence
    assert absence is not None
    floor = replace(facility, floor_bp=replace(facility.floor_bp, value=Decimal(25)))
    remainder = replace(facility, balance=replace(facility.balance, value=Decimal(40)))
    return {
        "positive": positive,
        "gap_no_facility_schedule": gap,
        "hedge_value": replace(positive, hedge_ratio=Decimal("0.6"), hedge_absence=None),
        "floor_above_zero": replace(positive, facility=floor),
        "remainder": replace(positive, facility=remainder),
        "no_debt_currency": replace(positive, debt_currency=None, debt_currency_absence=absence),
        "no_operating_split_absence_swapped": replace(
            positive,
            foreign_ebitda_share=replace(positive.total_debt, value=Decimal("0.25")),
            operating_fx_absence=None,
        ),
    }


VARIANTS = _variants()


@pytest.mark.parametrize("name", tuple(VARIANTS))
@pytest.mark.parametrize("hedge_pinned", (False, True))
def test_the_label_is_last_on_every_branch_that_composes_the_limitations(
    name: str, hedge_pinned: bool
) -> None:
    inputs = VARIANTS[name]
    base = cp2e.own_limitations(inputs)
    assert list(cp2e.compute(inputs).limitations) == list(base)
    assert SHOCKS not in base
    pinned_inputs = replace(inputs, pinned=True, hedge_pinned=hedge_pinned)
    line = SHOCKS_AND_HEDGE if hedge_pinned else SHOCKS
    got = cp2e.own_limitations(pinned_inputs)
    assert got == (*base, line)
    result = cp2e.compute(pinned_inputs)
    assert result.limitations == got
    ledger = next(t for t in result.tables if t.table_id == "T2F.9")
    assert len(ledger.rows) == len(base) + 1
    assert ledger.rows[-1].label == f"Limitation {len(base) + 1}"
    assert ledger.rows[-1].row_id == f"r{len(base) + 1:02d}"


def test_the_hedge_flag_alone_does_not_label_an_unpinned_run() -> None:
    inputs = replace(VARIANTS["positive"], pinned=False, hedge_pinned=True)
    assert cp2e.own_limitations(inputs) == cp2e.own_limitations(VARIANTS["positive"])


def test_the_gap_case_label_through_the_validator(tmp_path: Path) -> None:
    """The second base fixture, composed by the real validator under a context."""
    pack = _pack(tmp_path, "context-credit_snapshot.json", "gap_no_facility_schedule")
    gap = copy.deepcopy(tm.SUBMISSIONS["gap_no_facility_schedule"])
    outcome = _validate(pack, gap)
    assert outcome.issues == ()
    report = _report(outcome)
    want = tm.EXPECTED["cases"]["gap_no_facility_schedule"]["own_limitations"]
    assert list(report.limitations) == [*want, SHOCKS]


# --- the refusal of a context the run does not match -----------------------------------------------
def test_a_context_that_differs_from_the_run_is_one_refusal_line_after_the_content(
    tmp_path: Path,
) -> None:
    """P6-P3: only `ContextRefused` is caught; it becomes `Context refused: <message>`, with no
    pin lines, after the content issues."""
    pack = _pack(tmp_path, "context-covenant_refinancing.json")
    outcome = _validate(pack, _payload("match"))
    assert len(outcome.issues) == 1 and outcome.issues[0].startswith("Context refused: ")
    assert "pinned" not in outcome.issues[0]
    bad = _payload("match")
    bad["rate_shocks_bp"] = ["abc", "200"]
    got = _validate(pack, bad).issues
    assert got[0].startswith("rate_shocks_bp[0]:") and got[1:] == outcome.issues
    with pytest.raises(ValueError, match="Context refused"):
        cp2e.macro_fx(pack=pack, submission=_submission(_payload("match")))


def test_only_context_refused_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A `ValueError` that is not a `ContextRefused` escapes the validator and the composer."""
    pack = _pack(tmp_path, CASES["match"]["context"])

    def boom(*_: object, **__: object) -> tuple[str, ...]:
        raise ValueError("not a context refusal")

    monkeypatch.setattr(cp2e, "pin_issues", boom)
    with pytest.raises(ValueError, match="not a context refusal"):
        _validate(pack, _payload("match"))
    with pytest.raises(ValueError, match="not a context refusal"):
        cp2e.macro_fx(pack=pack, submission=_submission(_payload("match")))


def test_a_long_refusal_with_several_problems_is_one_clipped_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = _pack(tmp_path, CASES["match"]["context"])
    message = "; ".join(f"problem {i}: " + "x" * 120 for i in range(8))
    assert len(message) > MAX_ISSUE_CHARS

    def refuse(*_: object, **__: object) -> tuple[str, ...]:
        raise ContextRefused(message.split("; "))

    monkeypatch.setattr(cp2e, "pin_issues", refuse)
    issues = _validate(pack, _payload("match")).issues
    assert len(issues) == 1
    assert issues[0].startswith("Context refused: problem 0: ")
    assert len(issues[0]) <= MAX_ISSUE_CHARS and issues[0].endswith("…")


def test_nothing_is_mapped_when_no_context_pins_the_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No pin, no context: `pin_issues` is never called, so no submitted text is formatted."""

    def never(*_: object, **__: object) -> tuple[str, ...]:
        raise AssertionError("pin_issues called without a pin")

    monkeypatch.setattr(cp2e, "pin_issues", never)
    for case in ("no_pin", "no_context"):
        (tmp_path / case).mkdir()
        pack = _pack(tmp_path / case, CASES[case]["context"])
        assert _validate(pack, _payload(case)).issues == ()
