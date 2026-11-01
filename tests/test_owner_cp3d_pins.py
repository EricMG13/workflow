"""CP-3D honours the recovery rate pinned in the context file (Phase 6 Task 7).

Expectations come from `cases/pins-context-owner/{expected,submissions}.json` (the CP-3D entry) and
the frozen base oracle `cases/cp3d-owner/expected.json`, never from the code under test or a live
rebuild. Each case runs the entry validator and the composer over the base run's pack with the
`prepare`d context source appended last, on the `tests/test_connect_cp3d.py` store double. Fast: no
store promotion run (`tests/test_owner_cp3d.py`).
"""

from __future__ import annotations

import copy
import importlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from deploy_vii.execution import MAX_ISSUE_CHARS
from deploy_vii.preparation import PreparedPack, prepare
from deploy_workflow.context import (
    CONTEXT_SOURCE_ID,
    ContextRefused,
    load_context,
    preparation_request,
)
from deploy_workflow.owners import cp3d
from deploy_workflow.owners.pins import pinned_line, pins_of

conn: Any = importlib.import_module("test_connect_cp3d")
base: Any = importlib.import_module("test_method_cp3d")
ctx3: Any = importlib.import_module("test_cp3d_context")

ORACLE = Path(__file__).resolve().parents[1] / "cases" / "pins-context-owner"
EXPECTED: dict[str, Any] = json.loads((ORACLE / "expected.json").read_text())["modules"]["CP-3D"]
CASES: dict[str, Any] = json.loads((ORACLE / "submissions.json").read_text())["modules"]["CP-3D"][
    "cases"
]
PINNED = pinned_line("CP-3D")
REFUSED = ("differs", "absence", "non_numeric")
CONTEXT = "context-relative_value.json"
NO_CP3D = "context-relative_value-no-cp3d.json"
ROW = EXPECTED["cases"]["match"]["limitation_rows"]


def _pack(tmp_path: Path, context: str | None, base_case: str) -> PreparedPack:
    """The base run's pack with the prepared context source appended last."""
    plain: PreparedPack = conn._pack(base_case)
    if context is None:
        return plain
    raw = (ORACLE / context).read_bytes()
    request = preparation_request(
        load_context(raw), run_id=plain.run.run_id, context_path="context.json", sources=()
    )
    (tmp_path / "root").mkdir(parents=True)
    (tmp_path / "root" / "context.json").write_bytes(raw)
    prepared = prepare(request, tmp_path / "root", tmp_path / "pack")
    found = tuple(s for s in prepared.sources if s.source_id == CONTEXT_SOURCE_ID)
    assert len(found) == 1
    return PreparedPack(run=plain.run, sources=(*plain.sources, *found))


def _payload(case: str) -> dict[str, Any]:
    payload: dict[str, Any] = copy.deepcopy(CASES[case]["payload"])
    return payload


def _submission(payload: dict[str, Any]) -> cp3d.MarketImpliedSubmission:
    return cast(cp3d.MarketImpliedSubmission, base._submission(payload))


def _validate(pack: PreparedPack, payload: dict[str, Any], base_case: str) -> Any:
    """The entry validator over a one-step attempt whose payload is `payload`."""
    store = conn._PayloadStore(base_case, json.dumps(payload))
    store._pack = pack
    return cp3d.ENTRY_VALIDATOR(
        cast(Any, store), pack, conn._attempt_with_payload("p" * 64, base_case)
    )


def _upstream(pack: PreparedPack, base_case: str) -> cp3d.Upstream:
    return cp3d.upstream_of(pack=pack, cp0=conn._cp0(base_case))


def _report(
    pack: PreparedPack, payload: dict[str, Any], base_case: str
) -> cp3d.MarketImpliedReport:
    return cp3d.market_implied(
        pack=pack, submission=_submission(payload), upstream=_upstream(pack, base_case)
    )


def _same_cell(fact: Any, cell: dict[str, Any], *, spelling: bool) -> bool:
    """The fact equals the frozen cell. With `spelling` the amount only needs to be equal as a
    number: the recovery typed `70.00` is stored as `0.70`, the frozen `70` as `0.7`."""
    got, want = conn._fact_view(fact), conn._expected_view(cell)
    if spelling and got["amount"] is not None and want["amount"] is not None:
        if Decimal(got["amount"]) != Decimal(want["amount"]):
            return False
        got, want = {**got, "amount": None}, {**want, "amount": None}
    return bool(got == want)


def _expect_frozen(
    report: cp3d.MarketImpliedReport,
    base_case: str,
    *,
    pinned: bool,
    spelling: bool = False,
) -> None:
    """The report equals the frozen `cases/cp3d-owner` case, but for the pinned line when `pinned`:
    one more own limitation (last), one more T3E.9 row and fact (last), nothing else. `spelling`
    allows the recovery amount to differ in trailing zeros only (see `_same_cell`)."""
    want = conn.EXPECTED["cases"][base_case]
    facts = {f.fact_id: f for f in report.facts}
    assert [t.table_id for t in report.tables] == [t["table_id"] for t in want["tables"]]
    for table, frozen in zip(report.tables, want["tables"], strict=True):
        rows, frozen_rows = list(table.rows), list(frozen["rows"])
        if pinned and table.table_id == "T3E.9":
            assert len(rows) == len(frozen_rows) + 1
            rows = rows[:-1]
        assert [r.row_id for r in rows] == [r["row_id"] for r in frozen_rows]
        for row, frozen_row in zip(rows, frozen_rows, strict=True):
            assert row.label == frozen_row["label"]
            assert list(row.fact_ids) == [c["fact_id"] for c in frozen_row["facts"]]
            for fact_id, cell in zip(row.fact_ids, frozen_row["facts"], strict=True):
                assert _same_cell(facts[fact_id], cell, spelling=spelling), fact_id
    assert [(c.claim_id, c.text) for c in report.claims] == [
        (c["claim_id"], c["text"]) for c in want["claims"]
    ]
    assert list(report.limitations) == want["own_limitations"] + ([PINNED] if pinned else [])
    assert len(report.facts) == sum(
        len(c) for t in want["tables"] for r in t["rows"] for c in [r["facts"]]
    ) + (1 if pinned else 0)


# --- the oracle cases -----------------------------------------------------------------------


@pytest.mark.parametrize("case", REFUSED)
def test_a_pin_mismatch_is_refused_by_the_validator_and_the_composer(
    tmp_path: Path, case: str
) -> None:
    spec = CASES[case]
    pack = _pack(tmp_path, spec["context"], spec["base_case"])
    want = EXPECTED["cases"][case]["issues"]
    done = _validate(pack, _payload(case), spec["base_case"])
    assert list(done.issues) == want and done.output is None
    with pytest.raises(ValueError) as raised:
        _report(pack, _payload(case), spec["base_case"])
    assert str(raised.value) == "; ".join(want)


def test_the_oracle_wordings_are_the_issue_lines() -> None:
    assert EXPECTED["cases"]["differs"]["issues"] == [
        "assumptions.cp3d.recovery_pct: pinned 70; submitted 70.01"
    ]
    assert EXPECTED["cases"]["absence"]["issues"] == [
        "assumptions.cp3d.recovery_pct: pinned 70; submitted absence"
    ]


def test_a_numerically_equal_spelling_is_accepted_and_pinned(tmp_path: Path) -> None:
    spec = CASES["match"]
    assert _payload("match")["recovery"]["percent_text"] == "70.00"
    pack = _pack(tmp_path, spec["context"], spec["base_case"])
    done = _validate(pack, _payload("match"), spec["base_case"])
    assert done.issues == ()
    report = _report(pack, _payload("match"), spec["base_case"])
    assert done.output == report.model_dump_json()
    assert list(report.limitations) == EXPECTED["cases"]["match"]["own_limitations"]
    assert report.limitations[-1] == PINNED


def test_the_pinned_row_is_t3e9_r12_appended_last_and_nothing_moves(tmp_path: Path) -> None:
    spec = CASES["match"]
    pack = _pack(tmp_path, spec["context"], spec["base_case"])
    report = _report(pack, _payload("match"), spec["base_case"])
    _expect_frozen(report, "positive", pinned=True, spelling=True)
    table = next(t for t in report.tables if t.table_id == "T3E.9")
    assert [r.row_id for r in table.rows][-2:] == ["r11", "r12"]
    assert len(table.rows) == 12
    last = table.rows[-1]
    assert (last.row_id, last.label, list(last.fact_ids)) == (
        ROW["row_id"],
        ROW["label"],
        [ROW["fact_id"]],
    )
    assert ROW["fact_id"] == "T3E.9.r12.text" and ROW["text"] == PINNED
    fact = next(f for f in report.facts if f.fact_id == ROW["fact_id"])
    assert fact.text == PINNED
    assert [f.fact_id for f in report.facts][-1] == ROW["fact_id"]


def test_the_exact_pinned_spelling_70_is_accepted_too(tmp_path: Path) -> None:
    pack = _pack(tmp_path, CONTEXT, "positive")
    payload = _payload("match")
    payload["recovery"]["percent_text"] = "70"
    assert _validate(pack, payload, "positive").issues == ()
    _expect_frozen(_report(pack, payload, "positive"), "positive", pinned=True)


def test_no_pin_in_the_context_leaves_the_base_report_unlabelled(tmp_path: Path) -> None:
    spec = CASES["no_pin"]
    pack = _pack(tmp_path, spec["context"], spec["base_case"])
    done = _validate(pack, _payload("no_pin"), spec["base_case"])
    assert done.issues == ()
    report = _report(pack, _payload("no_pin"), spec["base_case"])
    _expect_frozen(report, "positive", pinned=False)
    assert PINNED not in report.limitations


def test_no_context_is_the_frozen_base_report(tmp_path: Path) -> None:
    spec = CASES["no_context"]
    pack = _pack(tmp_path, None, spec["base_case"])
    assert _validate(pack, _payload("no_context"), spec["base_case"]).issues == ()
    report = _report(pack, _payload("no_context"), spec["base_case"])
    _expect_frozen(report, "positive", pinned=False)
    assert cp3d._pin_lines(pack, _submission(_payload("no_context"))) == ()


def test_a_different_recovery_with_no_pin_is_not_refused(tmp_path: Path) -> None:
    pack = _pack(tmp_path, NO_CP3D, "positive")
    payload = _payload("no_pin")
    payload["recovery"]["percent_text"] = "55"
    assert _validate(pack, payload, "positive").issues == ()


# --- the mapped value is the typed text ------------------------------------------------------


@pytest.mark.parametrize(
    ("typed", "line"),
    [
        ("71", "assumptions.cp3d.recovery_pct: pinned 70; submitted 71"),
        ("70.01", "assumptions.cp3d.recovery_pct: pinned 70; submitted 70.01"),
        ("69.99", "assumptions.cp3d.recovery_pct: pinned 70; submitted 69.99"),
        (" 70", "assumptions.cp3d.recovery_pct: pinned 70; submitted  70"),
        ("70 ", "assumptions.cp3d.recovery_pct: pinned 70; submitted 70 "),
        ("x", "assumptions.cp3d.recovery_pct: pinned 70; submitted x"),
        ("7e1", "assumptions.cp3d.recovery_pct: pinned 70; submitted 7e1"),
    ],
)
def test_the_submitted_text_is_shown_as_typed_never_stripped_or_substituted(
    tmp_path: Path, typed: str, line: str
) -> None:
    pack = _pack(tmp_path, CONTEXT, "positive")
    payload = _payload("match")
    payload["recovery"]["percent_text"] = typed
    sub = _submission(payload)
    assert cp3d._pin_lines(pack, sub) == (line,)
    assert line in _validate(pack, payload, "positive").issues


@pytest.mark.parametrize("typed", ["70", "70.0", "70.00", "070.0"])
def test_a_numerically_equal_text_gets_no_pin_line(tmp_path: Path, typed: str) -> None:
    pack = _pack(tmp_path, CONTEXT, "positive")
    payload = _payload("match")
    payload["recovery"]["percent_text"] = typed
    assert cp3d._pin_lines(pack, _submission(payload)) == ()


def test_a_long_typed_text_is_clipped_to_one_bounded_line(tmp_path: Path) -> None:
    pack = _pack(tmp_path, CONTEXT, "positive")
    payload = _payload("match")
    payload["recovery"]["percent_text"] = "9" * 5000
    [line] = cp3d._pin_lines(pack, _submission(payload))
    assert len(line) <= MAX_ISSUE_CHARS and line.startswith("assumptions.cp3d.recovery_pct: ")
    assert line.endswith("…")


def test_an_absent_recovery_is_the_absence_line(tmp_path: Path) -> None:
    pack = _pack(tmp_path, CONTEXT, "gap_no_recovery")
    sub = _submission(_payload("absence"))
    assert sub.recovery is None and sub.recovery_absence is not None
    assert cp3d._pin_lines(pack, sub) == (
        "assumptions.cp3d.recovery_pct: pinned 70; submitted absence",
    )


def test_the_pin_line_follows_the_content_issue_and_is_never_alone_hidden(
    tmp_path: Path,
) -> None:
    """A content issue on the recovery does not hide the pin line: it comes after, once."""
    pack = _pack(tmp_path, CONTEXT, "positive")
    got = _validate(pack, _payload("non_numeric"), "positive").issues
    assert list(got) == EXPECTED["cases"]["non_numeric"]["issues"]
    assert got[0] == "recovery: percent must be at least 0 and below 100"
    assert len(got) == len(set(got))


def test_the_pin_line_follows_an_unrelated_content_issue(tmp_path: Path) -> None:
    pack = _pack(tmp_path, CONTEXT, "positive")
    payload = _payload("differs")
    payload["summary"]["text"] = ""
    got = list(_validate(pack, payload, "positive").issues)
    assert got[-1] == "assumptions.cp3d.recovery_pct: pinned 70; submitted 70.01"
    assert len(got) >= 2


def test_a_shape_failure_gets_no_pin_line(tmp_path: Path) -> None:
    pack = _pack(tmp_path, CONTEXT, "positive")
    done = _validate(pack, {"recovery": {"percent_text": "71"}}, "positive")
    assert done.issues and not any("recovery_pct" in i for i in done.issues)


# --- a context the run refuses ----------------------------------------------------------------


def _other_run(pack: PreparedPack) -> PreparedPack:
    return PreparedPack(
        run=pack.run.model_copy(update={"issuer_id": "someone-else"}), sources=pack.sources
    )


def test_a_refused_context_is_one_line_and_no_pin_line(tmp_path: Path) -> None:
    pack = _other_run(_pack(tmp_path, CONTEXT, "positive"))
    with pytest.raises(ContextRefused) as raised:
        pins_of("CP-3D", pack)
    want = "Context refused: " + str(raised.value)
    assert cp3d._pin_lines(pack, _submission(_payload("differs"))) == (want,)
    got = list(_validate(pack, _payload("differs"), "positive").issues)
    assert got.count(want) == 1 and got[-1] == want
    assert not any("recovery_pct" in i for i in got)
    with pytest.raises(ValueError) as composer:
        _report(pack, _payload("match"), "positive")
    assert want in str(composer.value)


def test_a_refusal_over_the_bound_with_many_problems_is_one_clipped_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = _pack(tmp_path, CONTEXT, "positive")
    problems = [f"identity.field_{i}: " + "y" * 120 for i in range(8)]

    def refuse(module_id: str, given: PreparedPack) -> None:
        raise ContextRefused(problems)

    monkeypatch.setattr(cp3d, "pins_of", refuse)
    lines = cp3d._pin_lines(pack, _submission(_payload("differs")))
    assert len(lines) == 1
    [line] = lines
    assert len(line) <= MAX_ISSUE_CHARS and line.startswith("Context refused: identity.field_0: ")
    assert line.endswith("…")
    assert len("; ".join(problems)) > MAX_ISSUE_CHARS


def test_only_a_context_refusal_is_caught_not_any_value_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = _pack(tmp_path, CONTEXT, "positive")

    def broken(module_id: str, given: PreparedPack) -> None:
        raise ValueError("not a context refusal")

    monkeypatch.setattr(cp3d, "pins_of", broken)
    with pytest.raises(ValueError, match="not a context refusal"):
        cp3d._pin_lines(pack, _submission(_payload("differs")))


def test_a_value_error_while_comparing_is_not_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = _pack(tmp_path, CONTEXT, "positive")

    def broken(*_: Any, **__: Any) -> None:
        raise ValueError("compare failed")

    monkeypatch.setattr(cp3d, "pin_issues", broken)
    with pytest.raises(ValueError, match="compare failed"):
        cp3d._pin_lines(pack, _submission(_payload("differs")))


def test_the_market_quote_context_errors_stay_a_separate_line(tmp_path: Path) -> None:
    """Phase 3's `context source unreadable` lines are not merged with the pin refusal."""
    pack = _other_run(_pack(tmp_path, CONTEXT, "positive"))
    content = cp3d.validate_market_implied(
        submission=_submission(_payload("match")), upstream=_upstream(pack, "positive")
    )
    got = cp3d._issues(pack, _submission(_payload("match")), _upstream(pack, "positive"))
    assert list(got[: len(content)]) == list(content)
    assert len(got) == len(content) + 1 and got[-1].startswith("Context refused: ")


# --- the label on every branch ----------------------------------------------------------------


def _result(sub: cp3d.MarketImpliedSubmission, ctx: cp3d.MarketContext, pinned: bool) -> Any:
    return cp3d.market_implied_result(submission=sub, context=ctx, pinned=pinned)


@pytest.mark.parametrize("case", conn.CASES)
def test_the_label_is_last_on_every_frozen_base_fixture(case: str) -> None:
    sub, ctx = _submission(base.SUBMISSIONS[case]), base._context(case)
    plain, labelled = _result(sub, ctx, False), _result(sub, ctx, True)
    assert PINNED not in plain.own_limitations
    assert labelled.own_limitations == (*plain.own_limitations, PINNED)
    table = next(t for t in labelled.tables if t.table_id == "T3E.9")
    assert table.rows[-1].facts[0].text == PINNED
    assert table.rows[-1].row_id == f"r{len(plain.own_limitations) + 1:02d}"
    assert cp3d.own_limitations(sub, ctx) == plain.own_limitations
    assert cp3d.own_limitations(sub, ctx, pinned=True)[-1] == PINNED


def _last(sub: cp3d.MarketImpliedSubmission, ctx: cp3d.MarketContext | None) -> tuple[str, ...]:
    out = cp3d.own_limitations(sub, ctx, pinned=True)
    assert out[-1] == PINNED and out.count(PINNED) == 1
    assert PINNED not in cp3d.own_limitations(sub, ctx)
    return out


def test_the_label_is_last_after_the_stale_lines() -> None:
    up = ctx3.upstream("stale")
    sub = ctx3.submission(ctx3.EXP["stale"]["cites_31_days"]["submitted_observations"])
    out = _last(sub, up.context)
    assert any(x.startswith("Stale") for x in out)


def test_the_label_is_last_after_the_context_single_dealer_lines() -> None:
    up = ctx3.upstream("observed-and-talk")
    both = _last(ctx3.submission(ctx3.by_row("o01", "o02", "o03")), up.context)
    assert both[0] == ctx3.SINGLE_NEW
    one = _last(ctx3.submission(ctx3.by_row("o01", "o03")), up.context)
    assert one[0] == ctx3.SINGLE_ONE_SIDE.format(side="bid")


def test_the_label_is_last_after_the_context_talk_line() -> None:
    up = ctx3.upstream("observed-and-talk")
    out = _last(ctx3.submission(ctx3.by_row("o03")), up.context)
    assert ctx3.TALK_LABEL in out


def test_the_label_is_last_with_a_sheet_single_dealer_and_a_context_up() -> None:
    up = ctx3.upstream("observed-and-talk")
    out = _last(base._submission(ctx3.POSITIVE), up.context)
    assert out[0] == ctx3.SINGLE_OLD


def test_the_label_is_last_with_no_market_facility() -> None:
    sub, ctx = _submission(base.SUBMISSIONS["gap_no_market"]), base._context("gap_no_market")
    assert sub.market_absence is not None
    out = _last(sub, ctx)
    assert out[0].startswith("No third-party market quotation source")


def test_the_label_is_last_without_a_recovery() -> None:
    sub, ctx = _submission(base.SUBMISSIONS["gap_no_recovery"]), base._context("gap_no_recovery")
    out = _last(sub, ctx)
    assert "The recovery rate was not assessed, so the default measures are not calculated" in out


def test_the_label_is_last_without_a_context() -> None:
    out = _last(_submission(base.SUBMISSIONS["positive"]), None)
    assert len(out) == len(cp3d.own_limitations(_submission(base.SUBMISSIONS["positive"]))) + 1


def test_the_composer_labels_through_the_context_offer_branch(tmp_path: Path) -> None:
    """An accepted submission that cites context rows (not the sheet) is labelled last."""
    pack = ctx3.context_pack("observed-and-talk")
    up = cp3d.upstream_of(pack=pack, cp0=conn._cp0("positive"))
    sub = ctx3.submission(ctx3.by_row("o01", "o02", "o03"))
    # The context file of the pack pins nothing: the label comes only with the pin.
    assert pins_of("CP-3D", pack) is None
    plain = cp3d.market_implied(pack=pack, submission=sub, upstream=up)
    assert PINNED not in plain.limitations
    assert plain.limitations == cp3d.own_limitations(
        cp3d.expand_context_rows(sub, up.context), up.context
    )
