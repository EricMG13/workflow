from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import pytest

from deploy_workflow.model.record import CallRecord
from deploy_workflow.model_testing.budget import Settlement
from deploy_workflow.model_testing.configs import CONFIGS
from deploy_workflow.model_testing.faults import FaultRecord
from deploy_workflow.model_testing.pathway import PathwayScore
from deploy_workflow.model_testing.records import RunMeta
from deploy_workflow.model_testing.report import render_report
from deploy_workflow.model_testing.scoring import FactScore, ModuleScore, Outcome

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
FIXTURE = Path(__file__).parent / "fixtures" / "model_testing" / "report_expected.md"

Runs = list[tuple[RunMeta, Sequence[CallRecord]]]


def call(
    config_id: str = "sol-medium",
    run_id: str = "r-sol",
    module_id: str = "CP-0",
    step_id: str = "s1",
    attempt: Literal[0, 1] = 0,
    index: int = 0,
    seconds: int | None = 10,
    tokens: tuple[int | None, int | None, int | None] = (None, None, None),
    settled: str | None = "0.10",
    reserved: str = "1",
    error_class: str | None = None,
) -> CallRecord:
    config = CONFIGS[config_id]
    body: dict[str, Any] = {
        "schema_version": "model-call/1",
        "run_id": run_id,
        "case_id": "shc-earnings-update",
        "pathway": "earnings_update",
        "module_id": module_id,
        "step_id": step_id,
        "attempt": attempt,
        "call_index": index,
        "config_id": config_id,
        "provider": config.provider,
        "requested_model": config.model,
        "reported_model": config.model,
        "requested_effort": config.effort,
        "invocation_digest": "a" * 64,
        "request_id": None,
        "http_status": None,
        "started_at": NOW,
        "first_byte_at": None,
        "finished_at": None if seconds is None else NOW + timedelta(seconds=seconds),
        "input_tokens": tokens[0],
        "cached_read_tokens": None,
        "cache_write_tokens": None,
        "output_tokens": tokens[1],
        "reasoning_tokens": tokens[2],
        "reserved_usd": Decimal(reserved),
        "settled_usd": None if settled is None else Decimal(settled),
        "cost_status": "unknown" if settled is None else "computed",
        "tool_calls": (),
        "submit_sha256": None,
        "error_class": error_class,
        "error": None,
    }
    return CallRecord(**body)


def meta(
    config_id: str = "sol-medium",
    run_id: str = "r-sol",
    mode: Literal["offline", "live"] = "live",
    stopped: str | None = None,
) -> RunMeta:
    live = mode == "live"
    return RunMeta(
        case_id="shc-earnings-update",
        pathway="earnings_update",
        config_id=config_id,
        run_id=run_id,
        mode=mode,
        cap_usd=Decimal(5),
        sources=(),
        cp_dr_invoked=False,
        replayed_from_run=None,
        outcome="settled" if stopped is None else "stopped",
        stopped_reason=stopped,
        ruling_path="r.md" if live else None,
        ruling_sha256="b" * 64 if live else None,
        ruling_date="2026-11-01" if live else None,
    )


def module(module_id: str, outcomes: Sequence[Outcome], passed: bool) -> ModuleScore:
    facts = tuple(
        FactScore(fact_id=f"{module_id}.{i}", outcome=o, expected=None, observed=None)
        for i, o in enumerate(outcomes)
    )
    return ModuleScore(
        module_id=module_id,
        head_status="accepted",
        facts=facts,
        untraced=(),
        unscored=0,
        judgment=False,
        passed=passed,
    )


def refused_module(module_id: str, outcomes: Sequence[Outcome], passed: bool) -> ModuleScore:
    """A refused head: its ``gap_ok`` facts carry the scorer's ``refused:`` marker."""
    facts = tuple(
        FactScore(
            fact_id=f"{module_id}.{i}",
            outcome=o,
            expected=None,
            observed="refused: pack" if o == "gap_ok" else None,
        )
        for i, o in enumerate(outcomes)
    )
    return ModuleScore(
        module_id=module_id,
        head_status="refused",
        facts=facts,
        untraced=(),
        unscored=0,
        judgment=False,
        passed=passed,
    )


def score(
    config_id: str,
    run_id: str,
    modules: Sequence[ModuleScore],
    stopped: str | None = None,
    mode: Literal["offline", "live"] = "live",
) -> PathwayScore:
    return PathwayScore(
        run_id=run_id,
        case_id="shc-earnings-update",
        pathway="earnings_update",
        config_id=config_id,
        mode=mode,
        outcome="settled" if stopped is None else "stopped",
        stopped_reason=stopped,
        ruling_sha256="b" * 64 if mode == "live" else None,
        modules=tuple(modules),
        rendered=True,
        passed=all(m.passed for m in modules),
    )


def fault(fault_id: str, fault_class: str, **over: Any) -> FaultRecord:
    base: dict[str, Any] = {
        "schema_version": "fault/1",
        "fault_id": fault_id,
        "run_id": "r-sol",
        "case_id": "shc-earnings-update",
        "pathway": "earnings_update",
        "module_id": "CP-1B",
        "step_id": "s1",
        "config_id": "sol-medium",
        "fault_class": fault_class,
        "assigned_by": "reviewer-1",
        "confirmed_by": "controller",
        "evidence": ("digest-1",),
        "fix_ref": None,
        "rerun_run_id": None,
        "rerun_passed": None,
    }
    base.update(over)
    return FaultRecord(**base)


def fixture_inputs() -> tuple[list[PathwayScore], Runs, list[FaultRecord]]:
    sol_records = [
        call(module_id="CP-0", seconds=10, tokens=(1000, 500, 200), settled="0.40"),
        call(module_id="CP-1", index=0, seconds=20, tokens=(5000, 1000, 1000), settled="0.130"),
        call(module_id="CP-1", index=1, seconds=12, tokens=(4000, 1000, None), settled="0.135"),
        call(module_id="CP-1B", index=0, seconds=3, error_class="rate_limit", settled="0"),
        call(module_id="CP-1B", index=1, seconds=None, settled=None, reserved="2.00"),
        call(module_id="CP-5", seconds=5, tokens=(300, 200, 0), settled="0.05"),
    ]
    opus_records = [
        call(
            "opus-medium", "r-opus", "CP-0", seconds=40, tokens=(2000, 700, None), settled="1.005"
        ),
        call(
            "opus-medium", "r-opus", "CP-1", seconds=30, tokens=(3000, 900, None), settled="0.500"
        ),
        call("opus-medium", "r-opus", "CP-5", seconds=8, tokens=(100, 50, None), settled="0.20"),
    ]
    scores = [
        score(
            "sol-medium",
            "r-sol",
            [
                module("CP-0", ["match"], True),
                module("CP-1", [*(4 * ("match",)), "inherited", "unmapped"], True),
                module("CP-1B", [*(3 * ("match",)), "mismatch"], False),
                module("CP-5", ["match", "gap_ok"], True),
            ],
        ),
        score(
            "opus-medium",
            "r-opus",
            [
                module("CP-0", ["conflict_ok", "gap_ok", "match", "missing_in_output"], False),
                module("CP-1", ["match", "match"], True),
                refused_module("CP-5", ["gap_ok", "gap_ok", "match"], True),
            ],
            mode="offline",
        ),
    ]
    runs: Runs = [
        (meta(), sol_records),
        (meta("opus-medium", "r-opus", "offline"), opus_records),
    ]
    faults = [
        fault("f2", "prompt", fix_ref="abc123", rerun_run_id="r-sol2", rerun_passed=True),
        fault("f1", "prompt"),
        fault("f3", "model", module_id="CP-0", rerun_passed=False),
    ]
    return scores, runs, faults


def test_report_matches_fixture() -> None:
    scores, runs, faults = fixture_inputs()
    text = render_report(scores, runs, faults)
    assert text == FIXTURE.read_text()
    assert render_report(scores, runs, faults) == text


def test_unknown_cost_flagged() -> None:
    scores = [score("sol-medium", "r-sol", [module("CP-0", ["match"], True)])]
    runs: Runs = [(meta(), [call(settled=None, reserved="2.5")])]
    text = render_report(scores, runs, [])
    assert "$2.50 reserved" in text


def test_retries_from_call_index_and_error_class() -> None:
    records = [
        call(index=0),
        call(index=1),
        call(index=2, error_class="timeout"),
        call(index=3),
        call(attempt=1, index=0),
    ]
    scores = [score("sol-medium", "r-sol", [module("CP-0", ["match"], True)])]
    text = render_report(scores, [(meta(), records)], [])
    rows = [line for line in text.splitlines() if line.startswith("| sol-medium")]
    assert rows[0].split(" | ")[-1].rstrip(" |") == "2"


def test_offline_runs_not_charged() -> None:
    scores = [score("opus-medium", "r-op", [module("CP-0", ["match"], True)], mode="offline")]
    runs: Runs = [
        (meta("opus-medium", "r-op", "offline"), [call("opus-medium", "r-op", settled="7")])
    ]
    text = render_report(scores, runs, [])
    assert text.splitlines()[0].startswith("Offline")
    assert "| anthropic | $0.00 | $135.00 | $135.00 |" in text
    assert "$7.00" in text  # the computed cost is still shown in the table


def test_no_offline_banner_when_all_live() -> None:
    scores = [score("sol-medium", "r-sol", [module("CP-0", ["match"], True)])]
    text = render_report(scores, [(meta(), [call()])], [])
    assert "Offline" not in text


def test_stopped_run_cell() -> None:
    scores = [
        score("sol-medium", "r-sol", [module("CP-0", ["match"], False)], stopped="cap | reached")
    ]
    runs: Runs = [(meta(stopped="cap | reached"), [call()])]
    text = render_report(scores, runs, [])
    assert "STOPPED (cap \\| reached)" in text


def test_tokens_none_never_zero() -> None:
    scores = [score("sol-medium", "r-sol", [module("CP-0", ["match"], True)])]
    text = render_report(scores, [(meta(), [call()])], [])
    assert "n/r tok" in text
    assert "0.0k" not in text


def test_cost_rounds_half_up() -> None:
    scores = [score("sol-medium", "r-sol", [module("CP-0", ["match"], True)])]
    text = render_report(scores, [(meta(), [call(settled="0.265")])], [])
    assert "$0.27" in text


def test_score_without_run_refused() -> None:
    scores = [score("sol-medium", "r-sol", [module("CP-0", ["match"], True)])]
    with pytest.raises(ValueError, match="r-sol"):
        render_report(scores, [], [])


def test_duplicate_score_refused() -> None:
    one = score("sol-medium", "r-sol", [module("CP-0", ["match"], True)])
    with pytest.raises(ValueError, match="duplicate"):
        render_report([one, one], [(meta(), [call()])], [])


def test_partial_tokens_marked_lower_bound() -> None:
    scores = [score("sol-medium", "r-sol", [module("CP-0", ["match"], True)])]
    records = [call(index=0, tokens=(1000, 500, 200)), call(index=1, tokens=(None, None, None))]
    text = render_report(scores, [(meta(), records)], [])
    assert "≥1.7k tok" in text
    assert text.count("≥1.7k tok") == 2  # the cell and the config total
    full = render_report(scores, [(meta(), [call(tokens=(1000, 500, 200))])], [])
    assert "≥" not in full
    assert "n/r tok" in render_report(scores, [(meta(), [call()])], [])


def test_unknown_pathway_refused() -> None:
    s = score("sol-medium", "r-sol", [module("CP-0", ["match"], True)])
    s = s.model_copy(update={"pathway": "nope"})
    with pytest.raises(ValueError, match="nope"):
        render_report([s], [(meta(), [call()])], [])


def test_cost_columns_split_live_and_offline() -> None:
    scores = [
        score("sol-medium", "r-sol", [module("CP-0", ["match"], True)]),
        score("sol-high", "r-off", [module("CP-0", ["match"], True)], mode="offline"),
    ]
    runs: Runs = [
        (meta(), [call(settled="1.00")]),
        (
            meta("sol-high", "r-off", "offline"),
            [call("sol-high", "r-off", settled=None, reserved="3")],
        ),
    ]
    text = render_report(scores, runs, [])
    assert "| Cost (live) | Cost (offline, computed) |" in text
    assert "| sol-medium | 100.0% (1/1) | $1.00 | $0.00 |" in text
    assert "| sol-high | 100.0% (1/1) | $0.00 | $3.00 reserved |" in text


def test_fault_line_has_config_and_rerun_field() -> None:
    text = render_report([], [], [fault("f1", "prompt"), fault("f2", "model", rerun_passed=True)])
    assert "- f1 · shc-earnings-update · CP-1B · sol-medium · fix — · rerun: none" in text
    assert "rerun: passed" in text


def test_refusal_gaps_are_not_matches() -> None:
    refused = refused_module("CP-0", ["gap_ok", "gap_ok", "gap_ok"], True)
    scores = [score("sol-medium", "r-sol", [refused])]
    text = render_report(scores, [(meta(), [call()])], [])
    assert "PASS 0/3 (3 refused)" in text
    assert "PASS 3/3" not in text
    assert "| sol-medium | 0.0% (0/3) |" in text
    both = refused_module("CP-0", ["gap_ok", "inherited", "match"], True)
    text = render_report([score("sol-medium", "r-sol", [both])], [(meta(), [call()])], [])
    assert "PASS 1/2 (1 refused) (1 inherited)" in text


def test_gap_ok_on_an_accepted_module_still_matches() -> None:
    accepted = module("CP-0", ["gap_ok", "match"], True)
    text = render_report([score("sol-medium", "r-sol", [accepted])], [(meta(), [call()])], [])
    assert "PASS 2/2" in text and "refused" not in text


def test_render_problem_shown_in_the_cell() -> None:
    s = score("sol-medium", "r-sol", [module("CP-0", ["match"], False)])
    s = s.model_copy(update={"rendered": False, "render_problem": "owner_render_stale"})
    text = render_report([s], [(meta(), [call()])], [])
    assert "FAIL 1/1 (render: owner_render_stale) · $0.10" in text


def test_score_disagreeing_with_its_run_refused() -> None:
    base = score("sol-medium", "r-sol", [module("CP-0", ["match"], True)])
    runs: Runs = [(meta(), [call()])]
    for field, value in (
        ("config_id", "opus-medium"),
        ("case_id", "other-case"),
        ("pathway", "credit_snapshot"),
    ):
        bad = base.model_copy(update={field: value})
        with pytest.raises(ValueError, match=field):
            render_report([bad], runs, [])


def test_scores_of_one_pathway_share_a_case() -> None:
    one = score("sol-medium", "r-sol", [module("CP-0", ["match"], True)])
    two = score("opus-medium", "r-op", [module("CP-0", ["match"], True)], mode="offline")
    two = two.model_copy(update={"case_id": "other-case"})
    other_meta = meta("opus-medium", "r-op", "offline").model_copy(update={"case_id": "other-case"})
    runs: Runs = [(meta(), [call()]), (other_meta, [call("opus-medium", "r-op")])]
    with pytest.raises(ValueError, match="case_id"):
        render_report([one, two], runs, [])


def _accuracy_cell(text: str, config_id: str) -> str:
    row = next(line for line in text.splitlines() if line.startswith(f"| {config_id} |"))
    return row.split("|")[2].strip()


def test_stopped_runs_get_no_accuracy_figure_in_totals() -> None:
    # opus-medium: its only run stopped; the golden-missing pass (gap_ok) would read 2/2 = 100.0%; two modules, one run, so it counts 1 stopped.
    stopped = score(
        "opus-medium",
        "r-op",
        [module("CP-0", ["gap_ok"], True), module("CP-1A", ["gap_ok"], True)],
        stopped="budget",
    )
    # sol-medium: earnings_update settled (match, mismatch = 1/2); credit_snapshot stopped
    # (match, match = 2/2 that must not count).
    settled = score("sol-medium", "r-sol", [module("CP-0", ["match", "mismatch"], False)])
    mixed_stopped = score(
        "sol-medium", "r-sol2", [module("CP-0", ["match", "match"], True)], stopped="budget"
    ).model_copy(update={"pathway": "credit_snapshot"})
    runs: Runs = [
        (meta("opus-medium", "r-op", stopped="budget"), [call("opus-medium", "r-op")]),
        (meta(run_id="r-sol"), [call()]),
        (
            meta(run_id="r-sol2", stopped="budget").model_copy(
                update={"pathway": "credit_snapshot"}
            ),
            [call(run_id="r-sol2")],
        ),
    ]
    text = render_report([stopped, settled, mixed_stopped], runs, [])
    assert _accuracy_cell(text, "opus-medium") == "n/a (1 stopped)"
    assert _accuracy_cell(text, "sol-medium") == "50.0% (1/2); 1 stopped"


def test_report_applies_user_settlements_to_spend() -> None:
    # sol-medium: one unknown call reserved 0.37, settled by the user at 0.0151735 -> $0.02.
    # sol-high: one unknown call reserved 0.37, not settled -> "$0.37 reserved".
    # openai Spend = 0.0151735 + 0.37 = 0.3851735 -> $0.39; usable = 130 * 0.9 = 117.00;
    # Remaining = 117 - 0.3851735 = 116.6148265 -> $116.61.
    settlement = Settlement(
        run_id="r-sol",
        module_id="CP-0",
        step_id="s1",
        attempt=0,
        call_index=0,
        settled_usd=Decimal("0.0151735"),
        by="user",
        date="2026-11-02",
        source="provider dashboard",
    )
    scores = [
        score("sol-medium", "r-sol", [module("CP-0", ["match"], True)]),
        score("sol-high", "r-high", [module("CP-0", ["match"], True)]),
    ]
    runs: Runs = [
        (meta(), [call(settled=None, reserved="0.37", run_id="r-sol")]),
        (
            meta("sol-high", "r-high"),
            [call("sol-high", "r-high", settled=None, reserved="0.37")],
        ),
    ]
    text = render_report(scores, runs, [], (settlement,))
    totals = {
        line.split("|")[1].strip(): line.split("|")[3].strip()
        for line in text.splitlines()
        if line.startswith(("| sol-medium |", "| sol-high |"))
    }
    assert totals["sol-medium"] == "$0.02"
    assert totals["sol-high"] == "$0.37 reserved"
    assert "| openai | $0.39 | $117.00 | $116.61 |" in text
